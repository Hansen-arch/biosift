"""Time-aware sampling for change-over-time analysis.

A single newest-first GBIF page has no temporal spread: for most
species `limit=500` lands entirely in the last year or two, so any
range-shift or trend figure computed from it is meaningless. These
probes give the missing history cheaply:

  year_histogram   one `facet=year` request — population record counts
                   per year over the whole query window
  year_probes      counts/effort (`limit=0` + `datasetKey` and
                   `recordedBy` facets, ~1 s each) for up to
                   `max_years` years, plus a coordinate subsample for
                   the earliest and latest years. The coordinate side
                   keeps probing further candidate years until it has
                   enough rows for a period, because early years for a
                   sparse species often carry no georeferenced records
                   at all. Both phases are wall-clock-bounded.
  effort_trend     records per distinct recorder (falling back to
                   reporting datasets) indexed to its own median

Two GBIF quirks encoded here:
  * only valid facet fields are honoured — `facet=dataset` is silently
    ignored (`facets: []`); the working names are `datasetKey` and
    `recordedBy`
  * bursts of coordinate requests get throttled, so those use a small
    pool with retries while the cheap facet queries fan out wide
"""
import time
from concurrent.futures import ThreadPoolExecutor, wait

import numpy as np
import pandas as pd
import requests

GBIF = "https://api.gbif.org/v1/occurrence/search"

COLUMNS = ["species", "decimalLatitude", "decimalLongitude", "year",
           "month", "country", "basisOfRecord", "datasetName",
           "coordinateUncertaintyInMeters", "eventDate"]

MIN_ROWS_PER_PERIOD = 10


def _params(species, year_from=None, year_to=None, basis=None, **more):
    p = {"scientificName": species}
    if year_from and year_to:
        p["year"] = f"{int(year_from)},{int(year_to)}"
    if basis and basis != "All":
        p["basisOfRecord"] = basis
    p.update(more)
    return p


def _get(params, timeout=15):
    r = requests.get(GBIF, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def year_histogram(species, year_from, year_to, basis) -> dict:
    """{year: records} over the whole matching population."""
    try:
        js = _get(_params(species, year_from, year_to, basis,
                          limit=0, facet="year", facetLimit=1000))
    except Exception:
        return {}
    facets = js.get("facets") or []
    if not facets:
        return {}
    out = {}
    for b in facets[0].get("counts", []):
        try:
            y = int(b.get("name"))
        except (TypeError, ValueError):
            continue
        if 1700 <= y <= 2100:
            out[y] = int(b.get("count") or 0)
    return dict(sorted(out.items()))


def _facet_count(js, field):
    for f in (js.get("facets") or []):
        if str(f.get("field", "")).upper() == field.upper():
            return len(f.get("counts") or [])
    return 0


def _counts_probe(species, year, basis):
    """Counts + effort facets for one year (cheap: no coordinates)."""
    try:
        params = _params(species, year, year, basis, limit=0,
                         facetLimit=500)
        # repeated query param: requests encodes a list as facet=a&facet=b
        params["facet"] = ["datasetKey", "recordedBy"]
        js = _get(params, timeout=12)
        return {
            "year": int(year),
            "records": int(js.get("count", 0)),
            "datasets": max(1, _facet_count(js, "DATASET_KEY")),
            "recorders": _facet_count(js, "RECORDED_BY"),
            "rows": None,
        }
    except Exception:
        return None


def _rows_probe(species, year, basis, per_year, attempts=3):
    """Coordinate subsample for one year (the expensive page).

    GBIF throttles bursts of coordinate requests, so this retries with
    a short backoff instead of silently returning an empty period.
    """
    params = _params(species, year, year, basis,
                     limit=per_year, hasCoordinate="true")
    for attempt in range(attempts):
        try:
            js = _get(params, timeout=20)
            frame = pd.DataFrame(js.get("results", []))
            cols = [c for c in COLUMNS if c in frame.columns]
            return int(year), (frame[cols] if len(cols) else None)
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return int(year), None


def _pool(fn, items, workers, budget):
    """Run fn(item) over items on a bounded pool; return truthy results
    finished inside the wall-clock budget."""
    if not items or budget <= 0:
        return []
    ex = ThreadPoolExecutor(max_workers=workers)
    futs = [ex.submit(fn, item) for item in items]
    done, _pending = wait(futs, timeout=budget)
    out = []
    for f in done:
        try:
            r = f.result()
        except Exception:
            continue
        if r:
            out.append(r)
    ex.shutdown(wait=False, cancel_futures=True)
    return out


def _collect_rows(species, basis, candidates, per_year,
                  want_rows=MIN_ROWS_PER_PERIOD, max_years=6, budget=16):
    """Pull coordinate rows for candidates (ordered by preference),
    two years per batch, until a side has enough rows.

    Returns (frame, years_used). Early years of a sparse species often
    have no georeferenced records at all, so "first try" would quietly
    produce an empty period.
    """
    frames, used, spent = [], [], 0.0
    i = 0
    while i < len(candidates) and len(used) < max_years and spent < budget:
        batch = candidates[i:i + 2]
        i += 2
        t0 = time.time()
        res = _pool(lambda it: _rows_probe(*it),
                    [(species, y, basis, per_year) for y in batch],
                    2, budget - spent)
        spent += time.time() - t0
        for year, frame in res:
            used.append(year)
            if frame is not None and len(frame):
                frames.append(frame)
        if sum(len(f) for f in frames) >= want_rows:
            break
    if not frames:
        return None, used
    return pd.concat(frames, ignore_index=True), used


def year_probes(species, year_from, year_to, basis, hist=None,
                max_years=12, per_year=60, row_years=3,
                workers=6, counts_budget=12, side_budget=18):
    """Probe years and build the two period samples.

    Returns (probes, histogram, periods) where `probes` feeds the
    reporting trend and `periods` is either None or a dict with
    `early`, `late` frames and a `disc` disclosure.
    """
    hist = hist if hist is not None else year_histogram(
        species, year_from, year_to, basis)
    yrs = [y for y, n in hist.items() if n > 0]
    if not yrs:
        return [], hist, None

    k = max(2, min(row_years, len(yrs) // 2))
    early_cand, late_cand = yrs[:k], list(reversed(yrs[-k:]))
    mid_pool = yrs[k:len(yrs) - k]
    n_mid = max(0, min(len(mid_pool), max_years - 2 * k))
    mid = []
    if mid_pool and n_mid:
        pick = np.unique(np.linspace(0, len(mid_pool) - 1,
                                     n_mid).astype(int))
        mid = [mid_pool[i] for i in pick]
    years = sorted(set(early_cand + mid + late_cand))

    # coordinate samples for both ends run alongside the counts phase
    # (each side walks outward from the true extremes until it holds
    # enough rows — early years of a sparse species often carry no
    # georeferenced records at all)
    with ThreadPoolExecutor(max_workers=3) as stage:
        f_counts = stage.submit(
            lambda: _pool(lambda it: _counts_probe(*it),
                          [(species, y, basis) for y in years],
                          workers, counts_budget))
        f_early = stage.submit(_collect_rows, species, basis, list(yrs),
                              per_year, MIN_ROWS_PER_PERIOD, 10,
                              side_budget)
        f_late = stage.submit(_collect_rows, species, basis,
                              list(reversed(yrs)), per_year,
                              MIN_ROWS_PER_PERIOD, 5, side_budget)
        probes = f_counts.result() or []
        early_df, early_used = f_early.result()
        late_df, late_used = f_late.result()

    probes.sort(key=lambda p: p["year"])

    periods = None
    if early_df is not None and late_df is not None:
        if early_df["year"].max() < late_df["year"].min():
            periods = {
                "early": early_df,
                "late": late_df,
                "disc": {
                    "early_years": sorted(int(y) for y in
                                          early_df["year"].unique()),
                    "late_years": sorted(int(y) for y in
                                         late_df["year"].unique()),
                    "note": ("Targeted period sample: GBIF serves recent "
                             "records first, so the earliest and latest "
                             "years were probed separately until each "
                             "period held enough georeferenced records."),
                },
            }
    return probes, hist, periods


def effort_trend(probes) -> dict | None:
    """Reporting-rate index across the probed years (population totals)."""
    rows = []
    for p in probes:
        effort = p.get("recorders") or p.get("datasets") or 1
        rows.append({"year": p["year"], "records": p["records"],
                     "datasets": p.get("datasets", 1),
                     "recorders": p.get("recorders", 0),
                     "effort": int(effort)})
    if len(rows) < 5:
        return None
    rate = [r["records"] / max(1, r["effort"]) for r in rows]
    base = float(np.median(rate)) or 1.0
    for r, v in zip(rows, rate):
        r["index"] = round(v / base * 100, 1)
    return {
        "series": rows,
        "method": (
            "Population totals per probed year (GBIF query counts, not "
            "the displayed sample). Index = records per distinct "
            "recorder (reporting datasets where no recorder name is "
            "given), median = 100 — the effort control means a year "
            "where more people or datasets report is not counted as a "
            "rise."
        ),
        "caveat": (
            "Reporting rate, not abundance or occupancy — use it to "
            "judge whether a count change is coverage."
        ),
        "targeted": {"years_sampled": len(rows),
                     "span": f"{rows[0]['year']}–{rows[-1]['year']}"},
    }
