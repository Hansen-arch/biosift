"""
BioSift Standalone API
──────────────────────
FastAPI wrapper around the framework-agnostic science layer in utils/.
Same checks, same standards, same outputs as the Streamlit app — no
Streamlit runtime required.

Run:
    uvicorn standalone.server:app --port 8080

Endpoints:
    GET  /api/health                 liveness + capability probe
    GET  /api/analysis/{species}     full analysis bundle (JSON)
    GET  /api/analysis/{species}/map folium map HTML (iframe-ready)
    GET  /                           MapLibre GL JS single-page frontend

CORS is open so the frontend can be served separately or from disk.
"""

import os
import sys

# ensure project root is importable regardless of launch cwd
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import numpy as np
import requests

from utils.gbif_fetch import fetch_occurrences
from utils.quality import (
    run_quality_checks, quality_summary, get_completeness_score,
    get_precision_stats, get_multimedia_stats,
)
from utils.species_info import get_species_info, iucn_chip
from utils.bdq import bdq_meta, citation_note
from utils.benchmark import fetch_population_stats, build_benchmark
from utils.fitness import audit_sdm_readiness, PROFILES
from utils.predict import run_distribution_metrics
from utils.carbon import estimate_carbon
from utils.interactions import fetch_interactions, summarize_interactions
from utils.cooccurrence import (
    fetch_genus_assemblage, build_cooccurrence, COO_CITATION,
)
from utils.maps import build_map
from utils.charts import get_temporal_stats

app = FastAPI(
    title="BioSift Standalone API",
    version="1.0",
    description=(
        "Biodiversity data-quality analysis over the GBIF occurrence API. "
        "Checks aligned with TDWG BDQ; benchmarking, SDM readiness "
        "(Zizka 2020 / Marcer 2022), distribution metrics and KBA "
        "Criterion B screening (IUCN 2016)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clean_records(df: pd.DataFrame, flags: pd.DataFrame | None = None,
                   limit=200):
    """JSON-safe row list from the analysed frame.

    When the flags frame is passed, each row also carries the BioSift
    BDQ verdict (biosift_flag / biosift_flags) so map colours and
    popups agree with the analysis tables instead of GBIF's benign
    `issues` column (COORDINATE_ROUNDED etc.).
    """
    out = []
    for i, (_, row) in enumerate(df.head(limit).iterrows()):
        rec = {}
        for col, val in row.items():
            if isinstance(val, float) and np.isnan(val):
                rec[col] = None
            elif isinstance(val, (list, dict)):
                rec[col] = str(val)[:200]
            elif isinstance(val, (np.integer,)):
                rec[col] = int(val)
            elif isinstance(val, (np.floating,)):
                rec[col] = None if np.isnan(val) else float(val)
            elif isinstance(val, (np.bool_,)):
                rec[col] = bool(val)
            else:
                rec[col] = val
        if flags is not None and i < len(flags):
            f = flags.iloc[i]
            rec["biosift_flag"] = bool(f["any_flag"])
            rec["biosift_flags"] = [
                c for c in flags.columns
                if c not in ("any_flag", "has_issues") and bool(f[c])
            ]
        out.append(rec)
    return out


@app.get("/api/health")
def health():
    try:
        r = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params={"limit": 0}, timeout=10,
        )
        gbif = "ok" if r.status_code == 200 else f"http {r.status_code}"
    except Exception as e:
        gbif = f"unreachable: {e}"
    return {"status": "ok", "service": "biosift-standalone",
            "version": "1.0", "gbif_api": gbif}


@app.get("/api/analysis/{species}")
def analysis(
    species: str,
    limit: int = Query(500, ge=50, le=5000),
    year_from: int = Query(1900, ge=1000, le=2026),
    year_to: int = Query(2026, ge=1000, le=2026),
    basis: str = Query("All"),
    fitness_profile: str = Query(
        "Standard (≤10 km, Zizka et al. 2020)"),
    include_records: bool = Query(False, description="embed row samples"),
):
    """
    Full analysis bundle for one species — the same pipeline the
    Streamlit app runs, as a single JSON document.
    """
    species = species.strip()
    if not species:
        raise HTTPException(400, "species required")

    df, total, err = fetch_occurrences(
        species_name=species, limit=limit,
        year_from=year_from, year_to=year_to, basis=basis,
    )
    if err or df is None:
        raise HTTPException(404, err or "no data")

    flags = run_quality_checks(df)
    summary = quality_summary(flags)
    clean_df = df[~flags["any_flag"]].reset_index(drop=True)
    score = round(len(clean_df) / len(df) * 100, 1) if len(df) else 0.0

    info = get_species_info(species) or {}
    pop = fetch_population_stats(
        species, year_range=f"{year_from},{year_to}", basis=basis
    )
    bench = []
    if pop:
        sample_stats = {
            "no_coords": round(float(flags["missing_coords"].mean()*100), 1),
            "no_year": round(float(flags["missing_year"].mean()*100), 1),
        }
        bench = build_benchmark(sample_stats, pop)

    profile = (fitness_profile if fitness_profile in PROFILES
               else list(PROFILES.keys())[0])
    fit = audit_sdm_readiness(df, flags, mode=profile)
    dist = run_distribution_metrics(
        df, iucn_category=info.get("iucn", "")
    )
    temporal = get_temporal_stats(df)
    completeness = get_completeness_score(df)
    interactions = fetch_interactions(species)
    i_by_type, i_partners = summarize_interactions(interactions)

    genus_df = fetch_genus_assemblage(
        species, year_from=year_from, year_to=year_to
    )
    coo = build_cooccurrence(species, df, genus_df, max_partners=8)
    carbon = estimate_carbon(
        df, species,
        family=info.get("family", ""),
        genus=info.get("genus", ""),
        kingdom=info.get("kingdom", ""),
    )

    bundle = {
        "schema": "biosift.analysis/1.1",
        "query": {
            "species": species, "limit": limit,
            "year_from": year_from, "year_to": year_to, "basis": basis,
        },
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "standards": {
            "quality_tests": citation_note(),
            "note": "Check labels carry TDWG BDQ test identifiers.",
        },
        "species": {
            "scientific_name": info.get("scientific_name", species),
            "common_names": info.get("common_names", []),
            "iucn_category": info.get("iucn", ""),
            "gbif_taxon_key": info.get("key"),
            "gbif_url": info.get("gbif_url"),
            "taxonomy": {
                k: info.get(k) for k in
                ("kingdom", "phylum", "class_", "order", "family", "genus")
            },
        },
        "scores": {
            "gbif_total_matching": total,
            "records_analysed": len(df),
            "records_clean": len(clean_df),
            "health_pct": score,
            "completeness_pct": (
                completeness["avg_score"] if completeness else None
            ),
        },
        "quality_checks": [
            {
                "check": k,
                "label": bdq_meta(k)[1],
                "bdq_test": bdq_meta(k)[0],
                "flagged": summary[k]["count"],
                "percent": summary[k]["percent"],
            }
            for k in summary if k not in ("any_flag", "has_issues")
        ],
        "benchmark": bench,
        "sdm_readiness": fit,
        "distribution_kba": dist,
        "temporal": temporal,
        "year_counts": (
            [
                {"year": int(r["year"]), "count": int(r["count"])}
                for _, r in df[df["year"].notna()]
                .assign(year=lambda x: x["year"].astype(int))
                .groupby("year").size().reset_index(name="count")
                .iterrows()
            ] or None
        ),
        "interactions": {
            "source": "GloBI — globalbioticinteractions.org",
            "total": len(interactions),
            "by_type": i_by_type,
            "top_partners": i_partners[:15],
        },
        "cooccurrence": {
            "genus": coo["genus"],
            "assemblage_size": coo["assemblage_size"],
            "method": COO_CITATION,
            "partners": coo["partners"],
        },
        "carbon": carbon,
        "precision_stats": get_precision_stats(df),
        "multimedia": get_multimedia_stats(df),
        "records": (
            {"analysed": _clean_records(df, flags),
             "clean": _clean_records(clean_df)}
            if include_records else None
        ),
    }
    return JSONResponse(bundle)


# ────────────────────────────────────────── bring-your-own-data (BYOD)

@app.post("/api/upload/inspect")
async def upload_inspect(file: UploadFile = File(...)):
    """Read an uploaded file and propose a column mapping.

    Metadata only — no analysis. The frontend shows the proposed
    mapping for user confirmation (review step, like GBIF IPT).
    """
    from standalone import byod
    try:
        raw = await file.read()
        df_raw = byod.read_any(file.filename, raw)
    except Exception as e:
        raise HTTPException(400, f"could not read file: {e}")
    if df_raw.empty:
        raise HTTPException(400, "file contains no data rows")
    df_mapped, applied = byod.map_columns(df_raw)
    present = [c for c in byod.CANONICAL if c in df_mapped.columns]
    missing = [c for c in byod.CANONICAL
               if c not in df_mapped.columns
               and c in ("species", "decimalLatitude", "decimalLongitude",
                         "year")]
    nrows = len(df_raw)
    col_stats = {}
    for c in df_raw.columns:
        s = df_raw[c]
        st = {
            "filled_pct": round(float(s.notna().mean()) * 100, 1)
            if nrows else 0.0,
            "distinct": int(s.nunique(dropna=True)),
            "kind": "numeric" if pd.api.types.is_numeric_dtype(s)
            else "text",
        }
        if st["kind"] == "text":
            vals = s.dropna().astype(str).unique()[:3]
            st["sample"] = [v[:32] for v in vals]
        col_stats[str(c)] = st
    return {
        "filename": file.filename,
        "rows": nrows,
        "columns": list(df_raw.columns),
        "col_stats": byod._jsonify(col_stats),
        "sample_rows": byod._jsonify(
            df_raw.head(3).astype(object).where(
                pd.notna(df_raw.head(3)), None).to_dict("records")),
        "proposed_mapping": applied,
        "core_present": present,
        "core_missing": missing,
        "needs_mapping": len(missing) > 0,
    }


@app.post("/api/upload/analyze")
async def upload_analyze(
    file: UploadFile = File(...),
    mapping: str = Form(None),
    dataset_name: str = Form(""),
    profile: str = Form("General"),
):
    """Full analysis of an uploaded dataset (same science layer as
    the species endpoint + geographic tests + name verification)."""
    from standalone import byod
    try:
        raw = await file.read()
        df_raw = byod.read_any(file.filename, raw)
    except Exception as e:
        raise HTTPException(400, f"could not read file: {e}")
    import json as _json
    mapping_dict = None
    if mapping:
        try:
            mapping_dict = _json.loads(mapping)
        except Exception:
            raise HTTPException(400, "mapping must be valid JSON")
    try:
        bundle = byod.analyze_uploaded(
            df_raw, mapping=mapping_dict,
            dataset_name=dataset_name or file.filename,
            profile=profile)
        return bundle
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"analysis failed: {e}")


@app.post("/api/upload/export")
async def upload_export(
    file: UploadFile = File(...),
    mapping: str = Form(None),
    profile: str = Form("General"),
    mode: str = Form("flagged"),
):
    """The user's own dataset back, with BioSift verdict columns.

    mode=flagged keeps every row and appends biosift_flag /
    biosift_exclude / biosift_reasons; mode=clean returns only rows
    passing the fit-for-use profile.
    """
    from standalone import byod
    try:
        raw = await file.read()
        df_raw = byod.read_any(file.filename, raw)
    except Exception as e:
        raise HTTPException(400, f"could not read file: {e}")
    import json as _json
    mapping_dict = None
    if mapping:
        try:
            mapping_dict = _json.loads(mapping)
        except Exception:
            raise HTTPException(400, "mapping must be valid JSON")
    try:
        csv_text = byod.cleaned_csv(df_raw, mapping_dict,
                                    profile=profile, mode=mode)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"export failed: {e}")
    stem = (file.filename or "dataset").rsplit(".", 1)[0] or "dataset"
    fname = f"biosift_{stem}_{mode}.csv"
    return JSONResponse(
        content={"filename": fname, "csv": csv_text},
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/analysis/{species}/map")
def analysis_map(
    species: str,
    limit: int = Query(500, ge=50, le=2000),
    year_from: int = Query(1900, ge=1000, le=2026),
    year_to: int = Query(2026, ge=1000, le=2026),
    basis: str = Query("All"),
    mode: str = Query("points", pattern="^(points|heatmap)$"),
):
    """Folium occurrence map as standalone HTML (iframe-ready)."""
    df, total, err = fetch_occurrences(
        species_name=species.strip(), limit=limit,
        year_from=year_from, year_to=year_to, basis=basis,
    )
    if err or df is None:
        raise HTTPException(404, err or "no data")
    flags = run_quality_checks(df)
    m = build_map(df, flags, map_type=mode)
    return HTMLResponse(m.get_root().render())


from standalone import frontend  # noqa: E402  (local module)


@app.get("/", response_class=HTMLResponse)
def index():
    return frontend.PAGE
