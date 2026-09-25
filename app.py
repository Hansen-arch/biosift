"""
BioSift — biodiversity data intelligence platform
Entry point. Pages live in views/ and are wired via st.navigation.
"""

import streamlit as st

import utils.theme as T
from views.home import render as home_render
from views.analysis import render as analysis_render
from views.batch import render as batch_render
from views.publisher import render as publisher_render
from views.methods import render as methods_render

st.set_page_config(
    page_title="BioSift",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

T.inject_css()

pages = [
    st.Page(home_render,       title="Home",                icon=":material/home:",
            default=True, url_path="home"),
    st.Page(analysis_render,   title="Species Analysis",    icon=":material/biotech:",
            url_path="analysis"),
    st.Page(batch_render,      title="Batch Comparison",    icon=":material/scale:",
            url_path="batch"),
    st.Page(publisher_render,  title="Publisher Report",    icon=":material/account_balance:",
            url_path="publisher"),
    st.Page(methods_render,    title="Methods & Standards", icon=":material/straighten:",
            url_path="methods"),
]

nav = st.navigation(pages)

# ── sidebar brand + nav ───────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="sb-brand">
        <div class="sb-logo">B</div>
        <div>
            <div class="sb-name">BioSift</div>
            <div class="sb-tag">Biodiversity IQ</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

nav.run()

# ── sidebar footer ────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.caption(
        "Data: [GBIF.org](https://www.gbif.org) · CC-BY\n\n"
        "Built for the [Ebbe Nielsen Challenge 2026]"
        "(https://www.gbif.org/ebbe)"
    )
