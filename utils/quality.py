import pandas as pd
import numpy as np

def run_quality_checks(df):
    flags = pd.DataFrame(index=df.index)

    try:
        flags["missing_coords"] = (
            df["decimalLatitude"].isna() | df["decimalLongitude"].isna()
        )
    except Exception:
        flags["missing_coords"] = False

    try:
        flags["zero_coords"] = (
            (df["decimalLatitude"] == 0) & (df["decimalLongitude"] == 0)
        )
    except Exception:
        flags["zero_coords"] = False

    try:
        flags["missing_year"] = df["year"].isna()
    except Exception:
        flags["missing_year"] = False

    try:
        flags["old_record"] = df["year"].notna() & (df["year"] < 1900)
    except Exception:
        flags["old_record"] = False

    try:
        if "eventDate" in df.columns:
            flags["missing_date"] = df["eventDate"].isna()
    except Exception:
        flags["missing_date"] = False

    try:
        flags["duplicate"] = df.duplicated(
            subset=["species", "decimalLatitude", "decimalLongitude", "year"],
            keep=False
        )
    except Exception:
        flags["duplicate"] = False

    try:
        flags["low_precision"] = df.apply(
            lambda row: _check_low_precision(
                row.get("decimalLatitude"),
                row.get("decimalLongitude")
            ), axis=1
        )
    except Exception:
        flags["low_precision"] = False

    try:
        if "issues" in df.columns:
            flags["has_issues"] = df["issues"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )
    except Exception:
        flags["has_issues"] = False

    core_flags = [c for c in flags.columns if c != "has_issues"]
    flags["any_flag"] = flags[core_flags].any(axis=1)

    return flags


def _check_low_precision(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return False
    try:
        lat_decimals = len(str(float(lat)).split(".")[-1].rstrip("0"))
        lon_decimals = len(str(float(lon)).split(".")[-1].rstrip("0"))
        return lat_decimals < 2 or lon_decimals < 2
    except Exception:
        return False


def quality_summary(flags):
    total = len(flags)
    summary = {}

    for col in flags.columns:
        try:
            count = flags[col].sum()
            summary[col] = {
                "count": int(count),
                "percent": round(count / total * 100, 1) if total > 0 else 0
            }
        except Exception:
            summary[col] = {"count": 0, "percent": 0}

    return summary


def get_precision_stats(df):
    try:
        def count_decimals(val):
            if pd.isna(val):
                return 0
            return len(str(float(val)).split(".")[-1].rstrip("0"))

        df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
        lat_prec = df["decimalLatitude"].apply(count_decimals)

        bins = {
            "Very Low (0-1 decimal, ~10km)": int((lat_prec <= 1).sum()),
            "Low (2 decimals, ~1km)":        int((lat_prec == 2).sum()),
            "Medium (3 decimals, ~100m)":    int((lat_prec == 3).sum()),
            "High (4 decimals, ~10m)":       int((lat_prec == 4).sum()),
            "Very High (5+ decimals, ~1m)":  int((lat_prec >= 5).sum()),
        }
        return bins
    except Exception:
        return {}