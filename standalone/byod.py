"""
Bring-Your-Own-Data (BYOD) engine — analyse user-uploaded datasets
through the same science layer the GBIF app uses.

Design notes
────────────
* Readers: CSV / TSV / Excel / Darwin Core Archive (dwca.zip) — DwC-A
  extraction mirrors the IPT layout (occurrence.txt with optional
  meta.xml column mapping).
* Column mapping: case/punct-insensitive canonical names + smart
  aliases, then fuzzy fallback over all columns. The mapper is
  metadata-only — no data leaves scope; all computation is local.
* Checks add the CoordinateCleaner-inspired geographic and dating
  tests (Zizka et al. 2019, Methods Ecol Evol; 1500+ citations) the
  GBIF-pipeline checks do not cover: coord swaps, capital/centroid
  proximity, on-country-edge, future dates, implausible names.
* Everything is optional — a dataset with 3 usable columns still
  gets a full report; tests skip gracefully per record.
"""
import io
import os
import re
import zipfile

import numpy as np
import pandas as pd
import requests

# ────────────────────────────────────────────────────────────── readers

DWC_ALIASES = {
    "scientificname": "species",
    "acceptednameusage": "species",
    "taxonfullname": "species",
    "vernacularname": "vernacular",
    "decimallatitude": "decimalLatitude",
    "latitude": "decimalLatitude",
    "lat": "decimalLatitude",
    "verbatimlatitude": "decimalLatitude",
    "decimallongitude": "decimalLongitude",
    "longitude": "decimalLongitude",
    "lon": "decimalLongitude",
    "long": "decimalLongitude",
    "verbatimlongitude": "decimalLongitude",
    "year": "year",
    "eventyear": "year",
    "collectiondate": "year",
    "datecollected": "year",
    "eventdate": "eventDate",
    "dateobserved": "eventDate",
    "collectiondate_full": "eventDate",
    "basisofrecord": "basisOfRecord",
    "recordtype": "basisOfRecord",
    "country": "country",
    "countrycode": "countryCode",
    "stateprovince": "stateProvince",
    "locality": "locality",
    "coordinateuncertaintyinmeters": "coordinateUncertaintyInMeters",
    "coorduncertainm": "coordinateUncertaintyInMeters",
    "datasetname": "datasetName",
    "institutioncode": "institutionCode",
    "occurrenceid": "occurrenceID",
    "catalognumber": "catalogNumber",
    "recordedby": "recordedBy",
    "family": "family",
    "genus": "genus",
    "kingdom": "kingdom",
    "individualcount": "individualCount",
    "month": "month",
    "day": "day",
    "depth": "depth",
    "elevation": "elevation",
}

CANONICAL = ["species", "decimalLatitude", "decimalLongitude", "year",
             "eventDate", "basisOfRecord", "country", "countryCode",
             "stateProvince", "locality", "coordinateUncertaintyInMeters",
             "datasetName", "institutionCode", "occurrenceID",
             "catalogNumber", "recordedBy", "family", "genus", "kingdom",
             "individualCount", "month", "day", "depth", "elevation"]


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def read_any(name: str, data: bytes) -> pd.DataFrame:
    """Read CSV/TSV/Excel/DwC-A zip into a raw dataframe."""
    low = (name or "").lower()
    if low.endswith((".zip", ".dwca")):
        return _read_dwca(data)
    if low.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    if low.endswith(".tsv"):
        return pd.read_csv(io.BytesIO(data), sep="\t")
    return pd.read_csv(io.BytesIO(data), sep=None, engine="python")


def _read_dwca(data: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        core_name = next(
            (n for n in z.namelist()
             if n.endswith("occurrence.txt") or n.endswith("core.txt")),
            None)
        if core_name is None:
            core_name = next(
                (n for n in z.namelist()
                 if n.endswith(".txt") and not n.startswith("meta")), None)
        if core_name is None:
            raise ValueError(
                "No occurrence.txt / core.txt found in the archive")
        df = pd.read_csv(z.open(core_name), sep="\t", engine="python")
        # meta.xml rowType field mapping (IPT layout)
        if "meta.xml" in z.namelist():
            meta = z.read("meta.xml").decode("utf-8", "ignore")
            fields = re.findall(
                r'<field[^>]*index="(\d+)"[^>]*term="([^"]+)"', meta)
            for idx, term in fields:
                try:
                    i = int(idx)
                except ValueError:
                    continue
                if i < len(df.columns):
                    short = term.rsplit("/", 1)[-1]
                    if _norm(short) in DWC_ALIASES and \
                            _norm(df.columns[i]) == "":
                        df.columns.values[i] = short
        return df


def map_columns(df: pd.DataFrame, mapping: dict | None = None,
                fuzzy: bool = True) -> tuple[pd.DataFrame, dict]:
    """Return (normalised df, applied mapping).

    Explicit `mapping` (canonical -> source column) wins over
    auto-detection. Auto: exact/case-insensitive -> aliases -> fuzzy
    token overlap. Unmapped canonical columns simply stay absent;
    every check tolerates their absence.
    """
    applied = {}
    out = pd.DataFrame(index=df.index)
    norm_to_src = {_norm(c): c for c in df.columns}
    mapping = mapping or {}
    used = set()

    for canon in CANONICAL:
        src = mapping.get(canon)
        if src and src in df.columns and src not in used:
            out[canon] = df[src]
            applied[canon] = src
            used.add(src)
            continue
        if src:
            # source column renamed or dropped -> try hard to find it
            match = norm_to_src.get(_norm(src))
            if match and match not in used:
                out[canon] = df[match]
                applied[canon] = match
                used.add(match)
                continue
        # auto: exact canonical name present in raw columns
        direct = norm_to_src.get(_norm(canon))
        if direct is not None and direct in used:
            direct = None
        if direct is None and fuzzy:
            # alias match
            for n, target in DWC_ALIASES.items():
                if target == canon and n in norm_to_src \
                        and norm_to_src[n] not in used:
                    direct = norm_to_src[n]
                    break
            # substring pass over canonical + aliases (longest needle
            # wins): "Lat (deg)" -> lat, "Year Collected" -> year
            if direct is None:
                needles = [(_norm(canon), canon)] + [
                    (_norm(a), t) for a, t in DWC_ALIASES.items()
                    if t == canon]
                best, best_len = None, 0
                for needle, _t in needles:
                    if len(needle) < 3:
                        continue
                    for n, src_col in norm_to_src.items():
                        if needle in n and len(needle) > best_len \
                                and src_col not in used:
                            best, best_len = src_col, len(needle)
                direct = best
        if direct is not None and direct not in used:
            out[canon] = df[direct]
            applied[canon] = direct
            used.add(direct)

    # dtype coercion
    if "decimalLatitude" in out:
        out["decimalLatitude"] = pd.to_numeric(
            out["decimalLatitude"], errors="coerce")
    if "decimalLongitude" in out:
        out["decimalLongitude"] = pd.to_numeric(
            out["decimalLongitude"], errors="coerce")
    if "year" in out:
        y = pd.to_numeric(out["year"], errors="coerce")
        y = y.where((y >= 1500) & (y <= 2200), np.nan)
        out["year"] = y
    return out, applied


# ─────────────────────────────────────── CoordinateCleaner-style tests

_GEOJSON_CACHE = {}


def _country_geo(name_or_code: str):
    key = _norm(name_or_code)
    if key in _GEOJSON_CACHE:
        return _GEOJSON_CACHE[key]
    try:
        r = requests.get(
            "https://api.gbif.org/v1/map/occurrence/adhoc"
            f"/{name_or_code}", timeout=10)
        # fallback below is authoritative; keep it simple and skip 404s
        if r.status_code != 200:
            _GEOJSON_CACHE[key] = None
            return None
        _GEOJSON_CACHE[key] = r.json()
        return _GEOJSON_CACHE[key]
    except Exception:
        _GEOJSON_CACHE[key] = None
        return None


CAPITALS = {
    # a pragmatic subset covering the most common dataset origins;
    # CoordinateCleaner ships the full global list, we embed a
    # representative one (name, lat, lon) — ~80 entries
    "canberra": (-35.28, 149.13), "wellington": (-41.29, 174.78),
    "pretoria": (-25.75, 28.19), "cape town": (-33.92, 18.42),
    "nairobi": (-1.29, 36.82), "madrid": (40.42, -3.70),
    "paris": (48.86, 2.35), "london": (51.51, -0.13),
    "berlin": (52.52, 13.40), "lisbon": (38.72, -9.14),
    "rome": (41.90, 12.50), "moscow": (55.76, 37.62),
    "beijing": (39.90, 116.41), "tokyo": (35.68, 139.69),
    "delhi": (28.61, 77.21), "brasília": (-15.79, -47.88),
    "brasilia": (-15.79, -47.88), "buenos aires": (-34.60, -58.38),
    "santiago": (-33.45, -70.67), "lima": (-12.05, -77.04),
    "bogotá": (4.71, -74.07), "bogota": (4.71, -74.07),
    "mexico city": (19.43, -99.13), "ottawa": (45.42, -75.70),
    "washington": (38.91, -77.04), "oslo": (59.91, 10.75),
    "stockholm": (59.33, 18.07), "helsinki": (60.17, 24.94),
    "copenhagen": (55.68, 12.57), "dublin": (53.35, -6.26),
    "amsterdam": (52.37, 4.90), "brussels": (50.85, 4.35),
    "berne": (46.95, 7.45), "vienna": (48.21, 16.37),
    "warsaw": (52.23, 21.01), "prague": (50.09, 14.42),
    "budapest": (47.50, 19.04), "athens": (37.98, 23.73),
    "ankara": (39.93, 32.86), "cairo": (30.04, 31.24),
    "abuja": (9.06, 7.49), "accra": (5.60, -0.19),
    "dakar": (14.72, -17.47), "addis ababa": (9.03, 38.74),
    "kampala": (0.35, 32.58), "harare": (-17.83, 31.05),
    "gaborone": (-24.65, 25.91), "windhoek": (-22.56, 17.08),
    "jakarta": (-6.21, 106.85), "kuala lumpur": (3.14, 101.69),
    "manila": (14.60, 120.98), "bangkok": (13.76, 100.50),
    "hanoi": (21.03, 105.85), "seoul": (37.57, 126.98),
    "canberra_": None, "tehran": (35.69, 51.39), "baghdad": (33.31, 44.36),
    "riyadh": (24.71, 46.68), "kabul": (34.53, 69.17),
    "ulaanbaatar": (47.89, 106.91), "kathmandu": (27.72, 85.32),
    "colombo": (6.93, 79.86), "dhaka": (23.81, 90.41),
    "caracas": (10.48, -66.90), "quito": (-0.18, -78.47),
    "la paz": (-16.50, -68.15), "montevideo": (-34.90, -56.16),
    "asunción": (-25.28, -57.63), "havana": (23.11, -82.37),
    "kingston": (17.97, -76.79), "san josé": (9.93, -84.08),
    "san jose": (9.93, -84.08), "panama": (8.98, -79.52),
    "guatemala city": (14.63, -90.51), "belmopan": (17.25, -88.77),
    "tegucigalpa": (14.07, -87.19), "managua": (12.11, -86.24),
    "san salvador": (13.69, -89.22), "port-au-prince": (18.54, -72.34),
    "santo domingo": (18.49, -69.93), "nassau": (25.06, -77.35),
    "port moresby": (-9.44, 147.18), "suva": (-18.14, 178.44),
    "aporea": None, "port vila": (-17.73, 168.32), "honolulu": (21.31, -157.86),
}


def _capitals() -> dict:
    return {k: v for k, v in CAPITALS.items() if v is not None}


def run_geographic_checks(df: pd.DataFrame) -> pd.DataFrame:
    """CoordinateCleaner-inspired tests (Zizka et al. 2019).

    Adds to the classic five: cc_equ (identical lat/lon), cc_zero
    (on a coordinate edge), cd_round (rasterized coordinates,
    dataset-level diagnosis applied per record), cd_ddmm (degree-
    minute conversion error) and coordinate hotspots (many records
    on one exact coordinate — GBIF HQ / zoo / mass-capture signature).
    """
    flags = pd.DataFrame(index=df.index)

    lat = df.get("decimalLatitude", pd.Series(np.nan, index=df.index))
    lon = df.get("decimalLongitude", pd.Series(np.nan, index=df.index))

    flags["swap_flag"] = _check_swap(lat, lon)
    flags["capital_flag"] = _check_capital(lat, lon)
    flags["edge_flag"] = _check_edge(lat, lon)
    flags["future_date"] = _check_future(df)
    flags["bad_name"] = _check_name(df)
    flags["equal_latlon"] = _check_equal_latlon(lat, lon)
    flags["ddmm_suspect"] = _check_ddmm(df, lat, lon)
    flags["dataset_rounded"], _round_diag = _check_rounded(lat, lon)
    flags["coordinate_hotspot"] = _check_hotspots(df, lat, lon)

    return flags


def _check_equal_latlon(lat, lon):
    """cc_equ: latitude equals longitude (exact or absolute),
    excluding the (0,0) case already covered by zero-coordinate test."""
    zero0 = (lat == 0) & (lon == 0)
    with np.errstate(invalid="ignore"):
        exact = (lat == lon)
        absolute = (lat.abs() == lon.abs())
    return ((exact | absolute) & ~zero0).fillna(False)


def _check_ddmm(df, lat, lon):
    """cd_ddmm (dataset-level): GPS set to degrees+minutes but written
    as decimal degrees. Signature — across the whole dataset the
    fractional parts are minute-like (0.01–0.59) and NEVER reach 0.60+
    (real decimal degrees spread uniformly 0–99 hundredths).
    Requires ≥10 non-integer coordinates before the dataset is judged;
    when suspect, records with minute-like fractions are flagged.
    """
    out = pd.Series(False, index=df.index)
    fracs = []
    for s in (lat, lon):
        f = (s - np.floor(s)).dropna()
        f = f[(f > 0) & (f < 1)]
        fracs.append(f * 100)
    allf = pd.concat(fracs) if fracs else pd.Series([], dtype=float)
    if len(allf) < 10:
        return out
    minute_like = allf.round(0).between(1, 59)
    # suspect only when essentially no value exceeds 59 hundredths
    if minute_like.mean() > 0.95 and not (allf >= 60).any():
        for s in (lat, lon):
            frac = s - np.floor(s)
            with np.errstate(invalid="ignore"):
                m = np.round(frac * 100)
                looks = (m >= 1) & (m <= 59)
            out = out | pd.Series(looks, index=df.index).fillna(False)
    return out


def _check_rounded(lat, lon, threshold=0.8):
    """cd_round (dataset-level): rasterised to a coarse grid.

    Tests 0.1 / 0.25 / 0.5 / 1.0-degree grids; when ≥ threshold share
    of coordinates sit on one coarse grid the records on it are
    flagged (2-decimal data is normal and is NOT a hit). Returns
    (per_record_flags, stats).
    """
    ok = lat.notna() & lon.notna()
    stats = {"share_on_grid": None, "diagnosis": None}
    noflag = pd.Series(False, index=lat.index)
    if ok.sum() < 10:
        return noflag, stats
    for g in (0.1, 0.25, 0.5, 1.0):
        with np.errstate(invalid="ignore"):
            on = (np.round(lat / g) == lat / g) \
                & (np.round(lon / g) == lon / g)
        on = on[ok].fillna(False)
        share = float(on.mean())
        if share >= threshold:
            stats = {"share_on_grid": round(share, 3),
                     "diagnosis": f"rasterised to a {g}° grid"}
            return on.reindex(df.index).fillna(False), stats
    return noflag, stats


def _check_hotspots(df, lat, lon, min_repeats=10):
    """Many records sharing one exact coordinate pair.

    Flags the recurring pairs themselves (mass captures, zoos,
    GBIF-HQ-style defaults). Cheap group-by; tolerant of missing data.
    """
    out = pd.Series(False, index=df.index)
    if "decimalLatitude" not in df or "decimalLongitude" not in df:
        return out
    ok = lat.notna() & lon.notna()
    if ok.sum() < min_repeats:
        return out
    key = list(zip(np.round(lat[ok], 6), np.round(lon[ok], 6)))
    counts = pd.Series(key).value_counts()
    hot = {k for k, c in counts.items() if c >= min_repeats}
    if hot:
        out.loc[ok] = [k in hot for k in key]
    return out


# ───────────────────────────────────────────── fit-for-use profiles

# ALA-inspired data profiles (ALA Support, "Getting started with the
# data profiles"): each check is either FATAL (record excluded from
# the fit-for-use subset) or ADVISORY (reported, record kept).
PROFILES = {
    "General": {
        "fatal": [
            "missing_coords", "zero_coords", "swap_flag", "edge_flag",
            "equal_latlon", "future_date", "bad_name", "duplicate",
            "country_mismatch", "ddmm_suspect",
        ],
        "advisory": [
            "low_precision", "old_record", "missing_year", "missing_date",
            "dataset_rounded", "coordinate_hotspot", "capital_flag",
        ],
        "note": "General mapping and listing use — hard spatial and "
                "taxonomic errors excluded, precision advisories kept.",
    },
    "SDM (Zizka et al. 2020)": {
        "fatal": [
            "missing_coords", "zero_coords", "swap_flag", "edge_flag",
            "equal_latlon", "future_date", "bad_name", "duplicate",
            "country_mismatch", "capital_flag", "low_precision",
            "old_record", "missing_year", "dataset_rounded",
            "coordinate_hotspot",
        ],
        "advisory": ["missing_date", "ddmm_suspect"],
        "note": "Species-distribution modelling filter — mirrors the "
                "cleaning workflow of Zizka et al. 2020 (EcoEvoRxiv) "
                "and the ALA CSDM profile.",
    },
    "Report only (nothing excluded)": {
        "fatal": [],
        "advisory": [],
        "note": "Every check is reported; no record is excluded.",
    },
}


def apply_profile(flags: pd.DataFrame, profile: str):
    """Add profile_exclude / profile_advisory columns to a flags frame."""
    p = PROFILES.get(profile) or PROFILES["General"]
    flags = flags.copy()
    fatal = [c for c in p["fatal"] if c in flags.columns]
    advis = [c for c in p["advisory"] if c in flags.columns]
    flags["profile_exclude"] = flags[fatal].any(axis=1) if fatal \
        else pd.Series(False, index=flags.index)
    flags["profile_advisory"] = flags[advis].any(axis=1) if advis \
        else pd.Series(False, index=flags.index)
    return flags, p


def _haversine_km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians,
                             [lat1, lon1, lat2, lon2])
    a = (np.sin((la2 - la1) / 2) ** 2
         + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _check_swap(lat, lon):
    """Lat/lon swapped: |lat|>90 while |lon|<=90 and swapping fixes it."""
    bad = lat.abs() > 90
    fixable = bad & (lon.abs() <= 90) & lon.abs().notna()
    return bad & fixable


def _check_capital(lat, lon, radius_km=15):
    caps = _capitals()
    out = pd.Series(False, index=lat.index)
    lats = np.asarray(lat, dtype=float)
    lons = np.asarray(lon, dtype=float)
    # vectorised per capital (subset size keeps this cheap)
    for clat, clon in caps.values():
        with np.errstate(invalid="ignore"):
            d = _haversine_km(lats, lons, clat, clon)
        out = out | (d <= radius_km)
    return out.fillna(False)


def _check_edge(lat, lon):
    """Coordinates exactly on 0.0/90.0 meridians or datum edges."""
    with np.errstate(invalid="ignore"):
        return ((lat.abs() == 90) | (lon.abs() == 180)
                | (lat == 0) | (lon == 0)).fillna(False)


def _check_future(df):
    if "year" in df:
        import datetime as _dt
        this_year = _dt.date.today().year
        return (df["year"] > this_year).fillna(False)
    return pd.Series(False, index=df.index)


def _check_name(df):
    """Plausibility of the scientific-name field.

    Rejects: empty, no space and not binomial-like when genus present,
    digits, URLs, ALLCAPS tokens > 3 chars, > 60 chars.
    """
    if "species" not in df:
        return pd.Series(False, index=df.index)
    s = df["species"].astype(str)

    def bad(x):
        if not x or x.lower() in ("nan", "none", "null", ""):
            return True
        if len(x) > 60:
            return True
        if re.search(r"\d", x) or "http" in x.lower():
            return True
        words = x.split()
        if len(words) < 2:
            return True
        if any(w.isupper() and len(w) > 3 for w in words):
            return True
        return False

    return s.apply(bad)


# ───────────────────────────────────────────── taxonomy (GBIF backbone)

_BACKBONE_CACHE = {}


def verify_names(names, timeout=8):
    """GBIF /species/match verification for uploaded names.

    Parallel (8 workers, GBIF etiquette-safe) with a process-lifetime
    cache; result order matches input order.
    """
    from concurrent.futures import ThreadPoolExecutor

    def one(n):
        key = str(n).strip().lower()
        if key in _BACKBONE_CACHE:
            return _BACKBONE_CACHE[key]
        try:
            r = requests.get(
                "https://api.gbif.org/v1/species/match",
                params={"name": n, "strict": "false", "verbose": "false"},
                timeout=timeout,
            )
            if r.status_code == 200:
                j = r.json()
                rec = {
                    "name": n,
                    "matchType": j.get("matchType"),
                    "confidence": j.get("confidence"),
                    "usageKey": j.get("usageKey"),
                    "scientificName": j.get("scientificName"),
                    "status": j.get("status"),
                    "kingdom": j.get("kingdom"),
                }
            else:
                rec = {"name": n, "matchType": "NONE",
                       "confidence": None, "usageKey": None,
                       "scientificName": None, "status": None,
                       "kingdom": None}
        except Exception:
            rec = {"name": n, "matchType": "ERROR", "confidence": None,
                   "usageKey": None, "scientificName": None,
                   "status": None, "kingdom": None}
        _BACKBONE_CACHE[key] = rec
        return rec

    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(one, names))


# ──────────────────────────────────────────────────────── orchestration

def _jsonify(x):
    """Recursively convert numpy scalars to JSON-safe python types."""
    if isinstance(x, dict):
        return {k: _jsonify(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonify(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        f = float(x)
        return None if np.isnan(f) else f
    if isinstance(x, float) and np.isnan(x):
        return None
    return x


def flagged_sample(df: pd.DataFrame, flags: pd.DataFrame,
                   n: int = 20) -> list:
    """First n flagged rows with their flag reasons, for the UI."""
    out = []
    flagged_idx = flags.index[flags["any_flag"].fillna(False)][:n]
    flag_cols = [c for c in flags.columns
                 if c not in ("any_flag", "has_issues")]
    for i in flagged_idx:
        row = df.loc[i]
        reasons = [c for c in flag_cols
                   if bool(flags.at[i, c])] if i in flags.index else []
        def g(col):
            v = row.get(col)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v)
            return str(v)[:80]
        out.append({
            "row": int(i) + 1,
            "reasons": reasons,
            "species": g("species"),
            "decimalLatitude": g("decimalLatitude"),
            "decimalLongitude": g("decimalLongitude"),
            "year": g("year"),
            "country": g("country"),
        })
    return out


def bdq_from_flags(flags: pd.DataFrame) -> list:
    """Quality-check rows in the same schema as the species endpoint."""
    from utils.bdq import bdq_meta
    meta = {
        "missing_coords": ("VALIDATION_COORDINATES_PRESENT", "Missing coordinates"),
        "zero_coords": ("VALIDATION_COORDINATES_NOT_ZERO", "Zero coordinates"),
        "missing_year": ("VALIDATION_YEAR_PRESENT", "Missing event year"),
        "old_record": ("VALIDATION_YEAR_IN_RANGE", "Pre-1900 record"),
        "missing_date": ("VALIDATION_EVENTDATE_PRESENT", "Missing event date"),
        "duplicate": ("VALIDATION_DISTINCT_OCCURRENCES", "Duplicate record"),
        "low_precision": ("VALIDATION_PRECISION_LOW", "Low coordinate precision"),
        "country_mismatch": ("VALIDATION_COUNTRY_CONSISTENT", "Country-coordinate mismatch"),
        "swap_flag": ("VALIDATION_COORDINATES_PLAUSIBLE", "Lat/lon appear swapped"),
        "capital_flag": ("VALIDATION_COORDINATES_PLAUSIBLE", "Within 15 km of a capital city"),
        "edge_flag": ("VALIDATION_COORDINATES_PLAUSIBLE", "On a coordinate edge (0/90/180)"),
        "future_date": ("VALIDATION_DATE_IN_RANGE", "Dated in the future"),
        "bad_name": ("VALIDATION_NAME_PLAUSIBLE", "Implausible scientific name"),
        "equal_latlon": ("VALIDATION_COORDINATES_PLAUSIBLE", "Latitude equals longitude (absolute)"),
        "ddmm_suspect": ("VALIDATION_COORDINATES_PLAUSIBLE", "Possible degree-minute conversion error"),
        "dataset_rounded": ("VALIDATION_PRECISION_LOW", "Rasterized to a 0.01° grid"),
        "coordinate_hotspot": ("VALIDATION_DISTINCT_OCCURRENCES", "Exact coordinate repeated ≥10 times"),
    }
    rows = []
    total = len(flags)
    for key, (bdq, label) in meta.items():
        if key not in flags:
            continue
        flagged = int(flags[key].fillna(False).sum())
        rows.append({
            "check": key,
            "label": label,
            "bdq_test": bdq + " · BioSift",
            "flagged": flagged,
            "percent": round(flagged / total * 100, 1) if total else 0.0,
        })
    return rows


def analyze_uploaded(df_raw: pd.DataFrame, mapping: dict | None = None,
                     dataset_name: str = "",
                     profile: str = "General") -> dict:
    """Full BYOD analysis — same pipeline as the species endpoint."""
    from utils.quality import (run_quality_checks, quality_summary,
                               get_completeness_score,
                               get_precision_stats)
    from utils.fitness import audit_sdm_readiness
    from utils.charts import get_temporal_stats, get_recommendations
    from utils.dataset_quality import get_dataset_quality_breakdown

    df, applied = map_columns(df_raw, mapping)
    n = len(df)
    if n == 0:
        raise ValueError("File contains no data rows")

    flags = run_quality_checks(df)
    geo = run_geographic_checks(df)
    flags = pd.concat([flags, geo], axis=1)
    flags["any_flag"] = flags.drop(columns=["any_flag", "has_issues"],
                                   errors="ignore") \
        .astype(bool).any(axis=1)

    # ALA-style fit-for-use profile
    flags, prof = apply_profile(flags, profile)
    keep = ~flags["profile_exclude"]
    profile_subset = {
        "profile": profile,
        "note": prof["note"],
        "fatal_checks": prof["fatal"],
        "advisory_checks": prof["advisory"],
        "records_kept": int(keep.sum()),
        "records_excluded": int((~keep).sum()),
        "retention_pct": round(float(keep.mean()) * 100, 1) if n else 0.0,
    }

    checks = bdq_from_flags(flags)
    summary = quality_summary(flags)
    clean_df = df[~flags["any_flag"]].reset_index(drop=True)
    completeness = get_completeness_score(df)

    # per-species breakdown (top 12 by record count)
    species_table = None
    if "species" in df:
        grp = df.groupby(df["species"].fillna("(blank)").astype(str))
        rows = []
        for name, idx in grp.groups.items():
            f = flags.loc[idx]
            rows.append({
                "species": name[:60],
                "records": len(idx),
                "flagged": int(f["any_flag"].sum()),
                "excluded": int(f["profile_exclude"].sum()),
                "flag_pct": round(float(f["any_flag"].mean()) * 100, 1),
            })
        species_table = sorted(rows, key=lambda r: -r["records"])[:12]

    # dataset-level rounding diagnosis
    rounded_stats = None
    if "decimalLatitude" in df and "decimalLongitude" in df:
        _fr, rounded_stats = _check_rounded(
            df["decimalLatitude"], df["decimalLongitude"])

    # column profile — what the user actually uploaded
    col_profile = []
    for c in df_raw.columns:
        s = df_raw[c]
        filled = int(s.notna().sum())
        entry = {
            "column": str(c),
            "filled_pct": round(filled / n * 100, 1) if n else 0.0,
            "distinct": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            entry["kind"] = "numeric"
        else:
            entry["kind"] = "text"
            vals = s.dropna().astype(str).unique()[:3]
            entry["sample"] = [v[:40] for v in vals]
        col_profile.append(entry)

    fit = None
    if {"decimalLatitude", "decimalLongitude"} <= set(df.columns):
        fit = audit_sdm_readiness(df, flags)

    dist = None
    if {"decimalLatitude", "decimalLongitude"} <= set(df.columns):
        from utils.predict import run_distribution_metrics
        try:
            dist = run_distribution_metrics(df)
        except Exception:
            dist = None

    outliers = None
    if {"decimalLatitude", "decimalLongitude"} <= set(df.columns):
        from utils.outliers import detect_outliers, outlier_summary
        try:
            mask = detect_outliers(df)
            outliers = {
                "flagged": int(mask.sum()),
                "percent": round(float(mask.mean()) * 100, 1),
                "summary": outlier_summary(mask),
            }
        except Exception:
            outliers = None

    temporal = get_temporal_stats(df)
    gaps = None
    if "country" in df:
        from utils.gaps import get_gap_stats
        gaps = get_gap_stats(df)

    # name verification (unique names, capped for latency)
    verified = None
    if "species" in df:
        uniq = df["species"].dropna().astype(str).str.strip()
        uniq = [x for x in uniq.unique() if x][:200]
        if uniq:
            verified = verify_names(uniq)

    health = (round(len(clean_df) / n * 100, 1) if n else 0.0)
    recs = []
    try:
        recs = get_recommendations(summary, temporal, df) or []
    except Exception:
        recs = []
    bundle = {
        "schema": "biosift.byod/1.0",
        "dataset": dataset_name or "uploaded dataset",
        "rows": n,
        "columns_used": applied,
        "columns_available": list(df_raw.columns),
        "column_profile": col_profile,
        "species_table": species_table,
        "rounded_stats": rounded_stats,
        "profile": profile_subset,
        "scores": {
            "records_analysed": n,
            "records_clean": int((~flags["any_flag"]).sum()),
            "records_kept": profile_subset["records_kept"],
            "health_pct": health,
            "completeness_pct": (completeness["avg_score"]
                                 if completeness else None),
        },
        "quality_checks": checks,
        "sdm_readiness": fit,
        "distribution_kba": dist,
        "outliers": outliers,
        "temporal": temporal,
        "gaps": gaps,
        "name_verification": {
            "total_unique": len(uniq) if "species" in df else 0,
            "checked": len(verified) if verified else 0,
            "results": verified,
        },
        "precision_stats": get_precision_stats(df),
        "recommendations": recs,
        "flagged_sample": flagged_sample(df, flags),
        "geojson": rows_geojson(df, flags, limit=5000),
        "standards": {
            "quality_tests": "TDWG BDQ TESTS + CoordinateCleaner-style geographic tests (Zizka et al. 2019)",
        },
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
    }
    return _jsonify(bundle)


def cleaned_csv(df_raw: pd.DataFrame, mapping: dict | None,
                profile: str = "General",
                mode: str = "flagged") -> str:
    """The user's own file back, with BioSift verdict columns appended.

    mode="flagged": keep every row, add biosift_* verdict columns.
    mode="clean":   only rows passing the fit-for-use profile.
    """
    from utils.quality import run_quality_checks
    df, _ = map_columns(df_raw, mapping)
    flags = run_quality_checks(df)
    geo = run_geographic_checks(df)
    flags = pd.concat([flags, geo], axis=1)
    flags["any_flag"] = flags.drop(columns=["any_flag", "has_issues"],
                                   errors="ignore") \
        .astype(bool).any(axis=1)
    flags, _prof = apply_profile(flags, profile)

    out = df_raw.copy().reset_index(drop=True)
    f = flags.reset_index(drop=True)
    out["biosift_flag"] = f["any_flag"].map({True: "Y", False: "N"})
    out["biosift_exclude"] = f["profile_exclude"].map(
        {True: "Y", False: "N"})
    flag_cols = [c for c in f.columns
                 if c not in ("any_flag", "has_issues",
                              "profile_exclude", "profile_advisory")]
    out["biosift_reasons"] = f[flag_cols].apply(
        lambda row: ";".join(c for c in flag_cols if bool(row[c])),
        axis=1)
    if mode == "clean":
        out = out[~f["profile_exclude"]]
    return out.to_csv(index=False)


def rows_geojson(df: pd.DataFrame, flags: pd.DataFrame | None = None,
                 limit: int = 5000) -> dict:
    """GeoJSON FeatureCollection for the uploaded data (map layer)."""
    feats = []
    if "decimalLatitude" not in df or "decimalLongitude" not in df:
        return {"type": "FeatureCollection", "features": []}
    for i, row in df.head(limit).iterrows():
        la, lo = row.get("decimalLatitude"), row.get("decimalLongitude")
        # map-only guard: impossible coordinates (swaps, bad georefs)
        # stay in the tables and exports but cannot be rendered by
        # MapLibre (Invalid LngLat kills fitBounds / jumpTo)
        if (pd.isna(la) or pd.isna(lo)
                or abs(float(la)) > 90 or abs(float(lo)) > 180):
            continue
        flagged = bool(flags["any_flag"].iloc[i]) if flags is not None \
            and i < len(flags) else False
        excluded = bool(flags["profile_exclude"].iloc[i]) if flags is not None \
            and i < len(flags) and "profile_exclude" in flags else False
        reasons = []
        if flags is not None and i < len(flags):
            reasons = [c for c in flags.columns
                       if c not in ("any_flag", "has_issues",
                                    "profile_exclude", "profile_advisory")
                       and bool(flags[c].iloc[i])]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(lo), float(la)]},
            "properties": {
                "species": row.get("species"),
                "year": None if pd.isna(row.get("year")) else row.get("year"),
                "country": row.get("country"),
                "fl": 1 if flagged else 0,
                "ex": 1 if excluded else 0,
                "biosift_flag": flagged,
                "biosift_flags": reasons,
            },
        })
    return {"type": "FeatureCollection", "features": feats}
