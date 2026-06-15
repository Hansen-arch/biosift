import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from utils.gbif_fetch import fetch_occurrences, SAMPLE_SPECIES
from utils.quality import run_quality_checks, quality_summary
from utils.maps import build_map
from utils.iucn import get_iucn_status
from utils.charts import (
    chart_records_per_year,
    chart_records_per_month,
    chart_basis_of_record,
    chart_top_countries
)

# ── page config ───────────────────────────────────────────
st.set_page_config(
    page_title="GBIF QuickCheck",
    page_icon="🌍",
    layout="wide"
)

# ── header ────────────────────────────────────────────────
st.title("🌍 GBIF QuickCheck")
st.markdown("**Instant biodiversity data quality diagnostics powered by GBIF**")
st.divider()

# ── sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.gbif.org/img/logo/GBIF-2015.png", width=150)
    st.header("⚙️ Search Settings")

    st.subheader("Quick Select")
    sample_choice = st.selectbox(
        "Load a sample species",
        ["— select —"] + list(SAMPLE_SPECIES.keys())
    )

    st.subheader("Custom Search")
    species_input = st.text_input(
        "Species name",
        placeholder="e.g. Panthera leo"
    )

    if sample_choice != "— select —":
        species_input = SAMPLE_SPECIES[sample_choice]
        st.info(f"Using: *{species_input}*")

    limit = st.slider("Max records to fetch", 100, 10000, 300, step=100)

    st.divider()

    st.subheader("🔴 IUCN Red List")
    iucn_key = st.text_input(
        "IUCN API Key (optional)",
        type="password",
        placeholder="Get free key at iucnredlist.org"
    )
    if not iucn_key:
        st.caption("Without key, IUCN status won't show")

    st.divider()

    search_btn = st.button("🔍 Run Analysis", use_container_width=True)

    st.divider()
    st.caption("Built for the 2026 GBIF Ebbe Nielsen Challenge")
    st.caption("Data source: [GBIF.org](https://www.gbif.org)")

# ── search logic ──────────────────────────────────────────
if search_btn:
    if not species_input:
        st.warning("⚠️ Please enter a species name or select a sample.")
    else:
        with st.spinner(f"Fetching GBIF data for *{species_input}*..."):
            df, total, error = fetch_occurrences(species_input, limit)

            if error:
                st.error(f"❌ {error}")
            else:
                st.session_state["df"]      = df
                st.session_state["total"]   = total
                st.session_state["species"] = species_input
                st.session_state["flags"]   = run_quality_checks(df)
                st.session_state["summary"] = quality_summary(
                    st.session_state["flags"]
                )

                if iucn_key:
                    with st.spinner("Fetching IUCN status..."):
                        iucn = get_iucn_status(species_input, iucn_key)
                        if iucn is None:
                            st.warning(
                                "⚠️ IUCN status not found. "
                                "Check species name or API key."
                            )
                        st.session_state["iucn"] = iucn
                else:
                    st.session_state["iucn"] = None

# ── results ───────────────────────────────────────────────
if "df" in st.session_state:
    df      = st.session_state["df"]
    total   = st.session_state["total"]
    flags   = st.session_state["flags"]
    summary = st.session_state["summary"]
    species = st.session_state["species"]
    iucn    = st.session_state.get("iucn")

    clean = len(flags) - int(summary["any_flag"]["count"])
    score = round(clean / len(flags) * 100, 1)

    # ── top metrics row ───────────────────────────────────
    st.subheader(f"Results for *{species}*")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total GBIF Records", f"{total:,}")
    with col2:
        st.metric("Records Analysed", f"{len(df):,}")
    with col3:
        st.metric("Clean Records", f"{clean:,}")
    with col4:
        st.metric("Health Score", f"{score}%")

    # ── IUCN badge ────────────────────────────────────────
    if iucn:
        status_colors = {
            "EX": "red", "EW": "red",
            "CR": "red", "EN": "orange",
            "VU": "orange", "NT": "green",
            "LC": "green", "DD": "gray", "NE": "gray"
        }
        color = status_colors.get(iucn["category"], "gray")
        st.markdown(
            f"**IUCN Red List Status:** "
            f"{iucn['emoji']} :{color}[**{iucn['label']} "
            f"({iucn['category']})**] "
            f"— *{iucn['scientific_name']}* "
            f"(assessed {iucn['published_year']})"
        )

    st.divider()

    # ── tabs ──────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Overview",
        "🗺️ Occurrence Map",
        "📊 Charts",
        "📦 Data & Export"
    ])

    # ── TAB 1: Overview ───────────────────────────────────
    with tab1:
        if score >= 80:
            st.success(f"✅ Data Health Score: {score}% — Good")
        elif score >= 50:
            st.warning(f"⚠️ Data Health Score: {score}% — Fair")
        else:
            st.error(f"❌ Data Health Score: {score}% — Poor")

        skip = ["any_flag", "has_issues"]

        st.subheader("Quality Issues Breakdown")

        issue_rows = []
        found_any = False

        for check, stats in summary.items():
            if check not in skip:
                issue_rows.append({
                    "Check": check.replace("_", " ").title(),
                    "Flagged Records": stats["count"],
                    "Percentage": f"{stats['percent']}%",
                    "Status": "⚠️ Issue" if stats["count"] > 0 else "✅ OK"
                })
                if stats["count"] > 0:
                    found_any = True

        st.dataframe(
            pd.DataFrame(issue_rows),
            use_container_width=True,
            hide_index=True
        )

        if not found_any:
            st.success("✅ No major quality issues found!")

        if "has_issues" in summary and summary["has_issues"]["count"] > 0:
            st.info(
                f"ℹ️ {summary['has_issues']['count']} records carry GBIF "
                f"internal flags. These are informational and do not "
                f"affect the health score."
            )

        if "basisOfRecord" in df.columns:
            st.subheader("Record Types")
            basis = df["basisOfRecord"].value_counts().reset_index()
            basis.columns = ["Basis of Record", "Count"]
            st.dataframe(basis, use_container_width=True, hide_index=True)

    # ── TAB 2: Map ────────────────────────────────────────
    with tab2:
        st.subheader("Occurrence Map")
        st.caption(
            "🟢 Clean records   🔴 Flagged records — "
            "click any point for details"
        )
        try:
            with st.spinner("Rendering map..."):
                m = build_map(df, flags)
                st_folium(m, width=None, height=550, returned_objects=[])
        except Exception as e:
            st.error(f"❌ Map failed to render: {str(e)}")

    # ── TAB 3: Charts ─────────────────────────────────────
    with tab3:
        st.subheader("Temporal & Geographic Analysis")

        col1, col2 = st.columns(2)

        with col1:
            fig_year = chart_records_per_year(df)
            if fig_year:
                st.plotly_chart(fig_year, use_container_width=True)
            else:
                st.info("ℹ️ Not enough year data to plot.")

            fig_basis = chart_basis_of_record(df)
            if fig_basis:
                st.plotly_chart(fig_basis, use_container_width=True)
            else:
                st.info("ℹ️ No basis of record data available.")

        with col2:
            fig_month = chart_records_per_month(df)
            if fig_month:
                st.plotly_chart(fig_month, use_container_width=True)
            else:
                st.info("ℹ️ Not enough month data to plot.")

            fig_country = chart_top_countries(df)
            if fig_country:
                st.plotly_chart(fig_country, use_container_width=True)
            else:
                st.info("ℹ️ No country data available.")

    # ── TAB 4: Data & Export ──────────────────────────────
    with tab4:
        st.subheader("Download Data")

        col1, col2 = st.columns(2)

        with col1:
            csv_full = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Full Data (CSV)",
                data=csv_full,
                file_name=f"gbif_{species.replace(' ', '_')}_full.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            clean_df = df[~flags["any_flag"]].reset_index(drop=True)
            csv_clean = clean_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Clean Records Only (CSV)",
                data=csv_clean,
                file_name=f"gbif_{species.replace(' ', '_')}_clean.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.caption(
            f"Full data: {len(df):,} records | "
            f"Clean data: {len(clean_df):,} records"
        )

        st.divider()
        st.subheader("Preview")
        st.dataframe(df, use_container_width=True)