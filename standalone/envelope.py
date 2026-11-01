"""Climate envelope — where the species sits in climate space.

Environmental layers are the usual blocker for browser-side niche
work: WorldClim/CHELSA rasters are hundreds of megabytes and any
tile/API key adds a hard dependency. NASA POWER's climatology point
endpoint is key-free and returns monthly temperature and precipitation
plus the surface elevation for a coordinate in one small request, so
the envelope is sampled at the record locations themselves.

Reported: annual temperature range, annual precipitation range,
elevation range across sampled records, and monthly median curves for
the charts. This is a descriptive envelope (where the records are), not
a fitted niche model — no model is calibrated here.
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

POWER_URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point")
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

_cache: dict = {}


def _fetch_point(lat: float, lon: float, timeout: int = 18):
    key = (round(float(lat), 3), round(float(lon), 3))
    if key in _cache:
        return _cache[key]
    try:
        r = requests.get(
            POWER_URL,
            params={"parameters": "T2M,PRECTOTCORR", "community": "AG",
                    "latitude": key[0], "longitude": key[1],
                    "format": "JSON"},
            timeout=timeout,
        )
        r.raise_for_status()
        js = r.json()
        par = js["properties"]["parameter"]
        t2m, prec = par.get("T2M"), par.get("PRECTOTCORR")
        if not t2m or not prec:
            raise ValueError("no parameters in response")
        z = (js.get("geometry") or {}).get("coordinates") or [None, None, None]
        out = {
            "t2m": {m: t2m.get(m) for m in MONTHS},
            "prec": {m: prec.get(m) for m in MONTHS},
            # ANN is not in MONTHS — keep the annual means explicitly
            "t2m_ann": t2m.get("ANN"),
            "prec_ann": prec.get("ANN"),
            "elev": z[2] if len(z) > 2 else None,
        }
        if out["t2m_ann"] is None or out["prec_ann"] is None:
            raise ValueError("no annual mean in response")
        _cache[key] = out
        return out
    except Exception:
        return None


def _rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {
        "min": round(float(np.min(vals)), 1),
        "median": round(float(np.median(vals)), 1),
        "max": round(float(np.max(vals)), 1),
    }


def climate_envelope(df: pd.DataFrame, sample: int = 24,
                     workers: int = 6) -> dict:
    """Sample the climatology at up to `sample` record locations."""
    needed = {"decimalLatitude", "decimalLongitude"}
    if not needed <= set(df.columns):
        return {"available": False,
                "reason": "coordinates are required"}

    lat = pd.to_numeric(df["decimalLatitude"], errors="coerce")
    lon = pd.to_numeric(df["decimalLongitude"], errors="coerce")
    ok = lat.notna() & lon.notna() & (lat.abs() <= 90) & (lon.abs() <= 180)
    pts = pd.DataFrame({"lat": lat[ok], "lon": lon[ok]}).dropna()
    if len(pts) < 5:
        return {"available": False,
                "reason": "not enough georeferenced records"}

    # even spread across the sorted sample, not just the first rows
    idx = np.unique(np.linspace(0, len(pts) - 1,
                                min(sample, len(pts))).astype(int))
    take = pts.iloc[idx]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = list(ex.map(lambda r: _fetch_point(r.lat, r.lon),
                          take.itertuples(index=False)))
    got = [g for g in got if g]

    if len(got) < 3:
        return {"available": False,
                "reason": "climate service unreachable or too few "
                          "sampled points returned data"}

    ann_t = [g["t2m_ann"] for g in got]
    ann_p = [g["prec_ann"] for g in got]
    elev = [g["elev"] for g in got if g.get("elev") is not None]

    monthly_t = [round(float(np.median(
        [g["t2m"][m] for g in got if g["t2m"].get(m) is not None])), 1)
        if any(g["t2m"].get(m) is not None for g in got) else None
        for m in MONTHS]
    monthly_p = [round(float(np.median(
        [g["prec"][m] for g in got if g["prec"].get(m) is not None])) * d, 1)
        if any(g["prec"].get(m) is not None for g in got) else None
        for m, d in zip(MONTHS, DAYS)]

    return {
        "available": True,
        "points_sampled": int(len(got)),
        "temp_annual_c": _rng(ann_t),
        "precip_annual_mm": _rng([p * 365 for p in ann_p]),
        "elevation_m": _rng(elev),
        "monthly_temp_c": monthly_t,
        "monthly_precip_mm": monthly_p,
        "months": [m.title() for m in MONTHS],
        "method": (
            f"NASA POWER long-term climatology sampled at {len(got)} of "
            f"{len(take)} record locations spread across the sample "
            "(monthly means aggregated to annual values)."
        ),
        "note": (
            "Descriptive envelope of where records occur — a fitted "
            "niche model would add background points and an algorithm."
        ),
    }
