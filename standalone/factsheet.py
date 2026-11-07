"""Species factsheet, the identity block an analysis should open with.

A species page in any reference resource (GBIF, NatureServe, iNaturalist,
a TDWG Species Profile Model implementation) answers *what is this
taxon* before it answers *where is it*: hierarchy, authorship, accepted
name history, vernacular names, habitat statements, threat status.

Everything here is key-free GBIF, fetched in parallel and cached.
Failures degrade per block: a missing synonym list never blanks the
taxonomy table.
"""
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st

GBIF = "https://api.gbif.org/v1"

RANK_ORDER = ["kingdom", "phylum", "class", "order", "family",
              "genus", "species"]


def _get(url, params=None, timeout=12):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def species_factsheet(scientific_name: str) -> dict:
    m = _get(f"{GBIF}/species/match",
             {"name": scientific_name, "strict": "false"})
    if not m or m.get("matchType") == "NONE":
        return {"available": False,
                "reason": "no match in the GBIF backbone"}

    key = m.get("usageKey") or m.get("speciesKey")
    if not key:
        return {"available": False, "reason": "no taxon key"}

    with ThreadPoolExecutor(max_workers=4) as ex:
        f_core = ex.submit(_get, f"{GBIF}/species/{key}")
        f_syn = ex.submit(_get, f"{GBIF}/species/{key}/synonyms",
                          {"limit": 100})
        f_vern = ex.submit(_get, f"{GBIF}/species/{key}/vernacularNames",
                           {"limit": 200})
        f_prof = ex.submit(_get, f"{GBIF}/species/{key}/speciesProfiles",
                           {"limit": 100})
        core = f_core.result() or {}
        syn = (f_syn.result() or {}).get("results", []) or []
        vern = (f_vern.result() or {}).get("results", []) or []
        prof = (f_prof.result() or {}).get("results", []) or []

    taxonomy = []
    for rank in RANK_ORDER:
        val = core.get(rank)
        if val:
            taxonomy.append({"rank": rank, "name": val})

    syn_names = []
    for s in syn:
        nm = s.get("canonicalName") or s.get("scientificName")
        if nm and nm not in syn_names:
            syn_names.append(nm)

    eng, other = [], []
    for v in vern:
        nm = v.get("vernacularName")
        if not nm:
            continue
        if v.get("language") == "eng":
            if nm not in eng:
                eng.append(nm)
        elif nm not in other:
            other.append(nm)

    habitats, threats, living = [], [], []
    for p in prof:
        h = p.get("habitat")
        if h and h not in habitats:
            habitats.append(h)
        t = p.get("threatStatus")
        if t and t not in threats:
            threats.append(t)
        lp = p.get("livingPeriod")
        if lp and lp not in living:
            living.append(lp)

    extinct = any(bool(p.get("extinct")) for p in prof)
    dataset_key = core.get("datasetKey")
    dataset_title = None
    if dataset_key:
        ds = _get(f"{GBIF}/dataset/{dataset_key}")
        if ds:
            dataset_title = ds.get("title")

    return {
        "available": True,
        "key": key,
        "canonical": core.get("canonicalName") or scientific_name,
        "scientific_name": core.get("scientificName") or scientific_name,
        "authorship": core.get("authorship") or "",
        "rank": core.get("rank") or "",
        "taxonomic_status": core.get("taxonomicStatus") or "",
        "basionym": core.get("basionym") or "",
        "taxonomy": taxonomy,
        "iucn": core.get("iucnRedListCategory") or "",
        "synonyms_total": len(syn_names),
        "synonyms": syn_names[:8],
        "common_names": eng[:6],
        "common_names_other": other[:4],
        "habitats": habitats[:6],
        "threat_status": threats[:4],
        "living_period": living[:1],
        "extinct": extinct,
        "source_dataset": dataset_title,
        "gbif_url": f"https://www.gbif.org/species/{key}",
        "match_type": m.get("matchType"),
        "confidence": m.get("confidence"),
    }
