import requests
import streamlit as st

GBIF_API = "https://api.gbif.org/v1"

# IUCN categories as returned by GBIF -> short code + display colour
IUCN_MAP = {
    "EXTINCT":              ("EX", "#000000"),
    "EXTINCT_IN_THE_WILD":  ("EW", "#4E4A45"),
    "CRITICALLY_ENDANGERED": ("CR", "#AC1C0F"),
    "ENDANGERED":           ("EN", "#D0342C"),
    "VULNERABLE":           ("VU", "#E97326"),
    "NEAR_THREATENED":      ("NT", "#CD9A1D"),
    "LEAST_CONCERN":        ("LC", "#2FC259"),
    "DATA_DEFICIENT":       ("DD", "#8A97A8"),
    "NOT_EVALUATED":        ("NE", "#5C6879"),
    "NOT_APPLICABLE":       ("NA", "#5C6879"),
}


def iucn_chip(raw_category):
    """Return (code, colour, tooltip) for a GBIF iucnRedListCategory string."""
    if not raw_category:
        return None
    key = str(raw_category).upper().replace("-", "_").replace(" ", "_")
    if key in IUCN_MAP:
        code, colour = IUCN_MAP[key]
        return code, colour, raw_category.replace("_", " ").title()
    return None


@st.cache_data(ttl=3600)
def get_species_info(scientific_name):
    try:
        url    = f"{GBIF_API}/species/match"
        params = {"name": scientific_name, "verbose": True}
        r      = requests.get(url, params=params, timeout=10)
        data   = r.json()

        if data.get("matchType") == "NONE":
            return None

        key = data.get("usageKey") or data.get("speciesKey")
        if not key:
            return None

        r2   = requests.get(f"{GBIF_API}/species/{key}", timeout=10)
        info = r2.json()

        r3       = requests.get(
            f"{GBIF_API}/species/{key}/vernacularNames",
            params={"limit": 10},
            timeout=10
        )
        vern     = r3.json()
        vern_res = vern.get("results", [])

        common_names = []
        for v in vern_res:
            lang = v.get("language", "")
            name = v.get("vernacularName", "")
            if name and lang == "eng":
                common_names.append(name)
            elif name and not common_names:
                common_names.append(name)

        r4     = requests.get(
            f"{GBIF_API}/occurrence/search",
            params={
                "scientificName": scientific_name,
                "mediaType"     : "StillImage",
                "limit"         : 5
            },
            timeout=10
        )
        occ_data  = r4.json()
        image_url = None

        for occ in occ_data.get("results", []):
            media = occ.get("media", [])
            for m in media:
                if m.get("type") == "StillImage" and m.get("identifier"):
                    image_url = m.get("identifier")
                    break
            if image_url:
                break

        return {
            "key"            : key,
            "scientific_name": info.get("canonicalName", scientific_name),
            "kingdom"        : info.get("kingdom",  ""),
            "phylum"         : info.get("phylum",   ""),
            "class_"         : info.get("class",    ""),
            "order"          : info.get("order",    ""),
            "family"         : info.get("family",   ""),
            "genus"          : info.get("genus",    ""),
            "species"        : info.get("species",  scientific_name),
            "rank"           : info.get("rank",     ""),
            "status"         : info.get("taxonomicStatus", ""),
            "common_names"   : list(dict.fromkeys(common_names))[:3],
            "image_url"      : image_url,
            "iucn"           : info.get("iucnRedListCategory", ""),
            "gbif_url"       : f"https://www.gbif.org/species/{key}"
        }

    except Exception:
        return None
