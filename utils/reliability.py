import pandas as pd
import numpy as np
from datetime import datetime, date


def compute_reliability_score(df):
    scores = pd.Series(100.0, index=df.index)

    basis_scores = {
        "HUMAN_OBSERVATION"  :   0,
        "MACHINE_OBSERVATION":  -5,
        "PRESERVED_SPECIMEN" : -10,
        "LIVING_SPECIMEN"    :  -5,
        "MATERIAL_SAMPLE"    : -10,
        "LITERATURE"         : -15,
        "FOSSIL_SPECIMEN"    : -20,
        "UNKNOWN"            : -20,
    }
    if "basisOfRecord" in df.columns:
        scores += df["basisOfRecord"].map(basis_scores).fillna(-20)

    def precision_penalty(val):
        if pd.isna(val):
            return -30
        try:
            decimals = len(str(float(val)).split(".")[-1].rstrip("0"))
            if decimals >= 5 : return   0
            elif decimals == 4: return  -5
            elif decimals == 3: return -10
            elif decimals == 2: return -15
            else              : return -25
        except Exception:
            return -25

    if "decimalLatitude" in df.columns:
        scores += df["decimalLatitude"].apply(precision_penalty)

    current_year = datetime.now().year
    if "year" in df.columns:
        def age_penalty(y):
            if pd.isna(y): return -20
            age = current_year - int(y)
            if age <= 5    : return   0
            elif age <= 15 : return  -5
            elif age <= 30 : return -10
            elif age <= 50 : return -15
            elif age <= 100: return -20
            else           : return -30
        scores += df["year"].apply(age_penalty)

    if "eventDate" in df.columns:
        scores -= df["eventDate"].isna().astype(int) * 10

    if "issues" in df.columns:
        def issue_penalty(x):
            if isinstance(x, list):
                return -min(len(x) * 3, 15)
            return 0
        scores += df["issues"].apply(issue_penalty)

    scores = scores.clip(0, 100).round(1)
    return scores


def get_reliability_label(score):
    if score >= 80:
        return "High",   "#3FB950"
    elif score >= 60:
        return "Medium", "#E3B341"
    elif score >= 40:
        return "Low",    "#F0883E"
    else:
        return "Poor",   "#F85149"


def get_data_fitness(score, summary, temporal_stats):
    suitability = []

    dup_pct    = summary.get("duplicate",      {}).get("percent", 0)
    coord_pct  = summary.get("missing_coords", {}).get("percent", 0)
    prec_pct   = summary.get("low_precision",  {}).get("percent", 0)
    gap_count  = temporal_stats.get("gap_count",  0) if temporal_stats else 0
    recent_pct = temporal_stats.get("recent_pct", 0) if temporal_stats else 0

    sdm_ok = score >= 70 and coord_pct < 10 and prec_pct < 30
    suitability.append({
        "use_case": "Species Distribution Modeling",
        "suitable": sdm_ok,
        "reason"  : "Good coordinate quality and health score"
                    if sdm_ok else
                    "High missing or low-precision coordinates "
                    "reduce SDM reliability"
    })

    temp_ok = gap_count < 20 and recent_pct >= 10
    suitability.append({
        "use_case": "Temporal Trend Analysis",
        "suitable": temp_ok,
        "reason"  : "Sufficient temporal coverage"
                    if temp_ok else
                    "Too many temporal gaps or insufficient recent data"
    })

    cons_ok = score >= 60 and dup_pct < 20
    suitability.append({
        "use_case": "Conservation Assessment",
        "suitable": cons_ok,
        "reason"  : "Adequate data quality for conservation use"
                    if cons_ok else
                    "High duplicate rate or low quality reduces confidence"
    })

    suitability.append({
        "use_case": "Citizen Science Reporting",
        "suitable": True,
        "reason"  : "General use reporting is appropriate for this data"
    })

    spatial_ok = prec_pct < 10 and coord_pct < 5
    suitability.append({
        "use_case": "Fine-scale Spatial Analysis",
        "suitable": spatial_ok,
        "reason"  : "Coordinate precision is sufficient"
                    if spatial_ok else
                    "Too many low-precision coordinates for fine-scale work"
    })

    return suitability


def generate_methods_text(species, df, clean_df, summary, score):
    today       = date.today().strftime("%d %B %Y")
    total_gbif  = len(df)
    clean_count = len(clean_df)

    removed_parts = []

    dup = summary.get("duplicate",      {}).get("count", 0)
    zc  = summary.get("zero_coords",    {}).get("count", 0)
    old = summary.get("old_record",     {}).get("count", 0)
    mc  = summary.get("missing_coords", {}).get("count", 0)
    lp  = summary.get("low_precision",  {}).get("count", 0)
    cm  = summary.get("country_mismatch", {}).get("count", 0)

    if dup: removed_parts.append(f"duplicates (n={dup})")
    if zc:  removed_parts.append(f"zero-coordinate records (n={zc})")
    if old: removed_parts.append(f"pre-1900 records (n={old})")
    if mc:  removed_parts.append(f"records missing coordinates (n={mc})")
    if lp:  removed_parts.append(f"low-precision coordinate records (n={lp})")
    if cm:  removed_parts.append(
        f"records with coordinates outside stated country (n={cm})"
    )

    removed_str = (
        "Records were filtered to remove "
        + ", ".join(removed_parts)
        + f", resulting in {clean_count:,} analysis-ready records."
        if removed_parts else
        f"All {clean_count:,} retrieved records passed quality checks."
    )

    text = (
        f"Occurrence data for {species} were retrieved from the Global "
        f"Biodiversity Information Facility (GBIF; GBIF.org) on {today} "
        f"using the GBIF Occurrence Search API with parameters: "
        f"scientificName='{species}', hasCoordinate=TRUE. "
        f"A total of {total_gbif:,} georeferenced records were retrieved "
        f"and subjected to automated quality assessment using BioSift "
        f"(github.com/Hansen-arch/biosift). "
        f"{removed_str} "
        f"The dataset achieved a data health score of {score}% based on "
        f"checks for duplicate records, coordinate validity, country "
        f"coordinate consistency, temporal completeness and coordinate "
        f"precision. "
        f"All data are available under their respective licences "
        f"via GBIF.org."
    )

    return text


def generate_citation(species, df, species_info=None):
    """
    Generate a formatted GBIF dataset citation for the analysed species.
    Returns a dict with:
      - apa      : APA-style citation string
      - bibtex   : BibTeX entry string
      - note     : guidance on getting a real DOI
      - search_url: direct GBIF search URL for this species
    """
    today      = date.today()
    year_str   = str(today.year)
    date_str   = today.strftime("%d %B %Y")
    date_iso   = today.strftime("%Y-%m-%d")

    safe_name  = species.replace(" ", "+")
    search_url = (
        f"https://www.gbif.org/occurrence/search"
        f"?scientificName={safe_name}&hasCoordinate=true"
    )

    record_count = len(df)

    # APA style
    apa = (
        f"GBIF.org ({year_str}). Occurrence records for "
        f"{species} [Dataset]. "
        f"Global Biodiversity Information Facility. "
        f"Retrieved {date_str} from {search_url} "
        f"({record_count:,} records accessed via BioSift)."
    )

    # BibTeX
    safe_key = species.replace(" ", "_").lower()
    bibtex = (
        f"@misc{{gbif_{safe_key}_{year_str},\n"
        f"  author    = {{{{GBIF.org}}}},\n"
        f"  title     = {{Occurrence records for {species}}},\n"
        f"  year      = {{{year_str}}},\n"
        f"  publisher = {{Global Biodiversity Information Facility}},\n"
        f"  note      = {{Retrieved {date_str}. "
        f"{record_count:,} records. Accessed via BioSift}},\n"
        f"  url       = {{{search_url}}}\n"
        f"}}"
    )

    note = (
        "For a citable DOI, download this dataset directly from GBIF: "
        "go to gbif.org/occurrence/search, apply your filters, "
        "click 'Download', and GBIF will generate a permanent DOI "
        "for your exact download (e.g. https://doi.org/10.15468/dl.xxxxx). "
        "Use that DOI in your citation instead."
    )

    return {
        "apa"       : apa,
        "bibtex"    : bibtex,
        "note"      : note,
        "search_url": search_url
    }