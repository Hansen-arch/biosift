# 🌿 BioSift

> Biodiversity data intelligence platform powered by GBIF

Built for the **2026 GBIF Ebbe Nielsen Challenge**

---

## What is BioSift?

BioSift is an open-source biodiversity data quality diagnostic tool that
enables researchers, conservationists and data managers to instantly assess
the quality, completeness and reliability of species occurrence data from
the Global Biodiversity Information Facility (GBIF).

Instead of manually inspecting raw datasets, users receive immediate visual
diagnostics across multiple quality dimensions — all in one place.

---

## Why does this matter?

GBIF aggregates hundreds of millions of occurrence records from thousands of
data publishers worldwide. However, many records contain quality issues such
as missing or zero coordinates, coordinates outside the stated country,
duplicate records, low coordinate precision and temporal gaps. These issues
directly affect the reliability of biodiversity analyses, species distribution
models and conservation assessments.

BioSift makes it easy for anyone to assess, diagnose and clean occurrence
data before using it in research or policy work.

---

## Who is it for?

| User | How they benefit |
|---|---|
| Researchers | Instantly assess data quality before analysis |
| Conservationists | View spatial data gaps and reliability scores |
| Data managers | Identify and fix issues in published datasets |
| Policy makers | Understand data reliability for decision making |
| Educators | Explore biodiversity data visually |

---

## Features

### Species Analysis Mode

**Data Quality**
- Data health score (0–100%) with visual progress bar
- Record completeness score — % of important fields filled per record
- Eight automated quality checks with detailed breakdown:
  - Missing coordinates
  - Zero coordinates
  - Missing year
  - Pre-1900 records
  - Missing event date
  - Duplicate records
  - Low coordinate precision
  - Country coordinate mismatch (coordinates outside stated country boundary)
- Coordinate precision analysis across 5 tiers (~10km to ~1m)
- DBSCAN spatial outlier detection
- Multimedia quality assessment (coverage % + broken URL detection)

**Analysis**
- Data fitness assessment for 5 scientific use cases
- Automated recommendations engine
- Per-record reliability scoring (0–100)
- Temporal analysis with trend detection and gap identification
- Observation density chart — country contribution as % of total

**Mapping**
- Interactive point map (green = clean, red = flagged)
- Heatmap
- DBSCAN outlier map
- Species Distribution Model preview (Kernel Density Estimation)
- Global data gap map (10° grid cells)

**Export & Reproducibility**
- Before & after cleaning comparison
- Three CSV export options (full dataset, clean records, scored records)
- Reproducible methods paragraph — publication-ready, copy-paste ready
- GBIF dataset citation generator (APA and BibTeX formats)

### Publisher Report Card Mode
- Search any GBIF data publishing institution by name
- View all published datasets with record counts
- Coordinate coverage percentage per dataset
- Dataset creation and last modified dates
- Downloadable publisher report CSV

---

## Live Demo

👉 [Open BioSift on Streamlit Cloud](https://biosift.streamlit.app)

---

## Installation

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
Usage
Species Analysis

    Enter a species scientific name (e.g. Panthera leo) or select a sample
    Set optional year range and basis of record filters
    Set maximum records to fetch (default: 500, max: 10,000)
    Click Run Analysis
    Explore 6 tabs: Overview · Occurrence Map · Temporal Analysis · Charts · Gap Analysis · Data & Export

Publisher Report Card

    Switch mode to Publisher Report Card in the sidebar
    Enter an institution name (e.g. iNaturalist)
    Click Get Report Card
    Select publisher from results
    Click Load Report

Project Structure

text

biosift/
├── app.py                  ← main Streamlit app
├── utils/
│   ├── gbif_fetch.py       ← GBIF API calls with pagination and caching
│   ├── quality.py          ← quality checks, completeness score, country mismatch
│   ├── maps.py             ← interactive occurrence maps and heatmap
│   ├── charts.py           ← temporal, geographic and density charts
│   ├── outliers.py         ← DBSCAN spatial outlier detection
│   ├── sdm.py              ← species distribution model preview
│   ├── reliability.py      ← reliability scoring, methods generator, citation generator
│   ├── gaps.py             ← global data gap grid map
│   └── publisher.py        ← publisher report card
├── .streamlit/
│   └── config.toml         ← dark theme config
├── requirements.txt
├── LICENSE
└── README.md

Data Sources

    Occurrence data: GBIF.org — Global Biodiversity Information Facility

All data accessed through free, open public APIs. No data is stored or redistributed by this tool.
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
Author

Reihan Apriandi · github.com/Hansen-arch
Built for

2026 GBIF Ebbe Nielsen Challenge gbif.org/news/3DyM3tK5wgYipqyaHwG2c2

Advancing open science through better biodiversity data intelligence.