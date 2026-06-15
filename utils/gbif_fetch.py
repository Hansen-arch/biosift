from pygbif import occurrences as occ
import pandas as pd

SAMPLE_SPECIES = {
    "🦁 African Lion": "Panthera leo",
    "🦋 Monarch Butterfly": "Danaus plexippus",
    "🐘 African Elephant": "Loxodonta africana",
    "🦅 Bald Eagle": "Haliaeetus leucocephalus",
    "🐸 Poison Dart Frog": "Dendrobates auratus"
}

def fetch_occurrences(species_name, limit=1000):
    data = occ.search(
        scientificName=species_name,
        limit=limit,
        hasCoordinate=True
    )

    results = data.get("results", [])

    if not results:
        return None, 0

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

    return df, total