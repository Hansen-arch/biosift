"""
BioSift — Publisher Report Card page
"""

import streamlit as st

import utils.theme as T
from utils.publisher import search_publisher, build_publisher_report


def render():
    T.inject_css()
    T.page_head(
        "Publisher Report Card",
        "Assess the data quality and coverage of any GBIF publishing "
        "institution — the same feedback loop the community uses to improve "
        "data at the source."
    )

    publisher_input = st.text_input(
        "Publisher or institution",
        placeholder="e.g. iNaturalist, NHM London, Senckenberg",
    )

    if st.button("Get Report Card", type="primary", use_container_width=True):
        if not publisher_input.strip():
            st.warning("Please enter a publisher or institution name.")
        else:
            with st.spinner(f"Searching for {publisher_input}…"):
                publishers, error = search_publisher(publisher_input)
                if error:
                    st.error(error)
                elif not publishers:
                    st.error("No publisher found — try a different name.")
                else:
                    st.session_state["publishers"] = publishers
                    st.session_state["pub_input"] = publisher_input

    if "publishers" in st.session_state:
        publishers = st.session_state["publishers"]
        T.section("Select publisher")
        pub_options = {
            p.get("title", "Unknown"): p.get("key", "")
            for p in publishers
        }
        selected_name = st.selectbox(
            "publisher", list(pub_options.keys()),
            label_visibility="collapsed",
        )
        selected_key = pub_options[selected_name]

        if st.button("Load Report", type="primary"):
            with st.spinner("Fetching publisher datasets…"):
                report, rep_error = build_publisher_report(
                    selected_key, selected_name, limit=10,
                )
                if rep_error:
                    st.error(rep_error)
                else:
                    st.session_state["pub_report"] = report

    if "pub_report" in st.session_state:
        report = st.session_state["pub_report"]
        T.section("Overview")
        st.markdown(f"""
        <div class="card">
            <div class="card-t" style="font-size:1.15rem">
                {report['publisher']}
            </div>
            <div class="card-d">
                {report['dataset_count']} datasets ·
                {report['total_records']:,} total records published
            </div>
        </div>
        """, unsafe_allow_html=True)

        T.section("Dataset overview")
        st.dataframe(report["datasets"], use_container_width=True,
                     hide_index=True)

        csv = (report["datasets"].to_csv(index=False).encode("utf-8"))
        st.download_button(
            "Download Publisher Report (CSV)",
            data=csv,
            file_name=(
                f"biosift_publisher_"
                f"{report['publisher'].replace(' ', '_')}.csv"
            ),
            mime="text/csv",
        )
    T.footer()
