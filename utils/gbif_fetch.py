from pygbif import occurrences as occ
import pandas as pd
import streamlit as st
import time

SAMPLE_SPECIES = {
    "African Lion": "Panthera leo",
    "Monarch Butterfly": "Danaus plexippus",
    "African Elephant": "Loxodonta africana",
    "Bald Eagle": "Haliaeetus leucocephalus",
    "Poison Dart Frog": "Dendrobates auratus"
}

@st.cache_data(ttl=3600)
def fetch_occurrences(species_name, limit=1000):
    retries = 3

    for attempt in range(retries):
        try:
            data = occ.search(
                scientificName=species_name,
                limit=limit,
                hasCoordinate=True
            )

            results = data.get("results", [])

            if not results:
                if attempt < retries - 1:
                    time.sleep(0.5)
                    continue
                return None, 0, "No records found. Check species name spelling."

            if len(results) < 2:
                return None, 0, "Not enough records to analyse. Try a different species."

            df = pd.DataFrame(results)

            cols = [
                "species", "country", "year", "month",
                "decimalLatitude", "decimalLongitude",
                "basisOfRecord", "issues", "datasetName",
                "occurrenceID", "eventDate"
            ]

            cols = [c for c in cols if c in df.columns]
            df = df[cols]

            total = data.get("count", 0)

            return df, total, None

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5)
                continue
            return None, 0, f"GBIF API error: {str(e)}"

    return None, 0, "GBIF API not responding. Please try again."