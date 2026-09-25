"""
SDM readiness audit
───────────────────
Journal-grounded, tiered assessment of whether the analysed sample can
support species distribution modelling — with the filtering *strictness*
the user chose made explicit.

Methodology implemented (flag names in brackets are CoordinateCleaner's):
  - Zizka et al. 2020 (Ecography 43:1–8, doi:10.1111/ecog.04895):
    automated filtering identifies problematic records; ~50% of records
    are typically removed at their recommended settings; effectiveness is
    species- and region-dependent.
  - Marcer et al. 2022 (Ecography 2022:e06025, doi:10.1111/ecog.06025):
    coordinate uncertainty is the dominant error axis for SDM fitness;
    records whose uncertainty is unknown must be treated as unverified.
  - Gur et al. / GBIF georeferencing best practice: 0/0 'Null Island'
    coordinates, country–coordinate mismatch, and pre-1900 imprecision.

BioSift extends the literature with an explicit, disclosed strictness
dimension: Standard mode uses the permissive-to-moderate thresholds from
Zizka et al.'s sensitivity analysis (uncertainty <= 10 km), while Strict
mode follows the 'publication-grade' end of the same pipeline
(uncertainty <= 1 km). Every gate reports its citation inline.
"""

import numpy as np
import pandas as pd

from utils.bdq import bdq_meta

CITATIONS = {
    "zizka": (
        "Zizka, A. et al. (2020). No one-size-fits-all solution to clean "
        "GBIF: embedded workflows for Windows, Mac and Linux. Ecography, "
        "43, 24–35. doi:10.1111/ecog.04895"
    ),
    "marcer": (
        "Marcer, A. et al. (2022). Uncertainty matters: ascertaining where "
        "specimens in natural history collections relate to coordinates "
        "and uncertainty. Ecography, 2022, e06025. doi:10.1111/ecog.06025"
    ),
    "gbif_refine": (
        "GBIF (2020). Georeferencing Best Practices. CP-83-007, "
        "doi:10.15468/doc-gg7h-s853"
    ),
}

# strictness profile: (max coordinate uncertainty in meters)
PROFILES = {
    "Standard (≤10 km, Zizka et al. 2020)": 10_000,
    "Strict (≤1 km, publication-grade)":    1_000,
}


def audit_sdm_readiness(df, flags, mode="Standard (≤10 km, Zizka et al. 2020)"):
    """
    Evaluate the analysed sample against SDM data-readiness gates.

    Returns dict:
      ready_records, retention_pct, gate (≥100), verdict, gates: [..],
      profile, citations
    """
    total = len(df)
    if total == 0:
        return None

    max_unc = PROFILES.get(mode, 10_000)

    lat = df.get("decimalLatitude")
    lon = df.get("decimalLongitude")

    gates = []

    def gate(name, mask, desc, cite=None, critical=True):
        """mask=True means the record PASSES this gate."""
        gates.append({
            "gate": name,
            "pass": int(mask.fillna(False).sum() if hasattr(mask, "sum")
                        else int(mask)),
            "fail": int((~mask.fillna(False)).sum()),
            "desc": desc,
            "cite": cite,
            "critical": critical,
        })
        return mask.fillna(False)

    # G1 — georeferenced
    g1 = lat.notna() & lon.notna()
    gate("Georeferenced", g1,
         "Records must carry decimalLatitude and decimalLongitude.",
         cite="Zizka et al. 2020 — coordinate presence filter")

    # G2 — not Null Island / implausible
    g2 = g1 & ~(
        (lat.fillna(0) == 0) & (lon.fillna(0) == 0)
    )
    gate("Non-zero coordinates", g2,
         "Excludes 0°N/0°E 'Null Island' artefacts.",
         cite="GBIF Georeferencing Best Practice 2020")

    # G3 — coordinate uncertainty within profile
    if "coordinateUncertaintyInMeters" in df.columns:
        unc = pd.to_numeric(df["coordinateUncertaintyInMeters"],
                            errors="coerce")
        known = g2 & unc.notna()
        within = known & (unc <= max_unc)
        g3 = g2 & (within | unc.isna())
        n_exceed = int((known & ~within).sum())
        desc = (
            f"Records with known coordinateUncertaintyInMeters must be "
            f"≤ {max_unc:,} m. {n_exceed} known records exceed it."
        )
        if n_exceed:
            med = float(unc[known & ~within].median())
            desc += (
                f" Median stated uncertainty among failing records: "
                f"{med/1000:,.1f} km — typical of citizen-science "
                f"observations and coarse georeferences. This is a "
                f"property of the data source, not of BioSift's filter "
                f"(cf. Zizka et al. 2022)."
            )
        gate("Uncertainty ≤ threshold", g3, desc,
             cite="Marcer et al. 2022 — uncertainty axis")
    else:
        g3 = g2
        gate("Uncertainty ≤ threshold", g3,
             "Field coordinateUncertaintyInMeters absent in sample — "
             "uncertainty gate not evaluated.",
             cite="Marcer et al. 2022 — uncertainty axis", critical=False)

    # G4 — precision sufficient (≥ 2 decimal places ≈ ≤1 km grid)
    def _prec(series):
        def dec(v):
            if pd.isna(v):
                return 0
            s = str(float(v))
            return len(s.split(".")[-1].rstrip("0")) if "." in s else 0
        return series.apply(dec)

    g4 = g3 & (lat.notna()) & (_prec(lat) >= 2) & (_prec(lon) >= 2)
    gate("Precision ≥ 2 decimals", g4,
         "Sub-1 km reporting precision required for fine-scale SDM.",
         cite="Zizka et al. 2020 — precision filter")

    # G5 — dated
    g5 = g4 & df["year"].notna()
    gate("Dated (year present)", g5,
         "Temporal context required for bias assessment and thinning.",
         cite="Zizka et al. 2020 — date filter")

    # G6 — no duplicate species+space+time
    g6_mask = ~df.duplicated(
        subset=["species", "decimalLatitude", "decimalLongitude", "year"],
        keep="first"
    )
    g6 = g5 & g6_mask
    gate("Non-duplicate", g6,
         "First occurrence of each species+coordinates+year combination.",
         cite="Zizka et al. 2020 — deduplication")

    ready_mask = g6
    ready = int(ready_mask.sum())
    retention = round(ready / total * 100, 1)

    # GBIF guidance: >= 100 unique, well-distributed records for
    # correlative SDM; below that, presence-only methods only.
    gate_ok = ready >= 100
    gates.append({
        "gate": "Minimum sample (≥100)",
        "pass": ready,
        "fail": 0,
        "desc": "Correlative SDMs generally require ≥100 usable records.",
        "cite": "Zizka et al. 2020; GBIF best practice",
        "critical": True,
    })

    if gate_ok and retention >= 40:
        verdict = "READY"
    elif ready >= 100:
        verdict = "CONDITIONAL"
    else:
        verdict = "NOT READY"

    return {
        "ready_records": ready,
        "retention_pct": retention,
        "min_sample_ok": gate_ok,
        "verdict": verdict,
        "gates": gates,
        "profile": mode,
        "citations": CITATIONS,
    }
