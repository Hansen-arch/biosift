"""
BioSift — Batch Comparison page
"""

import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import utils.theme as T
from utils.theme import C
from utils.gbif_fetch import fetch_occurrences
from utils.quality import (
    run_quality_checks, quality_summary, get_completeness_score,
)
from utils.reliability import compute_reliability_score
from utils.bdq import bdq_meta


def fix_species_name(name):
    name = name.strip()
    if not name:
        return name, False
    parts = name.split()
    corrected = " ".join(
        [parts[0].capitalize()] + [p.lower() for p in parts[1:]]
    )
    return corrected, corrected != name


def parse_species_list(raw_text):
    if not raw_text.strip():
        return []
    parts = re.split(r"[,\n]+", raw_text)
    result = []
    for name in parts:
        fixed, _ = fix_species_name(name)
        if fixed:
            result.append(fixed)
    seen = []
    for n in result:
        if n not in seen:
            seen.append(n)
    return seen[:5]


def render():
    T.inject_css()
    T.page_head(
        "Batch Comparison",
        "Compare data quality across up to five species side by side."
    )

    st.markdown(
        '<p class="field-label">Species to compare</p>',
        unsafe_allow_html=True,
    )
    st.caption("Separate names by comma or new line.")
    batch_input = st.text_area(
        "species",
        placeholder="Panthera leo, Loxodonta africana\nDanaus plexippus",
        height=110, label_visibility="collapsed",
    )
    if batch_input.strip():
        preview = parse_species_list(batch_input)
        if preview:
            st.caption(
                "Will compare: " + " · ".join(f"*{n}*" for n in preview)
            )

    c1, c2 = st.columns(2)
    with c1:
        batch_year_from = st.number_input(
            "From", min_value=1000, max_value=2026, value=1900,
            key="batch_year_from",
        )
    with c2:
        batch_year_to = st.number_input(
            "To", min_value=1000, max_value=2026, value=2026,
            key="batch_year_to",
        )
    batch_limit = st.slider(
        "Records per species", 50, 500, 200, step=50, key="batch_limit",
    )
    if batch_limit > 400:
        st.warning(
            f"{batch_limit} × 5 species = up to {batch_limit * 5:,} records "
            f"— this will be slow. 200 or fewer recommended."
        )

    if st.button("Compare Species", type="primary", use_container_width=True):
        _run_batch(parse_species_list(batch_input), int(batch_year_from),
                   int(batch_year_to), batch_limit)

    if "batch_results" in st.session_state:
        _render_results()
    T.footer()


def _run_batch(species_list, yr_from, yr_to, limit):
    if not species_list:
        st.warning("Enter at least one species name.")
        return

    prog = st.progress(0, text="Starting batch analysis…")
    results = []
    for i, sp in enumerate(species_list):
        prog.progress(i / len(species_list), text=f"Analysing {sp}…")
        try:
            df_sp, total_sp, err = fetch_occurrences(
                species_name=sp, limit=limit,
                year_from=yr_from, year_to=yr_to,
            )
            if err or df_sp is None:
                results.append(_error_row(sp, err or "No data"))
                continue

            fl = run_quality_checks(df_sp)
            sm = quality_summary(fl)
            rel = compute_reliability_score(df_sp)
            cs = get_completeness_score(df_sp)
            clean = int((~fl["any_flag"]).sum())
            health = round(clean / len(fl) * 100, 1) if len(fl) else 0

            results.append({
                "species": sp, "error": None,
                "total": total_sp, "analysed": len(df_sp),
                "health": health,
                "completeness": cs["avg_score"] if cs else None,
                "duplicates": sm.get("duplicate", {}).get("percent", 0),
                "missing_coords":
                    sm.get("missing_coords", {}).get("percent", 0),
                "low_precision":
                    sm.get("low_precision", {}).get("percent", 0),
                "country_mismatch":
                    sm.get("country_mismatch", {}).get("percent", 0),
                "avg_reliability": round(float(rel.mean()), 1),
            })
        except Exception as e:
            results.append(_error_row(sp, str(e)))

    prog.progress(1.0, text="Done!")
    prog.empty()
    st.session_state["batch_results"] = results
    st.session_state["batch_used"] = {
        "from": yr_from, "to": yr_to, "limit": limit,
    }


def _error_row(sp, err):
    return {
        "species": sp, "error": err, "total": 0, "analysed": 0,
        "health": None, "completeness": None, "duplicates": None,
        "missing_coords": None, "low_precision": None,
        "country_mismatch": None, "avg_reliability": None,
    }


def _render_results():
    results = st.session_state["batch_results"]
    used = st.session_state.get("batch_used", {})
    ok = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]

    st.caption(
        f"Year range {used.get('from', '—')}–{used.get('to', '—')} · "
        f"{used.get('limit', '—')} records per species"
    )
    for f in failed:
        st.warning(f"Could not fetch **{f['species']}**: {f['error']}")

    if not ok:
        return

    T.section("Health score comparison")
    cols = st.columns(len(ok))
    for i, r in enumerate(ok):
        cls = "good" if r["health"] >= 80 else (
            "fair" if r["health"] >= 50 else "poor"
        )
        cols[i].markdown(f"""
        <div class="card" style="text-align:center">
            <div class="compare-species" style="font-size:0.82rem;
                 font-style:italic;color:{C['text_dim']};
                 white-space:nowrap;overflow:hidden;
                 text-overflow:ellipsis">{r['species']}</div>
            <div class="score-big t-{cls}"
                 style="font-size:1.9rem">{r['health']}%</div>
            <div class="metric-note">{r['analysed']:,} analysed ·
                 {r['total']:,} in GBIF</div>
        </div>
        """, unsafe_allow_html=True)

    T.section("Full comparison table")
    rows = []
    for r in ok:
        rows.append({
            "Species": r["species"],
            "GBIF total": f"{r['total']:,}",
            "Analysed": f"{r['analysed']:,}",
            "Health": f"{r['health']}%",
            "Completeness":
                f"{r['completeness']}%" if r["completeness"] is not None else "—",
            "Duplicates": f"{r['duplicates']}%",
            "Missing coords": f"{r['missing_coords']}%",
            "Low precision": f"{r['low_precision']}%",
            "Country mismatch": f"{r['country_mismatch']}%",
            "Avg reliability":
                f"{r['avg_reliability']}/100"
                if r["avg_reliability"] is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True,
                 hide_index=True)
    st.caption(
        "Checks mapped to TDWG BDQ: "
        + bdq_meta("duplicate")[0] + " · "
        + bdq_meta("missing_coords")[0]
    )

    T.section("Visual comparison")
    metrics = ["health", "completeness", "duplicates", "missing_coords",
               "low_precision", "country_mismatch"]
    labels = ["Health", "Completeness", "Duplicates %", "Missing coords %",
              "Low precision %", "Country mismatch %"]
    palette = [C["accent"], C["blue"], C["orange"], C["violet"],
               C["amber"], C["red"]]

    fig = go.Figure()
    for i, r in enumerate(ok):
        fig.add_trace(go.Bar(
            name=r["species"], x=labels,
            y=[r.get(m) or 0 for m in metrics],
            marker_color=palette[i % len(palette)],
            text=[f"{r.get(m) or 0}%" for m in metrics],
            textposition="outside", textfont=dict(size=10),
        ))
    fig.update_layout(
        barmode="group", yaxis=dict(range=[0, 120]), height=430,
    )
    st.plotly_chart(T.style_fig(fig, height=430), use_container_width=True)

    st.download_button(
        "Download Comparison (CSV)",
        data=pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
        file_name="biosift_batch_comparison.csv", mime="text/csv",
    )
