"""
BioSift — Methods & Standards page
"""

import pandas as pd
import streamlit as st

import utils.theme as T
from utils.theme import C
from utils.bdq import BDQ, ORDER, citation_note


INTERACTIONS_ROWS = [
    ("Data source",
     "GloBI — Global Biotic Interactions (Poelen et al. 2014, Ecological "
     "Informatics)",
     "Interaction records are queried via GloBI's directional taxon "
     "parameters (sourceTaxon=, targetTaxon=), which return resolved, "
     "semantically-typed records. The fuzzy q= search is deliberately "
     "avoided: it returns name-resolution artefacts (citations and DOIs "
     "in taxon fields)."),
    ("Artefact filtering",
     "Taxon-name validation",
     "Records whose taxon fields fail plausibility checks (URLs, DOIs, "
     "digits, parenthesis, citation-length strings, all-caps dataset "
     "tokens) are dropped before aggregation."),
    ("Direction normalisation",
     "OBO relationship vocabulary",
     "When the analysed species appears as the object of a relationship, "
     "the interaction is inverted (e.g. preysOn → preyedUponBy) so the "
     "species card always reads as subject."),
    ("Deduplication",
     "(direction, partner) pair",
     "Multiple studies reporting the same pairwise interaction collapse "
     "to one record; sources are retained in the full table."),
]

FITNESS_ROWS = [
    ("Standard profile",
     "Coordinate uncertainty ≤ 10 km",
     "Mirrors the moderate settings of Zizka et al. 2020's automated "
     "cleaning pipeline — suitable for exploratory distribution work."),
    ("Strict profile",
     "Coordinate uncertainty ≤ 1 km",
     "Publication-grade end of the same sensitivity analysis; required "
     "for fine-scale SDM and Red List assessments."),
    ("Uncertainty gate",
     "Marcer et al. 2022",
     "Records with unknown coordinateUncertaintyInMeters are flagged "
     "rather than silently passed — uncertainty is the dominant error "
     "axis for SDM fitness."),
    ("Minimum sample gate",
     "≥ 100 usable records",
     "Correlative SDMs generally require at least 100 unique, "
     "well-distributed records; below that, presence-only methods only."),
]

CHECKS_ROWS = [
    ("Missing coordinates",
     "VALIDATION_DECIMALLATITUDE_NOTEMPTY · VALIDATION_DECIMALLONGITUDE_NOTEMPTY",
     "Records without decimalLatitude or decimalLongitude are excluded from "
     "all spatial analyses and flagged as incomplete."),
    ("Zero coordinates",
     "VALIDATION_COORDINATES_CAPABLEOFCONTAININGZERO",
     "0°N, 0°E ('Null Island') is overwhelmingly a georeferencing failure, "
     "not a real collection site in the Gulf of Guinea."),
    ("Missing year",
     "VALIDATION_YEAR_NOTEMPTY",
     "Records without dwc:year are excluded from temporal trend analyses."),
    ("Pre-1900 records",
     "VALIDATION_YEAR_INRANGE (custom lower bound 1900)",
     "Historical records are valid but often carry imprecise georeferences "
     "and historical place names — review before fine-scale use."),
    ("Missing event date",
     "VALIDATION_EVENTDATE_NOTEMPTY · VALIDATION_EVENTDATE_INRANGE",
     "Checks that dwc:eventDate is populated and consistent with dwc:year."),
    ("Duplicates",
     "VALIDATION_OCCURRENCEID_UNIQUE (proxy)",
     "Identical species + coordinates + year across records suggests "
     "duplicate mobilisation across datasets."),
    ("Low coordinate precision",
     "VALIDATION_DECIMALLATITUDE_PRECISION · VALIDATION_DECIMALLONGITUDE_PRECISION",
     "Fewer than 2 decimal places (~1 km or coarser) limits fine-scale "
     "analyses such as species distribution models."),
    ("Country–coordinate mismatch",
     "VALIDATION_COUNTRYCODE_STANDARD · VALIDATION_COUNTRY_COORDINATESMISMATCH",
     "Coordinates tested against the stated country's bounding box with a "
     "1° tolerance buffer — mismatches indicate georeferencing errors."),
    ("GBIF issue flags",
     "GBIF interpretation flags (informational)",
     "GBIF's own interpretation pipeline flags; informational and not "
     "treated as disqualifying."),
]


def render():
    T.inject_css()
    T.page_head(
        "Methods & Standards",
        "How BioSift works, which standards it follows, and how to cite it."
    )

    # ── pipeline ──────────────────────────────────────────
    T.section("Analysis pipeline")
    steps = st.columns(5)
    pipeline = [
        ("Fetch", "Live GBIF occurrence API sample with user filters"),
        ("Audit", "10 TDWG BDQ-aligned quality checks"),
        ("Score", "Health, completeness and per-record reliability"),
        ("Benchmark", "Defect rates vs full GBIF population"),
        ("Package", "Reproducibility Pack, PDF, DwC-A, cube SQL"),
    ]
    for col, (name, desc) in zip(steps, pipeline):
        col.markdown(
            f'<div class="card" style="min-height:130px">'
            f'<div class="card-t" style="color:{C["accent"]}">{name}</div>'
            f'<div class="card-d">{desc}</div></div>',
            unsafe_allow_html=True,
        )

    # ── health score ──────────────────────────────────────
    T.section("Health score definition")
    st.markdown(f"""
    <div class="card">
        <div class="card-d">
        The <b>Data Health Score</b> is the percentage of sampled records that
        pass <b>all</b> quality checks (any single flag disqualifies a record).
        It is deliberately strict — think of it as an upper bound on the
        share of records ready for demanding analyses. Complementary metrics
        (completeness, per-record reliability, benchmark deltas) contextualise
        the headline number so a single score never stands alone.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── BDQ mapping table ─────────────────────────────────
    T.section("Check → TDWG BDQ test mapping")
    st.caption(citation_note())
    rows = [{"BioSift check": c, "TDWG BDQ test(s)": b, "What it means": d}
            for c, b, d in CHECKS_ROWS]
    st.dataframe(pd.DataFrame(rows), use_container_width=True,
                 hide_index=True)

    # ── interactions methodology ──────────────────────────
    T.section("Species interactions methodology (GloBI)")
    irows = [{"Aspect": a, "Approach": b, "Detail": d}
             for a, b, d in INTERACTIONS_ROWS]
    st.dataframe(pd.DataFrame(irows), use_container_width=True,
                 hide_index=True)

    # ── SDM readiness methodology ─────────────────────────
    T.section("SDM readiness methodology")
    frows = [{"Component": a, "Threshold": b, "Rationale": d}
             for a, b, d in FITNESS_ROWS]
    st.dataframe(pd.DataFrame(frows), use_container_width=True,
                 hide_index=True)

    # ── distribution & KBA methodology ────────────────────
    T.section("Distribution metrics & KBA screening")
    st.dataframe(pd.DataFrame([
        {"Metric": "EOO — Extent of Occurrence",
         "Method": "Minimum convex hull in local equirectangular "
                   "projection, per IUCN Guidelines 4.0",
         "Caution": "Highly sensitive to outlier/vagrant records — the "
                    "hull can overstate range (Burgio et al. 2021). "
                    "BioSift warns when hull area is implausible."},
        {"Metric": "AOO — Area of Occupancy",
         "Method": "2×2 km occupancy grid, IUCN Standard 4.0",
         "Caution": "Sample-size dependent: more records → more occupied "
                    "cells, so compare only at comparable sampling."},
        {"Metric": "KBA Criterion B screen",
         "Method": "B1: EOO ≤ 20,000 km² · B2: AOO ≤ 2,000 km² "
                   "(IUCN 2016 Global KBA Standard)",
         "Caution": "Screening only. Formal KBA assessment requires "
                    "Red List status and stakeholder consultation."},
        {"Metric": "Geographic co-occurrence",
         "Method": "1° presence/absence grid Jaccard index between the "
                   "target and congeneric species (GBIF data)",
         "Caution": "Observed overlap conflates ecology with sampling "
                    "effort — read alongside the gap analysis."},
    ]), use_container_width=True, hide_index=True)
    for cite in (
        "Zizka, A. et al. (2020). No one-size-fits-all solution to clean "
        "GBIF. Ecography, 43, 24–35. doi:10.1111/ecog.04895",
        "Marcer, A. et al. (2022). Uncertainty matters. Ecography, 2022, "
        "e06025. doi:10.1111/ecog.06025",
        "Poelen, J.H., Simons, J.D. & Mungall, C.J. (2014). Global biotic "
        "interactions: an open infrastructure to share and analyze "
        "species-interaction data. Ecological Informatics, 24, 148–159.",
    ):
        st.markdown(
            f'<div class="alert a-info" style="font-size:0.8rem">'
            f'{cite}</div>',
            unsafe_allow_html=True,
        )

    # ── standards ─────────────────────────────────────────
    T.section("Standards & alignment")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(
            f'<div class="card"><div class="card-t">TDWG BDQ</div>'
            f'<div class="card-d">Quality assertions use the official '
            f'Biodiversity Data Quality TG2 core test vocabulary.'
            f'<br><a href="https://github.com/tdwg/bdq" target="_blank">'
            f'github.com/tdwg/bdq</a></div></div>',
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            f'<div class="card"><div class="card-t">Darwin Core</div>'
            f'<div class="card-d">All exports emit valid dwc terms; the '
            f'DwC-A includes meta.xml and EML metadata.'
            f'<br><a href="https://dwc.tdwg.org" target="_blank">'
            f'dwc.tdwg.org</a></div></div>',
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            f'<div class="card"><div class="card-t">GBIF data cubes</div>'
            f'<div class="card-d">Cube exports target the GBIF SQL download '
            f'service used by B-Cubed indicator pipelines.'
            f'<br><a href="https://techdocs.gbif.org/en/data-use/data-cubes" '
            f'target="_blank">techdocs.gbif.org</a></div></div>',
            unsafe_allow_html=True,
        )

    # ── reproducibility statement ─────────────────────────
    T.section("Reproducibility statement")
    st.markdown(f"""
    <div class="card">
        <div class="card-d">
        Every analysis is reproducible end-to-end: the <b>recipe.json</b> inside
        each Reproducibility Pack contains the exact GBIF API requests that
        generated the sample; the <b>biosift_report.json</b> follows a stable
        versioned schema (<code>biosift.report/1.0</code>) for machine
        ingestion; and all BioSift code is open source. Re-running the recipe
        against GBIF regenerates the identical input, and the checks are
        deterministic — same data in, same verdict out.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── cite biosift ──────────────────────────────────────
    T.section("Citing BioSift")
    st.code(
        "BioSift (2026). Biodiversity data intelligence platform. "
        "Version 2.0. https://biosift-gbif.streamlit.app",
        language="text",
    )

    T.footer()
