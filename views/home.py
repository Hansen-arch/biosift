"""
BioSift: Home / landing page
"""

import streamlit as st

import utils.theme as T
from utils.icons import icon

# Hierarchy reason (R-31): the three lead cards are the entry points
# (audit, benchmark, your own data). The other three are depth features
# you reach after a first audit, so they render without the accent edge.
FEATURES = [
    {
        "icon": "dna",
        "title": "10 checks, named the way publishers name them",
        "desc": "Zero coordinates, country mismatch, duplicates, bad dates. "
                "Each flag carries its TDWG BDQ test ID, so a node manager "
                "can reply without translating.",
        "lead": True,
    },
    {
        "icon": "pulse",
        "title": "Your sample vs the whole of GBIF",
        "desc": "A 74% health score means nothing alone. BioSift pulls the "
                "full GBIF population for the same species and shows whether "
                "your defects are yours or everybody's.",
        "lead": True,
    },
    {
        "icon": "globe",
        "title": "What eats it, what it eats (GloBI)",
        "desc": "Predator, prey, pollinator, parasite, fetched live from "
                "GloBI with direction fixed so the analysed species stays "
                "the subject. Empty for most taxa, and that is reported, not hidden.",
        "lead": False,
    },
    {
        "icon": "target",
        "title": "Can you model with this? Probably not yet",
        "desc": "Zizka 2020 / Marcer 2022 gates, stated plainly. Panthera leo "
                "fails Standard on coordinate uncertainty (about 31 km, typical "
                "of citizen-science records). The gate tells you why.",
        "lead": False,
    },
    {
        "icon": "download",
        "title": "A ZIP a reviewer can rerun",
        "desc": "Report JSON with schema version, methods paragraph, "
                "APA plus BibTeX citations, full and clean CSVs, DwC-A, and "
                "recipe.json with the exact GBIF queries.",
        "lead": False,
    },
    {
        "icon": "book",
        "title": "Upload your own spreadsheet",
        "desc": "CSV, TSV, Excel or DwC-A. 17 checks, fatal vs advisory "
                "per profile, and your file back with biosift_flag, "
                "biosift_exclude and biosift_reasons appended.",
        "lead": True,
    },
]

# Ledger reason (R-31): four audiences are reference rows, not four equal
# product pillars, so they render as ledger lines instead of a card row.
WHO = [
    ("Researchers", "Pre-flight data checks before SDMs and trend analyses"),
    ("Data managers", "Per-dataset defect attribution with A to F grades"),
    ("Node staff", "Publisher report cards in the shared BDQ vocabulary"),
    ("Policy analysts", "Reliability statements for GBF indicator workflows"),
]


def render():
    T.inject_css()

    # Hero facts render as ledger items, not pills: these are provenance
    # statements (sample size, runtime, licence), not status markers.
    st.markdown("""
    <div class="hero">
        <div class="hero-kicker">field log &middot; v3.4 &middot; reads live from GBIF, no key needed</div>
        <h1 class="hero-title">Does this GBIF sample hold up before you model it?</h1>
        <p class="hero-sub">Paste a scientific name. BioSift pulls a live
        occurrence sample, runs 10 TDWG BDQ checks, compares your defect rates
        against the full GBIF population for that species, and hands you the
        evidence pack, including the rows that fail. Try <i>Panthera leo</i>:
        it usually scores in the 70s and fails the SDM gate on uncertainty alone.</p>
        <div class="hero-facts">
            <span class="hero-fact">Sample: 300 records, about 30 to 75 s</span>
            <span class="hero-fact">Quercus robur passes &middot; Panthera leo doesn't</span>
            <span class="hero-fact">Data: GBIF.org &middot; CC-BY, cite the datasets</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    T.section("The audit")
    cols = st.columns(3)
    for i, f in enumerate(FEATURES):
        with cols[i % 3]:
            cls = "card card-hi" if f["lead"] else "card"
            st.markdown(
                f'<div class="{cls}" style="min-height:150px">'
                f'<div class="ic" style="margin-bottom:0.6rem">'
                f'{icon(f["icon"], 22)}</div>'
                f'<div class="card-t">{f["title"]}</div>'
                f'<div class="card-d">{f["desc"]}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    T.section("Who uses it")
    rows = "".join(
        f'<div style="display:flex;gap:0.8rem;padding:0.5rem 0;'
        f'border-bottom:1px solid {T.C["line"]}">'
        f'<span style="min-width:130px;font-weight:700;font-size:0.85rem;'
        f'color:{T.C["text"]}">{who}</span>'
        f'<span style="font-size:0.85rem;'
        f'color:{T.C["text_dim"]}">{need}</span></div>'
        for who, need in WHO
    )
    st.markdown(f'<div style="margin-bottom:0.5rem">{rows}</div>',
                unsafe_allow_html=True)

    # Run ledger reason (R-31): these are shell commands to copy, so they
    # render as mono ledger lines, not a 1-2-3 card row.
    T.section("Run it locally")
    st.markdown(
        f'<div style="font-family:ui-monospace,Menlo,Consolas,monospace;'
        f'font-size:0.82rem;color:{T.C["text_dim"]};'
        f'background:{T.C["card"]};border:1px solid {T.C["line"]};'
        f'border-radius:10px;padding:0.9rem 1.1rem;line-height:2.0">'
        f'pip install -r requirements.txt<br>'
        f'streamlit run app.py&nbsp;&nbsp;'
        f'<span style="color:{T.C["text_faint"]}"># Streamlit UI on :8501</span><br>'
        f'uvicorn standalone.server:app --port 8080&nbsp;&nbsp;'
        f'<span style="color:{T.C["text_faint"]}"># API plus MapLibre inspector</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    T.footer()
