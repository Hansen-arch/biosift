import streamlit as st
from streamlit_folium import st_folium
from utils.gbif_fetch import fetch_occurrences
from utils.quality import run_quality_checks, quality_summary
from utils.maps import build_map
from utils.charts import (
    chart_records_per_year,
    chart_records_per_month,
    chart_basis_of_record,
    chart_top_countries
)

st.title("🌍 GBIF QuickCheck")
st.write("Instant biodiversity data diagnostics")

species = st.text_input("Enter species name", "Panthera leo")
limit = st.slider("Max records", 100, 10000, 1000, step=100)

if st.button("Search"):
    with st.spinner("Fetching from GBIF..."):
        df, total = fetch_occurrences(species, limit)

        if df is None:
            st.error("No records found. Try another species name.")
        else:
            st.session_state["df"] = df
            st.session_state["total"] = total
            st.session_state["flags"] = run_quality_checks(df)
            st.session_state["summary"] = quality_summary(st.session_state["flags"])

if "df" in st.session_state:
    df = st.session_state["df"]
    total = st.session_state["total"]
    flags = st.session_state["flags"]
    summary = st.session_state["summary"]

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Overview", "🗺️ Map", "📊 Charts", "📦 Data"])

    with tab1:
        st.subheader("Summary")
        st.success(f"Showing {len(df)} of {total:,} total records")

        clean = len(flags) - int(summary["any_flag"]["count"])
        score = round(clean / len(flags) * 100, 1)

        if score >= 80:
            st.success(f"✅ Data Health Score: {score}% — Good")
        elif score >= 50:
            st.warning(f"⚠️ Data Health Score: {score}% — Fair")
        else:
            st.error(f"❌ Data Health Score: {score}% — Poor")

        skip = ["any_flag", "has_issues"]

        st.subheader("Quality Issues Found")
        found_any = False
        for check, stats in summary.items():
            if check not in skip and stats["count"] > 0:
                st.write(f"⚠️ **{check}**: {stats['count']} records ({stats['percent']}%)")
                found_any = True

        if not found_any:
            st.write("✅ No major issues found!")

        if "has_issues" in summary and summary["has_issues"]["count"] > 0:
            st.info(f"ℹ️ {summary['has_issues']['count']} records have GBIF flags (informational only, does not affect health score)")

    with tab2:
        st.subheader("Occurrence Map")
        st.caption("🟢 Clean records   🔴 Flagged records")
        m = build_map(df, flags)
        st_folium(m, width=700, height=500, returned_objects=[])

    with tab3:
        st.subheader("Charts")
        col1, col2 = st.columns(2)

        with col1:
            fig_year = chart_records_per_year(df)
            st.plotly_chart(fig_year, use_container_width=True)

            fig_basis = chart_basis_of_record(df)
            if fig_basis:
                st.plotly_chart(fig_basis, use_container_width=True)

        with col2:
            fig_month = chart_records_per_month(df)
            st.plotly_chart(fig_month, use_container_width=True)

            fig_country = chart_top_countries(df)
            if fig_country:
                st.plotly_chart(fig_country, use_container_width=True)

    with tab4:
        st.subheader("Raw Data")
        st.dataframe(df)