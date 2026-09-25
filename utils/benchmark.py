"""
GBIF-wide benchmarking
──────────────────────
Answers the question every reviewer asks: "is this dataset bad, or is it
just this sample?" We compare defect rates in the analysed sample against
the *entire* GBIF population matching the same species + filters, using
the occurrence search API (count queries only — no downloads).

Baselines:
  total      -> count() with the same filters
  no_coords  -> count() + hasCoordinate=false
  no_year    -> facet "year": records missing a year never appear in a
                facet bucket, so (total − Σ buckets) ≈ records w/o year
"""

import requests
import streamlit as st

GBIF_API = "https://api.gbif.org/v1/occurrence/search"

DEFECT_KEYS = ["no_coords", "no_year"]

LABELS = {
    "no_coords": "Records without coordinates",
    "no_year":   "Records without an event year",
}


@st.cache_data(ttl=3600)
def fetch_population_stats(species_name, year_range=None, basis=None):
    """
    Query GBIF over the FULL matching population.
    Returns {"total": int, "no_coords": {"value","pct"}, ...} or {} on failure.
    """
    base = {"scientificName": species_name, "limit": 0}
    if year_range:
        base["year"] = year_range
    if basis and basis != "All":
        base["basisOfRecord"] = basis

    def count(extra=None):
        params = dict(base)
        if extra:
            params.update(extra)
        try:
            r = requests.get(GBIF_API, params=params, timeout=15)
            return int(r.json().get("count", 0))
        except Exception:
            return None

    total = count()
    if not total:
        return {}

    no_coords = count({"hasCoordinate": "false"})
    if no_coords is None:
        no_coords = 0

    out = {
        "total": total,
        "no_coords": {
            "value": no_coords,
            "pct": round(no_coords / total * 100, 1),
        },
    }

    # Missing-year estimate via facet (buckets only contain years that exist)
    try:
        params = dict(base)
        params.update({"facet": "year", "facetLimit": 1000})
        r      = requests.get(GBIF_API, params=params, timeout=20)
        facets = r.json().get("facets", [])
        buckets = facets[0].get("counts", []) if facets else []
        summed  = sum(int(b.get("count", 0)) for b in buckets)
        no_year = max(total - summed, 0)
        out["no_year"] = {
            "value": no_year,
            "pct": round(no_year / total * 100, 1),
        }
    except Exception:
        pass

    return out


def build_benchmark(sample_stats, population_stats):
    """
    sample_stats:      {key: percent for the analysed df}
    population_stats:  result of fetch_population_stats()
    Returns list of dicts: label, sample_pct, population_pct, delta, verdict
    """
    rows = []
    for key in DEFECT_KEYS:
        s_pct = sample_stats.get(key)
        pop   = population_stats.get(key)
        if pop is None or s_pct is None:
            continue
        p_pct  = pop["pct"]
        delta  = round(s_pct - p_pct, 1)
        if abs(delta) < 1.0:
            verdict = "similar"
        else:
            verdict = "better" if delta < 0 else "worse"
        rows.append({
            "key"            : key,
            "label"          : LABELS[key],
            "sample_pct"     : s_pct,
            "population_pct" : p_pct,
            "delta"          : delta,
            "verdict"        : verdict,
        })
    return rows
