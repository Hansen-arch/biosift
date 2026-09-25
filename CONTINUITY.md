# BioSift — Project Continuity

> Living document. Update after every milestone so any future session can
> resume with full context. Last updated: 2026-09-25 (v2.0 redesign).

## Project

- **What**: Biodiversity data-quality intelligence platform over the GBIF
  occurrence API. Built for the 2026 GBIF Ebbe Nielsen Challenge.
- **Live**: https://biosift-gbif.streamlit.app
- **Repo**: https://github.com/Hansen-arch/biosift
- **Stack**: Python 3.12, Streamlit 1.58, Plotly, Folium, reportlab,
  scikit-learn. venv/ is committed-ignore; run with `venv/bin/streamlit run app.py`.

## Why v2.0 exists (research-backed rationale)

Jury criteria for the challenge: **relevance, novelty, quality, openness &
repeatability**. 2025 winners were a BDQ email QC service (GBIF Norway) and
the {galaxias} publishing package (ALA) — standards-aligned workflow tools.
GBIF Work Programme 2026 priorities: reproducible FAIR indicator workflows,
data quality at the source, DOI citation, TDWG BDQ, GBIF SQL data cubes
(B-Cubed). Every v2.0 feature maps to one of those.

## Architecture (v2.0)

```
app.py               entry point — st.Page(...url_path=...) + st.navigation
views/               one render() per page: home, analysis, batch,
                     publisher, methods
utils/theme.py       design system: C colour tokens, CSS, metric_card,
                     score_hero, badge, alert, style_fig
utils/bdq.py         maps the 10 quality checks to official TDWG BDQ IDs
utils/benchmark.py   GBIF-wide defect-rate baseline (count + facet API)
utils/reppack.py     Reproducibility Pack ZIP (report JSON, methods,
                     citations, CSVs, nested DwC-A, recipe.json, README)
utils/pdf_report.py  branded PDF via reportlab
utils/cube.py        GBIF SQL data-cube query builder
utils/quality.py     the 10 checks + completeness + multimedia (pre-existing)
utils/gbif_fetch.py  occurrence API client, pygbif, cached (pre-existing)
```

Design language: ink `#0B0F14` bg, emerald `#22C58B` accent, Fraunces
display serif + Inter, radius-16 cards, hairline `#1F2A38` borders.

## Judged working (verified live via CDP audit, 2026-09-25)

- All 5 pages route via real URLs (`/analysis`, `/batch`, `/publisher`,
  `/methods`), zero exceptions, zero horizontal overflow.
- Live analysis of *Panthera leo* with real GBIF data: metric row,
  benchmark strip, all 6 tabs (Overview / Map / Temporal / Charts / Gap /
  Data & Export), 5 download buttons (pack, PDF, cube SQL, 2 CSVs).
- IUCN chip renders from `species/{key}` `iucnRedListCategory`.
- Reproducibility Pack + PDF builders unit-smoke-tested with synthetic df.

## Gotchas learned (do not regress)

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

## Roadmap ideas (not started)

- pytest suite for quality checks + pack builders
- README screenshots from scripts/ui_audit.py output
- authenticated GBIF downloads for >10k records
- repatriated/facet expansion in benchmark.py
- st.navigation grouped sections if pages multiply
