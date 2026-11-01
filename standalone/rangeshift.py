"""Range-shift analysis — did the recorded distribution move?

The standard observed range-shift design compares where records sit in
two periods of the sampling history (cf. GBIF's climate-change use
cases; range-shift syntheses such as Rubenstein et al. 2023, Environ
Evid). Two entry points:

  range_shift(df)      auto-splits a frame that already spans time —
                       earliest vs latest 40% of records by year. This
                       is what an uploaded dataset gets.
  compare_periods(a,b)  compares two frames that were sampled from
                       known periods (the GBIF path, where a newest-
                       first page carries no history and the periods
                       are fetched explicitly).

Reported per period: record counts, year span, centroid, 5-95th
percentile latitudinal/longitudinal extent, occupied 1-degree cells.
Between periods: centroid shift (great-circle), signed north/south
component, extent change and grid turnover.

The caveat ships with the numbers: a shift in *recorded* extent also
contains changes in sampling effort and observer geography — it is an
observed distribution shift, not a demographic one.
"""
import numpy as np
import pandas as pd

MIN_PER_PERIOD = 10
MIN_YEAR_GAP = 3
EARTH_KM = 6371.0
MAX_POINTS_PER_PERIOD = 300

NOTES = {
    "method": (
        "Centroids are means, extent is the 5th-95th percentile span "
        "of coordinates, turnover is computed on occupied 1-degree "
        "grid cells."
    ),
    "caveat": (
        "Observed records, not individuals: a shift also reflects "
        "changes in sampling effort, observer geography and platform "
        "coverage (e.g. the post-2010 citizen-science surge). Treat "
        "the direction as a signal to check, not a demographic trend."
    ),
}


def _haversine_km(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2)
    dphi = p2 - p1
    dlam = np.radians(lo2 - lo1)
    a = (np.sin(dphi / 2) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2) ** 2)
    return float(2 * EARTH_KM * np.arcsin(np.sqrt(a)))


def _period(sub: pd.DataFrame) -> dict:
    lat = sub["decimalLatitude"].to_numpy(dtype=float)
    lon = sub["decimalLongitude"].to_numpy(dtype=float)
    yr = sub["year"].to_numpy(dtype=float)
    cells = set(zip(np.floor(lat).astype(int), np.floor(lon).astype(int)))
    block = {
        "records": int(len(sub)),
        "year_min": int(yr.min()),
        "year_max": int(yr.max()),
        "year_median": int(np.median(yr)),
        "centroid_lat": round(float(lat.mean()), 3),
        "centroid_lon": round(float(lon.mean()), 3),
        "lat_extent": round(float(np.percentile(lat, 95)
                                  - np.percentile(lat, 5)), 3),
        "lon_extent": round(float(np.percentile(lon, 95)
                                  - np.percentile(lon, 5)), 3),
    }
    return block, cells


def _sample_points(sub: pd.DataFrame,
                   limit: int = MAX_POINTS_PER_PERIOD) -> list:
    """Coordinates the period statistics were computed from.

    Returned so the map overlay can show exactly the records behind the
    numbers — never a differently-sampled set that may contain no
    records in either period at all.
    """
    if len(sub) > limit:
        idx = np.linspace(0, len(sub) - 1, limit).astype(int)
        sub = sub.iloc[idx]
    return [[round(float(lo), 4), round(float(la), 4)]
            for la, lo in zip(sub["decimalLatitude"],
                              sub["decimalLongitude"])]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    needed = {"year", "decimalLatitude", "decimalLongitude"}
    if not needed <= set(df.columns):
        return pd.DataFrame(columns=list(needed))
    sub = df.copy()
    sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
    lat = pd.to_numeric(sub["decimalLatitude"], errors="coerce")
    lon = pd.to_numeric(sub["decimalLongitude"], errors="coerce")
    ok = (sub["year"].notna() & lat.notna() & lon.notna()
          & (sub["year"] >= 1700) & (sub["year"] <= 2100)
          & (lat.abs() <= 90) & (lon.abs() <= 180))
    out = sub[ok].assign(decimalLatitude=lat[ok],
                         decimalLongitude=lon[ok])
    return out.sort_values("year")


def compare_periods(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """Compare two frames known to come from different periods."""
    a = _clean(a)
    b = _clean(b)
    if len(a) < MIN_PER_PERIOD or len(b) < MIN_PER_PERIOD:
        return {"available": False,
                "reason": f"needs at least {MIN_PER_PERIOD} records "
                          f"per period (early {len(a)}, late {len(b)})"}

    pa, cells_a = _period(a)
    pb, cells_b = _period(b)
    gap = pb["year_median"] - pa["year_median"]
    if gap < MIN_YEAR_GAP:
        return {"available": False,
                "reason": "the two periods are too close in time "
                          f"(median years differ by {gap})"}

    lat_shift_km = (pb["centroid_lat"] - pa["centroid_lat"]) * 110.574
    lon_shift_km = ((pb["centroid_lon"] - pa["centroid_lon"]) * 111.32
                    * np.cos(np.radians((pb["centroid_lat"]
                                         + pa["centroid_lat"]) / 2)))
    centroid_km = _haversine_km(pa["centroid_lat"], pa["centroid_lon"],
                                pb["centroid_lat"], pb["centroid_lon"])
    shared = cells_a & cells_b
    union = cells_a | cells_b

    return {
        "available": True,
        "period_a": pa,
        "period_b": pb,
        "points": {
            "a": _sample_points(a),
            "b": _sample_points(b),
        },
        "shift": {
            "centroid_km": round(centroid_km, 1),
            "north_km": round(float(lat_shift_km), 1),
            "east_km": round(float(lon_shift_km), 1),
            "lat_extent_delta": round(pb["lat_extent"]
                                      - pa["lat_extent"], 3),
            "direction": ("poleward/north" if lat_shift_km > 0
                          else "equatorward/south"),
        },
        "turnover": {
            "cells_a": len(cells_a),
            "cells_b": len(cells_b),
            "shared": len(shared),
            "only_a": len(cells_a - cells_b),
            "only_b": len(cells_b - cells_a),
            "jaccard": round(len(shared) / len(union), 3) if union else 0.0,
        },
        "method": NOTES["method"],
        "caveat": NOTES["caveat"],
    }


def range_shift(df: pd.DataFrame) -> dict:
    """Auto-split a time-spanning frame (early vs late 40% of records)."""
    if not {"year", "decimalLatitude",
            "decimalLongitude"} <= set(df.columns):
        return {"available": False,
                "reason": "year and coordinates are required"}

    sub = _clean(df)
    if len(sub) < 2 * MIN_PER_PERIOD:
        return {"available": False,
                "reason": f"needs at least {2 * MIN_PER_PERIOD} dated, "
                          f"georeferenced records (found {len(sub)})"}

    cut = int(len(sub) * 0.4)
    a = sub.iloc[:max(cut, MIN_PER_PERIOD)]
    b = sub.iloc[-max(cut, MIN_PER_PERIOD):]

    out = compare_periods(a, b)
    if out.get("available"):
        out["method"] = (
            "Earliest 40% vs latest 40% of records by year. "
            + NOTES["method"]
        )
    return out
