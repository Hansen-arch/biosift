"""
BioSift — Home / landing page
"""

import streamlit as st

import utils.theme as T
from utils.icons import icon

FEATURES = [
    {
        "icon": "dna",
        "title": "Standards-aligned quality audit",
        "desc": "Ten automated checks mapped to the official TDWG BDQ test "
                "vocabulary — the same language GBIF publishers and nodes use.",
    },
    {
        "icon": "pulse",
        "title": "GBIF-wide benchmarking",
        "desc": "Is your sample bad — or is every sample like this? Defect "
                "rates compared against the full GBIF population, live.",
    },
    {
        "icon": "globe",
        "title": "Species interactions (GloBI)",
        "desc": "Predator–prey, pollination and symbiosis records alongside "
                "distribution data — a GBIF priority data area, surfaced here.",
    },
    {
        "icon": "target",
        "title": "SDM readiness audit",
        "desc": "Journal-cited filtering gates (Zizka 2020, Marcer 2022) with "
                "disclosed strictness profiles — know before you model.",
    },
    {
        "icon": "download",
        "title": "Reproducibility Pack",
        "desc": "One click exports a reviewer-ready ZIP: report JSON, "
                "methods text, citations, CSVs, DwC-A and the exact API recipe.",
    },
    {
        "icon": "book",
        "title": "Publication-grade outputs",
        "desc": "Branded PDF quality report, Darwin Core Archive, GBIF data "
                "cube SQL — built for theses, DMPs and indicator pipelines.",
    },
]

WHO = [
    ("Researchers", "Pre-flight data checks before SDMs and trend analyses"),
    ("Data managers", "Per-dataset defect attribution with A–F grades"),
    ("Node staff", "Publisher report cards in the shared BDQ vocabulary"),
    ("Policy analysts", "Reliability statements for GBF indicator workflows"),
]


def render():
    T.inject_css()

    st.markdown(f"""
    <div class="hero">
        <div class="hero-kicker">{icon('spark', 14)} GBIF Ebbe Nielsen Challenge 2026</div>
        <h1 class="hero-title">Know your biodiversity data<br>before it lets you down.</h1>
        <p class="hero-sub">BioSift audits GBIF occurrence data in seconds — scoring health,
        benchmarking against the global population, and exporting
        standards-aligned evidence packs that reviewers and indicator pipelines can trust.</p>
        <div class="hero-actions">
            <span class="hero-pill">{icon('shield', 14)} 10 automated quality checks</span>
            <span class="hero-pill">{icon('ruler', 14)} TDWG BDQ aligned</span>
            <span class="hero-pill">{icon('pulse', 14)} GBIF-wide benchmarking</span>
            <span class="hero-pill">{icon('download', 14)} Reproducibility Pack</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    T.section("What BioSift does")
    cols = st.columns(3)
    for i, f in enumerate(FEATURES):
        with cols[i % 3]:
            st.markdown(
                f'<div class="card" style="min-height:150px">'
                f'<div class="ic" style="margin-bottom:0.6rem">'
                f'{icon(f["icon"], 22)}</div>'
                f'<div class="card-t">{f["title"]}</div>'
                f'<div class="card-d">{f["desc"]}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    T.section("Built for the people who use GBIF data")
    wc = st.columns(4)
    for i, (who, need) in enumerate(WHO):
        with wc[i]:
            st.markdown(
                f'<div class="card" style="min-height:120px">'
                f'<div class="card-t" style="color:{T.C["accent"]}">{who}</div>'
                f'<div class="card-d">{need}</div></div>',
                unsafe_allow_html=True,
            )

    # ── quick start ───────────────────────────────────────
    T.section("Start in ten seconds")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        st.markdown(
            f'<div class="card"><div class="card-t">1 · Pick a species</div>'
            f'<div class="card-d">Type any scientific name — or start with a '
            f'sample like <i>Panthera leo</i> or <i>Danaus plexippus</i>.</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="card"><div class="card-t">2 · Run the audit</div>'
            f'<div class="card-d">BioSift pulls a live sample from GBIF and '
            f'runs all checks, maps and benchmarks instantly.</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="card"><div class="card-t">3 · Export</div>'
            f'<div class="card-d">PDF report, Reproducibility Pack, '
            f'DwC-A, cube SQL.</div></div>',
            unsafe_allow_html=True,
        )

    T.footer()
