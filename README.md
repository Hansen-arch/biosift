# 🌿 BioSift

> Biodiversity data intelligence platform powered by GBIF & IUCN Red List

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
as missing or zero coordinates, duplicate records, low coordinate precision,
and temporal gaps. These issues directly affect the reliability of biodiversity
analyses, species distribution models and conservation assessments.

BioSift makes it easy for anyone to assess, diagnose and clean occurrence
data before using it in research or policy work.

---

## Who is it for?

| User | How they benefit |
|------|----------------|
| Researchers | Instantly assess data quality before analysis |
| Conservationists | View IUCN status alongside spatial data gaps |
| Data managers | Identify and fix issues in published datasets |
| Policy makers | Understand data reliability for decision making |
| Educators | Explore biodiversity data visually |

---

## Features

### Species Analysis Mode
- Data health score (0–100%) with visual progress bar
- Six automated quality checks with detailed breakdown
- Coordinate precision analysis (5 tiers)
- Data fitness assessment for 5 scientific use cases
- Automated recommendations engine
- Interactive occurrence map (point map + heatmap)
- DBSCAN spatial outlier detection
- Species Distribution Model preview (Kernel Density Estimation)
- Temporal analysis with trend detection and gap identification
- Global data gap map (10° grid)
- IUCN Red List conservation status integration
- Per-record reliability scoring (0–100)
- Before & after cleaning comparison
- Three CSV export options (full, clean, scored)
- Reproducible methods paragraph generator

### Publisher Report Card Mode
- Search any GBIF data publishing institution by name
- View all published datasets with record counts
- Coordinate coverage percentage per dataset
- Dataset creation and last modified dates
- Downloadable publisher report CSV

---

## Live Demo

👉 [Open BioSift](#) ← Streamlit URL coming soon

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
    Set maximum records to fetch (default: 500)
    Optionally enter your IUCN API key for conservation status
    Click Run Analysis
    Explore 6 tabs: Overview, Map, Temporal, Charts, Gap Analysis, Export

Publisher Report Card

    Switch mode to Publisher Report Card in sidebar
    Enter institution name (e.g. iNaturalist)
    Click Get Report Card
    Select publisher from results
    Click Load Report

IUCN Red List Integration

BioSift can display IUCN Red List conservation status alongside occurrence data. To enable:

    Get a free API key at https://apiv3.iucnredlist.org/api/v3/token
    Enter the key in the sidebar under IUCN API Key
    Conservation status badge appears above the metrics

biosift/
├── app.py                  ← main Streamlit app
├── utils/
│   ├── gbif_fetch.py       ← GBIF API calls with pagination and caching
│   ├── quality.py          ← data quality checks and precision analysis
│   ├── maps.py             ← interactive occurrence maps and heatmap
│   ├── charts.py           ← temporal and geographic charts
│   ├── outliers.py         ← DBSCAN spatial outlier detection
│   ├── sdm.py              ← species distribution model preview
│   ├── reliability.py      ← record reliability scoring and methods generator
│   ├── gaps.py             ← global data gap grid map
│   ├── publisher.py        ← publisher report card
│   └── iucn.py             ← IUCN Red List integration
├── .streamlit/
│   └── config.toml         ← app theme
├── requirements.txt
├── LICENSE
└── README.md

Data Sources

    Occurrence data: GBIF.org — Global Biodiversity Information Facility
    Conservation status: IUCN Red List

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
requests	IUCN & publisher API calls
License

MIT License — see LICENSE for details.
Author

Reihan Apriandi · github.com/Hansen-arch
Built for

2026 GBIF Ebbe Nielsen Challenge

Advancing open science through better biodiversity data intelligence.