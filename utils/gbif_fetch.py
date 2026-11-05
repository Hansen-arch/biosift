from pygbif import occurrences as occ
import pandas as pd
import requests
import streamlit as st
import time

SAMPLE_SPECIES = {
    "African Lion"      : "Panthera leo",
    "Monarch Butterfly" : "Danaus plexippus",
    "African Elephant"  : "Loxodonta africana",
    "Bald Eagle"        : "Haliaeetus leucocephalus",
    "Poison Dart Frog"  : "Dendrobates auratus"
}

COLS = [
    "species", "country", "year", "month",
    "decimalLatitude", "decimalLongitude",
    "basisOfRecord", "issues", "datasetName",
    "occurrenceID", "eventDate", "countryCode",
    "media", "coordinateUncertaintyInMeters"
]

MAX_PER_REQUEST = 300

COUNTRY_API = "https://api.gbif.org/v1/enumeration/country"

# Used only when the enumeration endpoint is unreachable, so a country
# filter never disappears silently. Deliberately short: a stale or partial
# list would be worse than a visible fallback.
COUNTRY_FALLBACK = [
    ("AR", "Argentina"), ("AU", "Australia"), ("AT", "Austria"),
    ("BE", "Belgium"), ("BR", "Brazil"), ("CA", "Canada"),
    ("CL", "Chile"), ("CN", "China"), ("CO", "Colombia"),
    ("CR", "Costa Rica"), ("DK", "Denmark"), ("EC", "Ecuador"),
    ("EG", "Egypt"), ("FI", "Finland"), ("FR", "France"),
    ("DE", "Germany"), ("GH", "Ghana"), ("GR", "Greece"),
    ("IN", "India"), ("ID", "Indonesia"), ("IE", "Ireland"),
    ("IL", "Israel"), ("IT", "Italy"), ("JP", "Japan"),
    ("KE", "Kenya"), ("MG", "Madagascar"), ("MY", "Malaysia"),
    ("MX", "Mexico"), ("MA", "Morocco"), ("NP", "Nepal"),
    ("NL", "Netherlands"), ("NZ", "New Zealand"), ("NG", "Nigeria"),
    ("NO", "Norway"), ("PE", "Peru"), ("PH", "Philippines"),
    ("PL", "Poland"), ("PT", "Portugal"), ("ZA", "South Africa"),
    ("ES", "Spain"), ("SE", "Sweden"), ("CH", "Switzerland"),
    ("TZ", "Tanzania"), ("TH", "Thailand"), ("TR", "Turkey"),
    ("UG", "Uganda"), ("GB", "United Kingdom"), ("US", "United States"),
    ("VN", "Vietnam"), ("ZW", "Zimbabwe"),
]


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_countries():
    """ISO-2 country list from GBIF, for filtering records by country.

    Returns (countries, source) where countries is a sorted list of
    {"code", "name"} dicts and source is "gbif" or "fallback". The
    fallback exists so the country filter degrades visibly rather than
    vanishing when the enumeration endpoint is down.
    """
    try:
        r = requests.get(COUNTRY_API, timeout=20)
        r.raise_for_status()
        rows = [
            {"code": c["iso2"],
             "name": (c.get("title") or c["iso2"]).strip()}
            for c in r.json()
            if c.get("iso2")
        ]
        if len(rows) > 100:
            return sorted(rows, key=lambda c: c["name"]), "gbif"
    except Exception:
        pass
    rows = [{"code": code, "name": name} for code, name in COUNTRY_FALLBACK]
    return sorted(rows, key=lambda c: c["name"]), "fallback"


def country_options(countries):
    """Label list for a selectbox, with the code in parentheses."""
    return ["All countries"] + [f"{c['name']} ({c['code']})"
                                for c in countries]


def country_code_from_label(label, countries):
    """Inverse of country_options: label -> ISO-2 code (None for All)."""
    if not label or label == "All countries":
        return None
    for c in countries:
        if label == f"{c['name']} ({c['code']})":
            return c["code"]
    return None

@st.cache_data(ttl=3600)
def fetch_occurrences(
    species_name,
    limit        = 500,
    year_from    = None,
    year_to      = None,
    country_code = None,
    basis        = None,
):
    try:
        all_results = []
        offset      = 0
        total       = None

        year_range = None
        if year_from and year_to:
            year_range = f"{year_from},{year_to}"
        elif year_from:
            year_range = f"{year_from},{year_from + 100}"
        elif year_to:
            year_range = f"1000,{year_to}"

        while len(all_results) < limit:
            batch_size = min(MAX_PER_REQUEST, limit - len(all_results))

            params = {
                "scientificName": species_name,
                "limit"         : batch_size,
                "offset"        : offset,
                "hasCoordinate" : True
            }

            if year_range:
                params["year"] = year_range
            if country_code and country_code != "All":
                params["country"] = country_code
            if basis and basis != "All":
                params["basisOfRecord"] = basis

            for attempt in range(3):
                try:
                    data = occ.search(**params)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        return None, 0, "GBIF API error. Please try again."

            results = data.get("results", [])

            if total is None:
                total = data.get("count", 0)

            if not results:
                break

            all_results.extend(results)
            offset += len(results)

            if offset >= total:
                break

        if not all_results:
            return (
                None, 0,
                "No records found. Check species name or adjust filters."
            )

        if len(all_results) < 2:
            return None, 0, "Not enough records to analyse."

        df   = pd.DataFrame(all_results)
        cols = [c for c in COLS if c in df.columns]
        df   = df[cols]

        return df, total, None

    except Exception as e:
        return None, 0, f"Error: {str(e)}"