import requests
import streamlit as st

GBIF_API = "https://api.gbif.org/v1"

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
            "gbif_url"       : f"https://www.gbif.org/species/{key}"
        }

    except Exception:
        return None