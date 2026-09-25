"""
Prediction: distribution metrics + KBA Criterion B screening
────────────────────────────────────────────────────────────
Implements the two standard extent metrics from species distribution
data, then screens them against the KBA Standard (IUCN 2016) Criterion B
— with explicit caveats that this is a *screening tool*, not an
assessment (formal KBA designation requires Red List evaluation and
stakeholder consultation).

Metrics:
  - EOO (Extent of Occurrence): minimum convex hull area (deg² → km²,
    cos-corrected), per IUCN Guidelines 4.0 — with the
    cosmopolitan-artefact caveat (Burgio 2021, Frontiers Ecol Evol;
    hulled EOO can overstate range for outlying/vagrant records).
  - AOO (Area of Occupancy): 2×2 km occupancy grid per IUCN Standard 4.0.

KBA Criterion B thresholds (IUCN 2016):
  B1: EOO ≤ 20,000 km²   (restricted-range species)
  B2: AOO ≤ 2,000 km²    (10 occupied 2×2 km cells)
"""

import numpy as np
import pandas as pd

KBA_B1_EOO_KM2 = 20_000
KBA_B2_AOO_KM2 = 2_000

CAVEAT = (
    "Screening indicator only. Formal KBA assessment (IUCN 2016) "
    "requires confirmed Red List status, stakeholder consultation, and "
    "the 'site contributes significantly to global persistence' test. "
    "BioSift flags candidates — it does not designate sites."
)

CITATIONS = {
    "iucn_kba": (
        "IUCN (2016). A Global Standard for the Identification of Key "
        "Biodiversity Areas, Version 1.0. Gland, Switzerland: IUCN."
    ),
    "iucn_guidelines": (
        "IUCN Red List Categories and Criteria, Version 14 (2024) — "
        "EOO/AOO calculation guidance (Guidelines 4.0)."
    ),
    "burgio": (
        "Burgio, K.R. et al. (2021). The danger of using EOO as a "
        "conservation metric. Frontiers of Biogeography, 13.3."
    ),
}


def _km_per_degree(lat):
    """Approximate km per degree latitude/longitude at a given latitude."""
    lat_rad = np.radians(lat)
    km_lat = 111.32
    km_lon = 111.32 * np.cos(lat_rad)
    return km_lat, km_lon


def convex_hull_points(lat, lon):
    """
    Compute the convex hull polygon (lon/lat rings) via Andrew's
    monotone chain in a local equirectangular frame, then unproject.
    Returns (hull_lonlat[list], area_km2, warnings[]).
    """
    warnings = []
    pts = np.column_stack([lat, lon])
    pts = pts[~np.isnan(pts).any(axis=1)]
    if len(pts) < 3:
        return 0.0, 0, ["fewer than 3 georeferenced records"]

    lat0 = float(np.mean(pts[:, 0]))
    km_lon = 111.32 * np.cos(np.radians(lat0))

    x = pts[:, 1] * km_lon
    y = pts[:, 0] * 111.32

    # Andrew's monotone chain convex hull
    P = sorted(zip(x, y))

    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

    def half(points):
        h = []
        for p in points:
            while len(h) >= 2 and cross(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h

    lower = half(P)
    upper = half(reversed(P))
    hull = lower[:-1] + upper[:-1]

    if len(hull) < 3:
        return [], 0.0, ["degenerate hull — fewer than 3 extreme points"]

    # shoelace area in km²
    area = 0.0
    n = len(hull)
    for i in range(n):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    area_km2 = abs(area) / 2.0

    if area_km2 > 20_000_000:
        warnings.append(
            "hull exceeds Earth's land area — likely cosmopolitan or "
            "erroneous outliers (Burgio 2021 caveat)"
        )

    # unproject hull vertices back to lon/lat
    hull_lonlat = [
        [float(px) / km_lon, float(py) / 111.32] for px, py in hull
    ]
    return hull_lonlat, area_km2, warnings


def hull_geojson(hull_lonlat):
    """Wrap hull ring as a GeoJSON Polygon Feature (or None)."""
    if not hull_lonlat or len(hull_lonlat) < 3:
        return None
    ring = hull_lonlat + [hull_lonlat[0]]  # close the ring
    return {
        "type": "Feature",
        "properties": {"name": "eoo_convex_hull"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring],
        },
    }


def aoo_km2(lat, lon, cell_km=2):
    """
    Area of occupancy on a km-grid (IUCN 2×2 km default).
    Uses the standard lat/lon-degree approximation per latitude band.
    """
    pts = np.column_stack([lat, lon])
    pts = pts[~np.isnan(pts).any(axis=1)]
    if len(pts) == 0:
        return 0, 0

    km_lat, _ = _km_per_degree(0)
    deg_per_cell_lat = cell_km / 111.32

    cells = set()
    for la, lo in pts:
        deg_per_cell_lon = cell_km / max(
            111.32 * np.cos(np.radians(la)), 1e-6
        )
        cells.add((int(la / deg_per_cell_lat), int(lo / deg_per_cell_lon)))

    n_cells = len(cells)
    return n_cells * (cell_km ** 2), n_cells


def screen_kba_b(eoo, aoo, iucn_category=""):
    """
    Screen EOO/AOO against KBA Criterion B.
    Returns dict with b1, b2 flags and contextual notes.
    Note: Criterion B formally applies to *threatened/restricted-range*
    species; without confirmed Red List status this is indicative only.
    Flags are coerced to plain bool (numpy.bool_ is not JSON-safe).
    """
    b1 = bool(eoo <= KBA_B1_EOO_KM2 and eoo > 0)
    b2 = bool(aoo <= KBA_B2_AOO_KM2 and aoo > 0)
    return {
        "b1_meets": b1,
        "b2_meets": b2,
        "b1_note": (
            f"EOO {float(eoo):,.0f} km² vs B1 threshold "
            f"{KBA_B1_EOO_KM2:,} km²"
        ),
        "b2_note": (
            f"AOO {float(aoo):,.0f} km² vs B2 threshold "
            f"{KBA_B2_AOO_KM2:,} km²"
        ),
        "iucn_category": iucn_category,
    }


def run_distribution_metrics(df, iucn_category=""):
    """
    Full pipeline: EOO + AOO + KBA-B screening on the analysed sample.
    Returns dict or None.
    """
    lat = pd.to_numeric(df.get("decimalLatitude"), errors="coerce")
    lon = pd.to_numeric(df.get("decimalLongitude"), errors="coerce")
    ok = lat.notna() & lon.notna()
    if ok.sum() < 3:
        return None

    hull_lonlat, eoo, hull_warnings = convex_hull_points(
        lat[ok].values, lon[ok].values
    )
    aoo, n_cells = aoo_km2(lat[ok].values, lon[ok].values)

    kba = screen_kba_b(eoo, aoo, iucn_category)

    return {
        "eoo_km2": eoo,
        "aoo_km2": aoo,
        "aoo_cells": n_cells,
        "hull_points": len(hull_lonlat),
        "hull_warnings": hull_warnings,
        "hull_geojson": hull_geojson(hull_lonlat),
        "kba": kba,
        "caveat": CAVEAT,
        "citations": CITATIONS,
    }
