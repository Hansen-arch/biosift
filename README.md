# 🌿 BioSift

> Biodiversity data intelligence platform powered by GBIF

Built for the **2026 GBIF Ebbe Nielsen Challenge**

---

## 🔗 Live Demo

**[biosift-gbif.streamlit.app](https://biosift-gbif.streamlit.app)**

No installation required. Open in any desktop browser and start analysing immediately.

---

## What is BioSift?

BioSift is an open-source biodiversity data quality diagnostic tool that
enables researchers, conservationists and data managers to instantly assess
the quality, completeness and reliability of species occurrence data from
the Global Biodiversity Information Facility (GBIF).

Instead of manually inspecting raw datasets, users receive immediate visual
diagnostics across multiple quality dimensions — all in one place,
with zero setup required.

---

## Why does this matter?

GBIF aggregates hundreds of millions of occurrence records from thousands of
data publishers worldwide. However, many records contain quality issues such
as missing or zero coordinates, coordinates falling outside the stated
country boundary, duplicate records, low coordinate precision and temporal
gaps. These issues directly affect the reliability of biodiversity analyses,
species distribution models and conservation assessments.

BioSift makes it easy for anyone to assess, diagnose and clean occurrence
data before using it in research or policy work — in seconds, not hours.

---

## Who is it for?

| User | How they benefit |
|---|---|
| Researchers | Instantly assess data quality before analysis |
| Conservationists | View spatial data gaps and reliability scores |
| Data managers | Identify which datasets are dragging down quality |
| Policy makers | Understand data reliability for decision making |
| Educators | Explore biodiversity data visually |

---

## Features

### Species Analysis Mode

**Data Quality (10 automated checks)**
- Data health score (0–100%) with visual progress bar
- Record completeness score — % of important fields filled per record
- Missing coordinates detection
- Zero coordinates detection
- Missing year detection
- Pre-1900 historical records flag
- Missing event date detection
- Duplicate records detection
- Low coordinate precision flag (< 2 decimal places)
- Country coordinate mismatch — flags records where coordinates
  fall outside the stated country boundary

**Spatial Analysis**
- Interactive point map (green = clean, red = flagged)
- Heatmap
- DBSCAN spatial outlier detection and map
- Species Distribution Model preview (Kernel Density Estimation)
- Global data gap map (10° grid cells) with spatial coverage alerts

**Temporal Analysis**
- Records per year chart with trend line
- Records by decade chart
- First/last record, year span, gap count
- Temporal insights (peak year, CS surge detection, major gap detection)

**Charts & Statistics**
- Observation density by country (% of total)
- Records per month (seasonal patterns)
- Basis of record breakdown
- Top 10 countries
- Coordinate precision tiers (5 levels, ~10km to ~1m)
- Per-contributing-dataset quality breakdown with A–F grades

**Assessment**
- Data fitness for 5 scientific use cases
- Per-record reliability scoring (0–100)
- Automated recommendations engine
- Multimedia quality (coverage % + broken URL detection)

**Export & Reproducibility**
- Full dataset CSV
- Clean records CSV
- Reliability-scored CSV
- Darwin Core Archive (DwC-A) — standards-compliant ZIP:
  occurrence.csv + meta.xml + eml.xml
- Clean Darwin Core Archive
- Reproducible methods paragraph (publication-ready)
- GBIF dataset citation generator (APA and BibTeX formats)

### Batch Comparison Mode
- Compare quality metrics across up to 5 species side by side
- Accepts comma or newline-separated species names
- Configurable year range and records per species
- Health score cards, full comparison table, grouped bar chart
- Downloadable comparison CSV

### Publisher Report Card Mode
- Search any GBIF data publishing institution by name
- View all published datasets with record counts
- Coordinate coverage percentage per dataset
- Dataset creation and last modified dates
- Downloadable publisher report CSV

---

## Quick Start

**No installation needed:**

👉 Open [biosift-gbif.streamlit.app](https://biosift-gbif.streamlit.app)

1. Enter a species scientific name (e.g. `Panthera leo`)
   or select from Quick Select samples
2. Set optional year range and basis of record filters
3. Set maximum records (default 500, max 10,000)
4. Click **Run Analysis**
5. Explore 6 tabs:
   Overview · Occurrence Map · Temporal Analysis ·
   Charts · Gap Analysis · Data & Export

---

## Local Installation

### Requirements
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Hansen-arch/biosift.git
cd biosift

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py

App opens at http://localhost:8501
Project Structure

text

biosift/
├── app.py                    ← main Streamlit app (3 modes)
├── utils/
│   ├── gbif_fetch.py         ← GBIF API, pagination, caching
│   ├── quality.py            ← 10 quality checks, completeness,
│   │                            country mismatch, precision stats
│   ├── maps.py               ← point map, heatmap
│   ├── charts.py             ← temporal, geographic, density charts
│   ├── outliers.py           ← DBSCAN spatial outlier detection
│   ├── sdm.py                ← KDE species distribution model
│   ├── reliability.py        ← reliability scoring, methods
│   │                            generator, citation generator
│   ├── gaps.py               ← global gap map + spatial alerts
│   ├── publisher.py          ← publisher report card
│   ├── species_info.py       ← species card: photo, taxonomy
│   ├── dwc.py                ← Darwin Core Archive builder
│   └── dataset_quality.py   ← per-dataset quality breakdown
├── .streamlit/
│   └── config.toml           ← dark theme
├── requirements.txt
├── LICENSE
└── README.md

Data Sources

    Occurrence data: GBIF.org — Global Biodiversity Information Facility

All data accessed via free, open public APIs. No data is stored or redistributed by BioSift.
Tech Stack
Library	Purpose
Python 3.12	Core language
Streamlit	Web UI framework
pygbif	GBIF API wrapper
pandas	Data manipulation
folium	Interactive maps
plotly	Interactive charts
scikit-learn	DBSCAN outlier detection
scipy	Kernel density estimation
numpy	Numerical computation
requests	API calls
License

MIT License — see LICENSE for details.

Open source, free to use, free to modify.
Author

Reihan Apriandi github.com/Hansen-arch
Built for

2026 GBIF Ebbe Nielsen Challenge gbif.org/news/3DyM3tK5wgYipqyaHwG2c2

Advancing open science through better biodiversity data intelligence.