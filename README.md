# BioSift

> Biodiversity data quality and distribution-intelligence platform powered by GBIF

[![Live Demo](https://img.shields.io/badge/live-demo-22C58B?style=flat-square)](https://biosift-gbif.streamlit.app)
[![Python](https://img.shields.io/badge/python-3.12-4DA3FF?style=flat-square)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.58-FF4B4B?style=flat-square)](https://streamlit.io)
[![License](https://img.shields.io/badge/license-MIT-8A97A8?style=flat-square)](LICENSE)

---

## Live demo

**[biosift-gbif.streamlit.app](https://biosift-gbif.streamlit.app)** — no
installation required.

---

## What is BioSift?

BioSift audits the quality of GBIF occurrence data in seconds and turns the
result into evidence a reviewer can trust: a standards-aligned quality
audit, a benchmark against the full GBIF population, and one-click export of
a Reproducibility Pack, PDF report, Darwin Core Archive and GBIF data-cube
SQL.

Instead of manually inspecting raw datasets, users get immediate, *
standardised* diagnostics — communicated in the TDWG Biodiversity Data
Quality (BDQ) vocabulary the global community already uses.

---

## Why does this matter?

GBIF aggregates hundreds of millions of occurrence records from thousands of
publishers. Quality issues — missing or zero coordinates, country/coordinate
mismatches, duplicates, low precision, temporal gaps — propagate directly
into species distribution models, red-list assessments and policy
indicators.

BioSift closes the loop: **diagnose → benchmark → export evidence → fix at
the source.**

---

## Who is it for?

| User | How they benefit |
|---|---|
| Researchers | Pre-flight data audit before SDMs and trend analyses |
| Conservationists | IUCN status + spatial gap maps + reliability scores |
| Data managers | Per-dataset defect attribution with A–F grades |
| Node staff | Publisher report cards in the shared BDQ vocabulary |
| Policy analysts | Indicator-grade exports for GBF reporting workflows |
| Educators | A living, visual lesson in biodiversity data quality |

---

## Features

### Species Analysis
- **10 automated quality checks, each mapped to its official
  [TDWG BDQ](https://github.com/tdwg/bdq) test** — the community-standard
  vocabulary for biodiversity data quality
- Data health score + record completeness score with visual scoring
- **GBIF-wide benchmarking** — defect rates compared live against the full
  GBIF population matching the same species + filters
- **IUCN Red List category** displayed on the species card
- Per-record reliability scores, data fitness-for-use badges, coordinate
  precision tiers, multimedia quality (incl. broken-image sampling)
- Per-contributing-dataset quality breakdown with A–F grades

### Species interactions (GloBI)
- Live query of [GloBI](https://globalbioticinteractions.org) — predator–prey,
  parasite–host, pollination, pathogen and symbiosis records for the
  analysed species, with direction normalisation and source citations
- Artefact-resistant: name-resolution failures in GloBI are filtered
  before aggregation (methodology documented in-app)

### SDM readiness audit
- Journal-cited filter gates: Zizka et al. 2020 (*Ecography*),
  Marcer et al. 2022 (*Ecography*), GBIF Georeferencing Best Practice
- Two disclosed strictness profiles — Standard (≤10 km coordinate
  uncertainty) and Strict (≤1 km, publication-grade)
- Verdict + retention + per-gate breakdown, including *why* records fail
  (e.g. stated uncertainty typical of citizen-science data)

### Spatial & temporal intelligence
- Six key-free professional basemaps (Esri World Imagery, Ocean,
  OpenTopoMap, Carto Voyager/Positron/dark) with in-map layer switching
- Five map modes: point map, heatmap, DBSCAN outliers, SDM (KDE) preview,
  and the 10°-grid global data gap map with coverage alerts
- Records-per-year trends, decade breakdowns, citizen-science surge
  detection, peak-year and major-gap insights, seasonal patterns

### Publication-grade exports
- **Reproducibility Pack (ZIP)** — `biosift_report.json` (versioned
  machine-readable schema), paste-ready methods text, APA + BibTeX
  citations, full/clean CSVs, the standards-compliant DwC-A, and
  `recipe.json` containing the exact GBIF API requests to regenerate the
  sample
- **Branded PDF quality report** for theses, DMPs and grant appendices
- **GBIF data-cube SQL** — indicator-grade cube queries targeting the
  GBIF SQL download service used by EU B-Cubed pipelines

### Batch Comparison & Publisher Report Card
- Side-by-side quality comparison of up to five species
- Institution-level report card for any GBIF publisher

---

## Two apps, one science layer

| | Streamlit app | Standalone (FastAPI + MapLibre) |
|---|---|---|
| Run | `streamlit run app.py` | `uvicorn standalone.server:app --port 8080` |
| UI | Multi-page data app | Single-page inspector + WebGL map |
| Map | Leaflet/folium | MapLibre GL JS (no key, no token) |
| API | — | `GET /api/analysis/{species}` (OpenJSON docs at `/docs`) |
| Use case | Interactive exploration | Automation, integration, self-hosting |

Both use the same `utils/` science layer: identical checks, identical
standards, identical verdicts.

### Deploying the standalone app

Any Docker host runs it as-is:

```bash
docker compose up --build        # http://localhost:8080
```

One-click options (auto-detect the Dockerfile):

| Host | Steps |
|---|---|
| Railway | New project → Deploy from GitHub repo → done |
| Render | New Web Service → Docker runtime → port 8080 |
| Fly.io | `fly launch` → `fly deploy` |
| Any VPS | `docker compose up -d` behind nginx/Caddy |

No environment variables or API keys are required — the app only talks
to public GBIF, GloBI and tile endpoints.

### Standalone API example

```bash
uvicorn standalone.server:app --port 8080
curl "localhost:8080/api/analysis/Panthera%20leo?limit=300" | jq .scores
```

The bundle includes BDQ-mapped checks, GBIF-wide benchmarking, SDM
readiness (Zizka 2020 / Marcer 2022 profiles), EOO/AOO + KBA Criterion
B screening with hull GeoJSON, GloBI interactions, and congeneric
co-occurrence (Jaccard) — one JSON document, schema
`biosift.analysis/1.1`.

## Running locally

```bash
git clone <this-repo>
cd <this-repo>
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app talks only to public GBIF API endpoints — no API key needed.

---

## Standards alignment

| Standard | How BioSift uses it |
|---|---|
| TDWG BDQ (TG2 core tests) | Every quality check is labelled with its official test ID |
| Darwin Core | Exports emit valid dwc terms; DwC-A includes `meta.xml` + EML |
| GBIF data cubes | Cube exports target the GBIF SQL download service |
| IUCN Red List | Categories surfaced via the GBIF species API |
| GloBI | Species interactions via directional taxon queries |

---

## Project structure

```
app.py                 # entry point — st.navigation wiring
views/                 # one module per page (home, analysis, batch, …)
utils/
  theme.py             # design system: tokens, components, chart theming
  bdq.py               # TDWG BDQ test mapping
  benchmark.py         # GBIF-wide population benchmarking
  reppack.py           # Reproducibility Pack builder
  pdf_report.py        # branded PDF report
  cube.py              # GBIF SQL data-cube exports
  quality.py           # the 10 quality checks
  gbif_fetch.py        # GBIF occurrence API client
  …                    # maps, charts, sdm, gaps, dwc, publisher, …
```

---

## License

MIT — see [LICENSE](LICENSE). GBIF-mediated data are shared under CC-BY;
please cite contributing datasets (BioSift generates these citations for
you in the Data & Export tab).
