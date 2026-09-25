"""
BioSift — Species Analysis page
"""

import streamlit as st
import pandas as pd
import requests

import utils.theme as T
from utils.theme import C
from utils.gbif_fetch import fetch_occurrences, SAMPLE_SPECIES
from utils.species_info import get_species_info, iucn_chip
from utils.quality import (
    run_quality_checks, quality_summary, get_precision_stats,
    get_multimedia_stats, get_completeness_score,
)
from utils.maps import build_map
from utils.outliers import detect_outliers, outlier_summary
from utils.sdm import build_sdm_map
from utils.reliability import (
    compute_reliability_score, get_data_fitness,
)
from utils.gaps import build_gap_map, get_gap_stats, get_gap_alerts
from utils.charts import (
    chart_records_per_year, chart_records_per_month,
    chart_basis_of_record, chart_top_countries, chart_country_density,
    chart_decade_breakdown, get_temporal_stats, get_recommendations,
)
from utils.dataset_quality import get_dataset_quality_breakdown
from utils.bdq import bdq_meta, citation_note
from utils.benchmark import fetch_population_stats, build_benchmark
from utils.reppack import build_reppack
from utils.pdf_report import build_pdf_report
from utils.cube import cube_exports


def score_class(score):
    if score >= 80:
        return "good"
    if score >= 50:
        return "fair"
    return "poor"


def fix_species_name(name):
    name = name.strip()
    if not name:
        return name, False
    parts = name.split()
    corrected = " ".join(
        [parts[0].capitalize()] + [p.lower() for p in parts[1:]]
    )
    return corrected, corrected != name


def clear_results():
    for key in [
        "df", "total", "species", "flags", "summary", "outliers",
        "reliability", "species_info", "multimedia", "completeness",
        "pop_stats", "year_from", "year_to", "basis_filter", "limit",
    ]:
        st.session_state.pop(key, None)


def render():
    T.inject_css()
    T.page_head(
        "Species Analysis",
        "Live quality audit of any GBIF species — standards-aligned, "
        "benchmarked, export-ready."
    )

    # ── inputs ─────────────────────────────────────────────
    sample_options = ["— select a sample —"] + list(SAMPLE_SPECIES.values())
    sample_choice = st.selectbox("Sample species", sample_options)

    species_raw = st.text_input(
        "Scientific name",
        placeholder="e.g. Panthera leo",
    )
    species_input = species_raw.strip()
    if species_input:
        species_input, was_fixed = fix_species_name(species_input)
        if was_fixed:
            st.warning(
                f"Auto-corrected to **{species_input}** — genus capitalised, "
                f"species epithet lowercase."
            )

    if sample_choice != "— select a sample —" and not species_raw.strip():
        species_input = sample_choice
        st.caption(f"Using sample: *{species_input}*")

    c1, c2 = st.columns(2)
    with c1:
        year_from = st.number_input(
            "Year from", min_value=1000, max_value=2026, value=1900
        )
    with c2:
        year_to = st.number_input(
            "Year to", max_value=2026, min_value=1000, value=2026
        )

    basis_filter = st.selectbox(
        "Basis of record",
        ["All", "HUMAN_OBSERVATION", "PRESERVED_SPECIMEN",
         "MACHINE_OBSERVATION", "LIVING_SPECIMEN", "LITERATURE",
         "FOSSIL_SPECIMEN"],
    )
    limit = st.slider("Max records", 100, 10000, 500, step=100)

    map_type = st.radio(
        "Map type",
        ["Point Map", "Heatmap", "DBSCAN Outliers", "SDM Preview"],
        key="map_type",
        horizontal=True,
    )

    run_btn = st.button("Run Analysis", type="primary",
                        use_container_width=True)
    if "df" in st.session_state:
        if st.button("Clear Results", use_container_width=True):
            clear_results()
            st.rerun()

    if run_btn:
        if not species_input:
            st.warning("Please enter a scientific name or select a sample.")
        else:
            _run_analysis(species_input, int(year_from), int(year_to),
                          basis_filter, limit)

    # ── results ────────────────────────────────────────────
    if "df" in st.session_state and st.session_state.get("species"):
        _render_results()


def _run_analysis(species_input, year_from, year_to, basis_filter, limit):
    progress = st.progress(0, text="Connecting to GBIF…")

    try:
        pre = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params={"scientificName": species_input, "limit": 1},
            timeout=10,
        ).json()
        if pre.get("count", 0) == 0:
            progress.empty()
            clear_results()
            st.error(
                f"No occurrence records found for *{species_input}* in GBIF."
            )
            st.stop()
    except Exception:
        pass

    df, total, error = fetch_occurrences(
        species_name=species_input, limit=limit,
        year_from=year_from, year_to=year_to, basis=basis_filter,
    )
    if error:
        progress.empty()
        clear_results()
        st.error(error)
        st.stop()

    progress.progress(0.4, text="Running quality checks…")
    flags = run_quality_checks(df)
    summary = quality_summary(flags)

    progress.progress(0.6, text="Detecting outliers & benchmarking…")
    outliers = detect_outliers(df)
    reliability = compute_reliability_score(df)

    yr = f"{year_from},{year_to}"
    pop_stats = fetch_population_stats(
        species_input, year_range=yr, basis=basis_filter
    )

    progress.progress(0.8, text="Fetching species info…")
    species_info = get_species_info(species_input)
    multimedia = get_multimedia_stats(df)
    completeness = get_completeness_score(df)

    progress.progress(1.0, text="Done!")
    progress.empty()

    st.session_state.update({
        "df": df, "total": total, "species": species_input,
        "flags": flags, "summary": summary, "outliers": outliers,
        "reliability": reliability, "species_info": species_info,
        "multimedia": multimedia, "completeness": completeness,
        "pop_stats": pop_stats,
        "year_from": year_from, "year_to": year_to,
        "basis_filter": basis_filter, "limit": limit,
    })


def _render_results():
    df = st.session_state["df"]
    total = st.session_state["total"]
    flags = st.session_state["flags"]
    summary = st.session_state["summary"]
    species = st.session_state["species"]
    outliers = st.session_state.get("outliers")
    reliability = st.session_state.get("reliability")
    species_info = st.session_state.get("species_info")
    multimedia = st.session_state.get("multimedia")
    completeness = st.session_state.get("completeness")
    pop_stats = st.session_state.get("pop_stats", {})
    yr_from = st.session_state.get("year_from", 1900)
    yr_to = st.session_state.get("year_to", 2026)
    basis_used = st.session_state.get("basis_filter", "All")
    map_type = st.session_state.get("map_type", "Point Map")

    clean_df = df[~flags["any_flag"]].reset_index(drop=True)
    clean = len(clean_df)
    score = round(clean / len(flags) * 100, 1) if len(flags) else 0

    # ── species header card ────────────────────────────────
    hc = st.columns([1, 3])
    with hc[0]:
        if species_info and species_info.get("image_url"):
            st.image(species_info["image_url"], use_container_width=True)
        else:
            st.markdown(
                '<div style="width:110px;height:110px;border-radius:14px;'
                f'background:{C["card"]};border:1px solid {C["line"]};'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:2.4rem">🌿</div>',
                unsafe_allow_html=True,
            )
    with hc[1]:
        name_html = (
            f"<i>{species_info['scientific_name']}</i>"
            if species_info else f"<i>{species}</i>"
        )
        chips = []
        if species_info and species_info.get("common_names"):
            chips.append(species_info["common_names"][0])
        chip_html = (
            f'<span style="font-size:0.85rem;color:{C["text_dim"]}">'
            f'{", ".join(species_info["common_names"])}</span>'
            if species_info and species_info.get("common_names") else ""
        )
        iucn = iucn_chip(species_info.get("iucn")) if species_info else None
        iucn_html = ""
        if iucn:
            code, colour, tip = iucn
            iucn_html = (
                f'<span class="iucn" style="background:{colour}" '
                f'title="{tip}">IUCN {code}</span>'
            )
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.7rem;flex-wrap:wrap">
            <span style="font-family:'Fraunces',Georgia,serif;font-size:1.5rem;
                         font-weight:700;color:{C['text']}">{name_html}</span>
            {iucn_html}
        </div>
        {chip_html}
        """, unsafe_allow_html=True)

        if species_info:
            tax = [
                ("Kingdom", species_info.get("kingdom", "—")),
                ("Phylum", species_info.get("phylum", "—")),
                ("Class", species_info.get("class_", "—")),
                ("Order", species_info.get("order", "—")),
                ("Family", species_info.get("family", "—")),
                ("Genus", species_info.get("genus", "—")),
            ]
            tcols = st.columns(6)
            for i, (rank, val) in enumerate(tax):
                with tcols[i]:
                    st.markdown(
                        f'<div class="tax"><div class="tax-r">{rank}</div>'
                        f'<div class="tax-v">{val}</div></div>',
                        unsafe_allow_html=True,
                    )
            st.markdown(
                f'[View on GBIF]({species_info["gbif_url"]}) · '
                f'[GBIF occurrences](https://www.gbif.org/occurrence/search?'
                f'taxon_key={species_info["key"]})'
            )

    # ── filter banner ──────────────────────────────────────
    filter_parts = []
    if yr_from != 1900 or yr_to != 2026:
        filter_parts.append(f"Year {yr_from}–{yr_to}")
    if basis_used != "All":
        filter_parts.append(f"Basis: {basis_used}")
    if filter_parts:
        st.info(
            f"Active filters — {' · '.join(filter_parts)}. "
            f"All statistics reflect the filtered sample only."
        )

    # ── metric row ─────────────────────────────────────────
    m = st.columns(4)
    metric_card = T.metric_card
    metric_card("GBIF records matching", f"{total:,}",
                "full filtered population", col=m[0])
    metric_card("Sample analysed", f"{len(df):,}", "live from GBIF API",
                col=m[1])
    metric_card("Clean records", f"{clean:,}", f"{score}% pass all checks",
                col=m[2])
    metric_card("Mean reliability", (
        f"{round(float(reliability.mean()), 1)}/100"
        if reliability is not None else "—"
    ), "per-record evidence score", col=m[3])

    st.divider()

    # ── benchmark strip ────────────────────────────────────
    if pop_stats:
        T.section("Benchmark vs GBIF-wide population")
        sample_stats = {
            "no_coords": round(
                float(flags["missing_coords"].mean() * 100), 1
            ),
            "no_year": round(
                float(flags["missing_year"].mean() * 100), 1
            ),
        }
        bench = build_benchmark(sample_stats, pop_stats)
        if bench:
            bc = st.columns(len(bench))
            for i, b in enumerate(bench):
                tone = {"better": "ok", "worse": "bad",
                        "similar": ""}.get(b["verdict"], "")
                arrow = {"better": "▲", "worse": "▼",
                         "similar": "◆"}.get(b["verdict"], "")
                sign = "+" if b["delta"] > 0 else ""
                bc[i].markdown(f"""
                <div class="metric">
                    <div class="metric-label">{b['label']}</div>
                    <div class="metric-value">{b['sample_pct']}%
                        <span style="font-size:0.85rem;font-weight:600;
                        color:{C['text_dim']}">vs {b['population_pct']}%</span>
                    </div>
                    <div class="metric-note">{arrow} {sign}{b['delta']} pp
                        vs GBIF-wide · {b['verdict']}</div>
                </div>
                """, unsafe_allow_html=True)
            st.caption(
                f"Baseline: {pop_stats.get('total', 0):,} GBIF records "
                f"matching the same species + filters. Negative delta = "
                f"fewer defects than the global population (better)."
            )

    # ── tabs ───────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Overview", "Occurrence Map", "Temporal", "Charts",
        "Gap Analysis", "Data & Export",
    ])

    with tab1:
        _tab_overview(df, flags, summary, score, completeness, multimedia,
                      outliers, reliability, clean_df)

    with tab2:
        _tab_map(df, flags, outliers, map_type)

    with tab3:
        _tab_temporal(df, yr_from, yr_to)

    with tab4:
        _tab_charts(df)

    with tab5:
        _tab_gaps(df)

    with tab6:
        _tab_export(df, clean_df, flags, summary, score, species,
                    reliability, completeness, species_info, yr_from,
                    yr_to, basis_used, total, pop_stats)

    T.footer()


def _tab_overview(df, flags, summary, score, completeness, multimedia,
                  outliers, reliability, clean_df):
    col_l, col_r = st.columns([1.15, 1])

    with col_l:
        T.score_hero("Data Health Score", score)

        if completeness:
            cs = completeness["avg_score"]
            T.score_hero("Record Completeness", cs)
            st.caption(
                f"{completeness['full_count']:,} fully complete · "
                f"{completeness['high_count']:,} at 80%+ · "
                f"{completeness['low_count']:,} below 50%"
            )

        T.section("Quality checks — TDWG BDQ aligned")
        rows = []
        for k in summary:
            if k in ("any_flag", "has_issues"):
                continue
            name = bdq_meta(k)[1]
            bdq = bdq_meta(k)[0]
            stats = summary[k]
            tone = "ok" if stats["count"] == 0 else (
                "warn" if stats["percent"] < 10 else "bad"
            )
            rows.append({
                "Check": name,
                "TDWG BDQ test": bdq,
                "Flagged": stats["count"],
                "%": f"{stats['percent']}%",
                "Status": tone,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True,
                     hide_index=True)
        st.caption(citation_note())

        if "has_issues" in summary and summary["has_issues"]["count"] > 0:
            T.alert(
                "info",
                "GBIF internal flags",
                f"{summary['has_issues']['count']} records carry GBIF's own "
                f"interpretation flags — informational, not all imply "
                f"unusable data.",
            )

        if outliers is not None:
            out_stats = outlier_summary(outliers)
            T.section("DBSCAN spatial outliers")
            o1, o2 = st.columns(2)
            T.metric_card("Spatial outliers",
                          f"{out_stats['outliers']:,}", col=o1)
            T.metric_card("Outlier share",
                          f"{out_stats['outlier_pct']}%", col=o2)

        T.section("Multimedia quality")
        if multimedia:
            m1, m2, m3 = st.columns(3)
            T.metric_card("Media coverage",
                          f"{multimedia['coverage_pct']}%", col=m1)
            T.metric_card("Missing media",
                          f"{multimedia['missing_media']:,}", col=m2)
            T.metric_card("Broken URLs (sampled)",
                          f"{multimedia['broken_urls']}", col=m3)
            if multimedia["broken_pct"] > 20:
                T.alert("warn", "Image URLs failing",
                        f"{multimedia['broken_pct']}% of sampled image URLs "
                        f"are inaccessible.")
            elif multimedia["coverage_pct"] < 20:
                T.alert("info", "Sparse multimedia",
                        f"Only {multimedia['coverage_pct']}% of records have "
                        f"images attached.")
            else:
                T.alert("success", "Good multimedia coverage",
                        f"{multimedia['coverage_pct']}% of records include "
                        f"images.")
        else:
            st.info("Multimedia data not available.")

    with col_r:
        temporal_stats = get_temporal_stats(df)
        fitness = get_data_fitness(score, summary, temporal_stats)
        T.section("Data fitness for use")
        st.caption("Judged on the currently fetched + filtered sample.")
        for f in fitness:
            b = T.badge(
                "Suitable" if f["suitable"] else "Not recommended",
                tone="ok" if f["suitable"] else "bad",
            )
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:0.45rem 0;border-bottom:1px solid {C["line"]};'
                f'font-size:0.86rem"><span>{f["use_case"]}</span>{b}</div>',
                unsafe_allow_html=True,
            )

        precision_stats = get_precision_stats(df)
        if precision_stats:
            T.section("Coordinate precision")
            st.dataframe(
                pd.DataFrame([{"Precision": k, "Records": v}
                              for k, v in precision_stats.items()]),
                use_container_width=True, hide_index=True,
            )

        if "basisOfRecord" in df.columns:
            T.section("Record types")
            basis = df["basisOfRecord"].value_counts().reset_index()
            basis.columns = ["Basis of record", "Count"]
            st.dataframe(basis, use_container_width=True, hide_index=True)

    recs = get_recommendations(summary, temporal_stats, df)
    T.section("Recommendations")
    kind_map = {"warning": "warn", "info": "info", "success": "success"}
    for rec in recs:
        T.alert(kind_map.get(rec["type"], "info"),
                rec["title"], rec["message"])

    T.section("Quality by contributing dataset")
    st.caption("Which datasets contribute the most quality issues.")
    ds_df, ds_fig = get_dataset_quality_breakdown(df, flags)
    if ds_fig:
        st.plotly_chart(ds_fig, use_container_width=True)
    if ds_df is not None:
        st.dataframe(ds_df, use_container_width=True, hide_index=True)
    else:
        st.info("Dataset breakdown unavailable — datasetName missing.")


def _tab_map(df, flags, outliers, map_type):
    from streamlit_folium import st_folium
    import folium as fl

    map_type = st.session_state.get("map_type", "Point Map")
    T.section("Occurrence map")
    st.caption(f"Mode: **{map_type}** — switch in the controls above.")

    try:
        if map_type == "Point Map":
            st.markdown(
                f'<span class="legend-dot dot-green"></span> Clean &nbsp;&nbsp;'
                f'<span class="legend-dot dot-red"></span> Flagged',
                unsafe_allow_html=True,
            )
            m = build_map(df, flags, map_type="points")
            st_folium(m, width=None, height=560, returned_objects=[],
                      key="map_points")
        elif map_type == "Heatmap":
            m = build_map(df, flags, map_type="heatmap")
            st_folium(m, width=None, height=560, returned_objects=[],
                      key="map_heatmap")
        elif map_type == "DBSCAN Outliers":
            lat_c = df["decimalLatitude"].dropna().mean()
            lon_c = df["decimalLongitude"].dropna().mean()
            m_db = fl.Map(location=[lat_c, lon_c], zoom_start=4,
                          tiles="CartoDB dark_matter")
            for idx, row in df.iterrows():
                try:
                    lat, lon = (row.get("decimalLatitude"),
                                row.get("decimalLongitude"))
                    if pd.isna(lat) or pd.isna(lon):
                        continue
                    is_out = (outliers.loc[idx]
                              if outliers is not None else False)
                    colour = "#F08A3E" if is_out else "#22C58B"
                    fl.CircleMarker(
                        location=[lat, lon], radius=4, color=colour,
                        fill=True, fill_color=colour, fill_opacity=0.7,
                    ).add_to(m_db)
                except Exception:
                    continue
            st_folium(m_db, width=None, height=560, returned_objects=[],
                      key="map_dbscan")
            if outliers is not None:
                out_stats = outlier_summary(outliers)
                T.alert(
                    "info", "DBSCAN result",
                    f"**{out_stats['outliers']}** spatial outliers "
                    f"({out_stats['outlier_pct']}% of records).",
                )
        elif map_type == "SDM Preview":
            st.info(
                "Kernel Density Estimation of habitat suitability — "
                "exploratory only, not a full correlative SDM."
            )
            sdm_map, sdm_err = build_sdm_map(df)
            if sdm_err:
                st.error(sdm_err)
            else:
                st_folium(sdm_map, width=None, height=560,
                          returned_objects=[], key="map_sdm")
    except Exception as e:
        st.error(f"Map error: {e}")


def _tab_temporal(df, yr_from, yr_to):
    T.section("Temporal overview")
    temporal_stats = get_temporal_stats(df)

    if not temporal_stats:
        st.info("Not enough temporal data — try widening the year range.")
        return

    boxes = [
        (temporal_stats["first_year"], "First record"),
        (temporal_stats["last_year"], "Latest record"),
        (temporal_stats["span_years"], "Year span"),
        (temporal_stats["gap_count"], "Years with no data"),
    ]
    bc = st.columns(4)
    for col, (val, lbl) in zip(bc, boxes):
        T.metric_card(lbl, str(val), col=col)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig_year = chart_records_per_year(df)
        if fig_year:
            st.plotly_chart(T.style_fig(fig_year, height=380),
                            use_container_width=True)
    with c2:
        fig_decade = chart_decade_breakdown(df)
        if fig_decade:
            st.plotly_chart(T.style_fig(fig_decade, height=380),
                            use_container_width=True)

    T.section("Insights")
    insights = [
        f"Peak recording year: **{temporal_stats['peak_year']}** "
        f"({temporal_stats['peak_count']:,} records).",
        f"Recording trend is **{temporal_stats['trend']}** over time.",
        f"**{temporal_stats['recent_pct']}%** of records fall in the last "
        f"5 years of the filtered range.",
    ]
    if temporal_stats.get("cs_surge"):
        insights.append(
            "Significant **citizen-science surge** detected post-2008."
        )
    if temporal_stats.get("major_gaps"):
        gaps = ", ".join(
            f"{s}–{e}" for s, e in temporal_stats["major_gaps"][:3]
        )
        insights.append(f"Major data gaps: **{gaps}**")
    for ins in insights:
        st.markdown(f"- {ins}")


def _tab_charts(df):
    T.section("Geographic & seasonal analysis")
    fig_density = chart_country_density(df)
    if fig_density:
        st.plotly_chart(T.style_fig(fig_density, height=420),
                        use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig_month = chart_records_per_month(df)
        if fig_month:
            st.plotly_chart(T.style_fig(fig_month, height=380),
                            use_container_width=True)
        fig_basis = chart_basis_of_record(df)
        if fig_basis:
            st.plotly_chart(T.style_fig(fig_basis, height=380),
                            use_container_width=True)
    with c2:
        fig_country = chart_top_countries(df)
        if fig_country:
            st.plotly_chart(T.style_fig(fig_country, height=380),
                            use_container_width=True)


def _tab_gaps(df):
    T.section("Global data gap map")
    st.info(
        "The world is divided into 10° grid cells. **Coloured cells** have "
        "records for this species; **dark cells** have none. Most of the "
        "globe will be dark for any species — that's ecology, not missing "
        "data."
    )
    st.caption(
        "🟢 data-rich · 🟡 sparse · 🟠 very sparse · 🔴 1–2 records"
    )
    gap_stats = get_gap_stats(df)
    if gap_stats:
        g = st.columns(3)
        T.metric_card("Cells with data", f"{gap_stats['covered']:,}", col=g[0])
        T.metric_card("Global coverage", f"{gap_stats['cov_pct']}%", col=g[1])
        T.metric_card("Countries with records",
                      f"{gap_stats['countries']:,}", col=g[2])
    from streamlit_folium import st_folium
    with st.spinner("Building gap map…"):
        gap_map = build_gap_map(df)
        if gap_map:
            st_folium(gap_map, width=None, height=500,
                      returned_objects=[], key="map_gap")
        else:
            st.error("Could not build gap map.")
    alerts = get_gap_alerts(df)
    if alerts:
        T.section("Spatial coverage alerts")
        kind_map = {"warning": "warn", "info": "info", "success": "success"}
        for alert in alerts:
            T.alert(kind_map.get(alert["type"], "info"),
                    alert["title"], alert["message"])


def _tab_export(df, clean_df, flags, summary, score, species, reliability,
                completeness, species_info, yr_from, yr_to, basis_used,
                total, pop_stats):
    T.section("Publication-grade exports")
    st.caption(
        "Everything a reviewer, repository or indicator pipeline needs — "
        "generated from this exact analysis run."
    )

    sample_stats = {
        "no_coords": round(float(flags["missing_coords"].mean() * 100), 1),
        "no_year": round(float(flags["missing_year"].mean() * 100), 1),
    }
    bench = build_benchmark(sample_stats, pop_stats) if pop_stats else []
    filters = {
        "year_from": yr_from, "year_to": yr_to,
        "year_range": f"{yr_from}–{yr_to}" if (yr_from != 1900 or yr_to != 2026) else "all years",
        "basis": basis_used, "limit": len(df), "gbif_total": int(total),
    }

    # ── Reproducibility Pack ──────────────────────────────
    pack, err = build_reppack(
        df, clean_df, species, score, summary,
        reliability=reliability, completeness=completeness,
        benchmark=bench, species_info=species_info, filters=filters,
    )
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        if pack:
            st.download_button(
                "⬇️ Reproducibility Pack (ZIP)",
                data=pack,
                file_name=f"biosift_{species.replace(' ', '_')}_pack.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
            st.caption(
                "Report JSON · methods · citations · CSVs · DwC-A · recipe"
            )
        else:
            st.error(f"Pack error: {err}")

    # ── PDF report ─────────────────────────────────────────
    with ec2:
        pdf, pdf_err = build_pdf_report(
            species, score, df, clean_df, summary, benchmark=bench,
            reliability=reliability, completeness=completeness,
            species_info=species_info, filters=filters,
        )
        if pdf:
            st.download_button(
                "⬇️ PDF Quality Report",
                data=pdf,
                file_name=f"biosift_{species.replace(' ', '_')}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption("Branded summary for theses, DMPs and grants")
        else:
            st.error(f"PDF error: {pdf_err}")

    # ── GBIF data cube ─────────────────────────────────────
    with ec3:
        sql, payload = cube_exports(
            species, yr_from, yr_to, basis_used, grid=10
        )
        st.download_button(
            "⬇️ GBIF Data Cube (SQL)",
            data=sql,
            file_name=f"biosift_{species.replace(' ', '_')}_cube.sql",
            mime="text/plain",
            use_container_width=True,
        )
        st.caption("Indicator-grade cube for the GBIF SQL download service")

    with st.expander("GBIF data cube payload (JSON)"):
        st.code(payload, language="json")
        st.markdown(
            f"[Open the GBIF SQL download form]("
            f"https://www.gbif.org/download/sql) — paste the query, "
            f"receive a citable DOI-backed download."
        )

    # ── before / after ─────────────────────────────────────
    T.section("Before & after cleaning")
    ba1, ba2 = st.columns(2)
    with ba1:
        T.metric_card("Before cleaning", f"{len(df):,}", "records analysed")
    with ba2:
        T.metric_card("After cleaning", f"{len(clean_df):,}",
                      f"{score}% retained")

    # ── CSV downloads ──────────────────────────────────────
    T.section("CSV downloads")
    from utils.reppack import _export_df
    ecsv1, ecsv2 = st.columns(2)
    with ecsv1:
        st.download_button(
            "Download Full Sample (CSV)",
            data=_export_df(df, score).to_csv(index=False).encode("utf-8"),
            file_name=f"biosift_{species.replace(' ', '_')}_full.csv",
            mime="text/csv", use_container_width=True,
        )
    with ecsv2:
        st.download_button(
            "Download Clean Records (CSV)",
            data=_export_df(clean_df, score).to_csv(index=False).encode("utf-8"),
            file_name=f"biosift_{species.replace(' ', '_')}_clean.csv",
            mime="text/csv", use_container_width=True,
        )

    # ── methods + citation ─────────────────────────────────
    T.section("Reproducible methods paragraph")
    st.caption("Copy-paste into your manuscript.")
    from utils.reliability import generate_methods_text, generate_citation
    st.text_area(
        "methods", value=generate_methods_text(
            species, df, clean_df, summary, score
        ),
        height=180, label_visibility="collapsed",
    )

    T.section("GBIF dataset citation")
    cite = generate_citation(species, df, species_info=species_info)
    ct1, ct2 = st.tabs(["APA", "BibTeX"])
    with ct1:
        st.code(cite["apa"], language="text")
    with ct2:
        st.code(cite["bibtex"], language="text")
    st.markdown(
        f'<div class="alert a-info"><div class="alert-m">{cite["note"]} '
        f'<a href="{cite["search_url"]}" target="_blank">View on GBIF</a>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── preview ────────────────────────────────────────────
    T.section("Sample preview")
    from utils.reppack import _export_df as ex
    st.dataframe(ex(df, score), use_container_width=True)
