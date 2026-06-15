import pandas as pd

def run_quality_checks(df):
    flags = pd.DataFrame(index=df.index)

    flags["missing_coords"] = df["decimalLatitude"].isna() | df["decimalLongitude"].isna()
    flags["zero_coords"] = (df["decimalLatitude"] == 0) & (df["decimalLongitude"] == 0)
    flags["missing_year"] = df["year"].isna()

    # only check old_record when year actually exists
    flags["old_record"] = df["year"].notna() & (df["year"] < 1900)

    if "eventDate" in df.columns:
        flags["missing_date"] = df["eventDate"].isna()

    flags["duplicate"] = df.duplicated(
        subset=["species", "decimalLatitude", "decimalLongitude", "year"],
        keep=False
    )

    # has_issues is informational only
    if "issues" in df.columns:
        flags["has_issues"] = df["issues"].apply(
            lambda x: len(x) > 0 if isinstance(x, list) else False
        )

    # health score excludes has_issues
    core_flags = [c for c in flags.columns if c != "has_issues"]
    flags["any_flag"] = flags[core_flags].any(axis=1)

    return flags


def quality_summary(flags):
    total = len(flags)
    summary = {}

    for col in flags.columns:
        count = flags[col].sum()
        summary[col] = {
            "count": int(count),
            "percent": round(count / total * 100, 1) if total > 0 else 0
        }

    return summary