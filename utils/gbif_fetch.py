from pygbif import occurrences as occ
import pandas as pd
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
    "occurrenceID", "eventDate", "countryCode"
]

MAX_PER_REQUEST = 300

@st.cache_data(ttl=3600)
def fetch_occurrences(
    species_name,
    limit        = 500,
    year_from    = None,
    year_to      = None,
    country_code = None,
    basis        = None
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
            return None, 0, "No records found. Check species name or adjust filters."

        if len(all_results) < 2:
            return None, 0, "Not enough records to analyse."

        df   = pd.DataFrame(all_results)
        cols = [c for c in COLS if c in df.columns]
        df   = df[cols]

        return df, total, None

    except Exception as e:
        return None, 0, f"Error: {str(e)}"