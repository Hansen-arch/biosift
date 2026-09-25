"""
Species interactions via GloBI
──────────────────────────────
Global Biotic Interactions (GloBI, Poelen et al. 2014, Ecological
Informatics) aggregates openly-licensed species-interaction data —
predator–prey, pollinator–plant, parasite–host, pathogen–host, symbionts.

GBIF's 2026 Work Programme explicitly names species interactions as a
priority data area; no quality dashboard surfaces them. This module is
the client used by BioSift's Interactions tab.
"""

import requests
import streamlit as st

GLOBI = "https://api.globalbioticinteractions.org"

# interactionType -> display label (GloBI uses OBO relationship vocab)
INTERACTION_LABELS = {
    "preysOn":            "Preys on",
    "preyedUponBy":       "Preyed upon by",
    "eats":               "Eats",
    "eatenBy":            "Eaten by",
    "pollinates":         "Pollinates",
    "pollinatedBy":       "Pollinated by",
    "parasiteOf":         "Parasite of",
    "hasParasite":        "Parasite of host",  # GloBI: hasParasite -> host of
    "hostOf":             "Host of",
    "hasHost":            "Host of parasite",
    "pathogenOf":         "Pathogen of",
    "hasPathogen":        "Pathogen of host",
    "symbiontOf":         "Symbiont of",
    "mutualistOf":        "Mutualist of",
    "commensalistOf":     "Commensal of",
    "kills":              "Kills",
    "kleptoparasiteOf":   "Kleptoparasite of",
    "dispersalVectorOf":  "Dispersal vector of",
    "endoparasiteOf":     "Endoparasite of",
    "ectoparasiteOf":     "Ectoparasite of",
}


# inverse relationship map for normalising direction
INVERSE = {
    "preysOn": "preyedUponBy", "eats": "eatenBy",
    "preyedUponBy": "preysOn", "eatenBy": "eats",
    "pollinates": "pollinatedBy", "pollinatedBy": "pollinates",
    "parasiteOf": "hasParasite", "hasParasite": "parasiteOf",
    "hostOf": "hasHost", "hasHost": "hostOf",
    "pathogenOf": "hasPathogen", "hasPathogen": "pathogenOf",
    "kills": "killedBy",
    "kleptoparasiteOf": "hasKleptoparasite",
}


@st.cache_data(ttl=86400, show_spinner=False)
def _valid_taxon_name(name):
    """
    GloBI contains name-resolution artefacts where taxon fields hold full
    citations, DOIs or URLs (external_id 'no:match'). Reject anything that
    is not plausibly a taxon/common name. Cached; returns bool.
    """
    if not name:
        return False
    name = name.strip()
    if not name or len(name) > 60:
        return False
    low = name.lower()
    if any(tok in low for tok in (
            "http", "doi", ".org", ".com", ".pdf", "accessed")):
        return False
    if "(" in name or ")" in name or "&" in name:
        return False
    if "," in name or name.count(".") > 1:
        return False
    if any(ch.isdigit() for ch in name):
        return False
    if name.isupper() and len(name) > 4:
        return False  # dataset artefact tokens (e.g. 'ABOLISHED')
    return True


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_interactions(scientific_name):
    """
    Query GloBI for all recorded interactions of a species using the
    directional taxon parameters (sourceTaxon= / targetTaxon=), which
    return resolved, semantically-typed records — unlike the fuzzy q=
    search, which is polluted with unresolved citation artefacts.

    Direction is normalised so the analysed species is the subject.
    Returns list of dicts: {type, label, other, source, citation, url}
    """
    combined = []
    for param, inverted in (("sourceTaxon", False), ("targetTaxon", True)):
        try:
            r = requests.get(
                f"{GLOBI}/interaction",
                params={
                    param: scientific_name,
                    "type": "json.v2",
                    "limit": 300,
                },
                timeout=20,
            )
            data = r.json()
        except Exception:
            continue

        for item in data if isinstance(data, list) else []:
            try:
                itype = item.get("interaction_type") or ""
                source_taxon = (item.get("source_taxon_name") or "").strip()
                target_taxon = (item.get("target_taxon_name") or "").strip()
                if not itype:
                    continue
                if not (_valid_taxon_name(source_taxon)
                        and _valid_taxon_name(target_taxon)):
                    continue

                if inverted:
                    # query species is the TARGET -> invert relationship
                    other = source_taxon
                    direction = INVERSE.get(itype, "interactsWith")
                else:
                    other = target_taxon
                    direction = itype

                if not other or other.lower() == scientific_name.lower():
                    continue
                combined.append({
                    "_dir": direction,
                    "_other": other,
                    "_src": item.get("study_url") or "",
                    "_cite": (
                        item.get("study_citation")
                        or item.get("reference_citation") or ""
                    ),
                })
            except Exception:
                continue

    # dedup on (direction, partner)
    rows, seen = [], set()
    for c in combined:
        key = (c["_dir"], c["_other"].lower())
        if key in seen:
            continue
        seen.add(key)
        d = c["_dir"]
        rows.append({
            "type": d,
            "label": INTERACTION_LABELS.get(
                d,
                "Interacts with" if d == "interactsWith"
                else d.replace("has", "has "),
            ),
            "other": c["_other"],
            "source": c["_src"],
            "citation": c["_cite"],
            "url": c["_src"],
        })
    return rows


def summarize_interactions(interactions):
    """
    Aggregate raw interaction rows into summary structures.
    Returns (by_type, partners):
      by_type:  [{label, count}] sorted desc
      partners: [{partner, kinds}] sorted by partner
    """
    by_type, partners = {}, {}
    for row in interactions:
        label = row.get("label") or row.get("type") or "interaction"
        by_type[label] = by_type.get(label, 0) + 1
        partner = row.get("other") or "Unknown"
        entry = partners.setdefault(partner, set())
        entry.add(label)
    type_rows = sorted(
        [{"label": k, "count": v} for k, v in by_type.items()],
        key=lambda x: -x["count"],
    )
    partner_rows = sorted(
        [{"partner": k, "kinds": ", ".join(sorted(v))}
         for k, v in partners.items()],
        key=lambda x: x["partner"],
    )
    return type_rows, partner_rows
