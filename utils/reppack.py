"""
Reproducibility Pack
────────────────────
One click produces a reviewer-ready ZIP:
  biosift_report.json    — run metadata, scores, per-check BDQ results
  methods.txt            — paste-ready methods paragraph
  citations.txt          — APA + BibTeX for the GBIF-mediated data
  data_full.csv          — analysed sample, export-friendly
  data_clean.csv         — quality-filtered subset
  dwca_occurrence.zip    — standards-compliant Darwin Core Archive
  recipe.json            — exact GBIF API calls to regenerate the sample
  README.txt             — what this pack is and how to reuse it
"""

import json
import datetime
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from utils.bdq import bdq_meta, citation_note
from utils.dwc import build_dwca
from utils.reliability import generate_methods_text, generate_citation


def _export_df(df, score):
    """Flatten media/issue lists and stamp provenance metadata columns."""
    export = df.copy()
    if "media" in export.columns:
        def extract_image_url(ml):
            if isinstance(ml, list):
                for item in ml:
                    if isinstance(item, dict):
                        url = item.get("identifier", "")
                        if url and url.startswith("http"):
                            return url
            return ""
        pos = export.columns.get_loc("media")
        export.insert(pos, "image_url", export["media"].apply(extract_image_url))
        export = export.drop(columns=["media"])
    if "issues" in export.columns:
        export["issues"] = export["issues"].apply(
            lambda x: "; ".join(str(i) for i in x)
            if isinstance(x, list) and len(x) > 0 else ""
        )
    export["biosift_health_score"] = score
    return export


def build_recipe_requests(species, filters):
    """Reconstruct the exact GBIF API calls used for this analysis."""
    req = {
        "method": "GET",
        "url": "https://api.gbif.org/v1/occurrence/search",
        "params": {
            "scientificName": species,
            "limit": 300,
            "offset": "<paginate: 0,300,600,... until endOfRecords>",
        },
    }
    if filters:
        if filters.get("year_from") and filters.get("year_to"):
            req["params"]["year"] = (
                f"{filters['year_from']},{filters['year_to']}"
            )
        if filters.get("basis") and filters["basis"] != "All":
            req["params"]["basisOfRecord"] = filters["basis"]
        if filters.get("country_code"):
            req["params"]["country"] = filters["country_code"]
    return req


def build_reppack(
    df, clean_df, species, score, summary,
    reliability=None, completeness=None, benchmark=None,
    species_info=None, filters=None, fitness=None, interactions=None,
):
    """Return (bytes, None) of the Reproducibility Pack ZIP, or (None, error)."""
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── biosift_report.json ────────────────────────────
        report = {
            "schema": "biosift.report/1.0",
            "generated": iso,
            "tool": {
                "name": "BioSift",
                "url": "https://biosift-gbif.streamlit.app",
                "version": "2.0",
            },
            "species": {
                "scientific_name": species,
                "gbif_taxon_key": (
                    species_info.get("key") if species_info else None
                ),
                "iucn_category": (
                    species_info.get("iucn", "") if species_info else ""
                ),
            },
            "filters": filters or {},
            "scores": {
                "health_pct": score,
                "records_sampled": int(len(df)),
                "records_clean": int(len(clean_df)),
                "gbif_total_matching": (
                    filters.get("gbif_total") if filters else None
                ),
            },
            "quality_checks": [
                {
                    "check": k,
                    "label": bdq_meta(k)[1],
                    "bdq_test": bdq_meta(k)[0],
                    "flagged": int(summary.get(k, {}).get("count", 0)),
                    "percent": summary.get(k, {}).get("percent", 0),
                }
                for k in summary.keys()
                if k not in ("any_flag", "has_issues")
            ],
            "reliability": {
                "mean": (
                    round(float(reliability.mean()), 1)
                    if reliability is not None else None
                ),
            },
            "completeness": {
                "mean": completeness.get("avg_score") if completeness else None,
            },
            "benchmark": benchmark or [],
            "sdm_readiness": {
                "verdict": fitness.get("verdict"),
                "profile": fitness.get("profile"),
                "ready_records": fitness.get("ready_records"),
                "retention_pct": fitness.get("retention_pct"),
                "gates": fitness.get("gates"),
                "citations": fitness.get("citations"),
            } if fitness else None,
            "interactions": {
                "source": "GloBI — globalbioticinteractions.org",
                "count": len(interactions),
                "records": interactions[:100],
            } if interactions is not None else None,
            "standards": {
                "quality_tests": citation_note(),
                "data_standard": "Darwin Core — https://dwc.tdwg.org",
            },
        }
        report_json = json.dumps(report, indent=2)

        # ── methods + citations ────────────────────────────
        methods_txt = generate_methods_text(
            species, df, clean_df, summary, score
        )
        cite = generate_citation(species, df, species_info=species_info)
        citations_txt = cite["apa"] + "\n\n" + cite["bibtex"]

        # ── data CSVs ──────────────────────────────────────
        csv_full = _export_df(df, score).to_csv(index=False)
        csv_clean = _export_df(clean_df, score).to_csv(index=False)

        # ── DwC-A (nested zip) ─────────────────────────────
        dwca, dwca_err = build_dwca(df, species, score, clean_only=False)

        # ── recipe.json ────────────────────────────────────
        recipe_json = json.dumps(
            {
                "schema": "biosift.recipe/1.0",
                "generated": iso,
                "source": (
                    "GBIF occurrence API — "
                    "https://www.gbif.org/developer/summary"
                ),
                "note": (
                    "Run these requests to regenerate the exact sample "
                    "analysed by BioSift. Paginate offset by 'limit' until "
                    "'endOfRecords' is true."
                ),
                "requests": build_recipe_requests(species, filters),
            },
            indent=2,
        )

        # ── README ─────────────────────────────────────────
        readme_txt = _readme(iso, species)

        # ── assemble the outer pack ────────────────────────
        buf = BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
            zf.writestr("biosift_report.json", report_json)
            zf.writestr("methods.txt", methods_txt)
            zf.writestr("citations.txt", citations_txt)
            zf.writestr("data_full.csv", csv_full)
            zf.writestr("data_clean.csv", csv_clean)
            if dwca:
                zf.writestr("dwca_occurrence.zip", dwca)
            elif dwca_err:
                zf.writestr("dwca_ERROR.txt", dwca_err)
            zf.writestr("recipe.json", recipe_json)
            zf.writestr("README.txt", readme_txt)

        return buf.getvalue(), None

    except Exception as e:
        return None, str(e)


def _readme(iso, species):
    return (
        "BioSift Reproducibility Pack\n"
        "============================\n"
        f"Generated: {iso}\n"
        f"Species:   {species}\n"
        "\n"
        "Contents\n"
        "--------\n"
        "biosift_report.json   Machine-readable run report (biosift.report/1.0)\n"
        "methods.txt           Paste-ready methods paragraph for manuscripts\n"
        "citations.txt         APA + BibTeX citations for the GBIF-mediated data\n"
        "data_full.csv         The analysed sample with provenance columns\n"
        "data_clean.csv        Quality-filtered subset (passes all checks)\n"
        "dwca_occurrence.zip   Darwin Core Archive (occurrence, meta.xml, eml.xml)\n"
        "recipe.json           Exact GBIF API requests to regenerate this sample\n"
        "\n"
        "Reuse\n"
        "-----\n"
        "- biosift_report.json is designed for ingestion into indicator\n"
        "  pipelines (e.g. B-Cubed style data cubes): stable keys, stable schema.\n"
        "- recipe.json makes the sample fully reproducible: anyone with\n"
        "  internet access can regenerate the identical input data.\n"
        "- The DwC-A is compatible with GBIF, iDigBio and ALA ingestion.\n"
        "\n"
        "Citation\n"
        "--------\n"
        "See citations.txt. GBIF-mediated data are shared under CC-BY;\n"
        "cite the contributing datasets and their publishers.\n"
    )
