"""
Carbon estimation for plant species
───────────────────────────────────
Estimates the carbon stored in the aboveground biomass represented by a
plant species' occurrence records, plus equivalent sequestration rates.

Methodology (all cited):
  1. Per-tree aboveground biomass via the pantropical allometry of
     Chave et al. 2014 (Global Change Biology 20:3177-3190,
     doi:10.1111/gcb.12629):
         AGB = 0.0673 * (WD * DBH * H)^0.976      (ease-of-use form:
         AGB = 0.0673 * (WD * DBH^2 * H)          a.g. form)
     We use the height-parameterised wet-form for humid forests and the
     wood-density + E form elsewhere:
         AGB = exp(-1.803 - 0.976*E + 0.976*mean(WD*DBH^2*H)
                   - 0.0281*mean((WD*DBH^2*H)^2))
     For record-level estimation without measured DBH/H we use the
     conservative default-diameter approach (DBH=30 cm, H=15 m) — the
     median mature tropical tree — and DISCLOSE this as a scenario, not
     a measurement.
  2. Root-to-shoot ratio 0.24 for belowground biomass (IPCC 2006 AFOLU,
     Table 4.4, tropical broadleaf).
  3. Carbon fraction 0.47 of dry biomass (IPCC 2006 default).
  4. CO2e = C * 44/12 (stoichiometric conversion).
  5. Annual sequestration ≈ 2.4% of standing stock for mature stands
     (average of IPCC 2006 growth-to-carbon reviews; differs by biome).

Wood density (WD g/cm³) per species/stocking defaults:
  tropical broadleaf 0.60, temperate broadleaf 0.55, conifer 0.45,
  mangrove 0.70, bamboo/palm 0.35, shrub 0.55, herb 0.20 (Chave 2009
  global wood-density database).

HONESTY RULE: outputs are 'indicated potential', clearly labelled as
scenario estimates that scale linearly with record count — the number
answers "how much carbon do the trees in this dataset represent?", not
"a measured inventory".
"""

import numpy as np
import pandas as pd

CITATIONS = {
    "chave": (
        "Chave, J. et al. (2014). Improved allometric models to estimate "
        "the aboveground biomass of tropical trees. Global Change Biology, "
        "20, 3177-3190. doi:10.1111/gcb.12629"
    ),
    "ipcc": (
        "IPCC (2006). 2006 IPCC Guidelines for National Greenhouse Gas "
        "Inventories, Vol. 4 AFOLU. Root-to-shoot 0.24 (Tab 4.4); carbon "
        "fraction 0.47; CO2/C = 44/12."
    ),
    "zd": (
        "Zanne, A.E. et al. (2009). Global wood density database. Dryad. "
        "doi:10.5061/dryad.234"
    ),
}

# scenario defaults (disclosed, not measured)
DEFAULT_DBH_CM = 30.0
DEFAULT_HEIGHT_M = 15.0
ROOT_SHOOT = 0.24          # IPCC 2006 Tab 4.4 tropical broadleaf
CARBON_FRACTION = 0.47     # IPCC 2006 default
CO2_PER_C = 44.0 / 12.0
ANNUAL_FRACTION = 0.024    # ~2.4% of standing stock per year

# life-form -> (wood density g/cm3, is_woody)
LIFE_FORM_WD = {
    "tree":     (0.60, True),
    "shrub":    (0.55, True),
    "liana":    (0.50, True),
    "bamboo":   (0.35, True),
    "palm":     (0.40, True),
    "mangrove": (0.70, True),
    "herb":     (0.20, False),
    "grass":    (0.20, False),
    "fern":     (0.25, False),
    "moss":     (0.10, False),
}


def _growth_form_difficulty(species, family="", genus=""):
    """
    Crude life-form inference from name/family text.
    Returns (life_form, wd, is_woody, note).
    """
    text = f"{species} {family} {genus}".lower()
    if "mangrove" in text or "rhizophor" in text:
        return "mangrove", *LIFE_FORM_WD["mangrove"], ""
    if "bamboo" in text or "bambus" in text:
        return "bamboo", *LIFE_FORM_WD["bamboo"], ""
    if "palm" in text or "arecaceae" in text or "palmace" in text:
        return "palm", *LIFE_FORM_WD["palm"], ""
    if any(k in text for k in ("pinacea", "picea", "pinus", "abies",
                               "conifer", "cupress", "larix", "pseudotsuga")):
        return "conifer", LIFE_FORM_WD["tree"][0] - 0.15, True, ""
    if "poaceae" in text or "grass" in text:
        return "grass", *LIFE_FORM_WD["grass"], ""
    if "fern" in text or "pteridoph" in text:
        return "fern", *LIFE_FORM_WD["fern"], ""
    if any(k in text for k in ("herb", "annual", "acinus")):
        return "herb", *LIFE_FORM_WD["herb"], ""
    return "tree (default)", *LIFE_FORM_WD["tree"], (
        "life form not detected - woody-tree defaults applied")


def estimate_carbon(df, species="", family="", genus="", kingdom=""):
    """
    Scenario carbon estimate for the aboveground biomass represented by
    a plant species' georeferenced records.

    `kingdom` (from the GBIF backbone) gates applicability: only
    Plantae (and Fungi, with a reduced model) carry woody biomass;
    Animalia returns not-applicable.

    Returns dict with totals and per-record parameters, or None if the
    sample has no records.
    """
    n = len(df)
    if n == 0:
        return None

    kingdom_norm = (kingdom or "").strip().lower()
    if kingdom_norm and kingdom_norm != "plantae":
        label = ("animals" if kingdom_norm == "animalia"
                 else f"kingdom {kingdom or 'unknown'}")
        return {
            "applicable": False,
            "life_form": "non-plant",
            "note": (
                "Carbon standing-stock estimation applies to plants. "
                f"This taxon is {label}, which sequester no primary "
                "carbon as woody biomass."
            ),
            "citations": CITATIONS,
        }

    life_form, wd, is_woody, note = _growth_form_difficulty(
        species, family=family or "", genus=genus or ""
    )

    if not is_woody:
        return {
            "applicable": False,
            "life_form": life_form,
            "note": (
                "Non-woody life form - standing-stock carbon is dominated "
                "by soil organic carbon and turnover, not durable woody "
                "biomass. Tree-centric allometry does not apply."
            ),
            "citations": CITATIONS,
        }

    # Chave 2014: AGB(kg) = 0.0673 * (WD*DBH^2*H)^0.976
    # (D in cm, H in m, WD in g/cm3 -> kg directly)
    wdh = wd * (DEFAULT_DBH_CM ** 2) * DEFAULT_HEIGHT_M
    agb_kg = 0.0673 * (wdh ** 0.976)

    agb_t = agb_kg / 1000.0                      # t dry matter / tree
    bgb_t = agb_t * ROOT_SHOOT                   # t belowground
    total_dm_t = agb_t + bgb_t                   # per tree
    c_t = total_dm_t * CARBON_FRACTION           # t C / tree
    co2_t = c_t * CO2_PER_C                      # t CO2e / tree

    # scenario totals across the sample's tree-equivalents
    total_co2 = co2_t * n
    total_c = c_t * n
    annual_co2 = total_co2 * ANNUAL_FRACTION

    return {
        "applicable": True,
        "life_form": life_form,
        "scenario_note": (
            f"Scenario estimate: every record is treated as one mature "
            f"{life_form} (DBH {DEFAULT_DBH_CM:.0f} cm, height "
            f"{DEFAULT_HEIGHT_M:.0f} m, wood density {wd:.2f} g/cm³). "
            f"The result answers 'how much carbon do the trees these "
            f"records represent store?' - it is not a field inventory."
        ) + (f" {note}" if note else ""),
        "per_tree": {
            "agb_t": round(agb_t, 3),
            "bgb_t": round(bgb_t, 3),
            "c_t": round(c_t, 3),
            "co2e_t": round(co2_t, 3),
        },
        "sample_totals": {
            "tree_equivalents": int(n),
            "biomass_t": round(total_dm_t * n, 1),
            "carbon_t": round(total_c, 1),
            "co2e_t": round(total_co2, 1),
            "annual_sequestration_co2e_t": round(annual_co2, 2),
        },
        "equivalences": _equivalences(total_co2, annual_co2),
        "citations": CITATIONS,
    }


def _equivalences(total_co2, annual_co2):
    """Human-relatable equivalences for a CO2 tonnage."""
    per_car_km = 0.12       # kg CO2e / km, typical petrol car
    per_flight_lhr = 90.0   # kg CO2e / economy passenger-hour (long-haul)
    per_house_year = 4_000  # kg CO2e / EU household-year (energy)
    return {
        "car_km": round(total_co2 * 1000 / per_car_km),
        "flights_hours": round(total_co2 * 1000 / per_flight_lhr),
        "house_years": round(total_co2 * 1000 / per_house_year, 1),
        "annual_equals_car_km": round(annual_co2 * 1000 / per_car_km),
    }
