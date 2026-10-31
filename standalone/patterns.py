"""Chart data for the standalone frontend.

Descriptive statistics only — no plotting dependency. The frontend
draws SVG/HTML from these numbers so every figure stays inside the
app's own design language and no data leaves the process.

Figures produced:
  correlation       Pearson r between record attributes (incl. the
                    number of checks each record triggered)
  cooccurrence      Jaccard overlap between quality checks — which
                    defects travel together
  decades           records and flag rate per decade
  completeness_dist distribution of per-record field completeness
  categorical       flag rate by country and by basis of record
"""
import numpy as np
import pandas as pd

COMPLETENESS_FIELDS = [
    "species", "decimalLatitude", "decimalLongitude", "year", "month",
    "eventDate", "basisOfRecord", "country", "datasetName", "occurrenceID",
]

LABELS = {
    "year": ("Year", "Year"),
    "latitude": ("Latitude", "Lat"),
    "longitude": ("Longitude", "Lon"),
    "uncertainty": ("Coord. uncertainty (m)", "Uncert."),
    "precision": ("Coord. precision (dp)", "Precision"),
    "completeness": ("Field completeness (%)", "Complete"),
    "flags": ("Checks triggered", "Flags"),
}

CHECK_SHORT = {
    "missing_coords": "No coords",
    "zero_coords": "Zero coords",
    "missing_year": "No year",
    "old_record": "Pre-1900",
    "missing_date": "No date",
    "duplicate": "Duplicate",
    "low_precision": "Low prec.",
    "country_mismatch": "Ctry mism.",
    "swap_flag": "Swap",
    "capital_flag": "Capital",
    "edge_flag": "Edge",
    "future_date": "Future",
    "bad_name": "Bad name",
    "equal_latlon": "Lat=lon",
    "ddmm_suspect": "DDMM",
    "dataset_rounded": "Grid",
    "coordinate_hotspot": "Hotspot",
}

META_COLS = {"any_flag", "has_issues", "profile_exclude", "profile_advisory"}


# ────────────────────────────────────────────────────── building blocks

def _decimals(s: pd.Series) -> pd.Series:
    """Decimal places of a coordinate series (0-6), NaN preserved."""
    v = pd.to_numeric(s, errors="coerce").abs()
    txt = v.map(lambda x: f"{x:.6f}".rstrip("0") if pd.notna(x) else "")
    dp = txt.str.split(".").str[1].fillna("").str.len().astype(float)
    return dp.where(v.notna())


def _attr_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    def num(col):
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
        return pd.Series(np.nan, index=df.index, dtype="float64")

    out["year"] = num("year")
    out["latitude"] = num("decimalLatitude")
    out["longitude"] = num("decimalLongitude")
    out["uncertainty"] = num("coordinateUncertaintyInMeters")
    out["precision"] = pd.concat(
        [_decimals(out["latitude"]), _decimals(out["longitude"])], axis=1
    ).max(axis=1)

    cols = [c for c in COMPLETENESS_FIELDS if c in df.columns]
    if cols:
        out["completeness"] = (
            df[cols].notna().sum(axis=1) / len(cols) * 100.0
        )
    else:
        out["completeness"] = np.nan
    return out


def _flag_cols(flags: pd.DataFrame) -> list:
    return [c for c in flags.columns if c not in META_COLS]


def _flag_count(flags: pd.DataFrame, index) -> pd.Series:
    cols = _flag_cols(flags)
    if not cols:
        return pd.Series(0, index=index, dtype="int64")
    return flags[cols].fillna(False).astype(bool).sum(axis=1)


def _check_label(key: str) -> str:
    try:
        from utils.bdq import bdq_meta
        return bdq_meta(key)[1]
    except Exception:
        return key.replace("_", " ").capitalize()


def _flag_series(flags: pd.DataFrame, index) -> pd.Series:
    if "any_flag" in flags.columns:
        return flags["any_flag"].fillna(False).astype(bool)
    return _flag_count(flags, index).astype(bool)


# ──────────────────────────────────────────────────────────── figures

def correlation(df: pd.DataFrame, flags: pd.DataFrame) -> dict:
    """Pearson r matrix over record attributes, pairwise-complete."""
    a = _attr_frame(df)
    a["flags"] = _flag_count(flags, df.index).astype(float)

    # a zero-variance column cannot correlate with anything — drop it
    keys = [k for k in LABELS if k in a.columns
            and a[k].notna().sum() >= 5 and a[k].std(ddof=0) > 0]
    variables = [
        {"key": k, "label": LABELS[k][0], "short": LABELS[k][1]}
        for k in keys
    ]

    cells, ns = [], []
    for k in keys:
        row, nrow = [], []
        for m in keys:
            # select by position: a[[k, k]] yields a two-column frame
            pair = a[[k, m]].dropna()
            n = int(len(pair))
            r = None
            if n >= 5:
                x, y = pair.iloc[:, 0], pair.iloc[:, 1]
                if x.std(ddof=0) > 0 and y.std(ddof=0) > 0:
                    val = x.corr(y)
                    if pd.notna(val):
                        r = round(float(val), 3)
            row.append(r)
            nrow.append(n)
        cells.append(row)
        ns.append(nrow)

    return {
        "variables": variables,
        "cells": cells,
        "n": ns,
        "method": (
            "Pearson r on pairwise-complete records (n≥5, cells with "
            "fewer pairs are blank). Flags = checks triggered per record."
        ),
    }


def cooccurrence(flags: pd.DataFrame, top: int = 8) -> dict:
    """Jaccard overlap between the checks that fire most often."""
    cols = _flag_cols(flags)
    counts = {c: int(flags[c].fillna(False).astype(bool).sum()) for c in cols}
    keep = [c for c in sorted(cols, key=lambda c: -counts[c])
            if counts[c] > 0][:top]

    if len(keep) < 2:
        return {"checks": [], "cells": [], "method": ""}

    b = flags[keep].fillna(False).astype(bool)
    cells = []
    for a in keep:
        row = []
        for c in keep:
            union = int((b[a] | b[c]).sum())
            both = int((b[a] & b[c]).sum())
            row.append(round(both / union, 3) if union else None)
        cells.append(row)

    checks = [
        {"key": c, "label": _check_label(c),
         "short": CHECK_SHORT.get(
             c, _check_label(c)[:9]), "flagged": counts[c]}
        for c in keep
    ]
    return {
        "checks": checks,
        "cells": cells,
        "method": (
            "Jaccard index: records flagged by both checks divided by "
            "records flagged by either. 1.0 = always together."
        ),
    }


def decades(df: pd.DataFrame, flags: pd.DataFrame) -> list:
    if "year" not in df.columns:
        return []
    y = pd.to_numeric(df["year"], errors="coerce")
    ok = y.notna() & (y >= 1700) & (y <= 2100)
    if not ok.any():
        return []
    f = _flag_series(flags, df.index)
    d = pd.DataFrame({
        "decade": (y[ok] // 10 * 10).astype(int),
        "flag": f[ok].astype(int),
    })
    g = d.groupby("decade")["flag"].agg(["size", "sum"])
    rows = []
    for dec, row in g.iterrows():
        total, fl = int(row["size"]), int(row["sum"])
        rows.append({
            "label": f"{int(dec)}s",
            "records": total,
            "flagged": fl,
            "flag_pct": round(fl / total * 100, 1) if total else 0.0,
        })
    return rows[-18:]


def completeness_dist(df: pd.DataFrame) -> list:
    a = _attr_frame(df)
    v = a["completeness"].dropna()
    if v.empty:
        return []
    cats = pd.cut(v, bins=range(0, 101, 10), include_lowest=True)
    cnt = cats.value_counts().sort_index()
    return [
        {"label": f"{int(i.left)}–{int(i.right)}", "count": int(c)}
        for i, c in cnt.items()
    ]


def categorical(df: pd.DataFrame, flags: pd.DataFrame) -> dict:
    f = _flag_series(flags, df.index)
    out = {}
    for col, key in (("country", "by_country"),
                     ("basisOfRecord", "by_basis")):
        if col not in df.columns:
            out[key] = []
            continue
        s = (df[col].fillna("(blank)").astype(str).str.strip()
             .replace("", "(blank)"))
        rows = []
        for val, cnt in s.value_counts().head(6).items():
            idx = s[s == val].index
            fl = int(f.loc[idx].sum())
            rows.append({
                "label": str(val)[:22],
                "records": int(cnt),
                "flagged": fl,
                "flag_pct": round(fl / len(idx) * 100, 1) if len(idx) else 0.0,
            })
        out[key] = rows
    return out


def build_patterns(df: pd.DataFrame, flags: pd.DataFrame) -> dict:
    """Build every figure, isolating failures per figure."""
    out = {}
    for key, fn in (
        ("correlation", lambda: correlation(df, flags)),
        ("cooccurrence", lambda: cooccurrence(flags)),
        ("decades", lambda: decades(df, flags)),
        ("completeness_dist", lambda: completeness_dist(df)),
        ("categorical", lambda: categorical(df, flags)),
    ):
        try:
            out[key] = fn()
        except Exception:
            out[key] = None
    return out
