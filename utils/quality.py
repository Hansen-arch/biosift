import pandas as pd
import numpy as np
import requests

# ── Country bounding boxes (ISO 3166-1 alpha-2) ───────────────
# Format: [lat_min, lat_max, lon_min, lon_max]
# Covers the most common countries in GBIF data
COUNTRY_BBOX = {
    "AD": [42.43, 42.65,  1.41,  1.79],
    "AE": [22.63, 26.08, 51.58, 56.38],
    "AF": [29.38, 38.49, 60.52, 74.92],
    "AG": [16.99, 17.73,-62.35,-61.67],
    "AL": [39.64, 42.66, 19.27, 21.06],
    "AM": [38.84, 41.30, 43.45, 46.63],
    "AO": [-18.02,  -4.39, 11.68, 24.08],
    "AR": [-55.06,-21.78,-73.56,-53.65],
    "AT": [46.37, 49.02, 9.53, 17.16],
    "AU": [-43.64,  -9.23,112.92,153.64],
    "AZ": [38.39, 41.91, 44.77, 50.37],
    "BA": [42.56, 45.27, 15.75, 19.62],
    "BB": [13.04, 13.34,-59.65,-59.42],
    "BD": [20.74, 26.63, 88.01, 92.67],
    "BE": [49.50, 51.51,  2.54,  6.40],
    "BF": [9.40, 15.08, -5.52,  2.40],
    "BG": [41.24, 44.22, 22.36, 28.61],
    "BH": [25.80, 26.33, 50.45, 50.82],
    "BI": [-4.47, -2.31, 28.99, 30.85],
    "BJ": [6.22, 12.41,  0.77,  3.84],
    "BN": [4.00,  5.07,114.08,115.36],
    "BO": [-22.90,-9.68,-69.64,-57.45],
    "BR": [-33.75,  5.27,-73.99,-34.73],
    "BS": [20.91, 27.26,-80.57,-72.71],
    "BT": [26.70, 28.32, 88.75, 92.13],
    "BW": [-26.91,-17.78, 19.99, 29.38],
    "BY": [51.26, 56.17, 23.18, 32.78],
    "BZ": [15.89, 18.49,-89.23,-87.77],
    "CA": [41.68, 83.11,-141.00,-52.62],
    "CD": [-13.45,  5.39, 12.21, 31.31],
    "CF": [ 2.22, 11.00, 14.42, 27.46],
    "CG": [-5.10,  3.70, 11.15, 18.65],
    "CH": [45.82, 47.81,  5.96, 10.49],
    "CI": [ 4.34, 10.74, -8.60,  -2.49],
    "CL": [-55.98,-17.50,-75.64,-66.42],
    "CM": [ 1.65, 13.08,  8.50, 16.19],
    "CN": [18.16, 53.56, 73.50,134.77],
    "CO": [-4.23, 13.39,-81.73,-66.87],
    "CR": [ 5.50, 11.22,-85.95,-82.56],
    "CU": [19.82, 23.27,-84.97,-74.13],
    "CV": [14.81, 17.21,-25.36,-22.66],
    "CY": [34.63, 35.71, 32.27, 34.60],
    "CZ": [48.55, 51.06, 12.09, 18.86],
    "DE": [47.27, 55.06,  5.87, 15.04],
    "DJ": [10.93, 12.71, 41.77, 43.42],
    "DK": [54.56, 57.75,  8.07, 15.19],
    "DM": [15.21, 15.63,-61.48,-61.25],
    "DO": [17.47, 19.93,-72.00,-68.32],
    "DZ": [18.97, 37.09, -8.67,  11.99],
    "EC": [-5.01,  1.68,-81.00,-75.19],
    "EE": [57.51, 59.68, 21.84, 28.21],
    "EG": [22.00, 31.67, 24.70, 36.90],
    "ER": [12.36, 18.00, 36.44, 43.14],
    "ES": [27.64, 43.79,-18.16,  4.33],
    "ET": [ 3.40, 15.00, 33.00, 47.99],
    "FI": [59.81, 70.09, 19.08, 31.59],
    "FJ": [-20.68,-12.48,177.29,180.00],
    "FR": [41.33, 51.12, -5.14, 9.56],
    "GA": [-3.98,  2.32,  8.70, 14.51],
    "GB": [49.86, 60.86,-8.65,  1.77],
    "GD": [11.99, 12.31,-61.80,-61.60],
    "GE": [41.06, 43.59, 40.01, 46.72],
    "GH": [ 4.74, 11.17, -3.26,  1.20],
    "GM": [13.07, 13.83,-16.82,-13.80],
    "GN": [ 7.19, 12.68,-15.08, -7.64],
    "GQ": [ 0.92,  3.79,  8.44, 11.33],
    "GR": [34.80, 41.75, 19.37, 29.65],
    "GT": [13.74, 17.82,-92.23,-88.23],
    "GW": [10.93, 12.69,-16.71,-13.64],
    "GY": [ 1.18,  8.56,-61.39,-56.48],
    "HN": [12.98, 16.52,-89.35,-83.15],
    "HR": [42.39, 46.56, 13.49, 19.44],
    "HT": [18.02, 20.09,-74.48,-71.62],
    "HU": [45.74, 48.59, 16.11, 22.90],
    "ID": [-11.00,  5.90, 95.00,141.02],
    "IE": [51.43, 55.39,-10.47, -5.99],
    "IL": [29.49, 33.34, 34.27, 35.90],
    "IN": [ 6.75, 37.09, 68.16, 97.40],
    "IQ": [29.06, 37.38, 38.80, 48.57],
    "IR": [25.06, 39.78, 44.05, 63.32],
    "IS": [63.29, 66.56,-24.55,-13.50],
    "IT": [35.49, 47.09,  6.63, 18.52],
    "JM": [17.70, 18.53,-78.37,-76.19],
    "JO": [29.19, 33.37, 34.96, 39.30],
    "JP": [24.04, 45.52,122.93,153.99],
    "KE": [-4.68,  4.62, 33.91, 41.90],
    "KG": [39.18, 43.26, 69.26, 80.28],
    "KH": [10.41, 14.69,102.34,107.63],
    "KI": [-11.44,  4.72,-174.53,176.45],
    "KM": [-12.44,-11.36, 43.22, 44.55],
    "KN": [17.10, 17.42,-62.87,-62.56],
    "KP": [37.67, 42.99,124.19,130.69],
    "KR": [33.10, 38.62,124.61,129.58],
    "KW": [28.52, 30.09, 46.55, 48.43],
    "KZ": [40.57, 55.46, 50.27, 87.35],
    "LA": [13.91, 22.50, 99.90,107.64],
    "LB": [33.06, 34.69, 35.10, 36.62],
    "LC": [13.70, 14.11,-61.08,-60.88],
    "LI": [47.05, 47.27,  9.47,  9.64],
    "LK": [ 5.92,  9.84, 79.70, 81.88],
    "LR": [ 4.35,  8.55,-11.49, -7.37],
    "LS": [-30.68,-28.57, 27.01, 29.46],
    "LT": [53.90, 56.45, 20.94, 26.84],
    "LU": [49.44, 50.18,  5.74,  6.53],
    "LV": [55.67, 57.97, 20.97, 28.24],
    "LY": [19.50, 33.17,  9.32, 25.15],
    "MA": [27.66, 35.93,-13.17,  1.14],
    "MC": [43.72, 43.77,  7.41,  7.44],
    "MD": [45.47, 48.49, 26.62, 30.13],
    "ME": [41.85, 43.52, 18.45, 20.36],
    "MG": [-25.60, -11.95, 43.22, 50.48],
    "MK": [40.85, 42.36, 20.45, 22.97],
    "ML": [10.15, 25.00,-12.24,  4.24],
    "MM": [9.78, 28.54, 92.19,101.17],
    "MN": [41.59, 52.15, 87.76,119.93],
    "MR": [14.72, 27.31,-17.07,  16.21],
    "MT": [35.81, 36.08, 14.18, 14.57],
    "MU": [-20.52,-19.98, 57.31, 57.79],
    "MV": [-0.70,  7.10, 72.72, 73.76],
    "MW": [-17.13,-9.37, 32.67, 35.92],
    "MX": [14.55, 32.72,-117.13,-86.74],
    "MY": [-4.64,  7.37,  99.64,119.27],
    "MZ": [-26.87,-10.47, 30.22, 40.84],
    "NA": [-29.04,-16.96, 11.72, 25.26],
    "NE": [11.69, 23.52,  0.17, 15.96],
    "NG": [ 4.28, 13.89,  2.69, 14.68],
    "NI": [10.71, 15.03,-87.69,-82.59],
    "NL": [50.75, 53.69,  3.31,  7.23],
    "NO": [57.96, 71.19,  4.50, 31.10],
    "NP": [26.37, 30.45, 80.06, 88.20],
    "NR": [-0.55, -0.50,166.91,166.96],
    "NZ": [-52.62,-29.23,165.87,178.55],
    "OM": [16.64, 26.40, 51.99, 59.84],
    "PA": [ 7.21, 9.64,-83.06,-77.18],
    "PE": [-18.35, -0.02,-81.33,-68.68],
    "PG": [-10.71,  -0.87,140.84,155.97],
    "PH": [ 4.64, 21.12,116.93,126.60],
    "PK": [23.69, 37.10, 60.87, 77.84],
    "PL": [49.00, 54.84, 14.12, 24.15],
    "PT": [30.03, 42.15,-31.27, -6.19],
    "PW": [2.95,  8.10,131.10,134.73],
    "PY": [-27.59,-19.29,-62.64,-54.29],
    "QA": [24.56, 26.15, 50.75, 51.61],
    "RO": [43.62, 48.27, 20.26, 29.70],
    "RS": [42.23, 46.18, 18.84, 22.99],
    "RU": [41.19, 82.04, 19.64,191.00],
    "RW": [-2.84, -1.05, 28.86, 30.90],
    "SA": [16.38, 32.16, 36.48, 55.67],
    "SB": [-11.86, -6.59,155.56,162.40],
    "SC": [-9.76, -4.28, 55.22, 56.30],
    "SD": [ 8.68, 22.23, 21.82, 38.58],
    "SE": [55.34, 69.06, 10.96, 24.17],
    "SG": [ 1.17,  1.47,103.60,104.09],
    "SI": [45.43, 46.88, 13.38, 16.61],
    "SK": [47.73, 49.62, 16.83, 22.56],
    "SL": [ 6.93,  9.99,-13.31, -10.27],
    "SM": [43.89, 44.01, 12.40, 12.51],
    "SN": [12.31, 16.69,-17.53,-11.36],
    "SO": [-1.68, 11.98, 40.98, 51.41],
    "SR": [ 1.84,  6.00,-58.08,-53.99],
    "SS": [ 3.49, 12.24, 23.44, 36.87],
    "ST": [-0.03,  1.70,  6.46,  7.46],
    "SV": [13.15, 14.45,-90.13,-87.71],
    "SY": [32.31, 37.32, 35.73, 42.38],
    "SZ": [-27.32,-25.72, 30.79, 32.14],
    "TD": [ 7.44, 23.45, 13.47, 24.00],
    "TG": [ 5.92, 11.14, -0.14,  1.81],
    "TH": [ 5.61, 20.46, 97.34,105.64],
    "TJ": [36.67, 41.04, 67.34, 75.15],
    "TL": [-9.50, -8.13,124.04,127.33],
    "TM": [35.14, 42.80, 52.44, 66.69],
    "TN": [30.24, 37.54,  7.52, 11.59],
    "TO": [-22.34,-15.55,-176.21,-173.74],
    "TR": [35.81, 42.11, 25.67, 44.83],
    "TT": [10.04, 11.35,-61.92,-60.53],
    "TV": [-9.00, -5.64,176.06,179.88],
    "TZ": [-11.75, -0.99, 29.34, 40.45],
    "UA": [44.39, 52.38, 22.14, 40.23],
    "UG": [-1.48,  4.23, 29.57, 35.00],
    "US": [18.91, 71.39,-179.15,-66.97],
    "UY": [-34.98,-30.08,-58.44,-53.09],
    "UZ": [37.18, 45.59, 55.99, 73.14],
    "VA": [41.90, 41.91, 12.44, 12.46],
    "VC": [12.58, 13.38,-61.46,-61.12],
    "VE": [ 0.65, 12.20,-73.35,-59.81],
    "VN": [ 8.56, 23.39,102.14,109.46],
    "VU": [-20.26,-13.07,166.52,170.24],
    "WS": [-14.07,-13.44,-172.81,-171.43],
    "YE": [12.11, 19.00, 42.55, 53.11],
    "ZA": [-34.82,-22.12, 16.46, 32.89],
    "ZM": [-18.08, -8.22, 21.97, 33.71],
    "ZW": [-22.42,-15.61, 25.24, 33.06],
}


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
        else:
            flags["missing_date"] = False
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
        flags["country_mismatch"] = _check_country_mismatch(df)
    except Exception:
        flags["country_mismatch"] = False

    try:
        if "issues" in df.columns:
            flags["has_issues"] = df["issues"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )
        else:
            flags["has_issues"] = False
    except Exception:
        flags["has_issues"] = False

    core_flags = [
        c for c in flags.columns
        if c not in ("has_issues",)
    ]
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


def _check_country_mismatch(df):
    """
    Flag records where coordinates fall clearly outside the stated
    country's bounding box.
    Only checks records that have both coordinates AND a countryCode.
    Uses approximate bounding boxes — not exact boundaries.
    """
    result = pd.Series(False, index=df.index)

    has_cc   = "countryCode" in df.columns
    has_lat  = "decimalLatitude"  in df.columns
    has_lon  = "decimalLongitude" in df.columns

    if not (has_cc and has_lat and has_lon):
        return result

    for idx, row in df.iterrows():
        try:
            cc  = row.get("countryCode", None)
            lat = row.get("decimalLatitude",  None)
            lon = row.get("decimalLongitude", None)

            if pd.isna(lat) or pd.isna(lon) or not cc:
                continue

            cc = str(cc).strip().upper()
            if cc not in COUNTRY_BBOX:
                continue

            lat_min, lat_max, lon_min, lon_max = COUNTRY_BBOX[cc]

            # add a 1-degree tolerance buffer
            buffer = 1.0
            outside = (
                float(lat) < lat_min - buffer or
                float(lat) > lat_max + buffer or
                float(lon) < lon_min - buffer or
                float(lon) > lon_max + buffer
            )

            if outside:
                result.at[idx] = True

        except Exception:
            continue

    return result


def quality_summary(flags):
    total   = len(flags)
    summary = {}

    for col in flags.columns:
        try:
            count = flags[col].sum()
            summary[col] = {
                "count"  : int(count),
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

        df = df.dropna(
            subset=["decimalLatitude", "decimalLongitude"]
        )
        lat_prec = df["decimalLatitude"].apply(count_decimals)

        bins = {
            "Very Low (0-1 decimal, ~10km)": int((lat_prec <= 1).sum()),
            "Low (2 decimals, ~1km)"        : int((lat_prec == 2).sum()),
            "Medium (3 decimals, ~100m)"    : int((lat_prec == 3).sum()),
            "High (4 decimals, ~10m)"       : int((lat_prec == 4).sum()),
            "Very High (5+ decimals, ~1m)"  : int((lat_prec >= 5).sum()),
        }
        return bins
    except Exception:
        return {}


def get_completeness_score(df):
    """
    Score each record on how many important fields are filled.
    Returns aggregate stats and per-record series.

    Fields scored (1 point each):
      species, decimalLatitude, decimalLongitude, year,
      month, eventDate, basisOfRecord, country,
      datasetName, occurrenceID
    """
    FIELDS = [
        "species", "decimalLatitude", "decimalLongitude",
        "year", "month", "eventDate", "basisOfRecord",
        "country", "datasetName", "occurrenceID"
    ]

    try:
        scores = pd.Series(0.0, index=df.index)
        total_fields = len(FIELDS)

        for field in FIELDS:
            if field in df.columns:
                filled = df[field].notna() & (df[field] != "")
                scores += filled.astype(float)

        pct_scores = (scores / total_fields * 100).round(1)

        avg_score  = round(pct_scores.mean(), 1)
        full_count = int((pct_scores == 100).sum())
        high_count = int((pct_scores >= 80).sum())
        low_count  = int((pct_scores <  50).sum())

        field_fill = {}
        for field in FIELDS:
            if field in df.columns:
                filled = df[field].notna() & (df[field] != "")
                field_fill[field] = round(filled.mean() * 100, 1)
            else:
                field_fill[field] = 0.0

        return {
            "avg_score"   : avg_score,
            "per_record"  : pct_scores,
            "full_count"  : full_count,
            "high_count"  : high_count,
            "low_count"   : low_count,
            "field_fill"  : field_fill,
            "total_fields": total_fields
        }

    except Exception:
        return None


def get_multimedia_stats(df):
    """
    Check multimedia quality of GBIF occurrence records.
    Returns stats on missing media, broken URLs and overall coverage.
    """
    try:
        total = len(df)

        if "media" not in df.columns:
            return {
                "has_media_field": False,
                "missing_media"  : total,
                "missing_pct"    : 100.0,
                "has_media"      : 0,
                "coverage_pct"   : 0.0,
                "broken_urls"    : 0,
                "broken_pct"     : 0.0,
                "sample_checked" : 0
            }

        def has_media(x):
            if isinstance(x, list):
                return len(x) > 0
            return False

        media_mask      = df["media"].apply(has_media)
        has_media_count = int(media_mask.sum())
        missing_media   = total - has_media_count
        coverage_pct    = round(
            has_media_count / total * 100, 1
        ) if total > 0 else 0
        missing_pct     = round(
            missing_media / total * 100, 1
        ) if total > 0 else 0

        image_urls = []
        for media_list in df.loc[media_mask, "media"]:
            if isinstance(media_list, list):
                for item in media_list:
                    if isinstance(item, dict):
                        url = item.get("identifier", "")
                        if url and url.startswith("http"):
                            image_urls.append(url)

        sample_size    = min(20, len(image_urls))
        broken_count   = 0
        sample_checked = 0

        if image_urls and sample_size > 0:
            import random
            sampled = random.sample(image_urls, sample_size)
            for url in sampled:
                try:
                    r = requests.head(url, timeout=5, allow_redirects=True)
                    if r.status_code >= 400:
                        broken_count += 1
                    sample_checked += 1
                except Exception:
                    broken_count  += 1
                    sample_checked += 1

        broken_pct = round(
            broken_count / sample_checked * 100, 1
        ) if sample_checked > 0 else 0.0

        return {
            "has_media_field": True,
            "missing_media"  : missing_media,
            "missing_pct"    : missing_pct,
            "has_media"      : has_media_count,
            "coverage_pct"   : coverage_pct,
            "broken_urls"    : broken_count,
            "broken_pct"     : broken_pct,
            "sample_checked" : sample_checked
        }

    except Exception:
        return None