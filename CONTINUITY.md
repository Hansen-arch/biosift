# BioSift — Project Continuity

> Living document. Update after every milestone so any future session can
> resume with full context. **Current version: v3.1** (2026-09-26).

---

## ⏯ START HERE — next session

### What BioSift is now (v3.1, all verified working)

A biodiversity data-quality & distribution-intelligence platform over
the public GBIF API, shipped as **two apps on one science layer**:

1. **Streamlit app** (`app.py`) — multi-page: Home, Species Analysis
   (10 tabs: Overview, Occurrence Map, Temporal, Charts, Ecological
   Community, Distribution & KBA, Carbon, SDM Readiness, Gap Analysis,
   Data & Export), Batch Comparison, Publisher Report, Methods &
   Standards.
2. **Standalone** (`standalone/server.py` + `standalone/frontend.py`)
   — FastAPI JSON API + MapLibre GL JS single-page inspector. No API
   keys anywhere. Dockerfile + compose ready.

Science layer (`utils/`): TDWG BDQ-mapped quality checks, GBIF-wide
benchmarking, SDM readiness gates (Zizka 2020 / Marcer 2022, 2
strictness profiles), EOO/AOO + KBA Criterion B screening (+ hull
GeoJSON), GloBI interactions, congeneric co-occurrence (Jaccard),
plant carbon scenarios (Chave 2014 + IPCC 2006), Reproducibility Pack,
PDF report, data-cube SQL.

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
   first real `docker compose up --build` succeeded — container
   biosift-standalone healthy in ~38 s; health, frontend, /docs and a
   full oak bundle all 200 (record: "Docker build verification" below).
3. **Host quirk**: SearXNG on this machine is a Docker container bound
   to 8080. It was STOPPED for the biosift build — `docker start
   searxng` restores it. Local uvicorn tests: use 8090/8095/8096.
   Docker access from the agent shell: `sg docker -c "..."` (hans was
   added to the docker group without re-login); compose v2 v5.5.1
   plugin installed user-space at ~/.docker/cli-plugins/.
4. Analysis bundles take 30–75 s (multi-request GBIF + GloBI + genus
   facet). If it feels slow next session: parallelise inside
   `standalone/server.py:analysis()` or cache genus_df by genus key.

### Prioritised roadmap

1. pytest suite (carbon, fitness gates, co-occurrence, interactions
   filtering) — protects the science during refactors
2. GitHub Actions: build Docker image on push + run API smoke tests
3. Re-enable Streamlit Cloud sharing (user, 2 minutes)
4. Per-record DBH uncertainty bands for carbon (Monte-Carlo around the
   30 cm scenario instead of a fixed point)
5. Species gallery with images (gaia-style discovery view)
6. Authenticated GBIF downloads for >10k-record species

### Hard-won API knowledge (do not re-learn)

- **GBIF occurrence search**: `facet=species` is a silent NO-OP — use
  `facet=scientificName` (returns authorship; strip with
  `_strip_authorship`) + `taxonKey=<genusKey from /species/match>`.
  The `genus=` text param is IGNORED on occurrence/search.
- **GloBI**: the fuzzy `q=` search returns name-resolution garbage
  (citations/DOIs in taxon fields). Use directional `sourceTaxon=` /
  `targetTaxon=` params; keep `_valid_taxon_name()` filtering.
- **Chave 2014 returns AGB in kg** for D in cm, H in m, WD in g/cm³ —
  do NOT divide by 1000 again.
- **numpy.bool_ breaks FastAPI JSON** — coerce flags with bool() in
  `screen_kba_b`.
- **st.Page needs unique `url_path=`** when page callables share a
  name (all views export `render`).
- **Streamlit h1 font reset** beats single-class selectors — use
  `.hero .hero-title` specificity.

---

## Project

- **What**: Biodiversity data-quality and distribution-intelligence
  platform over the GBIF occurrence API. (Competition framing removed
  from product and docs per user request, 2026-09-26.)
- **Live**: https://biosift-gbif.streamlit.app
- **Repo**: https://github.com/Hansen-arch/biosift
- **Stack**: Python 3.12, Streamlit 1.58, Plotly, Folium, reportlab,
  scikit-learn. venv/ is committed-ignore; run with `venv/bin/streamlit run app.py`.

## History — why v2.0 exists (pre-competition-removal rationale)

Jury criteria for the challenge: **relevance, novelty, quality, openness &
repeatability**. 2025 winners were a BDQ email QC service (GBIF Norway) and
the {galaxias} publishing package (ALA) — standards-aligned workflow tools.
GBIF Work Programme 2026 priorities: reproducible FAIR indicator workflows,
data quality at the source, DOI citation, TDWG BDQ, GBIF SQL data cubes
(B-Cubed). Every v2.0 feature maps to one of those.

## Architecture (current, v3.1)

```
app.py                Streamlit entry — st.Page(unique url_path) + nav
views/                home, analysis (10 tabs), batch, publisher, methods
standalone/
  server.py           FastAPI: /api/health, /api/analysis/{species}
                      (bundle biosift.analysis/1.1), /api/.../map, /
  frontend.py         MapLibre GL JS single-file UI (gaia-style landing:
                      numbered capabilities + audience chips)
Dockerfile            python:3.12-slim, uvicorn 0.0.0.0:8080, 2 workers
docker-compose.yml    healthcheck (CMD-SHELL /api/health), restart policy
utils/
  theme.py            design system: C tokens, CSS, metric_card, alert,
                      score_hero, style_fig (ink/emerald, Fraunces+Inter)
  icons.py            inline SVG line icons (icon('dna', 20)) — NO emoji
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

Design language: ink `#0B0F14` bg, emerald `#22C58B` accent, Fraunces
display serif + Inter, radius-16 cards, hairline `#1F2A38` borders.
**No emoji anywhere** — user explicitly rejected emoji styling as
"AI-generated looking". `utils/icons.py` provides inline SVG line icons
(icon('dna', 20)); st.Page icons use `:material/*:` names; nav uses a
monogram "B" logo. In-app artifact copy (gap map legend etc.) is
plain text.

## v2.1 additions (verified live, 2026-09-26)

- **utils/basemaps.py** — six key-free basemaps (Carto Voyager default,
  Esri World Imagery/Ocean, OpenTopoMap, Positron, dark) +
  `add_layer_control` for in-map switching. User reported CartoDB tiles
  now requiring an API key; Esri/OSM/Carto named-tile set chosen as the
  key-free professional fallback. Wired into maps.py, gaps.py, sdm.py,
  analysis DBSCAN map.
- **utils/interactions.py** — GloBI species interactions. CRITICAL API
  knowledge: the fuzzy `q=` search returns name-resolution artefacts
  (citations/DOIs in taxon_name fields, `interactsWith` noise); the
  directional `sourceTaxon=`/`targetTaxon=` params return resolved,
  semantically-typed records. `_valid_taxon_name()` drops remaining
  artefacts (URLs, digits, parens, >60 chars, all-caps tokens).
  Direction normalised so the analysed species is subject (INVERSE map).
- **utils/fitness.py** — SDM readiness audit: cited gates (Zizka 2020,
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
   — `.catch()` on them throws and killed every standalone run after
   the first (map kept stale layers, status showed an error). Fixed in
   `standalone/frontend.py: pushGeo()` with getLayer/getSource guards.
   New audit driver: `scripts/ui_audit_standalone.py` (boot, control
   hit-tests, real Run Analysis flow ×2 species, style-swap survival,
   narrow viewport) — `BIOSIFT_URL=http://localhost:8080
   venv/bin/python scripts/ui_audit_standalone.py "Panthera leo"`.
1. **st.Page pathname collision** — five views exporting functions all
   named `render` made Streamlit infer URL pathname `render` for every
   page → `StreamlitAPIException: Multiple Pages specified with URL
   pathname render`. Fixed with explicit `url_path=` per page. If adding a
   page, always pass unique `url_path`.
2. **Cross-function NameErrors in views/analysis.py** — `_render_results`
   needed `map_type` from session_state; `_tab_export` used bare `clean`
   instead of `len(clean_df)`. Both crashed at runtime only (py_compile
   can't catch them). Audit script catches them; keep it in CI habit.
3. **Streamlit h1 font specificity** — Streamlit resets h1 font-family;
   component classes need `.hero .hero-title`-style selectors to win.
4. **st.navigation run order** — `nav.run()` executes the page callable;
   sidebar widgets must be created before it.
5. **pkill -f "streamlit run"** kills your own wrapper shell (matches the
   command string). Use `fuser -k <port>/tcp` — but never on the port your
   shell runs on.
6. **Background servers die between tool calls** in this environment —
   always start server + run checks in ONE terminal command.
7. **st_folium needs stable `key=`** per map instance or tabs reset
   (pre-existing fix, keep it).

## Tooling

- `scripts/ui_audit.py` — raw-CDP headless Chrome driver (no playwright).
  `venv/bin/python scripts/ui_audit.py pages|analysis`.
  Requires: server already on `$BIOSIFT_URL` (default :8622),
  `websocket-client` installed, chrome flags `--headless=new --no-sandbox
  --remote-allow-origins=*`. Self-contained JS (survives Streamlit soft
  reloads); real mouse clicks via `Input.dispatchMouseEvent`; audit checks
  exceptions, horizontal overflow (excluding scrollable containers),
  Streamlit text input needs focus + Enter keypress to commit.

## Conventions

- Commit style: `feat:/fix:/docs:` prefixes, concise why-focused messages,
  Codebuff footer.
- Push to `main` after every audited milestone (user standing request).
- Streamlit text inputs need focus + Enter to commit values.
- Never echo the GitHub token baked into the remote URL.

## v2.2 additions (verified live, 2026-09-26)

- Basemaps rewritten with EXPLICIT XYZ URLs (vendor tile-name aliases
  were why maps broke for the user); every endpoint curl-verified
  200 image/*; browser probe confirms tiles load + layer switcher.
- utils/cooccurrence.py — genus assemblage (GBIF facet) + 1° Jaccard
  grid overlap; 'Ecological Community' tab merges GloBI + congeners.
- utils/predict.py — EOO (monotone-chain hull, Burgio 2021 caveat),
  AOO (2×2 km IUCN grid), KBA Criterion B screen (IUCN 2016) with
  screening-only caveat; 'Distribution & KBA' tab.
- Challenge framing REMOVED everywhere (user request).
- Live-verified: EOO warning fires on real data (29.6M km² hull from
  vagrant records) — the honesty-first pattern users can cite.

## v3.0 — Standalone app (built & audited, 2026-09-26)

- `standalone/server.py` — FastAPI wrapper over the SAME utils/ science
  layer. Endpoints: `/api/health`, `/api/analysis/{species}` (full JSON
  bundle, schema biosift.analysis/1.1, incl. records embed via
  `include_records=true`), `/api/analysis/{species}/map` (folium HTML),
  `/` (frontend). CORS open. Run: `uvicorn standalone.server:app --port 8080`.
- `standalone/frontend.py` — single-file MapLibre GL JS 4.7 app
  (no key/token): CARTO light default + Esri satellite + OpenTopoMap +
  dark switcher (rebuilds style via rasterStyle(); re-pushes GeoJSON on
  switch via window.__lastGeo). Occurrence points colored clean/flagged,
  EOO hull polygon overlay, fitBounds, species bar with IUCN chip.
  `window.__map` exposed for audits.
- Verified live: API 200 full bundle (health 98.7%, SDM 4 ready/1.3%,
  EOO 14.9M km² + hull GeoJSON 10 pts, B2 met, 271 GloBI interactions,
  58-species genus assemblage, 8 Jaccard partners — melanochaita 0.8
  high, pardus 0.33 moderate, leo leo 0.07 low — biologically correct);
  CDP audit: 0 exceptions, MapLibre map.loaded()=true, layers
  [bg, base, occ-pt-stroke, occ-pt-fill, occ-hull-fill, occ-hull-line],
  sources [base, occ, hull].
- API quirks discovered (do not regress): GBIF `facet=species` silently
  returns nothing — use `facet=scientificName` (authorship included,
  strip with _strip_authorship) + `taxonKey=<genusKey from
  /species/match>`; the `genus=` text param is ignored on occurrence
  search. numpy.bool_ is not FastAPI-JSON-serializable — coerce in
  screen_kba_b.
- Live deploy (streamlit cloud) currently behind a login redirect
  (sharing off or app suspended) — code is fine; user must re-enable
  public sharing in share.streamlit.io.

## v3.1 — Carbon, Carto removal, gaia-style design, deploy (2026-09-26)

### CHANGELOG — every change this version

1. **Carto basemaps deleted everywhere.** User reported Carto tiles
   requiring an API key in production. `utils/basemaps.py` now:
   Esri Light Gray (DEFAULT), OSM, Esri World Imagery, OpenTopoMap,
   Esri Ocean, Esri Dark Gray — all XYZ URLs curl-verified 200 image/*.
   `standalone/frontend.py` BASEMAPS mirrors the same set (key `light`
   is now Esri Light Gray; added `osm` entry). Zero `cartocdn`
   references remain in code.
2. **utils/carbon.py NEW** — scenario carbon standing-stock estimates
   for plant species.
   - Science: Chave et al. 2014 pantropical allometry
     AGB(kg) = 0.0673·(WD·DBH²·H)^0.976 (⚠ kg out, NOT g — first
     implementation divided by 1000 again and zeroed results);
     BGB = AGB×0.24 (IPCC 2006 Tab 4.4); C = DM×0.47 (IPCC default);
     CO2e = C×44/12; annual sequestration ≈ 2.4% of stock.
   - Scenario: each record = 1 mature tree (DBH 30 cm, H 15 m, WD by
     life form: tree 0.60, conifer 0.45, mangrove 0.70, bamboo 0.35,
     palm 0.40, herb/grass 0.20). Life form inferred from name/family
     text; disclosed in every output as a scenario, not an inventory.
   - **Kingdom gate**: only Plantae proceeds (Animalia/Fungi →
     applicable=false with reason). Kingdom comes from GBIF backbone
     via species/{key} — text inference alone cannot tell Panthera
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
   ⚠ host port 8080 is occupied by sandbox SearXNG — inside a
   container this is irrelevant.
5. **Landing-state bugfix**: capabilities/audience strips were only
   ever hidden (in render()) — now shown at boot.

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

## Docker build verification (2026-09-26) — REAL BUILD SUCCEEDED

**REAL BUILD RECORD (2026-09-26, host hans-ThinkPad-X230):**

1. Docker engine appeared on host (socket /var/run/docker.sock up);
   `sudo usermod -aG docker hans` granted access (used via `sg docker
   -c` from the agent shell — no re-login needed).
2. Compose v2 v5.5.1 plugin installed user-space (~/.docker/cli-plugins/);
   legacy docker-compose v1.29.2 also present but v2 is what runs.
3. Removed obsolete `version:` attribute from docker-compose.yml
   (compose v2 warning cleanup) — config then validated warning-free.
4. SearXNG container stopped to free host 8080 (`docker start searxng`
   restores it).
5. `docker compose up --build -d` → 11 steps, image
   gbif-quickcheck-biosift:latest built, container biosift-standalone
   created and started on first attempt. No build errors.
6. **healthy in ~38 s** (start_period 20s, interval 30s, retries 3).
   Cold build+boot comfortably under the ~2 min pip-layer estimate.
7. Live verification: /api/health 200 {"status":"ok","gbif_api":"ok"}
   (GBIF reachable from inside the container); frontend / 200 (23.6
   kB); /docs 200; full oak bundle HTTP 200 in 87 s — schema
   biosift.analysis/1.1, 8 quality checks, SDM READY,
   carbon.per_tree.co2e_t 0.939, carbon.sample_totals 469.3 t CO2e /
   11.26 t-yr over 500 records, equivalences + Chave/IPCC/Zanne
   citations all present. Matches all pre-verified expected values.

The simulation record below (kept for history) was done before daemon
access existed — it predicted this build correctly, including the
healthcheck YAML bug it caught:

1. `docker compose config` unavailable (old docker CLI) → validated
   docker-compose.yml with Python yaml.safe_load instead. **This caught
   a real bug**: the healthcheck `test:` used a multi-line flow sequence
   `["CMD", "python", "-c", ...]` that is invalid YAML flow syntax
   (would have failed `docker compose up`). Fixed to CMD-SHELL + folded
   scalar; shell command executed and verified against a dead port.
2. Build-context simulation: fresh dir /tmp/biosift_img with ONLY the
   files the Dockerfile COPYs (utils, standalone, views, app.py,
   requirements.txt) — mirrors what .dockerignore lets into the image.
3. Fresh venv + `pip install -r requirements.txt` → exit 0, all heavy
   imports OK (fastapi, uvicorn, streamlit, folium, reportlab, plotly,
   sklearn, scipy) — proves the requirements pin set is complete for a
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
