import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from utils.gbif_fetch    import fetch_occurrences, SAMPLE_SPECIES
from utils.quality       import run_quality_checks, quality_summary, get_precision_stats
from utils.maps          import build_map
from utils.iucn          import get_iucn_status
from utils.outliers      import detect_outliers, outlier_summary
from utils.sdm           import build_sdm_map
from utils.reliability   import (
    compute_reliability_score,
    get_reliability_label,
    get_data_fitness,
    generate_methods_text
)
from utils.gaps          import build_gap_map, get_gap_stats
from utils.publisher     import search_publisher, build_publisher_report
from utils.charts import (
    chart_records_per_year,
    chart_records_per_month,
    chart_basis_of_record,
    chart_top_countries,
    chart_decade_breakdown,
    get_temporal_stats,
    get_recommendations
)

# ── page config ───────────────────────────────────────────
st.set_page_config(
    page_title="BioSift",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── mobile ── */
    .mobile-notice {
        display: none;
        background: #2D1D10;
        border: 1px solid #F0883E;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.875rem;
        color: #F0883E;
        margin-bottom: 1rem;
        text-align: center;
    }
    @media (max-width: 768px) {
        .mobile-notice {
            display: block;
        }
        .app-title {
            font-size: 1.3rem;
        }
        .app-subtitle {
            font-size: 0.8rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }
        .health-score {
            font-size: 1.5rem;
        }
        .temporal-stat-value {
            font-size: 1.1rem;
        }
    }

    /* ── global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    .stApp { background-color: #0D1117; }
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #21262D;
        padding-top: 1rem;
    }
    .app-header {
        padding: 2rem 0 1.5rem 0;
        border-bottom: 1px solid #21262D;
        margin-bottom: 2rem;
    }
    .app-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #F0F6FC;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.875rem;
        color: #8B949E;
        margin: 0.3rem 0 0 0;
    }
    .app-badge {
        display: inline-block;
        margin-top: 0.5rem;
        padding: 0.2rem 0.6rem;
        background-color: #1F2D1F;
        color: #3FB950;
        border: 1px solid #3FB950;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    [data-testid="metric-container"] {
        background-color: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1.2rem 1rem;
        transition: border-color 0.2s;
    }
    [data-testid="metric-container"]:hover { border-color: #3FB950; }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F0F6FC;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .section-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8B949E;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #21262D;
    }
    .species-title {
        font-size: 1.4rem;
        font-weight: 600;
        font-style: italic;
        color: #F0F6FC;
        margin: 0 0 0.25rem 0;
    }
    .iucn-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .iucn-cr{background:#2D1515;color:#F85149;border:1px solid #F85149;}
    .iucn-en{background:#2D1D10;color:#F0883E;border:1px solid #F0883E;}
    .iucn-vu{background:#2D270A;color:#E3B341;border:1px solid #E3B341;}
    .iucn-lc{background:#1F2D1F;color:#3FB950;border:1px solid #3FB950;}
    .iucn-nt{background:#1F2D1F;color:#3FB950;border:1px solid #3FB950;}
    .iucn-dd{background:#1C2128;color:#8B949E;border:1px solid #8B949E;}
    .iucn-ex{background:#1C2128;color:#8B949E;border:1px solid #8B949E;}
    .health-bar-wrap {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .health-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8B949E;
        margin-bottom: 0.5rem;
    }
    .health-score {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    .health-good{color:#3FB950;}
    .health-fair{color:#E3B341;}
    .health-poor{color:#F85149;}
    .health-bar-bg {
        background: #21262D;
        border-radius: 999px;
        height: 6px;
        width: 100%;
        overflow: hidden;
    }
    .health-bar-fill { height:6px; border-radius:999px; }
    .health-bar-good{background:#3FB950;}
    .health-bar-fair{background:#E3B341;}
    .health-bar-poor{background:#F85149;}
    .rec-card {
        padding: 0.85rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.6rem;
        font-size: 0.875rem;
        line-height: 1.5;
    }
    .rec-warning{background:#2D1D10;border-left:3px solid #F0883E;}
    .rec-info{background:#0D1926;border-left:3px solid #58A6FF;}
    .rec-success{background:#1F2D1F;border-left:3px solid #3FB950;}
    .rec-title{font-weight:600;margin-bottom:0.2rem;color:#F0F6FC;}
    .rec-msg{color:#8B949E;}
    .temporal-stat-box {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .temporal-stat-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #F0F6FC;
    }
    .temporal-stat-label {
        font-size: 0.75rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.2rem;
    }
    .before-after {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .fitness-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.6rem 0;
        border-bottom: 1px solid #21262D;
        font-size: 0.875rem;
    }
    .fitness-badge-yes {
        background: #1F2D1F;
        color: #3FB950;
        border: 1px solid #3FB950;
        border-radius: 12px;
        padding: 0.15rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .fitness-badge-no {
        background: #2D1515;
        color: #F85149;
        border: 1px solid #F85149;
        border-radius: 12px;
        padding: 0.15rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .map-legend {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 0.75rem;
        font-size: 0.8rem;
        color: #8B949E;
    }
    .legend-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 4px;
        vertical-align: middle;
    }
    .dot-green{background:#3FB950;}
    .dot-red{background:#F85149;}
    .dot-orange{background:#F0883E;}
    .sidebar-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #8B949E;
        margin-bottom: 0.25rem;
    }
    .pub-card {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .pub-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #F0F6FC;
        margin-bottom: 0.5rem;
    }
    .pub-stat { font-size: 0.875rem; color: #8B949E; }
    hr { border-color: #21262D; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="app-title">BioSift</p>
    <p class="app-subtitle">
        Biodiversity data intelligence platform powered by
        GBIF & IUCN Red List
    </p>
    <span class="app-badge">Ebbe Nielsen Challenge 2026</span>
</div>
""", unsafe_allow_html=True)

# ── mobile notice ─────────────────────────────────────────
st.markdown("""
<div class="mobile-notice">
    📱 BioSift is optimised for desktop browsers.
    For the best experience, please open on a laptop or desktop.
</div>
""", unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-label">Mode</p>', unsafe_allow_html=True)
    mode = st.radio(
        "",
        ["Species Analysis", "Publisher Report Card"],
        label_visibility="collapsed"
    )
    st.divider()

    if mode == "Species Analysis":
        st.markdown(
            '<p class="sidebar-label">Quick Select</p>',
            unsafe_allow_html=True
        )
        sample_choice = st.selectbox(
            "",
            ["— select a sample —"] + list(SAMPLE_SPECIES.keys()),
            label_visibility="collapsed"
        )

        st.markdown(
            '<p class="sidebar-label">Species Name</p>',
            unsafe_allow_html=True
        )
        species_input = st.text_input(
            "",
            placeholder="e.g. Panthera leo",
            label_visibility="collapsed"
        )

        if sample_choice != "— select a sample —":
            species_input = SAMPLE_SPECIES[sample_choice]
            st.caption(f"*{species_input}*")

        st.markdown(
            '<p class="sidebar-label">Max Records</p>',
            unsafe_allow_html=True
        )
        limit = st.slider(
            "", 100, 10000, 500,
            step=100,
            label_visibility="collapsed"
        )

        st.divider()

        st.markdown(
            '<p class="sidebar-label">IUCN API Key</p>',
            unsafe_allow_html=True
        )
        iucn_key = st.text_input(
            "",
            type="password",
            placeholder="Optional",
            label_visibility="collapsed"
        )
        st.caption(
            "Get free key at "
            "[iucnredlist.org](https://apiv3.iucnredlist.org/api/v3/token)"
        )

        st.divider()
        search_btn = st.button(
            "Run Analysis",
            use_container_width=True,
            type="primary"
        )

    else:
        st.markdown(
            '<p class="sidebar-label">Publisher / Institution Name</p>',
            unsafe_allow_html=True
        )
        publisher_input = st.text_input(
            "",
            placeholder="e.g. iNaturalist",
            label_visibility="collapsed"
        )
        st.divider()
        pub_btn = st.button(
            "Get Report Card",
            use_container_width=True,
            type="primary"
        )

    st.divider()
    st.caption(
        "Data: [GBIF.org](https://www.gbif.org) · "
        "[IUCN](https://iucnredlist.org)"
    )

# ══════════════════════════════════════════════════════════
# MODE: SPECIES ANALYSIS
# ══════════════════════════════════════════════════════════
if mode == "Species Analysis":

    if search_btn:
        if not species_input:
            st.warning("Please enter a species name or select a sample.")
        else:
            with st.spinner(f"Fetching data for {species_input}..."):
                df, total, error = fetch_occurrences(species_input, limit)

                if error:
                    st.error(error)
                else:
                    st.session_state["df"]         = df
                    st.session_state["total"]       = total
                    st.session_state["species"]     = species_input
                    st.session_state["flags"]       = run_quality_checks(df)
                    st.session_state["summary"]     = quality_summary(
                        st.session_state["flags"]
                    )
                    st.session_state["outliers"]    = detect_outliers(df)
                    st.session_state["reliability"] = compute_reliability_score(df)

                    if iucn_key:
                        with st.spinner("Checking IUCN status..."):
                            iucn = get_iucn_status(species_input, iucn_key)
                            if iucn is None:
                                st.warning(
                                    "IUCN status not found for this species."
                                )
                            st.session_state["iucn"] = iucn
                    else:
                        st.session_state["iucn"] = None

    if "df" in st.session_state and mode == "Species Analysis":
        df          = st.session_state["df"]
        total       = st.session_state["total"]
        flags       = st.session_state["flags"]
        summary     = st.session_state["summary"]
        species     = st.session_state["species"]
        iucn        = st.session_state.get("iucn")
        outliers    = st.session_state.get("outliers")
        reliability = st.session_state.get("reliability")

        clean_df = df[~flags["any_flag"]].reset_index(drop=True)
        clean    = len(clean_df)
        score    = round(clean / len(flags) * 100, 1)

        # ── species + iucn ────────────────────────────────
        st.markdown(
            f'<p class="species-title">{species}</p>',
            unsafe_allow_html=True
        )

        if iucn:
            cat = iucn["category"]
            css_class = {
                "CR":"iucn-cr","EN":"iucn-en","VU":"iucn-vu",
                "NT":"iucn-lc","LC":"iucn-lc","DD":"iucn-dd",
                "EX":"iucn-ex","EW":"iucn-ex","NE":"iucn-dd"
            }.get(cat, "iucn-dd")
            st.markdown(
                f'<span class="iucn-badge {css_class}">'
                f'{iucn["emoji"]} {iucn["label"]} ({cat})'
                f' · Assessed {iucn["published_year"]}'
                f'</span>',
                unsafe_allow_html=True
            )

        # ── metrics ───────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total GBIF Records", f"{total:,}")
        with col2:
            st.metric("Records Analysed", f"{len(df):,}")
        with col3:
            st.metric("Clean Records", f"{clean:,}")
        with col4:
            st.metric("Health Score", f"{score}%")

        st.divider()

        # ── tabs ──────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Overview",
            "Occurrence Map",
            "Temporal Analysis",
            "Charts",
            "Gap Analysis",
            "Data & Export"
        ])

        # ── TAB 1: Overview ───────────────────────────────
        with tab1:
            col_left, col_right = st.columns([1, 1])

            with col_left:
                if score >= 80:
                    h_class = "health-good"
                    b_class = "health-bar-good"
                    label   = "Good"
                elif score >= 50:
                    h_class = "health-fair"
                    b_class = "health-bar-fair"
                    label   = "Fair"
                else:
                    h_class = "health-poor"
                    b_class = "health-bar-poor"
                    label   = "Poor"

                st.markdown(f"""
                <div class="health-bar-wrap">
                    <div class="health-label">Data Health Score</div>
                    <div class="health-score {h_class}">
                        {score}% — {label}
                    </div>
                    <div class="health-bar-bg">
                        <div class="health-bar-fill {b_class}"
                             style="width:{score}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(
                    '<p class="section-header">Quality Issues</p>',
                    unsafe_allow_html=True
                )
                skip       = ["any_flag", "has_issues"]
                issue_rows = []
                found_any  = False

                for check, stats in summary.items():
                    if check not in skip:
                        issue_rows.append({
                            "Check"          : check.replace("_"," ").title(),
                            "Flagged Records": stats["count"],
                            "Percentage"     : f"{stats['percent']}%",
                            "Status"         : "Issue Found"
                                               if stats["count"] > 0 else "OK"
                        })
                        if stats["count"] > 0:
                            found_any = True

                st.dataframe(
                    pd.DataFrame(issue_rows),
                    use_container_width=True,
                    hide_index=True
                )

                if not found_any:
                    st.success("No major quality issues found.")

                if ("has_issues" in summary
                        and summary["has_issues"]["count"] > 0):
                    st.info(
                        f"{summary['has_issues']['count']} records carry "
                        f"GBIF internal flags — informational only."
                    )

                if outliers is not None:
                    out_stats = outlier_summary(outliers)
                    st.markdown(
                        '<p class="section-header">'
                        'DBSCAN Spatial Outliers</p>',
                        unsafe_allow_html=True
                    )
                    o1, o2 = st.columns(2)
                    with o1:
                        st.metric(
                            "Spatial Outliers",
                            f"{out_stats['outliers']:,}"
                        )
                    with o2:
                        st.metric(
                            "Outlier %",
                            f"{out_stats['outlier_pct']}%"
                        )

            with col_right:
                temporal_stats = get_temporal_stats(df)
                fitness        = get_data_fitness(score, summary, temporal_stats)

                st.markdown(
                    '<p class="section-header">Data Fitness</p>',
                    unsafe_allow_html=True
                )

                for f in fitness:
                    badge = (
                        '<span class="fitness-badge-yes">Suitable</span>'
                        if f["suitable"] else
                        '<span class="fitness-badge-no">Not Recommended</span>'
                    )
                    st.markdown(f"""
                    <div class="fitness-row">
                        <span>{f['use_case']}</span>
                        {badge}
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                precision_stats = get_precision_stats(df)
                if precision_stats:
                    st.markdown(
                        '<p class="section-header">'
                        'Coordinate Precision</p>',
                        unsafe_allow_html=True
                    )
                    prec_df = pd.DataFrame([
                        {"Precision Level": k, "Records": v}
                        for k, v in precision_stats.items()
                    ])
                    st.dataframe(
                        prec_df,
                        use_container_width=True,
                        hide_index=True
                    )

                if "basisOfRecord" in df.columns:
                    st.markdown(
                        '<p class="section-header">Record Types</p>',
                        unsafe_allow_html=True
                    )
                    basis = df["basisOfRecord"].value_counts().reset_index()
                    basis.columns = ["Basis of Record", "Count"]
                    st.dataframe(
                        basis,
                        use_container_width=True,
                        hide_index=True
                    )

            recs = get_recommendations(summary, temporal_stats, df)
            st.markdown(
                '<p class="section-header">Recommendations</p>',
                unsafe_allow_html=True
            )
            for rec in recs:
                css = f"rec-{rec['type']}"
                st.markdown(f"""
                <div class="rec-card {css}">
                    <div class="rec-title">{rec['title']}</div>
                    <div class="rec-msg">{rec['message']}</div>
                </div>
                """, unsafe_allow_html=True)

        # ── TAB 2: Map ────────────────────────────────────
        with tab2:
            st.markdown(
                '<p class="section-header">Occurrence Map</p>',
                unsafe_allow_html=True
            )

            map_type = st.radio(
                "Map type",
                ["Point Map", "Heatmap", "DBSCAN Outliers", "SDM Preview"],
                horizontal=True
            )

            if map_type == "Point Map":
                st.markdown("""
                <div class="map-legend">
                    <span>
                        <span class="legend-dot dot-green"></span>
                        Clean record
                    </span>
                    <span>
                        <span class="legend-dot dot-red"></span>
                        Flagged record
                    </span>
                </div>
                """, unsafe_allow_html=True)
                try:
                    with st.spinner("Rendering map..."):
                        m = build_map(df, flags, map_type="points")
                        st_folium(m, width=None, height=560, returned_objects=[])
                except Exception as e:
                    st.error(f"Map error: {str(e)}")

            elif map_type == "Heatmap":
                try:
                    with st.spinner("Rendering heatmap..."):
                        m = build_map(df, flags, map_type="heatmap")
                        st_folium(m, width=None, height=560, returned_objects=[])
                except Exception as e:
                    st.error(f"Map error: {str(e)}")

            elif map_type == "DBSCAN Outliers":
                st.markdown("""
                <div class="map-legend">
                    <span>
                        <span class="legend-dot dot-green"></span>
                        Core cluster
                    </span>
                    <span>
                        <span class="legend-dot dot-orange"></span>
                        Spatial outlier
                    </span>
                </div>
                """, unsafe_allow_html=True)
                try:
                    import folium as fl
                    lat_c = df["decimalLatitude"].dropna().mean()
                    lon_c = df["decimalLongitude"].dropna().mean()
                    m_db  = fl.Map(
                        location=[lat_c, lon_c],
                        zoom_start=4,
                        tiles="CartoDB dark_matter"
                    )
                    for idx, row in df.iterrows():
                        try:
                            lat = row.get("decimalLatitude")
                            lon = row.get("decimalLongitude")
                            if pd.isna(lat) or pd.isna(lon):
                                continue
                            is_out = (
                                outliers.loc[idx]
                                if outliers is not None else False
                            )
                            color = "#F0883E" if is_out else "#3FB950"
                            fl.CircleMarker(
                                location=[lat, lon],
                                radius=4,
                                color=color,
                                fill=True,
                                fill_color=color,
                                fill_opacity=0.7
                            ).add_to(m_db)
                        except Exception:
                            continue

                    st_folium(m_db, width=None, height=560, returned_objects=[])

                    if outliers is not None:
                        out_stats = outlier_summary(outliers)
                        st.info(
                            f"DBSCAN detected "
                            f"**{out_stats['outliers']}** spatial outliers "
                            f"({out_stats['outlier_pct']}% of records)"
                        )
                except Exception as e:
                    st.error(f"DBSCAN map error: {str(e)}")

            elif map_type == "SDM Preview":
                st.info(
                    "SDM Preview uses Kernel Density Estimation to show "
                    "predicted habitat suitability based on occurrence "
                    "records. Red = high suitability, green = low."
                )
                with st.spinner("Building SDM..."):
                    sdm_map, sdm_error = build_sdm_map(df)
                    if sdm_error:
                        st.error(sdm_error)
                    else:
                        st_folium(
                            sdm_map, width=None,
                            height=560,
                            returned_objects=[]
                        )

        # ── TAB 3: Temporal Analysis ──────────────────────
        with tab3:
            st.markdown(
                '<p class="section-header">Temporal Overview</p>',
                unsafe_allow_html=True
            )

            temporal_stats = get_temporal_stats(df)

            if temporal_stats:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f"""
                    <div class="temporal-stat-box">
                        <div class="temporal-stat-value">
                            {temporal_stats['first_year']}
                        </div>
                        <div class="temporal-stat-label">First Record</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="temporal-stat-box">
                        <div class="temporal-stat-value">
                            {temporal_stats['last_year']}
                        </div>
                        <div class="temporal-stat-label">Latest Record</div>
                    </div>""", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="temporal-stat-box">
                        <div class="temporal-stat-value">
                            {temporal_stats['span_years']}
                        </div>
                        <div class="temporal-stat-label">Year Span</div>
                    </div>""", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"""
                    <div class="temporal-stat-box">
                        <div class="temporal-stat-value">
                            {temporal_stats['gap_count']}
                        </div>
                        <div class="temporal-stat-label">
                            Years With No Data
                        </div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    fig_year = chart_records_per_year(df)
                    if fig_year:
                        st.plotly_chart(fig_year, use_container_width=True)
                with col2:
                    fig_decade = chart_decade_breakdown(df)
                    if fig_decade:
                        st.plotly_chart(fig_decade, use_container_width=True)

                st.markdown(
                    '<p class="section-header">Temporal Insights</p>',
                    unsafe_allow_html=True
                )

                insights = [
                    f"Peak recording year was "
                    f"**{temporal_stats['peak_year']}** "
                    f"with **{temporal_stats['peak_count']:,}** records.",
                    f"Recording trend is "
                    f"**{temporal_stats['trend']}** over time.",
                    f"**{temporal_stats['recent_pct']}%** of records are "
                    f"from the last 5 years."
                ]

                if temporal_stats["cs_surge"]:
                    insights.append(
                        "Significant **citizen science surge** detected "
                        "post-2008, likely from platforms like iNaturalist."
                    )

                if temporal_stats["major_gaps"]:
                    gap_strs = [
                        f"{s}–{e}"
                        for s, e in temporal_stats["major_gaps"][:3]
                    ]
                    insights.append(
                        f"Major data gaps detected: "
                        f"**{', '.join(gap_strs)}**"
                    )

                for insight in insights:
                    st.markdown(f"- {insight}")

            else:
                st.info("Not enough temporal data to analyse.")

        # ── TAB 4: Charts ─────────────────────────────────
        with tab4:
            st.markdown(
                '<p class="section-header">'
                'Geographic & Seasonal Analysis</p>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)
            with col1:
                fig_month = chart_records_per_month(df)
                if fig_month:
                    st.plotly_chart(fig_month, use_container_width=True)
                else:
                    st.info("Not enough month data.")

                fig_basis = chart_basis_of_record(df)
                if fig_basis:
                    st.plotly_chart(fig_basis, use_container_width=True)
                else:
                    st.info("No basis of record data.")

            with col2:
                fig_country = chart_top_countries(df)
                if fig_country:
                    st.plotly_chart(fig_country, use_container_width=True)
                else:
                    st.info("No country data.")

        # ── TAB 5: Gap Analysis ───────────────────────────
        with tab5:
            st.markdown(
                '<p class="section-header">Global Data Gap Map</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Green = data rich · Yellow = sparse · "
                "Orange = very sparse · Red = no data. "
                "Grid resolution: 10° cells."
            )

            gap_stats = get_gap_stats(df)

            if gap_stats:
                g1, g2, g3 = st.columns(3)
                with g1:
                    st.metric(
                        "Grid Cells Covered",
                        f"{gap_stats['covered']:,}"
                    )
                with g2:
                    st.metric(
                        "Global Coverage",
                        f"{gap_stats['cov_pct']}%"
                    )
                with g3:
                    st.metric(
                        "Countries",
                        f"{gap_stats['countries']:,}"
                    )

            with st.spinner("Building gap map..."):
                gap_map = build_gap_map(df)
                if gap_map:
                    st_folium(
                        gap_map, width=None,
                        height=560,
                        returned_objects=[]
                    )
                else:
                    st.error("Could not build gap map.")

        # ── TAB 6: Data & Export ──────────────────────────
        with tab6:

            if reliability is not None:
                st.markdown(
                    '<p class="section-header">'
                    'Record Reliability Scores</p>',
                    unsafe_allow_html=True
                )
                avg_rel          = round(reliability.mean(), 1)
                rel_lab, rel_col = get_reliability_label(avg_rel)

                r1, r2, r3 = st.columns(3)
                with r1:
                    st.metric("Avg Reliability", f"{avg_rel}/100")
                with r2:
                    st.metric("Reliability Level", rel_lab)
                with r3:
                    st.metric(
                        "High Reliability Records",
                        f"{(reliability >= 80).sum():,}"
                    )

                df_with_rel = df.copy()
                df_with_rel.insert(
                    0, "Reliability Score", reliability.values
                )
                df_with_rel = df_with_rel.sort_values(
                    "Reliability Score", ascending=False
                )

            st.markdown(
                '<p class="section-header">Before & After Cleaning</p>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="before-after">
                    <div class="health-label">Before Cleaning</div>
                    <div style="font-size:1.6rem;font-weight:700;
                                color:#F85149;">{len(df):,}</div>
                    <div style="color:#8B949E;font-size:0.8rem;">
                        Total records
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="before-after">
                    <div class="health-label">After Cleaning</div>
                    <div style="font-size:1.6rem;font-weight:700;
                                color:#3FB950;">{clean:,}</div>
                    <div style="color:#8B949E;font-size:0.8rem;">
                        Clean records ({score}% retained)
                    </div>
                </div>
                """, unsafe_allow_html=True)

            removed = len(df) - clean
            st.caption(
                f"{removed:,} records removed "
                f"({round(removed / len(df) * 100, 1)}% of total)"
            )

            st.divider()

            st.markdown(
                '<p class="section-header">Download</p>',
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                csv_full = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Full Dataset",
                    data=csv_full,
                    file_name=f"gbif_{species.replace(' ','_')}_full.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption(f"{len(df):,} records")

            with col2:
                csv_clean = clean_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Clean Records",
                    data=csv_clean,
                    file_name=f"gbif_{species.replace(' ','_')}_clean.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption(f"{clean:,} records")

            with col3:
                if reliability is not None:
                    csv_rel = df_with_rel.to_csv(
                        index=False
                    ).encode("utf-8")
                    st.download_button(
                        label="Download With Reliability Scores",
                        data=csv_rel,
                        file_name=(
                            f"gbif_{species.replace(' ','_')}_scored.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.caption(f"{len(df):,} records + scores")

            st.divider()

            st.markdown(
                '<p class="section-header">'
                'Reproducible Methods Paragraph</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Copy and paste directly into your research paper "
                "methods section."
            )

            methods_text = generate_methods_text(
                species, df, clean_df, summary, score
            )

            st.text_area(
                "",
                value=methods_text,
                height=200,
                label_visibility="collapsed"
            )

            st.divider()
            st.markdown(
                '<p class="section-header">Preview</p>',
                unsafe_allow_html=True
            )
            if reliability is not None:
                st.dataframe(df_with_rel, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)

# ══════════════════════════════════════════════════════════
# MODE: PUBLISHER REPORT CARD
# ══════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <p style="font-size:1.1rem;font-weight:600;
                  color:#F0F6FC;margin:0">
            Publisher Report Card
        </p>
        <p style="font-size:0.875rem;color:#8B949E;
                  margin:0.3rem 0 0 0">
            Assess the data quality and coverage of any GBIF
            data publishing institution
        </p>
    </div>
    """, unsafe_allow_html=True)

    if pub_btn:
        if not publisher_input:
            st.warning("Please enter a publisher or institution name.")
        else:
            with st.spinner(f"Searching for {publisher_input}..."):
                publishers, error = search_publisher(publisher_input)

                if error:
                    st.error(error)
                elif not publishers:
                    st.error("No publisher found. Try a different name.")
                else:
                    st.session_state["publishers"] = publishers
                    st.session_state["pub_input"]  = publisher_input

    if "publishers" in st.session_state and mode == "Publisher Report Card":
        publishers = st.session_state["publishers"]

        st.markdown(
            '<p class="section-header">Select Publisher</p>',
            unsafe_allow_html=True
        )

        pub_options = {
            p.get("title", "Unknown"): p.get("key", "")
            for p in publishers
        }

        selected_pub_name = st.selectbox(
            "",
            list(pub_options.keys()),
            label_visibility="collapsed"
        )
        selected_pub_key = pub_options[selected_pub_name]

        if st.button("Load Report", type="primary"):
            with st.spinner("Fetching publisher datasets..."):
                report, rep_error = build_publisher_report(
                    selected_pub_key,
                    selected_pub_name,
                    limit=10
                )

                if rep_error:
                    st.error(rep_error)
                else:
                    st.session_state["pub_report"] = report

    if "pub_report" in st.session_state and mode == "Publisher Report Card":
        report = st.session_state["pub_report"]

        st.markdown(f"""
        <div class="pub-card">
            <div class="pub-title">{report['publisher']}</div>
            <div class="pub-stat">
                {report['dataset_count']} datasets ·
                {report['total_records']:,} total records
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p class="section-header">Dataset Overview</p>',
            unsafe_allow_html=True
        )
        st.dataframe(
            report["datasets"],
            use_container_width=True,
            hide_index=True
        )

        csv_pub = report["datasets"].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Publisher Report (CSV)",
            data=csv_pub,
            file_name=(
                f"gbif_publisher_"
                f"{report['publisher'].replace(' ','_')}.csv"
            ),
            mime="text/csv"
        )