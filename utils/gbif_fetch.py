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
    "occurrenceID", "eventDate"
]

MAX_PER_REQUEST = 300

@st.cache_data(ttl=3600)
def fetch_occurrences(species_name, limit=300):
    try:
        all_results = []
        offset      = 0
        total       = None

        while len(all_results) < limit:
            batch_size = min(MAX_PER_REQUEST, limit - len(all_results))

            for attempt in range(3):
                try:
                    data = occ.search(
                        scientificName = species_name,
                        limit          = batch_size,
                        offset         = offset,
                        hasCoordinate  = True
                    )
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

            # stop if we've fetched everything available
            if offset >= total:
                break

        if not all_results:
            return None, 0, "No records found. Check species name spelling."

        if len(all_results) < 2:
            return None, 0, "Not enough records to analyse."

        df   = pd.DataFrame(all_results)
        cols = [c for c in COLS if c in df.columns]
        df   = df[cols]

        return df, total, None

    except Exception as e:
        return None, 0, f"Error: {str(e)}"