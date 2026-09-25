"""
Ecological co-occurrence
────────────────────────
Ecological communities, not pairwise trophic lists: for a target species,
we fetch the genus-level assemblage from GBIF (all congeneric records in
the same filtered window), then quantify shared geography with a 1°-grid
Jaccard overlap — a standard presence/absence similarity index
(Jaccard 1901; Real & Vargas 1996 for its use in biogeography).

High overlap with a congener flags: shared habitat use, sampling
co-detection, or genuine ecological association. Low-overlap congeners
distinguish allopatric relatives. This is *observed* community structure
from GBIF itself — not inferred network guesses.
"""

import requests
import streamlit as st
import pandas as pd
import numpy as np

GBIF = "https://api.gbif.org/v1/occurrence/search"


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_genus_assemblage(genus, limit=1200, year_from=None,
                           year_to=None):
    """
    Fetch occurrence counts per species within the genus (excluding the
    target species itself is done by the caller), paginating the GBIF
    species-facet. Returns DataFrame [species, records].
    """
    params = {
        "genus": genus,
        "limit": 0,
        "facet": "species",
        "facetLimit": min(limit, 1000),
    }
    if year_from and year_to:
        params["year"] = f"{year_from},{year_to}"
    try:
        r = requests.get(GBIF, params=params, timeout=30)
        data = r.json()
        facets = data.get("facets", [])
        counts = facets[0].get("counts", []) if facets else []
        rows = [
            {"species": b["name"], "records": int(b["count"])}
            for b in counts if b.get("name")
        ]
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["species", "records"])


def grid_presence(df, grid=1.0):
    """Set of 'lat,lon' cell keys for a DataFrame with lat/lon columns."""
    if df is None or len(df) == 0:
        return set()
    lat = pd.to_numeric(df["decimalLatitude"], errors="coerce")
    lon = pd.to_numeric(df["decimalLongitude"], errors="coerce")
    ok = lat.notna() & lon.notna()
    if not ok.any():
        return set()
    la = np.floor(lat[ok] / grid).astype(int)
    lo = np.floor(lon[ok] / grid).astype(int)
    return set(zip(la, lo))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 3) if union else 0.0


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_species_grids(species_list, limit=300):
    """
    Fetch a small coordinate sample per species for grid overlap.
    Returns {species: set_of_cells}.
    """
    out = {}
    for sp in species_list:
        try:
            r = requests.get(
                GBIF,
                params={
                    "scientificName": sp, "limit": min(limit, 300),
                    "hasCoordinate": "true",
                },
                timeout=20,
            )
            results = r.json().get("results", [])
            df = pd.DataFrame([
                {"decimalLatitude": x.get("decimalLatitude"),
                 "decimalLongitude": x.get("decimalLongitude")}
                for x in results
            ])
            out[sp] = grid_presence(df)
        except Exception:
            out[sp] = set()
    return out


def build_cooccurrence(target_species, target_df, genus_df, max_partners=8):
    """
    Compose the co-occurrence analysis.
    Returns dict: {genus, assemblage_size, congeners: [..], partners: [..]}
      partners: [{species, records, overlap, cells, jaccard_label}]
    """
    target_cells = grid_presence(target_df)

    congeners = genus_df[
        genus_df["species"].str.lower() != target_species.lower()
    ].sort_values("records", ascending=False)

    top = congeners.head(max_partners)
    grids = fetch_species_grids(list(top["species"]))

    partners = []
    for _, row in top.iterrows():
        sp = row["species"]
        cells = grids.get(sp, set())
        jac = jaccard(target_cells, cells)
        partners.append({
            "species": sp,
            "records": int(row["records"]),
            "cells": len(cells),
            "overlap": jac,
            "jaccard_label": (
                "high" if jac >= 0.4 else
                "moderate" if jac >= 0.15 else "low"
            ),
        })

    partners.sort(key=lambda x: -x["overlap"])
    return {
        "genus": target_species.split()[0] if target_species else "",
        "assemblage_size": int(genus_df["species"].nunique())
        if not genus_df.empty else 0,
        "target_cells": len(target_cells),
        "partners": partners,
    }


COO_CITATION = (
    "Jaccard, P. (1901). Étude comparative de la distribution florale "
    "dans une portion des Alpes et du Jura. Bulletin de la Société "
    "Vaudoise des Sciences Naturelles, 37, 547–579. · Real, R. & Vargas, "
    "J.M. (1996). The probabilistic basis of Jaccard's index of "
    "similarity. Systematic Biology, 45, 380–385."
)
