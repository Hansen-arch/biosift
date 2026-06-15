import pandas as pd

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
        if "issues" in df.columns:
            flags["has_issues"] = df["issues"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )
    except Exception:
        flags["has_issues"] = False

    core_flags = [c for c in flags.columns if c != "has_issues"]
    flags["any_flag"] = flags[core_flags].any(axis=1)

    return flags


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