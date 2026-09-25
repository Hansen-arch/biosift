"""
TDWG Biodiversity Data Quality (BDQ) standards mapping
──────────────────────────────────────────────────────
Maps every BioSift check to its official TDWG BDQ Test identifier
(https://github.com/tdwg/bdq — TG2 core tests), so results are
communicated in the vocabulary the global community already uses.

Identifiers follow the TG2 core test list (tdwg/bdq repo, tg2/core).
"""

BDQ = {
    "missing_coords": {
        "bdq": "VALIDATION_DECIMALLATITUDE_NOTEMPTY · VALIDATION_DECIMALLONGITUDE_NOTEMPTY",
        "name": "Coordinates present",
        "desc": "Flags records missing decimalLatitude or decimalLongitude.",
    },
    "zero_coords": {
        "bdq": "VALIDATION_COORDINATES_CAPABLEOFCONTAININGZERO",
        "name": "Non-zero coordinates",
        "desc": "0°N 0°E ('Null Island') almost always indicates a data entry error.",
    },
    "missing_year": {
        "bdq": "VALIDATION_YEAR_NOTEMPTY",
        "name": "Event year present",
        "desc": "Records without dwc:year cannot be used in temporal analyses.",
    },
    "old_record": {
        "bdq": "VALIDATION_YEAR_INRANGE (custom lower bound: 1900)",
        "name": "Year in range",
        "desc": "Pre-1900 records are valid but often use historical place names "
                "and imprecise georeference — review before use.",
    },
    "missing_date": {
        "bdq": "VALIDATION_EVENTDATE_NOTEMPTY · VALIDATION_EVENTDATE_INRANGE",
        "name": "Event date present and in range",
        "desc": "Checks dwc:eventDate is populated and consistent with dwc:year.",
    },
    "duplicate": {
        "bdq": "VALIDATION_OCCURRENCEID_UNIQUE (proxy)",
        "name": "Records unique",
        "desc": "Same species + coordinates + year appearing multiple times "
                "suggests duplicated occurrences across datasets.",
    },
    "low_precision": {
        "bdq": "VALIDATION_DECIMALLATITUDE_PRECISION · VALIDATION_DECIMALLONGITUDE_PRECISION",
        "name": "Coordinate precision",
        "desc": "Fewer than 2 decimal places (~1 km or coarser) limits fine-scale "
                "analyses such as SDMs.",
    },
    "country_mismatch": {
        "bdq": "VALIDATION_COUNTRYCODE_STANDARD · VALIDATION_COUNTRY_COORDINATESMISMATCH",
        "name": "Coordinates within stated country",
        "desc": "Coordinates checked against the stated country bounding box "
                "(1° tolerance) — mismatches indicate georeferencing errors.",
    },
    "has_issues": {
        "bdq": "GBIF interpretation flags (informational)",
        "name": "GBIF issue flags",
        "desc": "GBIF's own interpretation pipeline flagged these records. "
                "Informational — not all flags imply unusable data.",
    },
}

ORDER = [
    "missing_coords", "zero_coords", "missing_year", "old_record",
    "missing_date", "duplicate", "low_precision", "country_mismatch",
    "has_issues",
]


def bdq_meta(key):
    """Return (bdq_id, friendly_name, description) for a check key."""
    meta = BDQ.get(key, {})
    return (
        meta.get("bdq", "—"),
        meta.get("name", key.replace("_", " ").title()),
        meta.get("desc", ""),
    )


def bdq_id(key):
    return BDQ.get(key, {}).get("bdq", "—")


def citation_note():
    return (
        "Quality assertions follow the TDWG Biodiversity Data Quality (BDQ) "
        "TG2 core test vocabulary — https://github.com/tdwg/bdq"
    )
