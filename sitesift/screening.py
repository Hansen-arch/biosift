"""SiteSift screening core, what lives inside a site polygon.

Site-level screening (TNFD LEAP "Locate/Evaluate", ESRS E4 site disclosure,
EIA scoping) normally means licensing IBAT, whose report downloads and API
sit behind paid tiers. This module does the part that only needs open data,
and says plainly what it cannot do.

Everything below was measured against the live API, not assumed:

  * ``geometry=POLYGON((...))`` works keyless and is fast (~2 s)
  * one request can carry nine facets at once (~0.8 s), all the
    composition numbers, country attribution included, come from a single
    call
  * ``iucnRedListCategory=CR`` filters records, so named species of
    concern are reachable without per-taxon lookups
  * ``iucnRedListCategory=CR,EN,VU`` returns **0**, unlike ``year`` it
    takes no comma list, so threatened categories are one call each
  * ``geoDistance=lat,lon,km`` is unusable: a 10 km radius returned 64
    records where the equivalent bounding box returned 2.9 million, and
    counts did not scale with area. Point+radius is built here as a real
    polygon instead.
  * ``facetLimit`` defaults to 10. Without setting it, species lists
    truncate silently at ten names.

Deliberately excluded: WDPA/WDPCA and KBA boundaries. Both are licensed -
Protected Planet's API returns 401 without a token and the KBA download is
a request form, so claiming a designation overlap from open data would be
a fabrication. The bundle states this instead of guessing.
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor

import requests

GBIF = "https://api.gbif.org/v1/occurrence/search"
GBIF_DATASET = "https://api.gbif.org/v1/dataset"

THREATENED = ("CR", "EN", "VU")
IUCN_ORDER = ("EX", "EW", "CR", "EN", "VU", "NT", "LC", "DD")
IUCN_FULL = {
    "EX": "Extinct",
    "EW": "Extinct in the Wild",
    "CR": "Critically Endangered",
    "EN": "Endangered",
    "VU": "Vulnerable",
    "NT": "Near Threatened",
    "LC": "Least Concern",
    "DD": "Data Deficient",
}

# An individual record can carry several of these at once, so percentages
# are "% of records flagged with this issue", never a sum to 100.
ISSUE_LABELS = {
    "ZERO_COORDINATE": ("Zero coordinates", "serious"),
    "COORDINATE_INVALID": ("Invalid coordinates", "serious"),
    "PRESUMED_SWAPPED_COORDINATE": ("Presumed swapped lat/lon", "serious"),
    "COUNTRY_COORDINATE_MISMATCH": ("Country does not match coordinates",
                                    "serious"),
    "RECORDED_DATE_MISMATCH": ("Recorded date mismatch", "warning"),
    "TAXON_MATCH_HIGHERRANK": ("Identified only to higher rank", "warning"),
    "TAXON_ID_NOT_FOUND": ("Taxon ID missing from backbone", "warning"),
    "TAXON_CONCEPT_ID_NOT_FOUND": ("Taxon concept ID not resolvable",
                                     "benign"),
    "INSTITUTION_MATCH_NONE": ("Institution match failed", "benign"),
    "INSTITUTION_MATCH_FUZZY": ("Institution matched only approximately",
                                "benign"),
    "COORDINATE_ROUNDED": ("Coordinates rounded", "benign"),
    "GEODETIC_DATUM_ASSUMED_WGS84": ("Datum assumed WGS84", "benign"),
    "CONTINENT_DERIVED_FROM_COORDINATES": ("Continent derived from "
                                           "coordinates", "benign"),
    "COUNTRY_DERIVED_FROM_COORDINATES": ("Country derived from coordinates",
                                         "benign"),
}

R_KM = 6371.0088
MAX_AREA_KM2 = 5_000_000.0
FACET_LIMIT = 300
POINT_SAMPLE = 300

# GBIF flags ~43 issues; most are technical bookkeeping ("collection match
# fuzzy") that mean nothing for a site screen. Only these change whether a
# record is trustworthy evidence about a place or a taxon. Everything else
# is counted and reported as "other technical flags".
MATERIAL_ISSUES = {
    "ZERO_COORDINATE", "COORDINATE_INVALID",
    "PRESUMED_SWAPPED_COORDINATE", "COUNTRY_COORDINATE_MISMATCH",
    "CONTINENT_COORDINATE_MISMATCH", "COUNTRY_INVALID",
    "CONTINENT_INVALID", "COORDINATE_PRECISION_INVALID",
    "COORDINATE_UNCERTAINTY_METERS_INVALID", "RECORDED_DATE_INVALID",
    "RECORDED_DATE_UNLIKELY", "RECORDED_DATE_MISMATCH",
    "TAXON_MATCH_HIGHERRANK", "TAXON_MATCH_NONE",
    "TAXON_ID_NOT_FOUND", "SCIENTIFIC_NAME_AND_ID_INCONSISTENT",
    "BASIS_OF_RECORD_INVALID", "INDIVIDUAL_COUNT_INVALID",
    "FOOTPRINT_WKT_INVALID", "GEODETIC_DATUM_INVALID",
}

_session = requests.Session()
_session.headers.update({
    "User-Agent": "SiteSift/1.0 (open biodiversity screening; GBIF API)",
})

# Repeat screens of the same site are common while a user tries different
# filters. Keyed on the exact query so nothing stale is ever served.
_CACHE: dict = {}
_CACHE_TTL = 3600.0


# ────────────────────────────────────────────── geometry


def _ring_area_km2(ring) -> float:
    """Spherical area of one ring, the same formulation turf.js uses."""
    if len(ring) < 4:
        return 0.0
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total * R_KM * R_KM / 2.0)


def _signed_area(ring) -> float:
    """Planar shoelace area; positive means counter-clockwise."""
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _orient(ring, ccw: bool = True):
    """Force ring winding. GBIF rejects clockwise exterior rings outright
    (HTTP 400 "Polygon with clockwise exterior ring"), and a drawn or
    uploaded polygon can have either winding, so it is normalised here.
    """
    a = _signed_area(ring)
    if (ccw and a < 0) or ((not ccw) and a > 0):
        return list(reversed(ring))
    return ring


def _circle_ring(lat: float, lon: float, radius_km: float,
                 steps: int = 64):
    """Ring approximating a radius on the sphere (geoDistance is broken)."""
    d = radius_km / R_KM
    lat1, lon1 = math.radians(lat), math.radians(lon)
    ring = []
    for i in range(steps + 1):
        brg = 2 * math.pi * i / steps
        lat2 = math.asin(math.sin(lat1) * math.cos(d)
                         + math.cos(lat1) * math.sin(d) * math.cos(brg))
        lon2 = lon1 + math.atan2(
            math.sin(brg) * math.sin(d) * math.cos(lat1),
            math.cos(d) - math.sin(lat1) * math.sin(lat2))
        ring.append([math.degrees(lon2), math.degrees(lat2)])
    return ring


def _valid_ring(ring) -> bool:
    if not isinstance(ring, (list, tuple)) or len(ring) < 4:
        return False
    for pt in ring:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            return False
        lon, lat = float(pt[0]), float(pt[1])
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            return False
    return True


def prepare_site(geometry: dict) -> dict:
    """Normalise a site geometry into WKT plus its derived measures.

    Accepts a GeoJSON Polygon/MultiPolygon, or a point with `radius_km`.
    Raises ValueError with a user-facing message on bad input.
    """
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be an object")

    gtype = geometry.get("type")
    rings = []          # outer rings only; holes are subtracted from area
    if gtype == "Point":
        coords = geometry.get("coordinates") or []
        radius = geometry.get("radius_km")
        if len(coords) < 2:
            raise ValueError("point needs longitude and latitude")
        if not radius or float(radius) <= 0:
            raise ValueError("radius_km must be greater than zero")
        if float(radius) > 500:
            raise ValueError("radius_km above 500 makes the screen too "
                             "coarse to mean anything")
        ring = _circle_ring(float(coords[1]), float(coords[0]),
                            float(radius))
        rings = [ring]
    elif gtype in ("Polygon", "MultiPolygon"):
        polys = ([geometry.get("coordinates") or []]
                 if gtype == "Polygon"
                 else (geometry.get("coordinates") or []))
        for poly in polys:
            if not poly or not _valid_ring(poly[0]):
                raise ValueError("polygon needs at least three valid "
                                 "longitude/latitude vertices")
            outer = [[float(p[0]), float(p[1])] for p in poly[0]]
            if outer[0] != outer[-1]:
                outer.append(outer[0])
            outer = _orient(outer, ccw=True)
            holes = []
            for hole in poly[1:]:
                if _valid_ring(hole):
                    h = [[float(p[0]), float(p[1])] for p in hole]
                    if h[0] != h[-1]:
                        h.append(h[0])
                    holes.append(_orient(h, ccw=False))
            rings.append({"outer": outer, "holes": holes})
    else:
        raise ValueError("geometry must be a Polygon, MultiPolygon or Point")

    if rings and isinstance(rings[0], list):
        polys = [{"outer": _orient(rings[0], ccw=True), "holes": []}]
    else:
        polys = rings

    area = 0.0
    lons, lats = [], []
    for poly in polys:
        area += _ring_area_km2(poly["outer"])
        for hole in poly["holes"]:
            area -= _ring_area_km2(hole)
        lons += [p[0] for p in poly["outer"]]
        lats += [p[1] for p in poly["outer"]]

    if area <= 0:
        raise ValueError("polygon encloses no area, check the vertex order")
    if area > MAX_AREA_KM2:
        raise ValueError(
            f"site is {area:,.0f} km², above the "
            f"{MAX_AREA_KM2:,.0f} km² limit for a meaningful site screen")

    # WKT with holes kept, so the query matches what was drawn
    parts = []
    for poly in polys:
        part = "(" + _ring_wkt(poly["outer"])
        for hole in poly["holes"]:
            part += "," + _ring_wkt(hole)
        parts.append(part + ")")
    wkt = ("POLYGON" if len(parts) == 1 else "MULTIPOLYGON") + \
          (parts[0] if len(parts) == 1 else "(" + ",".join(parts) + ")")

    return {
        "wkt": wkt,
        "area_km2": round(area, 2),
        "bbox": [round(min(lons), 5), round(min(lats), 5),
                 round(max(lons), 5), round(max(lats), 5)],
        "centroid": [round(sum(lons) / len(lons), 5),
                     round(sum(lats) / len(lats), 5)],
    }


def _ring_wkt(ring) -> str:
    return "(" + ",".join(f"{p[0]:.6f} {p[1]:.6f}" for p in ring) + ")"


# ────────────────────────────────────────────── GBIF plumbing


def _get(url, params, timeout=25, attempts=3):
    last = None
    for i in range(attempts):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                raise requests.RequestException(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except Exception as e:                      # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(0.6 * (i + 1))
    raise RuntimeError(f"GBIF request failed: {last}")


def _base(site_wkt, year_from=None, year_to=None, basis=None,
          country=None):
    """Params shared by every query in a screen.

    `occurrenceStatus=PRESENT` is not a default in the API: absence
    records are returned as occurrences. Measured effect of filtering:
    Acer pseudoplatanus 1,339,414 → 1,276,719 (4.7% were absences).
    """
    p = [
        ("geometry", site_wkt),
        ("hasCoordinate", "true"),
        ("occurrenceStatus", "PRESENT"),
    ]
    if year_from and year_to:
        p.append(("year", f"{int(year_from)},{int(year_to)}"))
    if basis and basis != "All":
        p.append(("basisOfRecord", basis))
    # country= takes an ISO 3166-1 alpha-2 code. It filters on GBIF's
    # *interpreted* country, which is filled from the coordinates when the
    # publisher left it blank, so a border site can lose records that sit
    # in the polygon but are attributed to the neighbour.
    if country:
        p.append(("country", country))
    return p


def _facets(js) -> dict:
    return {f["field"]: f["counts"] for f in js.get("facets") or []}


def _strip_authorship(name: str) -> str:
    """'Columba palumbus Linnaeus, 1758' -> 'Columba palumbus'."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    if "(" in name:
        name = name.split("(")[0].strip()
    toks = name.split()
    if toks and toks[0] in ("×", "x") and len(toks) > 1:
        toks = toks[1:]
    if len(toks) <= 2:
        return " ".join(toks)
    keep = 2
    if toks[2].lower().rstrip(".") in ("subsp", "var", "f", "fo", "forma",
                                       "nothosubsp", "convar"):
        keep = 4
    return " ".join(toks[:keep]).rstrip(",;")


def _threatened_species(site_wkt, year_from, year_to, basis, country=None):
    """Named species of concern. One call per category: this filter takes
    no comma list (`CR,EN,VU` returns 0)."""
    out = {}
    for cat in THREATENED:
        params = _base(site_wkt, year_from, year_to, basis, country) + [
            ("iucnRedListCategory", cat),
            ("limit", "0"),
            ("facet", "scientificName"),
            ("facetLimit", "100"),
        ]
        try:
            js = _get(GBIF, params)
        except Exception:                       # noqa: BLE001
            out[cat] = {"records": None, "species": [], "error": True}
            continue
        counts = (_facets(js).get("SCIENTIFIC_NAME") or [])
        out[cat] = {
            "records": js.get("count", 0),
            "species": [{"name": _strip_authorship(c["name"]),
                         "records": c["count"]} for c in counts],
            "truncated": len(counts) >= 100,
        }
    return out


def _dataset_titles(keys):
    def one(key):
        try:
            js = _get(f"{GBIF_DATASET}/{key}", None, timeout=15, attempts=2)
            return key, (js.get("title") or "").strip(), \
                js.get("publishingOrganizationKey")
        except Exception:                       # noqa: BLE001
            return key, "", None

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(keys)))) as ex:
        return {k: t for k, t, _ in ex.map(one, keys)}


def _point_sample(site_wkt, year_from, year_to, basis, country=None):
    params = _base(site_wkt, year_from, year_to, basis, country) + [
        ("limit", str(POINT_SAMPLE)),
    ]
    js = _get(GBIF, params, timeout=40)
    pts = []
    for r in js.get("results") or []:
        lat, lon = r.get("decimalLatitude"), r.get("decimalLongitude")
        if lat is None or lon is None:
            continue
        pts.append({
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "species": _strip_authorship(r.get("scientificName")
                                         or r.get("species") or ""),
            "year": r.get("year"),
            "iucn": r.get("iucnRedListCategory") or "",
            "dataset": r.get("datasetKey") or "",
            "basis": r.get("basisOfRecord") or "",
        })
    return pts


# ────────────────────────────────────────────── the screen


def screen(geometry: dict, label: str = "", year_from=None, year_to=None,
           basis: str = "All", country: str = None,
           include_points: bool = True) -> dict:
    """Screen a site polygon against GBIF occurrence records.

    `country` is an ISO 3166-1 alpha-2 code limiting the screen to one
    country's records. It is applied as a filter, never as an inference:
    the country breakdown is always reported so the effect of the filter
    is visible rather than hidden.
    """
    site = prepare_site(geometry)
    country = (country or "").strip().upper() or None
    key = (site["wkt"], year_from, year_to, basis, country, include_points)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        bundle = dict(hit[1])
        bundle["cached"] = True
        bundle["site"] = dict(bundle["site"], label=label or "Untitled site")
        return bundle

    t0 = time.time()
    wkt = site["wkt"]

    # One call carries every composition facet (measured ~1.7 s).
    params = _base(wkt, year_from, year_to, basis, country) + [
        ("limit", "0"),
        ("facetLimit", str(FACET_LIMIT)),
    ] + [("facet", f) for f in ("scientificName", "iucnRedListCategory",
                                "establishmentMeans", "basisOfRecord",
                                "datasetKey", "year", "month", "issue",
                                "country")]
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_main = ex.submit(_get, GBIF, params)
        f_threat = ex.submit(_threatened_species, wkt, year_from, year_to,
                             basis, country)
        f_points = (ex.submit(_point_sample, wkt, year_from, year_to, basis,
                              country)
                    if include_points else None)
        main = f_main.result()
        threatened = f_threat.result()
        points, points_error = [], None
        if f_points is not None:
            try:
                points = f_points.result()
            except Exception as e:              # noqa: BLE001
                points_error = str(e)

    total = int(main.get("count") or 0)
    facets = _facets(main)

    sci = facets.get("SCIENTIFIC_NAME") or []
    species = [{"name": _strip_authorship(c["name"]),
                "records": c["count"]} for c in sci]
    species = [s for s in species if s["name"]]
    species_truncated = len(sci) >= FACET_LIMIT

    iucn_counts = {c["name"]: c["count"]
                   for c in facets.get("IUCN_RED_LIST_CATEGORY") or []}
    iucn = [{"code": code, "label": IUCN_FULL[code],
             "records": iucn_counts.get(code, 0)}
            for code in IUCN_ORDER if code in iucn_counts]
    threatened_records = sum(iucn_counts.get(c, 0) for c in THREATENED)

    est = {c["name"]: c["count"]
           for c in facets.get("ESTABLISHMENT_MEANS") or []}
    est_total = sum(est.values())
    introduced_keys = ("introduced", "introducedAssistedColonisation",
                       "vagrant", "naturalised")
    # establishmentMeans is sparsely populated (oak carried it on ~3% of
    # records), so it is reported as coverage, never used as a filter or
    # it would silently discard almost all the evidence.
    establishment = {
        "recorded": est_total,
        "coverage_pct": round(est_total / total * 100, 1) if total else 0.0,
        "native": est.get("native", 0),
        "introduced": sum(v for k, v in est.items()
                          if k in introduced_keys),
        "uncertain": est.get("uncertain", 0),
        "other": {k: v for k, v in est.items()
                  if k not in ("native", "introduced", "uncertain")},
    }

    basis_mix = [{"basis": c["name"], "records": c["count"]}
                 for c in facets.get("BASIS_OF_RECORD") or []]

    years = {}
    for c in facets.get("YEAR") or []:
        try:
            years[int(c["name"])] = c["count"]
        except (TypeError, ValueError):
            continue
    decades = {}
    for y, n in years.items():
        decades[(y // 10) * 10] = decades.get((y // 10) * 10, 0) + n
    temporal = {
        "first_year": min(years) if years else None,
        "last_year": max(years) if years else None,
        "years_with_records": len(years),
        "decades": [{"decade": d, "records": decades[d]}
                    for d in sorted(decades)],
        "recent_pct": round(
            sum(n for y, n in years.items() if y >= 2000) / total * 100, 1)
        if total else 0.0,
        "pre_1950_pct": round(
            sum(n for y, n in years.items() if y < 1950) / total * 100, 1)
        if total else 0.0,
    }

    months = {}
    for c in facets.get("MONTH") or []:
        try:
            months[int(c["name"])] = c["count"]
        except (TypeError, ValueError):
            continue

    issues = []
    for c in facets.get("ISSUE") or []:
        name = c["name"]
        lbl, sev = ISSUE_LABELS.get(name, (name.replace("_", " ").title(),
                                           "warning"))
        issues.append({
            "code": name, "label": lbl, "severity": sev,
            "material": sev == "serious" or name in MATERIAL_ISSUES,
            "records": c["count"],
            "pct": round(c["count"] / total * 100, 1) if total else 0.0,
        })
    issues.sort(key=lambda i: (-i["material"], -i["records"]))
    other_flags = sum(1 for i in issues if not i["material"])

    # Which countries the records are attributed to. A site is usually
    # reported against one country, but border sites, marine records and
    # records held by foreign institutions do not stay in one bucket, and
    # that is worth showing before anyone filters to a country.
    country_facet = facets.get("COUNTRY") or []
    countries = sorted(
        ({"code": c["name"], "records": c["count"]} for c in country_facet),
        key=lambda c: -c["records"],
    )

    ds_facet = facets.get("DATASET_KEY") or []
    top_ds = ds_facet[:6]
    titles = _dataset_titles([c["name"] for c in top_ds]) if top_ds else {}
    datasets = []
    for c in top_ds:
        key_ = c["name"]
        title = titles.get(key_) or ""
        datasets.append({
            "key": key_,
            "title": title or key_,
            "records": c["count"],
            "pct": round(c["count"] / total * 100, 1) if total else 0.0,
            "url": f"https://www.gbif.org/dataset/{key_}",
        })

    species_sorted = sorted(species, key=lambda s: -s["records"])

    caveats = [
        "Designated sites (WDPA/WDPCA) and Key Biodiversity Areas are "
        "not included: both are licensed datasets (Protected Planet's "
        "API requires a token, the KBA download is a request form). "
        "Overlap must be confirmed against those sources or IBAT.",
        "Only georeferenced records can be assigned to a polygon. Records "
        "at this site that carry no coordinates cannot be screened and are "
        "absent from every count here.",
        "Absence records are excluded (occurrenceStatus=PRESENT); GBIF "
        "returns them as occurrences by default.",
        f"Native/introduced status is recorded on only "
        f"{establishment['coverage_pct']}% of these records, so it is "
        f"reported as coverage, not applied as a filter.",
        "Survey effort is uneven across taxa and time. A species missing "
        "from this list may be unsurveyed rather than absent.",
    ]
    if country:
        caveats.insert(1, (
            f"Filtered to country {country}. This uses GBIF's interpreted "
            "country, which is derived from the coordinates when the "
            "publisher left it blank, so records inside the polygon that "
            "are attributed to another country are excluded."))
    elif len(countries) > 1:
        caveats.insert(1, (
            f"Records here are attributed to {len(countries)} countries "
            f"({', '.join(c['code'] for c in countries[:4])}"
            f"{'…' if len(countries) > 4 else ''}). Use the country filter "
            "if the screen should cover only one."))
    if site["area_km2"] > 50_000:
        caveats.insert(1, (
            f"At {site['area_km2']:,.0f} km² this site is large enough that "
            "a record anywhere inside it is treated as evidence for the "
            "whole site, too coarse for a project footprint."))
    bundle = {
        "site": {"label": label or "Untitled site",
                 "area_km2": site["area_km2"],
                 "bbox": site["bbox"],
                 "centroid": site["centroid"],
                 "wkt": wkt},
        "filters": {"year_from": year_from, "year_to": year_to,
                    "basis": basis, "country": country},
        "summary": {
            "records": total,
            "species_observed": len(species),
            "species_truncated": species_truncated,
            "datasets": len(ds_facet),
            "datasets_truncated": len(ds_facet) >= FACET_LIMIT,
            "threatened_records": threatened_records,
            "threatened_species": sum(
                len(v.get("species") or []) for v in threatened.values()),
            "records_per_km2": round(total / site["area_km2"], 2)
            if site["area_km2"] else 0.0,
        },
        "iucn": iucn,
        "threatened": {
            "categories": [
                {"code": cat, "label": IUCN_FULL[cat],
                 "records": (threatened.get(cat) or {}).get("records"),
                 "species": (threatened.get(cat) or {}).get("species") or [],
                 "truncated": bool((threatened.get(cat) or {})
                                   .get("truncated"))}
                for cat in THREATENED
            ],
            "note": (
                "Global IUCN Red List category as recorded by GBIF. A "
                "species being listed does not mean the site is important "
                "for it, that needs population evidence and a formal "
                "assessment."
            ),
        },
        "species": species_sorted[:30],
        "establishment": establishment,
        "basis_of_record": basis_mix,
        "temporal": temporal,
        "months": [{"month": m, "records": months.get(m, 0)}
                   for m in range(1, 13)],
        "issues": issues,
        "other_flag_count": other_flags,
        "countries": countries[:20],
        "countries_total": len(countries),
        "datasets": datasets,
        "points": points,
        "points_error": points_error,
        "points_sampled": len(points),
        "cached": False,
        "elapsed_s": round(time.time() - t0, 1),
        "caveats": caveats,
        "method": (
            "GBIF occurrence search restricted to the site polygon, "
            "georeferenced and PRESENT records"
            + (f", limited to country {country}" if country else "")
            + ", aggregated with facets (species, IUCN category, "
            "establishment means, basis of record, dataset, year, month, "
            "country, GBIF issues)."
        ),
    }
    _CACHE[key] = (time.time(), bundle)
    return bundle


def clear_cache():
    _CACHE.clear()
