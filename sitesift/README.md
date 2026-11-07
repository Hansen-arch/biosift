# SiteSift

**Site-level biodiversity screening from open GBIF data.**

Draw a polygon over a site, a project footprint, a development parcel, a
survey plot, and SiteSift reports which species are recorded there, which
are of conservation concern, how the records are distributed in time, who
published them, and how trustworthy they are.

It exists because site screening (TNFD LEAP *Locate/Evaluate*, ESRS E4 site
disclosure, EIA scoping) is normally licensed: IBAT's free tier shows a map,
but report downloads cost $750–$1,500 per site and **API access starts at
$35,000/year**. SiteSift covers the part that only needs open data, so a
screen can be run, scripted and audited before anyone buys a report.

It is a **triage layer, not an IBAT replacement.** See *What it will not
claim* below.

> **Merged into BioSift (2026-11-05).** The screen is now the **Site
> Screening** page of the main app (`streamlit run app.py`, `/site`): draw,
> bounding box, point + radius, or import a GeoJSON / KML / WKT / CSV
> boundary, with GeoJSON/KML/WKT export and a country filter. This
> standalone server is kept as the JSON surface over the same
> `screening.py` engine, so there is one implementation of the science.

---

## Run

From the repository root:

```bash
pip install -r requirements.txt
uvicorn sitesift.server:app --port 8090
# open http://localhost:8090
```

Requires only `fastapi`, `uvicorn` and `requests`, already in
`requirements.txt`. No API keys, no database, no build step; the frontend is
a single HTML page with MapLibre from a CDN.

UI audit (headless Chrome over CDP):

```bash
SITESIFT_URL=http://localhost:8090 venv/bin/python scripts/ui_audit_sitesift.py
```

---

## How to use it

1. **Click** the map to place three or more vertices around the site.
   `Backspace` undoes, `Esc` clears, `Enter` screens.
   Or press **Use current map view** to screen the visible extent. The API
   also accepts a point plus `radius_km`.
2. Set a name, optionally restrict **From/To year** or **record type**.
3. **Screen site.**
4. Read *Read before you cite* before using any number.

A 4 km² central-London site returns in about 5 s; results are cached per
query for an hour, so changing the label or re-opening is instant.

---

## What it reports

| Panel | What it answers |
|---|---|
| Summary | records inside, species recorded, threatened records, dataset count, records per km² |
| Species of concern | named CR / EN / VU species with record counts |
| IUCN categories | full composition, EX → DD |
| Native or introduced | split **with its coverage**, because the field is sparse |
| Most recorded species | top 30 with counts |
| Survey effort over time | decade histogram, first/last year, % since 2000 |
| Seasonality | records by month |
| Record quality | GBIF issues that actually affect evidence, with percentages |
| Which datasets | attribution with links to GBIF |
| Caveats | the limitations, stated in plain language |
| Exports | JSON bundle, rerun scripts in R (`rgbif`) and Python (`requests`) |

Every screen is reproducible: the exported scripts contain the exact WKT,
filters and the note that IUCN categories take no comma list.

---

## What it will not claim

Three deliberate refusals, each because the honest answer is "we cannot know
this from open data":

- **No protected-area or KBA overlap.** WDPA/WDPCA and the World Database of
  KBAs are licensed. Protected Planet's API returns `401` without a token and
  the KBA download is a request form. A site screen that guessed at
  designations would be fabricating the single most consequential finding, so
  SiteSift omits it and says so in the caveats.
- **No native/introduced filtering.** The field is recorded on a small
  fraction of records (3% for *Quercus robur*, 1.7% in the London test site).
  Filtering would discard almost all evidence, so coverage is disclosed
  instead, which is also what makes planted species visible rather than
  silently mixed into a threatened-species list.
- **No population or trend claim.** Record counts measure survey effort.
  A species absent from a site list may be unsurveyed.

Absence records are excluded (`occurrenceStatus=PRESENT`); GBIF returns them
as occurrences by default.

---

## API

`POST /api/screen`

```json
{
  "geometry": {"type": "Polygon",
               "coordinates": [[[-0.14,51.48],[-0.10,51.48],
                                [-0.10,51.52],[-0.14,51.52],[-0.14,51.48]]]},
  "label": "Depot extension",
  "year_from": 2000,
  "year_to": 2026,
  "basis": "All",
  "country": "GB"
}
```

Also accepts `{"type":"Point","coordinates":[lon,lat],"radius_km":2}`.
`country` takes an ISO 3166-1 alpha-2 code and is optional.
Returns the full bundle (site, summary, threatened, iucn, establishment,
species, temporal, months, issues, **countries**, datasets, points,
caveats, method).
`GET /api/health` for liveness. Bad geometry returns `422` with a readable
reason; GBIF failure returns `502`.

---

## GBIF behaviours this depends on (measured, do not re-learn)

| Behaviour | Consequence |
|---|---|
| `geometry=POLYGON((...))` works keyless, ~2 s | the whole app is possible without a key |
| Eight facets in one request, ~1.7 s | all composition from a single call |
| **Clockwise exterior rings are rejected** (`400 Polygon with clockwise exterior ring`) | rings are re-wound before querying, a drawn polygon can go either way |
| `iucnRedListCategory=CR` filters records | named species of concern without per-taxon calls |
| **`iucnRedListCategory=CR,EN,VU` returns 0** | one call per category, never a comma list |
| `facetLimit` defaults to **10** | unset, species lists truncate silently |
| **`geoDistance=lat,lon,km` is broken** | 10 km radius returned 64 records where the equivalent bbox returned 2.9 million, and counts did not scale with area. Point+radius is built as a real polygon instead |
| `occurrenceStatus` defaults to including ABSENT | always filter `PRESENT` (4.7% of *Acer pseudoplatanus* records were absences) |
| ~43 `issue` values, mostly bookkeeping | a curated material subset is shown; the rest is counted |

---

## Files

```
sitesift/
  screening.py   # GBIF queries, polygon handling, bundle assembly
  server.py      # FastAPI: /, /api/health, /api/screen
  frontend.py    # single-page MapLibre UI, SVG charts, script exports
scripts/
  ui_audit_sitesift.py   # 28-check CDP audit
```

Science notes: EOO/AOO, KBA Criterion B screening and BDQ checks live in the
main BioSift app (`utils/`, `standalone/`); SiteSift deliberately shares no
code with them so either app can change without breaking the other.
