# BioSift, Project Continuity

> Living document. Update after every milestone so any future session can
> resume with full context. **Current version: v3.7** (2026-11-05).

---

## ⏯ START HERE, next session

### What BioSift is now (v3.7, all verified working)

**v3.7, SiteSift folded in + country filtering (2026-11-05).** Site
screening is no longer a separate app: `views/site.py` is a BioSift page
("Site Screening", url_path `site`) over the unchanged engine in
`sitesift/screening.py`, so the page and the optional `sitesift/server.py`
API cannot drift. The page takes a boundary four ways, folium Draw
(polygon/rectangle), bounding box, point + radius, or paste/upload, and
boundary I/O is the new `utils/polygon.py` (GeoJSON incl. Feature/
FeatureCollection/bare coordinates, KML, WKT with SRID, CSV with header
or magnitude-inferred lat/lon order; exports GeoJSON/KML/WKT). Live check:
4 km² central London, HUMAN_OBSERVATION, 2000–2026, GB → 6.3 s, no errors;
5 result tables, 4 download buttons.

The Draw map can also screen *what it is showing*: "Use current map view"
turns the reported viewport into a bbox polygon (the standalone app's
`useView()`). It stays disabled until `st_folium` reports bounds and says
which case it is in, the opening whole-world view asks for a zoom-in, and
a view that crosses the antimeridian is refused rather than silently
becoming a 360° band. Provenance is kept in `ss_geometry_source`
(`draw`/`view`/`input`) so a draw layer that reports no drawings does not
erase an extent boundary. Browser-verified: London at zoom 13 → 64.6 km²,
569,951 records inside; panning to the date line shows the refusal.

Country filtering (`country=ISO2`) is applied at the query level, never as
an inference: `screen()` gained a `country` argument (cache key includes
it), the bundle gained a `COUNTRY` facet breakdown (`countries`,
`countries_total`) and a caveat explaining that GBIF's country is
*interpreted*, derived from coordinates when the publisher left it blank.
Same filter added to Species Analysis (`utils/gbif_fetch.fetch_countries()`,
251 countries from `/v1/enumeration/country`, 50-country fallback), and
threaded through `fetch_population_stats(country=)` and
`cube_exports(country=)` so the benchmark and the cube SQL keep the same
scope as the sample; `filters` in the Reproducibility Pack records it.
Measured: an Aachen border polygon (0.024°) holds 271,092 records split
NL 170,329 / DE 94,906 / BE 5,854, proof the filter earns its keep.
Nine facets in one request take ~0.8 s.

Verified: `utils/polygon.py` round-trips Polygon/MultiPolygon/circle
through all four formats with identical areas, rejects points, one-vertex
rings, swapped coordinates and unclosed rings with readable messages;
AppTest ran both pages end-to-end (analysis with DE + HUMAN_OBSERVATION:
41.6 s, 5 download buttons, no exceptions).

**v3.6, species analysis studio (2026-11-01).** The standalone app now
answers the analysis questions the audit raised before it checked data:
`factsheet` (taxonomy/synonyms/vernacular/habitat from `/species`,
`/synonyms`, `/vernacularNames`, `/speciesProfiles`), `rangeshift`
(early vs late period, counts, centroid, 5–95th extent, 1° cell
turnover with Jaccard, km displacement and direction, **plus the exact
coordinates each period's statistics came from** under `points.a/b` for
the map overlay), `envelope` (NASA POWER climatology at ≤24 record
locations: annual T/P/elevation ranges, monthly medians), `patterns.trend`
(records per distinct `recordedBy` per year, indexed to median -
reported as a reporting-rate proxy, not abundance), `year_counts`
(the `facet=year` population histogram, 127 years for oak). New module
`standalone/timeseries.py` does the time-aware probing because a
newest-first page carries no history. Frontend gained three sections,
seasonality + envelope + trend + year-curve charts, the period overlay,
and R (`rgbif`) / Python script exports. Full UI audit: **ALL CHECKS
PASSED** (both species, 4 viewports, BYOD, basemap switch).

**SiteSift (2026-11-01, merged into BioSift 2026-11-05)**, originally a
third, *separate* app in `sitesift/`, now the "Site Screening" page:
site-level screening from open GBIF data. Draw a polygon → species
recorded there, named CR/EN/VU species, native/introduced coverage,
decade effort, GBIF issue profile, dataset attribution, and JSON + R/Python
exports. The page imports `sitesift.screening` directly; the original
standalone UI still runs with `uvicorn sitesift.server:app --port 8090`
(audit: `scripts/ui_audit_sitesift.py`, 28 checks passed) and now also
accepts `country` in its request body. It shares no code with `utils/` or
`standalone/` on purpose, except the new `utils/polygon.py` boundary I/O
used only by the page. It deliberately omits
protected-area/KBA overlap (WDPA/WDPCA and WDKBA are licensed, Protected
Planet returns 401 without a token, KBA download is a request form) and does
not filter on establishmentMeans (present on only ~1.7–3% of records).
Motivation: IBAT's free tier is a map, but report downloads are
$750–1,500/site and its API starts at $35,000/yr, SiteSift is the free
triage layer before that purchase, and openly says so. See `sitesift/README.md`.

A biodiversity data-quality & distribution-intelligence platform over
the public GBIF API, **and over the user's own data (BYOD)**, shipped
as **two apps on one science layer**:

1. **Streamlit app** (`app.py`), multi-page: Home, Species Analysis
   (10 tabs: Overview, Occurrence Map, Temporal, Charts, Ecological
   Community, Distribution & KBA, Carbon, SDM Readiness, Gap Analysis,
   Data & Export), Batch Comparison, Publisher Report, Methods &
   Standards.
2. **Standalone** (`standalone/server.py` + `standalone/frontend.py`)
  , FastAPI JSON API + MapLibre GL JS single-page inspector. No API
   keys anywhere. Dockerfile + compose ready.

Science layer (`utils/`): TDWG BDQ-mapped quality checks, GBIF-wide
benchmarking, SDM readiness gates (Zizka 2020 / Marcer 2022, 2
strictness profiles), EOO/AOO + KBA Criterion B screening (+ hull
GeoJSON), GloBI interactions, congeneric co-occurrence (Jaccard),
plant carbon scenarios (Chave 2014 + IPCC 2006), Reproducibility Pack,
PDF report, data-cube SQL, and a **patterns layer** (attribute
correlation matrix, check co-occurrence Jaccard matrix, flag rate by
decade/country/basis, completeness distribution) served as
`bundle.patterns` for both apps.

Charts render as SVG/CSS in the standalone frontend, no charting
library, no extra network calls, no API keys.

### Run everything

```bash
git clone https://github.com/Hansen-arch/biosift && cd biosift
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

streamlit run app.py                          # Streamlit :8501
uvicorn standalone.server:app --port 8080     # Standalone :8080
docker compose up --build                     # Standalone in Docker
```

Smoke tests:
```bash
curl localhost:8080/api/health
curl "localhost:8080/api/analysis/Quercus%20robur?limit=200" | jq .carbon
curl "localhost:8080/api/analysis/Panthera%20leo?limit=300" | jq .sdm_readiness.verdict
# expect: oak SDM READY · carbon per_tree.co2e_t ~0.94 t; sample_totals scale
#   with GBIF sample (150 rec ~140.8 t CO2e, 500 rec ~469.3 t / 11.26 t/yr)
#   · lion SDM "NOT READY"
```

UI audit (headless Chrome CDP, needs websocket-client):
```bash
BIOSIFT_URL=http://localhost:8622 venv/bin/python scripts/ui_audit.py pages
BIOSIFT_URL=http://localhost:8622 venv/bin/python scripts/ui_audit.py analysis
```

### Known issues / pending (pick up here)

1. **Streamlit Cloud URL is login-walled**
   (biosift-gbif.streamlit.app → /-/login). Sharing was disabled or the
   app suspended server-side. FIX: share.streamlit.io → app → Settings
   → Sharing → make public. Code on main is current; nothing else
   blocks it.
2. ~~Docker verified by simulation only~~ **RESOLVED 2026-09-26**:
   first real `docker compose up --build` succeeded, container
   biosift-standalone healthy in ~38 s; health, frontend, /docs and a
   full oak bundle all 200 (record: "Docker build verification" below).
3. **Host quirk**: SearXNG on this machine is a Docker container bound
   to 8080. It was STOPPED for the biosift build, `docker start
   searxng` restores it. Local uvicorn tests: use 8090/8095/8096.
   Docker access from the agent shell: `sg docker -c "..."` (hans was
   added to the docker group without re-login); compose v2 v5.5.1
   plugin installed user-space at ~/.docker/cli-plugins/.
4. Analysis bundles take ~45–80 s since v3.6 (time probes, factsheet,
   envelope and period sampling all hit the network; they run in a
   4-worker pool). The UI audit's per-analysis budget is 180 s, so a
   full audit now runs ~5 min, do not raise concurrency to compensate,
   GBIF throttles. **Do not
   hammer GBIF while testing**, burst traffic throttles the API and
   the next analysis then blocks for minutes, which looks exactly like
   an app bug (the audit times out at 180 s and later checks fail
   against a stale bundle). If a run seems broken, wait a minute and
   rerun before debugging.

### Prioritised roadmap

1. pytest suite (carbon, fitness gates, co-occurrence, interactions
   filtering), protects the science during refactors
2. GitHub Actions: build Docker image on push + run API smoke tests
3. Re-enable Streamlit Cloud sharing (user, 2 minutes)
4. Per-record DBH uncertainty bands for carbon (Monte-Carlo around the
   30 cm scenario instead of a fixed point)
5. Species gallery with images (gaia-style discovery view)
6. Authenticated GBIF downloads for >10k-record species

### Hard-won API knowledge (do not re-learn)

- **GBIF facets (v3.6)**: only real field names work, `facet=dataset`
  and `facet=year`-as-a-wrong-shape are silently dropped (`facets: []`).
  Working names: `datasetKey`, `recordedBy`, `year`. Multiple facets go
  as a **list** (`params=[("facet","datasetKey"),("facet","recordedBy")]`),
  because `facet=[...]` as a kwargs value raises. `limit=0` facet probes
  cost ~1 s versus ~7 s for a coordinate page. Concurrent coordinate
  pages get throttled, small pool (5) + retries.
- **GBIF geometry / screening (SiteSift, verified live)**: a polygon query
  needs **counter-clockwise exterior rings**, clockwise returns `400 Polygon
  with clockwise exterior ring`. `geoDistance=lat,lon,km` is **broken** (10 km
  radius → 64 records where the equivalent bbox → 2.9 M, and counts don't
  scale with area); build a real polygon instead. Eight facets fit in one
  request (~1.7 s). `iucnRedListCategory` filters records but takes **no
  comma list** (`CR,EN,VU` → 0). `facetLimit` defaults to 10. Absence
  records are included by default, filter `occurrenceStatus=PRESENT`.
  `establishmentMeans` is sparse (~3%), so report coverage, never filter.
- **Range-shift overlay (v3.6)**: never rebuild overlay points from the
  map sample's years. The 500-record sample is newest-first and can hold
  no records in either measured period (oak: periods 1900-1901 and
  2025-2026 both empty in the sample), so the toggle silently no-ops.
  The backend returns `rangeshift.points.a/b` and the overlay plots them.
- **GBIF occurrence search**: `facet=species` is a silent NO-OP, use
  `facet=scientificName` (returns authorship; strip with
  `_strip_authorship`) + `taxonKey=<genusKey from /species/match>`.
  The `genus=` text param is IGNORED on occurrence/search.
- **GloBI**: the fuzzy `q=` search returns name-resolution garbage
  (citations/DOIs in taxon fields). Use directional `sourceTaxon=` /
  `targetTaxon=` params; keep `_valid_taxon_name()` filtering.
- **Chave 2014 returns AGB in kg** for D in cm, H in m, WD in g/cm³ -
  do NOT divide by 1000 again.
- **numpy.bool_ breaks FastAPI JSON**, coerce flags with bool() in
  `screen_kba_b`.
- **st.Page needs unique `url_path=`** when page callables share a
  name (all views export `render`).
- **Streamlit h1 font reset** beats single-class selectors, use
  `.hero .hero-title` specificity.
- **GBIF congener grids** (`utils/cooccurrence.py`): a `scientificName`
  occurrence query is a full-text search and takes 20-40 s; resolve the
  name via `/species/match` to a `speciesKey` first and filter on that
  (~3 s). GBIF throttles concurrent bursts, so the pool stays at 4
  workers. `fetch_species_grids(budget=28)` returns partial results
  labelled `no sample` rather than stalling the endpoint (was 290 s,
  now 16 s typical).
- **Audit clip detector**: SVG children report 0 for
  clientWidth/scrollWidth, so overflow must be measured as painted
  overflow (`getBoundingClientRect()` of the text vs its SVG viewport).
  The old scrollWidth test false-positived on rotated axis labels.
- **`patterns.py`**: `a[[k, k]]` returns a two-column frame, select
  correlated columns by position (`iloc[:,0]/[:,1]`), not by name.

---

## v3.5, correlation & pattern charts (2026-10-31)

Both modes gained a charts layer answering two questions the report
could not: *which attributes move together* and *which defects travel
together*.

- **New `standalone/patterns.py`** (pure pandas, no plotting
  dependency, the frontend draws SVG heatmaps and CSS bars so the
  figures inherit the app's palette and need no network):
  - `correlation`, Pearson *r* over Year, Lat, Lon, coordinate
    uncertainty, decimal precision, field completeness and checks
    triggered per record. Pairwise-complete rows (n≥5);
    zero-variance columns are dropped, since a constant column cannot
    correlate and used to render a blank diagonal cell.
  - `cooccurrence`, Jaccard overlap between the eight most frequent
    checks: which defects tend to hit the same records.
  - `decades`, records and flag rate per decade.
  - `completeness_dist`, per-record share of the ten scored Darwin
    Core fields.
  - `categorical`, flag rate by country and by basis of record.
- Served as `bundle.patterns` in **both** the species endpoint and the
  BYOD bundle; rendered in a new "Patterns & correlations" section in
  `standalone/frontend.py`. Graceful degradation: fewer usable columns
  means fewer figures, and blank cells read "too few pairs".
- Audit gained `#patterns` assertions for both the GBIF run and the
  BYOD flow (heatmaps must draw cells, bar charts must draw rows).

**Performance fix found while verifying** (`utils/cooccurrence.py`):
the community panel fetched congener coordinate samples serially with
name-text queries, 20-40 s each, so a 500-record analysis could
block for **290 s**. Names are now resolved to speciesKeys first
(exact filter), fetched on a 4-worker pool under a 28 s wall-clock
budget, and species the budget missed are reported as `no sample`
instead of being shown as zero overlap (which would read as
allopatry). Measured: 290 s → 16 s typical.

## v3.4, light scholarly UI overhaul, both apps (2026-10-21)

Complete UI overhaul under the antislop filter
(`github.com/miqdadbadjuber/anti-slop`, now vendored: `antislop.md` +
`skills/` + pointer block in `AGENTS.md`). Direction chosen by the
project owner: **light scholarly look**, transcribed into `DESIGN.md`.
Everything verified live via CDP; screenshots in `/tmp/biosift_shots`.

- **New identity**: warm paper `#F4F1E8` / card `#FBF9F2` / hairline
  `#D6CFBC`, ink `#232019`, ONE accent deep emerald `#136F4E`, status
  hues only for state (amber `#75530F`, red `#A2382B`, blue `#1D5FA8`).
  Georgia serif display, system sans + tabular numerals, mono for
  machine strings. Radius 4px (pill reserved for status badges), flat
  surfaces (only the map popup floats), hover-only motion. Data colours
  live in `utils/theme.D` (map/chart state encoding).
- **`utils/theme.py` rewritten** (tokens + CSS + components + light
  plotly theme `style_fig`); `.streamlit/config.toml` switched to
  `base = "light"`; `utils/charts.py`, `utils/dataset_quality.py`,
  `utils/maps.py`, `utils/gaps.py`, `utils/sdm.py`,
  `utils/reliability.py` recoloured off the GitHub-dark palette onto
  the new tokens. IUCN chips keep official IUCN colours (a standard's
  data, not our palette).
- **`standalone/frontend.py` re-skinned** to the same identity (CSS
  variables, MapLibre cluster/popup/legend/select colours, data colours
  `ACC/RED/AMBER` = `#1E7A54/#C2402F/#C9922B`); glass blur removed from
  legend/speciesbar.
- **Bugfix**: `views/analysis.py:_tab_map` used `fl.CircleMarker` with
  no `import folium as fl`, so the DBSCAN map always died into the
  `except` and showed "Map error". Now imported inside the tab.
- **Copy fixes**: unbalanced parentheses in 4 alert/warning messages;
  batch limit warning sentence joined without a period; section title
  "Check → TDWG BDQ" arrow replaced; hero facts are now ledger items
  (not pills) because they are provenance statements, not status.
- **Audit tooling**: `scripts/ui_audit.py` dark-theme text heuristic
  replaced with a real luminance contrast probe (flags any text under
  2.5:1, theme-agnostic); the export check now polls up to 120 s for
  the 5 download buttons (reppack ZIP + reportlab PDF + GloBI fetch are
  slower than the old 2 s sample); `BOOT` string is now raw (killed a
  SyntaxWarning).
- **Verified**: `contrast-check.py` (antislop-human) passes 4.5:1 on
  all 13 token pairs after darkening warn amber to `#75530F`; ui_audit
  pages phase 5/5 pages clean (0 exceptions, 0 overflow, 0
  low-contrast); analysis phase clean across all 10 tabs, exports show
  pack/pdf/cube + 5 download buttons; standalone FULL audit ALL CHECKS
  PASSED (2 GBIF species incl. map-colour verdict cross-check 55/55,
  full BYOD flow with flagged-CSV round-trip, 4-viewport matrix).

## Project

- **What**: Biodiversity data-quality and distribution-intelligence
  platform over the GBIF occurrence API. (Competition framing removed
  from product and docs per user request, 2026-09-26.)
- **Live**: https://biosift-gbif.streamlit.app
- **Repo**: https://github.com/Hansen-arch/biosift
- **Stack**: Python 3.12, Streamlit 1.58, Plotly, Folium, reportlab,
  scikit-learn. venv/ is committed-ignore; run with `venv/bin/streamlit run app.py`.

## v3.2, standalone feature-parity push (2026-09-26)

Map/interaction (MapLibre official patterns): click popups with
record detail + BDQ verdict chips + source-record link; clustering
(clusterMaxZoom 8) with flagged-ratio-tinted clusters + count labels
(demotiles glyph server, verified 200). Point colours now come from
the BioSift BDQ verdict (`records.analysed[*].biosift_flag/
biosift_flags`, new in bundle) instead of GBIF's benign `issues`
string, oak: 55 red / 145 green, agreeing with the 74.2 % health
score (was: everything red).

Panel: temporal section (SVG sparkline from new bundle `year_counts`,
span/gaps/trend/recent/citizen-science rows, major-gap chips), SDM
gate-by-gate table (pass/fail + profile + citations), completeness
tile, JSON bundle + records CSV export buttons, fluid panel width
`clamp(320px,29vw,420px)`, table-layout fixed + overflow-wrap:anywhere
(anti-truncation), exports section.

Audit (`scripts/ui_audit_standalone.py` v3): text-clip detector
(scrollWidth/Height probe), map-colour ↔ analysis cross-check, real
cluster + popup click tests (project→container-offset math), 4-viewport
matrix (1440×900, 1092×560 = user's 1366×768 @125 %, 820×900, 390×844
mobile) asserting form-above-fold, reachability and zero clipped text
at every size; `SA_PHASE=viewport` fast mode. FULL RUN: ALL CHECKS
PASSED against the Docker build.

## v3.3, BYOD: bring-your-own-data analysis (2026-09-27)

Research basis: CoordinateCleaner full test catalog (ropensci, Zizka
2019, cc_cap/cc_equ/cc_val/cd_round/cd_ddmm semantics), ALA data
profiles (support.ala.org.au, fatal vs advisory filters applied to
downloads), BDQ TG2 test vocabulary. Gap confirmed: no web tool
combines GBIF-validation + geo plausibility + SDM readiness +
distribution + **cleaned-data export** for uploaded datasets.

- **standalone/byod.py** (engine): readers CSV/TSV/Excel/DwC-A
  (meta.xml field mapping); column mapper (canonical + DWC_ALIASES +
  fuzzy substring, used-column tracking); 9 BYOD-only checks on top
  of the 8 shared ones: swap, capital (80-entry CAPITALS dict,
  15 km haversine), edge, future-date, bad-name, equal-lat/lon
  (cc_equ, (0,0) excluded), ddmm_suspect (cd_ddmm, DATASET-LEVEL:
  suspect only when ≥10 fractional values and NONE ≥0.60),
  dataset_rounded (cd_round, coarse 0.1/0.25/0.5/1.0° grids ≥80 %
  share; 2-decimal data is NOT a hit), coordinate_hotspot (exact
  pair repeated ≥10×). ALA-style PROFILES (General / SDM
  (Zizka et al. 2020) / Report only) with fatal vs advisory checks →
  profile_exclude/profile_advisory columns + retention stats.
  `verify_names` is PARALLEL (8 workers, GBIF etiquette), 200 names
  ~8 s, was ~2 min serial. `cleaned_csv()` returns the USER'S file
  back with biosift_flag/biosift_exclude/biosift_reasons appended,
  or profile-filtered (mode=clean). `rows_geojson` carries
  fl/ex/biosift_flags; impossible coords (|lat|>90, |lon|>180)
  excluded MAP-ONLY (stay in tables/exports), MapLibre throws
  `Invalid LngLat` on fitBounds/jumpTo otherwise and kills renderByod.
- **server endpoints**: POST /api/upload/inspect (metadata +
  proposed_mapping + col_stats {filled%, distinct, kind, sample} +
  3 sample rows), POST /api/upload/analyze (File + mapping +
  dataset_name + profile Form; bundle schema biosift.byod/1.0 now
  includes profile, column_profile, species_table, rounded_stats,
  geojson with verdicts), POST /api/upload/export (mode=flagged|clean
  → {filename, csv} JSON download).
- **frontend**: segmented mode switch (GBIF species / Your data),
  inspect → editable 24-row mapping table (core chips, per-column
  filled/distinct stats, 3-row sample preview) → run → render:
  profile retention box, 17-check table with triggered-count chips,
  species breakdown, dataset profile, outliers, backbone name
  verification, flagged records, recommendations; map colours
  clean=green / flagged=amber / profile-excluded=red; popup shows
  flags + 'Excluded by profile'; exports: JSON, GeoJSON, Flagged CSV,
  Clean CSV. gbif-only sections hidden in BYOD mode (benchmark,
  community, carbon). `pushGeo` now removes any stale popup (a
  popup left open at the same coords swallows the next synthetic
  click, real UX bug found by the audit).
- **audit v4** (`ui_audit_standalone.py`): `byod_flow()`, mode
  switch, file injection via DataTransfer, mapping assertions
  (auto-mapping correctness), run, profile box, 17 checks, flagged
  table, namecheck (case-insensitive, th CSS uppercases), verdict
  colours on map, EXCLUDED-point popup content, flagged-CSV export
  round-trip, then restores GBIF mode. FULL RUN: ALL CHECKS PASSED
  (2×GBIF species + full BYOD + 4 viewports).
- Design polish: joined segmented mode control, count chips in
  section headers, profile summary box, amber legend entry.

Jury criteria for the challenge: **relevance, novelty, quality, openness &
repeatability**. 2025 winners were a BDQ email QC service (GBIF Norway) and
the {galaxias} publishing package (ALA), standards-aligned workflow tools.
GBIF Work Programme 2026 priorities: reproducible FAIR indicator workflows,
data quality at the source, DOI citation, TDWG BDQ, GBIF SQL data cubes
(B-Cubed). Every v2.0 feature maps to one of those.

## Architecture (current, v3.1)

```
app.py                Streamlit entry, st.Page(unique url_path) + nav
views/                home, analysis (10 tabs), batch, publisher, methods
standalone/
  server.py           FastAPI: /api/health, /api/analysis/{species}
                      (bundle biosift.analysis/1.1), /api/.../map, /
  frontend.py         MapLibre GL JS single-file UI (gaia-style landing:
                      numbered capabilities + audience chips)
Dockerfile            python:3.12-slim, uvicorn 0.0.0.0:8080, 2 workers
docker-compose.yml    healthcheck (CMD-SHELL /api/health), restart policy
utils/
  theme.py            design system: C/D tokens, CSS, metric_card, alert,
                      score_hero, style_fig (paper/ink light scholarly,
                      Georgia + system sans; see DESIGN.md v3.4)
  icons.py            inline SVG line icons (icon('dna', 20)), NO emoji
  bdq.py              10 checks → official TDWG BDQ test IDs
  quality.py          the checks + completeness + multimedia stats
  gbif_fetch.py       occurrence client (pygbif, cached; now fetches
                      coordinateUncertaintyInMeters too)
  benchmark.py        GBIF-wide defect baseline (count + facet API)
  fitness.py          SDM readiness gates, 2 strictness profiles,
                      Zizka/Marcer citations
  predict.py          EOO (hull→GeoJSON) + AOO (2×2 km) + KBA-B screen
  carbon.py           Chave 2014 + IPCC 2006 plant carbon scenarios
  interactions.py     GloBI client (directional queries + filtering)
  cooccurrence.py     genus assemblage + 1° Jaccard overlap
  basemaps.py         key-free XYZ registry (Esri default; NO Carto)
  maps.py / gaps.py / sdm.py   folium builders (all basemap-aware)
  reppack.py          Reproducibility Pack ZIP (report JSON incl.
                      fitness + interactions, methods, citations, CSVs,
                      nested DwC-A, recipe.json)
  pdf_report.py       branded PDF (reportlab)
  cube.py             GBIF SQL data-cube query builder
  species_info.py     species/match + IUCN chip helper
scripts/ui_audit.py   raw-CDP audit driver (pages|analysis phases;
                      BIOSIFT_URL env, default :8622)
CONTINUITY.md         this file
```

Design language (v3.4): warm paper `#F4F1E8` bg, ink `#232019`, one
accent deep emerald `#136F4E`, Georgia display serif + system sans,
radius-4 flat cards, hairline `#D6CFBC` borders. Full direction and
reasons in `DESIGN.md`.
**No emoji anywhere**, user explicitly rejected emoji styling as
"AI-generated looking". `utils/icons.py` provides inline SVG line icons
(icon('dna', 20)); st.Page icons use `:material/*:` names; nav uses a
monogram "B" logo. In-app artifact copy (gap map legend etc.) is
plain text.

## v2.1 additions (verified live, 2026-09-26)

- **utils/basemaps.py**, six key-free basemaps (Carto Voyager default,
  Esri World Imagery/Ocean, OpenTopoMap, Positron, dark) +
  `add_layer_control` for in-map switching. User reported CartoDB tiles
  now requiring an API key; Esri/OSM/Carto named-tile set chosen as the
  key-free professional fallback. Wired into maps.py, gaps.py, sdm.py,
  analysis DBSCAN map.
- **utils/interactions.py**, GloBI species interactions. CRITICAL API
  knowledge: the fuzzy `q=` search returns name-resolution artefacts
  (citations/DOIs in taxon_name fields, `interactsWith` noise); the
  directional `sourceTaxon=`/`targetTaxon=` params return resolved,
  semantically-typed records. `_valid_taxon_name()` drops remaining
  artefacts (URLs, digits, parens, >60 chars, all-caps tokens).
  Direction normalised so the analysed species is subject (INVERSE map).
- **utils/fitness.py**, SDM readiness audit: cited gates (Zizka 2020,
  Marcer 2022, GBIF best practice), two strictness profiles (Standard
  ≤10 km / Strict ≤1 km), funnel G1–G6 + ≥100 sample gate. Honest-data
  moment: *P. leo* iNat-style records carry ~31 km stated uncertainty →
  they fail the 10 km gate legitimately; gate text now explains this
  (median of failing records, source-typical, cites Zizka 2022).
- Analysis page now has 8 tabs incl. Interactions + SDM Readiness;
  reppack report JSON carries `sdm_readiness` + `interactions` blocks.

## Judged working (verified live via CDP audit, 2026-09-25)

- All 5 pages route via real URLs (`/analysis`, `/batch`, `/publisher`,
  `/methods`), zero exceptions, zero horizontal overflow.
- Live analysis of *Panthera leo* with real GBIF data: metric row,
  benchmark strip, all 6 tabs (Overview / Map / Temporal / Charts / Gap /
  Data & Export), 5 download buttons (pack, PDF, cube SQL, 2 CSVs).
- IUCN chip renders from `species/{key}` `iucnRedListCategory`.
- Reproducibility Pack + PDF builders unit-smoke-tested with synthetic df.

## Gotchas learned (do not regress)

1. **MapLibre v4 removeLayer/removeSource return void, NOT Promises**
  , `.catch()` on them throws and killed every standalone run after
   the first (map kept stale layers, status showed an error). Fixed in
   `standalone/frontend.py: pushGeo()` with getLayer/getSource guards.
   New audit driver: `scripts/ui_audit_standalone.py` (boot, control
   hit-tests, real Run Analysis flow ×2 species, style-swap survival,
   narrow viewport), `BIOSIFT_URL=http://localhost:8080
   venv/bin/python scripts/ui_audit_standalone.py "Panthera leo"`;
   quick mode without the 2×90 s API runs: `SA_PHASE=viewport`.
2. **Short-viewport fold rule**, the gaia pitch (capabilities +
   audience, ~595 px) used to sit ABOVE the search form and pushed it
   below the fold at 1366×768 physical (1092×560 CSS at 125 % zoom):
   the user literally could not see or reach the form. Pitch now lives
   below the form inside .scroll. Audit asserts form above fold at
   1092×560 AND 820×900.
3. **MapLibre v4 cluster features expose `point_count` /
   `point_count_abbreviated`**, filters written as `['has','count']`
   silently match NOTHING (empty layers, no error). This made every
   point render through the leaf layers at world zoom. Also: cluster
   colour from summed leaf flags needs `clusterProperties` + a
   `case`/`max` expression (paint arrays must be valid expressions).
4. **`fitness.CITATIONS` is a dict**, not a list, any frontend
   `(fit.citations||[]).map(...)` throws and kills the whole render
   (cascades: no map layers, no hull). Guard with type checks.
5. **CDP/map coordinate facts (do not re-learn)**: `map.project()`
   returns CONTAINER-relative px, add the map div's bounding-rect
   offset for CDP mouse clicks; `jumpTo` returns the map object, so
   never return it from Runtime.evaluate ("Object reference chain is
   too long"), wrap in an IIFE; leaves only exist above
   clusterMaxZoom, and on SPARSE data a cluster centroid at z9 can be
   empty, jump to a real leaf coordinate from `window.__lastGeo`.
6. **Bundle embeds only the first 200 analysed rows** (`_clean_records`
   limit), per-record comparisons (e.g. map colour agreement) must be
   against embedded rows, not the full-frame scores.
7. **BYOD facts**: `byod.CANONICAL` = 24 canonical fields; mapper is
   metadata-only and tolerant (missing fields skip gracefully);
   `_jsonify()` sanitises numpy scalars (numpy.bool_ breaks FastAPI
   JSON, again); name verification caps at 200 unique names and is
   the latency driver, keep it parallel. MapLibre cannot render
   |lat|>90/|lon|>180 (swapped coords!), `rows_geojson` filters them
   map-only, and `renderByod` filters defensively client-side too.
8. **Stale popups swallow clicks**: a MapLibre popup left open sits
   ON TOP of the canvas in DOM, a synthetic click at the same pixel
   hits the popup, not the map (queryRenderedFeatures still sees the
   point → tests pass in isolation but fail after a prior popup
   phase). `pushGeo` now closes any open popup when new data is
   pushed; the audit closes it before click tests.
9. **cd_ddmm/cd_round are DATASET-LEVEL tests**, naive per-record
   implementations flag every normal 2-decimal coordinate
   (synthetic 300-row test proved it: 300/300 false positives).
   ddmm requires zero fractions ≥0.60 across the dataset;
   rounded requires ≥80 % share on a coarse grid.
1. **st.Page pathname collision**, five views exporting functions all
   named `render` made Streamlit infer URL pathname `render` for every
   page → `StreamlitAPIException: Multiple Pages specified with URL
   pathname render`. Fixed with explicit `url_path=` per page. If adding a
   page, always pass unique `url_path`.
2. **Cross-function NameErrors in views/analysis.py**, `_render_results`
   needed `map_type` from session_state; `_tab_export` used bare `clean`
   instead of `len(clean_df)`. Both crashed at runtime only (py_compile
   can't catch them). Audit script catches them; keep it in CI habit.
3. **Streamlit h1 font specificity**, Streamlit resets h1 font-family;
   component classes need `.hero .hero-title`-style selectors to win.
4. **st.navigation run order**, `nav.run()` executes the page callable;
   sidebar widgets must be created before it.
5. **pkill -f "streamlit run"** kills your own wrapper shell (matches the
   command string). Use `fuser -k <port>/tcp`, but never on the port your
   shell runs on.
6. **Background servers die between tool calls** in this environment -
   always start server + run checks in ONE terminal command.
7. **st_folium needs stable `key=`** per map instance or tabs reset
   (pre-existing fix, keep it).

## Tooling

- `scripts/ui_audit.py`, raw-CDP headless Chrome driver (no playwright).
  `venv/bin/python scripts/ui_audit.py pages|analysis`.
  Requires: server already on `$BIOSIFT_URL` (default :8622),
  `websocket-client` installed, chrome flags `--headless=new --no-sandbox
  --remote-allow-origins=*`. Self-contained JS (survives Streamlit soft
  reloads); real mouse clicks via `Input.dispatchMouseEvent`; audit checks
  exceptions, horizontal overflow (excluding scrollable containers),
  Streamlit text input needs focus + Enter keypress to commit.

## Conventions

- Commit style: `feat:/fix:/docs:` prefixes, concise why-focused messages,
  no tool attribution.
- Push to `main` after every audited milestone (user standing request).
- Streamlit text inputs need focus + Enter to commit values.
- Never echo the GitHub token baked into the remote URL.

## v2.2 additions (verified live, 2026-09-26)

- Basemaps rewritten with EXPLICIT XYZ URLs (vendor tile-name aliases
  were why maps broke for the user); every endpoint curl-verified
  200 image/*; browser probe confirms tiles load + layer switcher.
- utils/cooccurrence.py, genus assemblage (GBIF facet) + 1° Jaccard
  grid overlap; 'Ecological Community' tab merges GloBI + congeners.
- utils/predict.py, EOO (monotone-chain hull, Burgio 2021 caveat),
  AOO (2×2 km IUCN grid), KBA Criterion B screen (IUCN 2016) with
  screening-only caveat; 'Distribution & KBA' tab.
- Challenge framing REMOVED everywhere (user request).
- Live-verified: EOO warning fires on real data (29.6M km² hull from
  vagrant records), the honesty-first pattern users can cite.

## v3.0, Standalone app (built & audited, 2026-09-26)

- `standalone/server.py`, FastAPI wrapper over the SAME utils/ science
  layer. Endpoints: `/api/health`, `/api/analysis/{species}` (full JSON
  bundle, schema biosift.analysis/1.1, incl. records embed via
  `include_records=true`), `/api/analysis/{species}/map` (folium HTML),
  `/` (frontend). CORS open. Run: `uvicorn standalone.server:app --port 8080`.
- `standalone/frontend.py`, single-file MapLibre GL JS 4.7 app
  (no key/token): CARTO light default + Esri satellite + OpenTopoMap +
  dark switcher (rebuilds style via rasterStyle(); re-pushes GeoJSON on
  switch via window.__lastGeo). Occurrence points colored clean/flagged,
  EOO hull polygon overlay, fitBounds, species bar with IUCN chip.
  `window.__map` exposed for audits.
- Verified live: API 200 full bundle (health 98.7%, SDM 4 ready/1.3%,
  EOO 14.9M km² + hull GeoJSON 10 pts, B2 met, 271 GloBI interactions,
  58-species genus assemblage, 8 Jaccard partners, melanochaita 0.8
  high, pardus 0.33 moderate, leo leo 0.07 low, biologically correct);
  CDP audit: 0 exceptions, MapLibre map.loaded()=true, layers
  [bg, base, occ-pt-stroke, occ-pt-fill, occ-hull-fill, occ-hull-line],
  sources [base, occ, hull].
- API quirks discovered (do not regress): GBIF `facet=species` silently
  returns nothing, use `facet=scientificName` (authorship included,
  strip with _strip_authorship) + `taxonKey=<genusKey from
  /species/match>`; the `genus=` text param is ignored on occurrence
  search. numpy.bool_ is not FastAPI-JSON-serializable, coerce in
  screen_kba_b.
- Live deploy (streamlit cloud) currently behind a login redirect
  (sharing off or app suspended), code is fine; user must re-enable
  public sharing in share.streamlit.io.

## v3.1, Carbon, Carto removal, gaia-style design, deploy (2026-09-26)

### CHANGELOG, every change this version

1. **Carto basemaps deleted everywhere.** User reported Carto tiles
   requiring an API key in production. `utils/basemaps.py` now:
   Esri Light Gray (DEFAULT), OSM, Esri World Imagery, OpenTopoMap,
   Esri Ocean, Esri Dark Gray, all XYZ URLs curl-verified 200 image/*.
   `standalone/frontend.py` BASEMAPS mirrors the same set (key `light`
   is now Esri Light Gray; added `osm` entry). Zero `cartocdn`
   references remain in code.
2. **utils/carbon.py NEW**, scenario carbon standing-stock estimates
   for plant species.
   - Science: Chave et al. 2014 pantropical allometry
     AGB(kg) = 0.0673·(WD·DBH²·H)^0.976 (⚠ kg out, NOT g, first
     implementation divided by 1000 again and zeroed results);
     BGB = AGB×0.24 (IPCC 2006 Tab 4.4); C = DM×0.47 (IPCC default);
     CO2e = C×44/12; annual sequestration ≈ 2.4% of stock.
   - Scenario: each record = 1 mature tree (DBH 30 cm, H 15 m, WD by
     life form: tree 0.60, conifer 0.45, mangrove 0.70, bamboo 0.35,
     palm 0.40, herb/grass 0.20). Life form inferred from name/family
     text; disclosed in every output as a scenario, not an inventory.
   - **Kingdom gate**: only Plantae proceeds (Animalia/Fungi →
     applicable=false with reason). Kingdom comes from GBIF backbone
     via species/{key}, text inference alone cannot tell Panthera
     from Platanus.
   - Sanity check vs literature: 30 cm/15 m oak ≈ 0.44 t AGB ≈ 0.94
     t CO2e/tree. 500 oaks → 469 t CO2e, 11.3 t/yr sequestration.
   - Wired into: Streamlit 'Carbon' tab (tab 7), API bundle `.carbon`,
     frontend '#carbon' section with equivalences (car-km, house-yrs).
3. **Standalone frontend redesigned (gaia.eco style reference)**:
   header tagline 'Professional Biodiversity Studio'; numbered
   capability strip (5 caps) + audience chips shown on landing,
   hidden once results render; carbon section added. No emoji.
4. **Docker deploy**: Dockerfile (python:3.12-slim, uvicorn 0.0.0.0
   8080, 2 workers, keep-alive 120), docker-compose.yml with
   healthcheck on /api/health, .dockerignore. Docker daemon needs
   sudo in this sandbox → NOT built here; production CMD verified on
   0.0.0.0:8095 (health 200, frontend 200, oak bundle 200 with
   carbon). README documents Railway/Render/Fly/VPS paths.
   ⚠ host port 8080 is occupied by sandbox SearXNG, inside a
   container this is irrelevant.
5. **Landing-state bugfix**: capabilities/audience strips were only
   ever hidden (in render()), now shown at boot.

### REPRODUCE THIS SESSION (full v1→v3.1 path)

```bash
git clone https://github.com/Hansen-arch/biosift && cd biosift
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Streamlit app (multi-page, 10 tabs incl. Carbon)
streamlit run app.py                    # http://localhost:8501

# Standalone app (FastAPI + MapLibre, no keys)
uvicorn standalone.server:app --port 8080   # http://localhost:8080

# Docker (any host with a docker daemon)
docker compose up --build               # http://localhost:8080

# UI audit (needs: chrome + websocket-client)
BIOSIFT_URL=http://localhost:8622 python scripts/ui_audit.py pages
BIOSIFT_URL=http://localhost:8622 python scripts/ui_audit.py analysis
```

API smoke:
```bash
curl localhost:8080/api/health
curl "localhost:8080/api/analysis/Quercus%20robur?limit=200" | jq .carbon
curl "localhost:8080/api/analysis/Panthera%20leo?limit=300" | jq .sdm_readiness.verdict
```

Audit history: every version was verified live via CDP (screenshots in
/tmp/biosift_shots: 01–05 pages, 06–15 streamlit flow, 20–22 live
cloud attempts, 30–43 new tabs + tiles, 40–43 v2.2, 50 live-deploy,
60–62 standalone v3.0, 70–72 v3.1).

## Docker build verification (2026-09-26), REAL BUILD SUCCEEDED

**REAL BUILD RECORD (2026-09-26, host hans-ThinkPad-X230):**

1. Docker engine appeared on host (socket /var/run/docker.sock up);
   `sudo usermod -aG docker hans` granted access (used via `sg docker
   -c` from the agent shell, no re-login needed).
2. Compose v2 v5.5.1 plugin installed user-space (~/.docker/cli-plugins/);
   legacy docker-compose v1.29.2 also present but v2 is what runs.
3. Removed obsolete `version:` attribute from docker-compose.yml
   (compose v2 warning cleanup), config then validated warning-free.
4. SearXNG container stopped to free host 8080 (`docker start searxng`
   restores it).
5. `docker compose up --build -d` → 11 steps, image
   gbif-quickcheck-biosift:latest built, container biosift-standalone
   created and started on first attempt. No build errors.
6. **healthy in ~38 s** (start_period 20s, interval 30s, retries 3).
   Cold build+boot comfortably under the ~2 min pip-layer estimate.
7. Live verification: /api/health 200 {"status":"ok","gbif_api":"ok"}
   (GBIF reachable from inside the container); frontend / 200 (23.6
   kB); /docs 200; full oak bundle HTTP 200 in 87 s, schema
   biosift.analysis/1.1, 8 quality checks, SDM READY,
   carbon.per_tree.co2e_t 0.939, carbon.sample_totals 469.3 t CO2e /
   11.26 t-yr over 500 records, equivalences + Chave/IPCC/Zanne
   citations all present. Matches all pre-verified expected values.

The simulation record below (kept for history) was done before daemon
access existed, it predicted this build correctly, including the
healthcheck YAML bug it caught:

1. `docker compose config` unavailable (old docker CLI) → validated
   docker-compose.yml with Python yaml.safe_load instead. **This caught
   a real bug**: the healthcheck `test:` used a multi-line flow sequence
   `["CMD", "python", "-c", ...]` that is invalid YAML flow syntax
   (would have failed `docker compose up`). Fixed to CMD-SHELL + folded
   scalar; shell command executed and verified against a dead port.
2. Build-context simulation: fresh dir /tmp/biosift_img with ONLY the
   files the Dockerfile COPYs (utils, standalone, views, app.py,
   requirements.txt), mirrors what .dockerignore lets into the image.
3. Fresh venv + `pip install -r requirements.txt` → exit 0, all heavy
   imports OK (fastapi, uvicorn, streamlit, folium, reportlab, plotly,
   sklearn, scipy), proves the requirements pin set is complete for a
   clean environment.
4. Production CMD booted from the simulated image fs:
   `uvicorn standalone.server:app --host 0.0.0.0 --port ... --workers 1
   --timeout-keep-alive 120` → health 200, frontend 200, /docs 200,
   full oak analysis 200 (health 67.3%, SDM READY, carbon 140.8 t
   CO2e / 3.38 t per year).

Remaining for a real host: `docker compose up --build` and confirm the
container healthcheck flips to healthy (start_period 20s, interval 30s,
retries 3). Expect first-boot cold ~2 min for pip layer.

## Roadmap ideas (not started)

- **Standalone app (user wants this)**: FastAPI backend wrapping utils/
  (already framework-agnostic) + MapLibre GL JS frontend; deploy via
  Docker. Keeps Streamlit app as the quick-share demo.

- pytest suite for quality checks + pack builders
- README screenshots from scripts/ui_audit.py output
- authenticated GBIF downloads for >10k records
- repatriated/facet expansion in benchmark.py
- st.navigation grouped sections if pages multiply
