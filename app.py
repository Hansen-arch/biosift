import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import requests
import re
from utils.gbif_fetch     import fetch_occurrences, SAMPLE_SPECIES
from utils.species_info   import get_species_info
from utils.quality        import (
    run_quality_checks,
    quality_summary,
    get_precision_stats,
    get_multimedia_stats,
    get_completeness_score
)
from utils.maps           import build_map
from utils.outliers       import detect_outliers, outlier_summary
from utils.sdm            import build_sdm_map
from utils.reliability    import (
    compute_reliability_score,
    get_reliability_label,
    get_data_fitness,
    generate_methods_text,
    generate_citation
)
from utils.gaps           import build_gap_map, get_gap_stats, get_gap_alerts
from utils.publisher      import search_publisher, build_publisher_report
from utils.charts         import (
    chart_records_per_year,
    chart_records_per_month,
    chart_basis_of_record,
    chart_top_countries,
    chart_country_density,
    chart_decade_breakdown,
    get_temporal_stats,
    get_recommendations
)
from utils.dwc            import build_dwca
from utils.dataset_quality import get_dataset_quality_breakdown

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
        .mobile-notice { display: block; }
        .app-title { font-size: 1.3rem; }
        .app-subtitle { font-size: 0.8rem; }
        [data-testid="stMetricValue"] { font-size: 1.2rem; }
        .health-score { font-size: 1.5rem; }
        .temporal-stat-value { font-size: 1.1rem; }
    }
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
    [data-testid="metric-container"]:hover {
        border-color: #3FB950;
    }
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
    .health-bar-wrap {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .completeness-bar-wrap {
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
    .health-good  { color: #3FB950; }
    .health-fair  { color: #E3B341; }
    .health-poor  { color: #F85149; }
    .health-bar-bg {
        background: #21262D;
        border-radius: 999px;
        height: 6px;
        width: 100%;
        overflow: hidden;
    }
    .health-bar-fill  { height: 6px; border-radius: 999px; }
    .health-bar-good  { background: #3FB950; }
    .health-bar-fair  { background: #E3B341; }
    .health-bar-poor  { background: #F85149; }
    .rec-card {
        padding: 0.85rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.6rem;
        font-size: 0.875rem;
        line-height: 1.5;
    }
    .rec-warning { background:#2D1D10; border-left:3px solid #F0883E; }
    .rec-info    { background:#0D1926; border-left:3px solid #58A6FF; }
    .rec-success { background:#1F2D1F; border-left:3px solid #3FB950; }
    .rec-title {
        font-weight: 600;
        margin-bottom: 0.2rem;
        color: #F0F6FC;
    }
    .rec-msg { color: #8B949E; }
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
        background:#1F2D1F; color:#3FB950;
        border:1px solid #3FB950; border-radius:12px;
        padding:0.15rem 0.6rem;
        font-size:0.75rem; font-weight:600;
    }
    .fitness-badge-no {
        background:#2D1515; color:#F85149;
        border:1px solid #F85149; border-radius:12px;
        padding:0.15rem 0.6rem;
        font-size:0.75rem; font-weight:600;
    }
    .map-legend {
        display:flex; gap:1.5rem;
        margin-bottom:0.75rem;
        font-size:0.8rem; color:#8B949E;
    }
    .legend-dot {
        display:inline-block;
        width:10px; height:10px;
        border-radius:50%;
        margin-right:4px;
        vertical-align:middle;
    }
    .dot-green  { background:#3FB950; }
    .dot-red    { background:#F85149; }
    .dot-orange { background:#F0883E; }
    .sidebar-label {
        font-size:0.75rem; font-weight:600;
        text-transform:uppercase; letter-spacing:0.5px;
        color:#8B949E; margin-bottom:0.25rem;
    }
    .pub-card {
        background:#161B22;
        border:1px solid #21262D;
        border-radius:10px;
        padding:1.2rem 1.5rem;
        margin-bottom:1rem;
    }
    .pub-title {
        font-size:1.1rem; font-weight:600;
        color:#F0F6FC; margin-bottom:0.5rem;
    }
    .pub-stat { font-size:0.875rem; color:#8B949E; }
    .citation-note {
        background:#0D1926;
        border-left:3px solid #58A6FF;
        border-radius:4px;
        padding:0.75rem 1rem;
        font-size:0.8rem;
        color:#8B949E;
        margin-top:0.75rem;
    }
    .compare-card {
        background:#161B22;
        border:1px solid #21262D;
        border-radius:10px;
        padding:1rem 1.2rem;
        margin-bottom:0.75rem;
        text-align:center;
    }
    .compare-species {
        font-size:0.85rem;
        font-style:italic;
        color:#8B949E;
        margin-bottom:0.5rem;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
    }
    .compare-score {
        font-size:1.6rem;
        font-weight:700;
    }
    hr { border-color:#21262D; margin:1rem 0; }
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="app-title">BioSift</p>
    <p class="app-subtitle">
        Biodiversity data intelligence platform powered by GBIF
    </p>
    <span class="app-badge">Ebbe Nielsen Challenge 2026</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mobile-notice">
    BioSift is optimised for desktop browsers.
    For the best experience, please open on a laptop or desktop.
</div>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────
def clear_results():
    for key in [
        "df", "total", "species", "flags", "summary",
        "outliers", "reliability", "species_info",
        "multimedia", "completeness"
    ]:
        st.session_state.pop(key, None)


def prepare_export_df(df):
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
        export.insert(
            export.columns.get_loc("media"),
            "image_url",
            export["media"].apply(extract_image_url)
        )
        export = export.drop(columns=["media"])
    if "issues" in export.columns:
        export["issues"] = export["issues"].apply(
            lambda x: "; ".join(str(i) for i in x)
            if isinstance(x, list) and len(x) > 0 else ""
        )
    return export


def score_class(score):
    if score >= 80: return "health-good"
    elif score >= 50: return "health-fair"
    else: return "health-poor"


def bar_class(score):
    if score >= 80: return "health-bar-good"
    elif score >= 50: return "health-bar-fair"
    else: return "health-bar-poor"


def score_label(score):
    if score >= 80: return "Good"
    elif score >= 50: return "Fair"
    else: return "Poor"


def fix_species_name(name):
    """
    Auto-correct scientific name capitalisation.
    Genus capitalised, species and infraspecific lowercase.
    Returns (corrected_name, was_changed bool).
    """
    name = name.strip()
    if not name:
        return name, False
    parts = name.split()
    corrected_parts = (
        [parts[0].capitalize()]
        + [p.lower() for p in parts[1:]]
    )
    corrected = " ".join(corrected_parts)
    return corrected, corrected != name


def parse_species_list(raw_text):
    """
    Parse species names from textarea.
    Accepts newline-separated OR comma-separated OR mixed.
    Auto-corrects capitalisation.
    Returns list of up to 5 unique corrected names.
    """
    if not raw_text.strip():
        return []
    parts  = re.split(r"[,\n]+", raw_text)
    names  = [p.strip() for p in parts if p.strip()]
    result = []
    for name in names:
        fixed, _ = fix_species_name(name)
        if fixed:
            result.append(fixed)
    seen = []
    for n in result:
        if n not in seen:
            seen.append(n)
    return seen[:5]


# ── init persistent state ─────────────────────────────────
if "map_type" not in st.session_state:
    st.session_state["map_type"] = "Point Map"


# ── sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<p class="sidebar-label">Mode</p>',
        unsafe_allow_html=True
    )
    mode = st.radio(
        "",
        [
            "Species Analysis",
            "Batch Comparison",
            "Publisher Report Card"
        ],
        label_visibility="collapsed"
    )
    st.divider()

    if mode == "Species Analysis":

        st.markdown(
            '<p class="sidebar-label">Quick Select</p>',
            unsafe_allow_html=True
        )
        sample_options = (
            ["— select a sample —"] + list(SAMPLE_SPECIES.values())
        )
        sample_choice = st.selectbox(
            "",
            sample_options,
            label_visibility="collapsed"
        )

        st.markdown(
            '<p class="sidebar-label">Species Name</p>',
            unsafe_allow_html=True
        )
        st.caption(
            "Genus capitalised, species lowercase. "
            "Example: Panthera leo"
        )
        species_input_raw = st.text_input(
            "",
            placeholder="e.g. Panthera leo",
            label_visibility="collapsed"
        )

        species_input = species_input_raw.strip()
        if species_input:
            species_input, was_fixed = fix_species_name(species_input)
            if was_fixed:
                st.warning(
                    f"Auto-corrected to: **{species_input}** — "
                    f"genus must be capitalised, "
                    f"species epithet lowercase."
                )

        if (
            sample_choice != "— select a sample —"
            and not species_input_raw.strip()
        ):
            species_input = sample_choice
            st.caption(f"Using sample: *{species_input}*")

        st.divider()

        st.markdown(
            '<p class="sidebar-label">Filters</p>',
            unsafe_allow_html=True
        )
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            year_from = st.number_input(
                "Year from",
                min_value=1000, max_value=2026,
                value=1900, step=1
            )
        with col_y2:
            year_to = st.number_input(
                "Year to",
                min_value=1000, max_value=2026,
                value=2026, step=1
            )

        basis_options = [
            "All", "HUMAN_OBSERVATION", "PRESERVED_SPECIMEN",
            "MACHINE_OBSERVATION", "LIVING_SPECIMEN",
            "LITERATURE", "FOSSIL_SPECIMEN"
        ]
        st.markdown(
            '<p class="sidebar-label">Basis of Record</p>',
            unsafe_allow_html=True
        )
        basis_filter = st.selectbox(
            "",
            basis_options,
            label_visibility="collapsed"
        )

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
            '<p class="sidebar-label">Map Type</p>',
            unsafe_allow_html=True
        )
        st.radio(
            "",
            ["Point Map", "Heatmap",
             "DBSCAN Outliers", "SDM Preview"],
            key="map_type",
            label_visibility="collapsed"
        )
        if "df" not in st.session_state:
            st.caption("Run an analysis to activate the map.")
        st.divider()

        search_btn = st.button(
            "Run Analysis",
            use_container_width=True,
            type="primary"
        )

        if "df" in st.session_state:
            if st.button("Clear Results", use_container_width=True):
                clear_results()
                st.rerun()

    elif mode == "Batch Comparison":

        st.markdown(
            '<p class="sidebar-label">Species to Compare</p>',
            unsafe_allow_html=True
        )
        st.caption(
            "Up to 5 species. Separate by comma or new line."
        )
        batch_input = st.text_area(
            "",
            placeholder=(
                "Panthera leo, Loxodonta africana\n"
                "Danaus plexippus"
            ),
            height=110,
            label_visibility="collapsed"
        )

        if batch_input.strip():
            preview = parse_species_list(batch_input)
            if preview:
                st.caption(
                    "Will compare: "
                    + " · ".join(f"*{n}*" for n in preview)
                )

        st.divider()

        st.markdown(
            '<p class="sidebar-label">Year Range</p>',
            unsafe_allow_html=True
        )
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            batch_year_from = st.number_input(
                "From",
                min_value=1000, max_value=2026,
                value=1900, step=1,
                key="batch_year_from"
            )
        with b_col2:
            batch_year_to = st.number_input(
                "To",
                min_value=1000, max_value=2026,
                value=2026, step=1,
                key="batch_year_to"
            )

        st.markdown(
            '<p class="sidebar-label">Records per Species</p>',
            unsafe_allow_html=True
        )
        batch_limit = st.slider(
            "",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
            label_visibility="collapsed",
            key="batch_limit"
        )

        if batch_limit > 400:
            st.warning(
                f"⚠️ {batch_limit} records × 5 species = up to "
                f"{batch_limit * 5:,} API calls. "
                f"This will be slow. "
                f"Recommended: 200 records or fewer."
            )
        elif batch_limit > 300:
            st.caption(
                f"Fetching {batch_limit} records per species. "
                f"This may take a moment."
            )
        else:
            st.caption(
                f"{batch_limit} records per species — good speed."
            )

        st.divider()

        batch_btn = st.button(
            "Compare Species",
            use_container_width=True,
            type="primary"
        )
        if "batch_results" in st.session_state:
            if st.button(
                "Clear Comparison",
                use_container_width=True
            ):
                st.session_state.pop("batch_results", None)
                st.rerun()

    else:
        st.markdown(
            '<p class="sidebar-label">'
            'Publisher / Institution Name</p>',
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
    st.caption("Data: [GBIF.org](https://www.gbif.org)")


# ══════════════════════════════════════════════════════════
# MODE: SPECIES ANALYSIS
# ══════════════════════════════════════════════════════════
if mode == "Species Analysis":

    if search_btn:
        if not species_input:
            st.warning(
                "Please enter a scientific name or select a sample."
            )
        else:
            progress_bar = st.progress(0, text="Connecting to GBIF...")

            try:
                pre_check = requests.get(
                    "https://api.gbif.org/v1/occurrence/search",
                    params={
                        "scientificName": species_input,
                        "limit"         : 1
                    },
                    timeout=10
                ).json()
                pre_count = pre_check.get("count", 0)

                if pre_count == 0:
                    progress_bar.empty()
                    clear_results()
                    st.error(
                        f"No occurrence records found for "
                        f"*{species_input}* in GBIF. "
                        f"Please check the spelling or try a "
                        f"different species name."
                    )
                    st.stop()

            except Exception:
                pass

            df, total, error = fetch_occurrences(
                species_name = species_input,
                limit        = limit,
                year_from    = int(year_from),
                year_to      = int(year_to),
                basis        = basis_filter
            )

            if error:
                progress_bar.empty()
                clear_results()
                st.error(error)
            else:
                progress_bar.progress(
                    0.5, text="Running quality checks..."
                )
                st.session_state["df"]           = df
                st.session_state["total"]         = total
                st.session_state["species"]       = species_input
                st.session_state["year_from"]     = int(year_from)
                st.session_state["year_to"]       = int(year_to)
                st.session_state["basis_filter"]  = basis_filter
                st.session_state["flags"]         = run_quality_checks(df)
                st.session_state["summary"]       = quality_summary(
                    st.session_state["flags"]
                )
                st.session_state["completeness"]  = get_completeness_score(df)

                progress_bar.progress(
                    0.7, text="Detecting outliers..."
                )
                st.session_state["outliers"]      = detect_outliers(df)
                st.session_state["reliability"]   = compute_reliability_score(df)

                progress_bar.progress(
                    0.85, text="Fetching species info..."
                )
                st.session_state["species_info"]  = get_species_info(
                    species_input
                )

                progress_bar.progress(
                    0.95, text="Checking multimedia..."
                )
                st.session_state["multimedia"]    = get_multimedia_stats(df)

                progress_bar.progress(1.0, text="Done!")
                progress_bar.empty()

    if "df" in st.session_state and mode == "Species Analysis":
        df           = st.session_state["df"]
        total        = st.session_state["total"]
        flags        = st.session_state["flags"]
        summary      = st.session_state["summary"]
        species      = st.session_state["species"]
        outliers     = st.session_state.get("outliers")
        reliability  = st.session_state.get("reliability")
        species_info = st.session_state.get("species_info")
        multimedia   = st.session_state.get("multimedia")
        completeness = st.session_state.get("completeness")
        yr_from      = st.session_state.get("year_from",    1900)
        yr_to        = st.session_state.get("year_to",      2026)
        basis_used   = st.session_state.get("basis_filter", "All")

        clean_df = df[~flags["any_flag"]].reset_index(drop=True)
        clean    = len(clean_df)
        score    = round(clean / len(flags) * 100, 1)

        # ── species card ──────────────────────────────────
        if species_info:
            col_img, col_info = st.columns([1, 4])
            with col_img:
                if species_info.get("image_url"):
                    st.image(
                        species_info["image_url"],
                        width=150,
                        use_container_width=False
                    )
                else:
                    st.markdown(
                        '<div style="width:120px;height:120px;'
                        'background:#21262D;border-radius:8px;'
                        'display:flex;align-items:center;'
                        'justify-content:center;'
                        'font-size:2.5rem">🌿</div>',
                        unsafe_allow_html=True
                    )
            with col_info:
                st.markdown(f"**{species_info['scientific_name']}**")
                if species_info.get("common_names"):
                    st.markdown(
                        f"*{', '.join(species_info['common_names'])}*"
                    )
                tax_data = {
                    "Kingdom": species_info.get("kingdom", "—"),
                    "Phylum" : species_info.get("phylum",  "—"),
                    "Class"  : species_info.get("class_",  "—"),
                    "Order"  : species_info.get("order",   "—"),
                    "Family" : species_info.get("family",  "—"),
                    "Genus"  : species_info.get("genus",   "—"),
                }
                tax_cols = st.columns(6)
                for i, (rank, value) in enumerate(tax_data.items()):
                    with tax_cols[i]:
                        st.markdown(
                            f'<div style="font-size:0.65rem;'
                            f'font-weight:600;text-transform:uppercase;'
                            f'letter-spacing:0.5px;color:#8B949E">'
                            f'{rank}</div>'
                            f'<div style="font-size:0.8rem;'
                            f'color:#C9D1D9;font-style:italic">'
                            f'{value}</div>',
                            unsafe_allow_html=True
                        )
                if species_info.get("gbif_url"):
                    st.markdown(
                        f'[View on GBIF]({species_info["gbif_url"]})'
                    )
        else:
            st.markdown(f"### *{species}*")

        filter_parts = []
        if yr_from != 1900 or yr_to != 2026:
            filter_parts.append(f"Year: {yr_from}–{yr_to}")
        if basis_used != "All":
            filter_parts.append(f"Basis: {basis_used}")
        if filter_parts:
            st.info(
                f"Active filters: {' · '.join(filter_parts)}. "
                f"All statistics reflect the filtered dataset only."
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total GBIF Records", f"{total:,}")
        with col2:
            st.metric("Records Analysed",   f"{len(df):,}")
        with col3:
            st.metric("Clean Records",       f"{clean:,}")
        with col4:
            st.metric("Health Score",        f"{score}%")

        st.divider()

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Overview",
            "Occurrence Map",
            "Temporal Analysis",
            "Charts",
            "Gap Analysis",
            "Data & Export"
        ])

        # ══════════════════════════════════════════════════
        # TAB 1 — Overview
        # ══════════════════════════════════════════════════
        with tab1:
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown(f"""
                <div class="health-bar-wrap">
                    <div class="health-label">Data Health Score</div>
                    <div class="health-score {score_class(score)}">
                        {score}% — {score_label(score)}
                    </div>
                    <div class="health-bar-bg">
                        <div class="health-bar-fill {bar_class(score)}"
                             style="width:{score}%"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if completeness:
                    cs = completeness["avg_score"]
                    st.markdown(f"""
                    <div class="completeness-bar-wrap">
                        <div class="health-label">
                            Record Completeness Score
                        </div>
                        <div class="health-score {score_class(cs)}">
                            {cs}%
                        </div>
                        <div class="health-bar-bg">
                            <div class="health-bar-fill {bar_class(cs)}"
                                 style="width:{cs}%"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    cm1, cm2, cm3 = st.columns(3)
                    with cm1:
                        st.metric(
                            "Fully Complete",
                            f"{completeness['full_count']:,}"
                        )
                    with cm2:
                        st.metric(
                            "High (80%+)",
                            f"{completeness['high_count']:,}"
                        )
                    with cm3:
                        st.metric(
                            "Low (<50%)",
                            f"{completeness['low_count']:,}"
                        )
                    with st.expander("Field-level Completeness"):
                        st.dataframe(
                            pd.DataFrame([
                                {"Field": k, "Fill Rate": f"{v}%"}
                                for k, v
                                in completeness["field_fill"].items()
                            ]),
                            use_container_width=True,
                            hide_index=True
                        )

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
                            "Check": check.replace(
                                "_", " "
                            ).title(),
                            "Flagged Records": stats["count"],
                            "Percentage"     : f"{stats['percent']}%",
                            "Status"         : (
                                "Issue Found"
                                if stats["count"] > 0 else "OK"
                            )
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
                if (
                    "has_issues" in summary
                    and summary["has_issues"]["count"] > 0
                ):
                    st.info(
                        f"{summary['has_issues']['count']} records "
                        f"carry GBIF internal flags — informational."
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
                    st.caption(
                        "Outlier % varies with record count and "
                        "geographic distribution of the sample."
                    )

                st.markdown(
                    '<p class="section-header">Multimedia Quality</p>',
                    unsafe_allow_html=True
                )
                if multimedia:
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric(
                            "Media Coverage",
                            f"{multimedia['coverage_pct']}%"
                        )
                    with m2:
                        st.metric(
                            "Missing Media",
                            f"{multimedia['missing_media']:,}"
                        )
                    with m3:
                        st.metric(
                            "Broken URLs",
                            f"{multimedia['broken_urls']:,}"
                        )
                    if multimedia["broken_pct"] > 20:
                        st.warning(
                            f"{multimedia['broken_pct']}% of sampled "
                            f"image URLs are inaccessible."
                        )
                    elif multimedia["coverage_pct"] < 20:
                        st.info(
                            f"Only {multimedia['coverage_pct']}% of "
                            f"records have images attached."
                        )
                    else:
                        st.success(
                            f"{multimedia['coverage_pct']}% of records "
                            f"have images — good multimedia coverage."
                        )
                    if multimedia["sample_checked"] > 0:
                        st.caption(
                            f"Broken URL check sampled "
                            f"{multimedia['sample_checked']} URLs."
                        )
                else:
                    st.info("Multimedia data not available.")

            with col_right:
                temporal_stats = get_temporal_stats(df)
                fitness        = get_data_fitness(
                    score, summary, temporal_stats
                )
                st.markdown(
                    '<p class="section-header">Data Fitness</p>',
                    unsafe_allow_html=True
                )
                st.caption(
                    "Based on currently fetched and filtered dataset."
                )
                for f in fitness:
                    badge = (
                        '<span class="fitness-badge-yes">Suitable</span>'
                        if f["suitable"] else
                        '<span class="fitness-badge-no">'
                        'Not Recommended</span>'
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
                    st.dataframe(
                        pd.DataFrame([
                            {"Precision Level": k, "Records": v}
                            for k, v in precision_stats.items()
                        ]),
                        use_container_width=True,
                        hide_index=True
                    )

                if "basisOfRecord" in df.columns:
                    st.markdown(
                        '<p class="section-header">Record Types</p>',
                        unsafe_allow_html=True
                    )
                    basis = (
                        df["basisOfRecord"]
                        .value_counts()
                        .reset_index()
                    )
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
                st.markdown(f"""
                <div class="rec-card rec-{rec['type']}">
                    <div class="rec-title">{rec['title']}</div>
                    <div class="rec-msg">{rec['message']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(
                '<p class="section-header">'
                'Quality by Contributing Dataset</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Identifies which datasets are contributing "
                "quality issues to this species analysis."
            )
            ds_df, ds_fig = get_dataset_quality_breakdown(df, flags)
            if ds_fig:
                st.plotly_chart(ds_fig, use_container_width=True)
            if ds_df is not None:
                st.dataframe(
                    ds_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "Dataset breakdown not available — "
                    "datasetName field missing from records."
                )

        # ══════════════════════════════════════════════════
        # TAB 2 — Occurrence Map
        # ══════════════════════════════════════════════════
        with tab2:
            st.markdown(
                '<p class="section-header">Occurrence Map</p>',
                unsafe_allow_html=True
            )
            map_type = st.session_state.get("map_type", "Point Map")
            st.caption(
                f"Showing: **{map_type}** — "
                f"change map type in the sidebar"
            )

            if map_type == "Point Map":
                st.markdown("""
                <div class="map-legend">
                    <span>
                        <span class="legend-dot dot-green"></span>
                        Clean
                    </span>
                    <span>
                        <span class="legend-dot dot-red"></span>
                        Flagged
                    </span>
                </div>
                """, unsafe_allow_html=True)
                try:
                    with st.spinner("Rendering map..."):
                        m = build_map(df, flags, map_type="points")
                        st_folium(
                            m, width=None, height=560,
                            returned_objects=[]
                        )
                except Exception as e:
                    st.error(f"Map error: {str(e)}")

            elif map_type == "Heatmap":
                try:
                    with st.spinner("Rendering heatmap..."):
                        m = build_map(df, flags, map_type="heatmap")
                        st_folium(
                            m, width=None, height=560,
                            returned_objects=[]
                        )
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
                                if outliers is not None
                                else False
                            )
                            color = (
                                "#F0883E" if is_out else "#3FB950"
                            )
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
                    st_folium(
                        m_db, width=None, height=560,
                        returned_objects=[]
                    )
                    if outliers is not None:
                        out_stats = outlier_summary(outliers)
                        st.info(
                            f"DBSCAN detected "
                            f"**{out_stats['outliers']}** spatial "
                            f"outliers "
                            f"({out_stats['outlier_pct']}% of records)"
                        )
                except Exception as e:
                    st.error(f"DBSCAN map error: {str(e)}")

            elif map_type == "SDM Preview":
                st.info(
                    "SDM Preview uses Kernel Density Estimation to "
                    "show predicted habitat suitability. "
                    "Red = high, green = low."
                )
                with st.spinner("Building SDM..."):
                    sdm_map, sdm_error = build_sdm_map(df)
                    if sdm_error:
                        st.error(sdm_error)
                    else:
                        st_folium(
                            sdm_map, width=None, height=560,
                            returned_objects=[]
                        )

        # ══════════════════════════════════════════════════
        # TAB 3 — Temporal Analysis
        # ══════════════════════════════════════════════════
        with tab3:
            st.markdown(
                '<p class="section-header">Temporal Overview</p>',
                unsafe_allow_html=True
            )
            if yr_from != 1900 or yr_to != 2026:
                st.caption(f"Filtered range: {yr_from}–{yr_to}")

            temporal_stats = get_temporal_stats(df)

            if temporal_stats:
                c1, c2, c3, c4 = st.columns(4)
                boxes = [
                    (temporal_stats['first_year'], "First Record"),
                    (temporal_stats['last_year'],  "Latest Record"),
                    (temporal_stats['span_years'], "Year Span"),
                    (temporal_stats['gap_count'],  "Years With No Data"),
                ]
                for col, (val, lbl) in zip(
                    [c1, c2, c3, c4], boxes
                ):
                    with col:
                        st.markdown(f"""
                        <div class="temporal-stat-box">
                            <div class="temporal-stat-value">
                                {val}
                            </div>
                            <div class="temporal-stat-label">
                                {lbl}
                            </div>
                        </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    fig_year = chart_records_per_year(df)
                    if fig_year:
                        st.plotly_chart(
                            fig_year, use_container_width=True
                        )
                    else:
                        st.info("Not enough yearly data.")
                with col2:
                    fig_decade = chart_decade_breakdown(df)
                    if fig_decade:
                        st.plotly_chart(
                            fig_decade, use_container_width=True
                        )

                st.markdown(
                    '<p class="section-header">Insights</p>',
                    unsafe_allow_html=True
                )
                insights = [
                    f"Peak recording year: "
                    f"**{temporal_stats['peak_year']}** "
                    f"({temporal_stats['peak_count']:,} records).",
                    f"Recording trend is "
                    f"**{temporal_stats['trend']}** over time.",
                    f"**{temporal_stats['recent_pct']}%** of records "
                    f"from the last 5 years of the filtered range."
                ]
                if temporal_stats["cs_surge"]:
                    insights.append(
                        "Significant **citizen science surge** "
                        "detected post-2008."
                    )
                if temporal_stats["major_gaps"]:
                    gap_strs = [
                        f"{s}–{e}"
                        for s, e
                        in temporal_stats["major_gaps"][:3]
                    ]
                    insights.append(
                        f"Major data gaps: "
                        f"**{', '.join(gap_strs)}**"
                    )
                for insight in insights:
                    st.markdown(f"- {insight}")
            else:
                st.info(
                    "Not enough temporal data. "
                    "Try widening your year range filter."
                )

        # ══════════════════════════════════════════════════
        # TAB 4 — Charts
        # ══════════════════════════════════════════════════
        with tab4:
            st.markdown(
                '<p class="section-header">'
                'Geographic & Seasonal Analysis</p>',
                unsafe_allow_html=True
            )
            fig_density = chart_country_density(df)
            if fig_density:
                st.plotly_chart(
                    fig_density, use_container_width=True
                )
            else:
                st.info("No country data for density chart.")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                fig_month = chart_records_per_month(df)
                if fig_month:
                    st.plotly_chart(
                        fig_month, use_container_width=True
                    )
                else:
                    st.info("Not enough month data.")

                fig_basis = chart_basis_of_record(df)
                if fig_basis:
                    st.plotly_chart(
                        fig_basis, use_container_width=True
                    )
                else:
                    st.info("No basis of record data.")

            with col2:
                fig_country = chart_top_countries(df)
                if fig_country:
                    st.plotly_chart(
                        fig_country, use_container_width=True
                    )
                else:
                    st.info("No country data.")

        # ══════════════════════════════════════════════════
        # TAB 5 — Gap Analysis
        # ══════════════════════════════════════════════════
        with tab5:
            st.markdown(
                '<p class="section-header">Global Data Gap Map</p>',
                unsafe_allow_html=True
            )

            # ── clear gap map explanation ─────────────────
            st.info(
                "This map divides the world into 10° grid cells. "
                "**Coloured cells** show where occurrence records "
                "exist for this species. "
                "**Uncoloured (dark) cells** have no records at all "
                "— these are the data gaps. "
                "Most of the world will appear dark for any species "
                "because species don't occur everywhere."
            )
            st.caption(
                "🟢 Data rich · 🟡 Sparse · 🟠 Very sparse · "
                "🔴 Only 1–2 records in cell. "
                "Dark = no records in GBIF for this species."
            )

            gap_stats = get_gap_stats(df)
            if gap_stats:
                g1, g2, g3 = st.columns(3)
                with g1:
                    st.metric(
                        "Grid Cells With Data",
                        f"{gap_stats['covered']:,}"
                    )
                with g2:
                    st.metric(
                        "Global Grid Coverage",
                        f"{gap_stats['cov_pct']}%"
                    )
                with g3:
                    st.metric(
                        "Countries With Records",
                        f"{gap_stats['countries']:,}"
                    )

            with st.spinner("Building gap map..."):
                gap_map = build_gap_map(df)
                if gap_map:
                    st_folium(
                        gap_map, width=None, height=500,
                        returned_objects=[]
                    )
                else:
                    st.error("Could not build gap map.")

            alerts = get_gap_alerts(df)
            if alerts:
                st.markdown(
                    '<p class="section-header">'
                    'Spatial Coverage Alerts</p>',
                    unsafe_allow_html=True
                )
                for alert in alerts:
                    st.markdown(f"""
                    <div class="rec-card rec-{alert['type']}">
                        <div class="rec-title">{alert['title']}</div>
                        <div class="rec-msg">{alert['message']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # ══════════════════════════════════════════════════
        # TAB 6 — Data & Export
        # ══════════════════════════════════════════════════
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
                        "High Reliability (80+)",
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
                '<p class="section-header">'
                'Before & After Cleaning</p>',
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
                f"({round(removed/len(df)*100,1)}% of total)"
            )

            st.divider()

            st.markdown(
                '<p class="section-header">Download CSV</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Includes clean image_url column and readable "
                "GBIF issue flags."
            )
            export_full  = prepare_export_df(df)
            export_clean = prepare_export_df(clean_df)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    label="Download Full Dataset",
                    data=export_full.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name=(
                        f"biosift_"
                        f"{species.replace(' ','_')}_full.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption(f"{len(df):,} records")
            with col2:
                st.download_button(
                    label="Download Clean Records",
                    data=export_clean.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name=(
                        f"biosift_"
                        f"{species.replace(' ','_')}_clean.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True
                )
                st.caption(f"{clean:,} records")
            with col3:
                if reliability is not None:
                    export_scored = prepare_export_df(df_with_rel)
                    st.download_button(
                        label="Download Scored Records",
                        data=export_scored.to_csv(
                            index=False
                        ).encode("utf-8"),
                        file_name=(
                            f"biosift_"
                            f"{species.replace(' ','_')}_scored.csv"
                        ),
                        mime="text/csv",
                        use_container_width=True
                    )
                    st.caption(f"{len(df):,} records + scores")

            st.divider()

            st.markdown(
                '<p class="section-header">'
                'Darwin Core Archive (DwC-A)</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Standards-compliant ZIP: occurrence.csv + "
                "meta.xml (TDWG field mapping) + "
                "eml.xml (EML dataset metadata). "
                "Compatible with GBIF, iDigBio and ALA."
            )
            dwca_col1, dwca_col2 = st.columns(2)
            with dwca_col1:
                dwca_full, dwca_err = build_dwca(
                    df, species, score, clean_only=False
                )
                if dwca_full:
                    st.download_button(
                        label="Download Full DwC-A",
                        data=dwca_full,
                        file_name=(
                            f"biosift_"
                            f"{species.replace(' ','_')}"
                            f"_full.dwca.zip"
                        ),
                        mime="application/zip",
                        use_container_width=True
                    )
                    st.caption(f"{len(df):,} records")
                else:
                    st.error(f"DwC-A error: {dwca_err}")
            with dwca_col2:
                dwca_clean, dwca_err2 = build_dwca(
                    clean_df, species, score, clean_only=True
                )
                if dwca_clean:
                    st.download_button(
                        label="Download Clean DwC-A",
                        data=dwca_clean,
                        file_name=(
                            f"biosift_"
                            f"{species.replace(' ','_')}"
                            f"_clean.dwca.zip"
                        ),
                        mime="application/zip",
                        use_container_width=True
                    )
                    st.caption(f"{clean:,} clean records")
                else:
                    st.error(f"DwC-A error: {dwca_err2}")

            st.divider()

            st.markdown(
                '<p class="section-header">'
                'Reproducible Methods Paragraph</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "Copy and paste into your research paper."
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
                '<p class="section-header">'
                'GBIF Dataset Citation</p>',
                unsafe_allow_html=True
            )
            st.caption(
                "For a permanent DOI, download directly from GBIF."
            )
            citation = generate_citation(
                species, df,
                species_info=st.session_state.get("species_info")
            )
            cite_t1, cite_t2 = st.tabs(["APA", "BibTeX"])
            with cite_t1:
                st.text_area(
                    "",
                    value=citation["apa"],
                    height=120,
                    label_visibility="collapsed",
                    key="citation_apa"
                )
            with cite_t2:
                st.text_area(
                    "",
                    value=citation["bibtex"],
                    height=180,
                    label_visibility="collapsed",
                    key="citation_bibtex"
                )
            st.markdown(f"""
            <div class="citation-note">
                {citation['note']}
                &nbsp;<a href="{citation['search_url']}"
                         target="_blank"
                         style="color:#58A6FF">
                    View on GBIF
                </a>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            st.markdown(
                '<p class="section-header">Preview</p>',
                unsafe_allow_html=True
            )
            if reliability is not None:
                st.dataframe(
                    prepare_export_df(df_with_rel),
                    use_container_width=True
                )
            else:
                st.dataframe(
                    prepare_export_df(df),
                    use_container_width=True
                )


# ══════════════════════════════════════════════════════════
# MODE: BATCH COMPARISON
# ══════════════════════════════════════════════════════════
elif mode == "Batch Comparison":

    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <p style="font-size:1.1rem;font-weight:600;
                  color:#F0F6FC;margin:0">
            Batch Species Comparison
        </p>
        <p style="font-size:0.875rem;color:#8B949E;
                  margin:0.3rem 0 0 0">
            Compare data quality metrics across multiple species
            side by side. Accepts comma or newline-separated names.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if batch_btn:
        species_list = parse_species_list(batch_input)

        if not species_list:
            st.warning(
                "Please enter at least one species name. "
                "Separate multiple names by comma or new line."
            )
        else:
            b_yr_from = int(
                st.session_state.get("batch_year_from", 1900)
            )
            b_yr_to   = int(
                st.session_state.get("batch_year_to",   2026)
            )
            b_limit   = int(
                st.session_state.get("batch_limit", 200)
            )

            results = []
            prog = st.progress(0, text="Starting batch analysis...")

            for i, sp in enumerate(species_list):
                prog.progress(
                    i / len(species_list),
                    text=f"Analysing {sp} "
                         f"({i+1}/{len(species_list)})..."
                )
                try:
                    df_sp, total_sp, err = fetch_occurrences(
                        species_name = sp,
                        limit        = b_limit,
                        year_from    = b_yr_from,
                        year_to      = b_yr_to
                    )
                    if err or df_sp is None:
                        results.append({
                            "species"         : sp,
                            "error"           : err or "No data",
                            "total"           : 0,
                            "analysed"        : 0,
                            "health"          : None,
                            "completeness"    : None,
                            "duplicates"      : None,
                            "missing_coords"  : None,
                            "low_precision"   : None,
                            "country_mismatch": None,
                            "avg_reliability" : None,
                        })
                        continue

                    fl_sp  = run_quality_checks(df_sp)
                    sm_sp  = quality_summary(fl_sp)
                    rel_sp = compute_reliability_score(df_sp)
                    cs_sp  = get_completeness_score(df_sp)

                    clean_sp = int((~fl_sp["any_flag"]).sum())
                    health   = round(clean_sp / len(fl_sp) * 100, 1)

                    results.append({
                        "species"         : sp,
                        "error"           : None,
                        "total"           : total_sp,
                        "analysed"        : len(df_sp),
                        "health"          : health,
                        "completeness"    : (
                            cs_sp["avg_score"]
                            if cs_sp else None
                        ),
                        "duplicates"      : sm_sp.get(
                            "duplicate", {}
                        ).get("percent", 0),
                        "missing_coords"  : sm_sp.get(
                            "missing_coords", {}
                        ).get("percent", 0),
                        "low_precision"   : sm_sp.get(
                            "low_precision", {}
                        ).get("percent", 0),
                        "country_mismatch": sm_sp.get(
                            "country_mismatch", {}
                        ).get("percent", 0),
                        "avg_reliability" : round(
                            rel_sp.mean(), 1
                        ),
                    })

                except Exception as e:
                    results.append({
                        "species"         : sp,
                        "error"           : str(e),
                        "total"           : 0,
                        "analysed"        : 0,
                        "health"          : None,
                        "completeness"    : None,
                        "duplicates"      : None,
                        "missing_coords"  : None,
                        "low_precision"   : None,
                        "country_mismatch": None,
                        "avg_reliability" : None,
                    })

            prog.progress(1.0, text="Done!")
            prog.empty()
            st.session_state["batch_results"] = results
            st.session_state["batch_year_from_used"] = b_yr_from
            st.session_state["batch_year_to_used"]   = b_yr_to
            st.session_state["batch_limit_used"]      = b_limit

    if "batch_results" in st.session_state:
        results  = st.session_state["batch_results"]
        ok       = [r for r in results if r["error"] is None]
        failed   = [r for r in results if r["error"] is not None]

        b_yr_from_used = st.session_state.get(
            "batch_year_from_used", 1900
        )
        b_yr_to_used   = st.session_state.get(
            "batch_year_to_used",   2026
        )
        b_limit_used   = st.session_state.get(
            "batch_limit_used", 200
        )

        st.caption(
            f"Results for year range: **{b_yr_from_used}–"
            f"{b_yr_to_used}** · "
            f"{b_limit_used} records per species"
        )

        if failed:
            for f in failed:
                st.warning(
                    f"Could not fetch **{f['species']}**: "
                    f"{f['error']}"
                )

        if ok:
            # score cards
            st.markdown(
                '<p class="section-header">'
                'Health Score Comparison</p>',
                unsafe_allow_html=True
            )
            cols = st.columns(len(ok))
            for i, r in enumerate(ok):
                with cols[i]:
                    h  = r["health"]
                    sc = score_class(h)
                    st.markdown(f"""
                    <div class="compare-card">
                        <div class="compare-species">
                            {r['species']}
                        </div>
                        <div class="compare-score {sc}">
                            {h}%
                        </div>
                        <div style="font-size:0.75rem;
                                    color:#8B949E;
                                    margin-top:0.3rem;">
                            Health Score
                        </div>
                        <div style="font-size:0.75rem;
                                    color:#8B949E;">
                            {r['analysed']:,} records analysed
                        </div>
                        <div style="font-size:0.7rem;
                                    color:#3FB950;
                                    margin-top:0.2rem;">
                            {r['total']:,} total in GBIF
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # comparison table
            st.markdown(
                '<p class="section-header">'
                'Full Comparison Table</p>',
                unsafe_allow_html=True
            )
            table_rows = []
            for r in ok:
                table_rows.append({
                    "Species"         : r["species"],
                    "GBIF Total"      : f"{r['total']:,}",
                    "Analysed"        : f"{r['analysed']:,}",
                    "Health Score"    : f"{r['health']}%",
                    "Completeness"    : (
                        f"{r['completeness']}%"
                        if r["completeness"] is not None else "—"
                    ),
                    "Duplicates"      : f"{r['duplicates']}%",
                    "Missing Coords"  : f"{r['missing_coords']}%",
                    "Low Precision"   : f"{r['low_precision']}%",
                    "Country Mismatch": f"{r['country_mismatch']}%",
                    "Avg Reliability" : (
                        f"{r['avg_reliability']}/100"
                        if r["avg_reliability"] is not None else "—"
                    ),
                })
            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                hide_index=True
            )

            # grouped bar chart
            st.markdown(
                '<p class="section-header">'
                'Visual Comparison</p>',
                unsafe_allow_html=True
            )
            import plotly.graph_objects as go

            metrics = [
                "health", "completeness",
                "duplicates", "missing_coords",
                "low_precision", "country_mismatch"
            ]
            metric_labels = [
                "Health Score", "Completeness",
                "Duplicates %", "Missing Coords %",
                "Low Precision %", "Country Mismatch %"
            ]
            colors_list = [
                "#3FB950", "#58A6FF", "#F0883E",
                "#BC8CFF", "#E3B341", "#F85149"
            ]

            fig = go.Figure()
            for i, r in enumerate(ok):
                vals = [r.get(m) or 0 for m in metrics]
                fig.add_trace(go.Bar(
                    name=r["species"],
                    x=metric_labels,
                    y=vals,
                    marker_color=colors_list[
                        i % len(colors_list)
                    ],
                    text=[f"{v}%" for v in vals],
                    textposition="outside",
                    textfont=dict(size=10)
                ))

            fig.update_layout(
                barmode="group",
                plot_bgcolor="#161B22",
                paper_bgcolor="#161B22",
                font_color="#F0F6FC",
                legend=dict(
                    bgcolor="#1C2128",
                    bordercolor="#21262D"
                ),
                yaxis=dict(
                    gridcolor="#21262D",
                    range=[0, 120]
                ),
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            compare_csv = (
                pd.DataFrame(table_rows)
                .to_csv(index=False)
                .encode("utf-8")
            )
            st.download_button(
                label="Download Comparison (CSV)",
                data=compare_csv,
                file_name="biosift_batch_comparison.csv",
                mime="text/csv"
            )


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
            st.warning(
                "Please enter a publisher or institution name."
            )
        else:
            with st.spinner(f"Searching for {publisher_input}..."):
                publishers, error = search_publisher(publisher_input)
                if error:
                    st.error(error)
                elif not publishers:
                    st.error(
                        "No publisher found. Try a different name."
                    )
                else:
                    st.session_state["publishers"] = publishers
                    st.session_state["pub_input"]  = publisher_input

    if (
        "publishers" in st.session_state
        and mode == "Publisher Report Card"
    ):
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

    if (
        "pub_report" in st.session_state
        and mode == "Publisher Report Card"
    ):
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
        csv_pub = (
            report["datasets"]
            .to_csv(index=False)
            .encode("utf-8")
        )
        st.download_button(
            label="Download Publisher Report (CSV)",
            data=csv_pub,
            file_name=(
                f"biosift_publisher_"
                f"{report['publisher'].replace(' ','_')}.csv"
            ),
            mime="text/csv"
        )