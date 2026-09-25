"""
GBIF occurrence data cubes
──────────────────────────
GBIF now exposes a SQL-based service for species occurrence cubes
(the basis of the EU B-Cubed indicator infrastructure). This module turns
the current analysis into a ready-to-run cube recipe so users graduate
from "dashboard" to "indicator-grade reproducible pipeline".
"""

import json

SQL_DOC = "https://techdocs.gbif.org/en/data-use/api-sql-downloads"
CUBE_DOC = "https://techdocs.gbif.org/en/data-use/data-cubes"


def build_cube_sql(species, year_from=None, year_to=None, basis=None,
                   grid=10):
    """
    Return a GBIF SQL download query that produces a species x cell x year
    occurrence cube for the current analysis filters.

    GBIF's cube functions:
      gbif_eea_cellcode(eea_cell_code_size, decimalLatitude, decimalLongitude)
      gbif_eea_cellcode_1deg(...)
    """
    conds = [
        f"gbif_eea_cellcode({grid}, \"decimalLatitude\", \"decimalLongitude\") AS eea_cell_code",
        "speciesKey",
        "year",
        "COUNT(*) AS occurrences",
    ]
    where = [f"species = '{species}'"]
    if year_from and year_to:
        where.append(f"year BETWEEN {int(year_from)} AND {int(year_to)}")
    if basis and basis != "All":
        where.append(f"basisOfRecord = '{basis}'")

    sql = (
        "SELECT " + ", ".join(conds) + "\n"
        "FROM occurrence;\n"
        "\n"
        "-- WHERE clause to apply in the GBIF SQL download form:\n"
        "-- " + " AND ".join(where) + "\n"
        "\n"
        "-- Paste into the GBIF SQL download (see " + SQL_DOC + ")\n"
        "-- or the 'Cube' option on gbif.org, then download as CSV.\n"
        "-- Group-by fields: eea_cell_code, speciesKey, year"
    )
    return sql


def build_cube_payload(species, year_from=None, year_to=None, basis=None,
                       grid=10):
    """JSON payload mirroring build_cube_sql for scripted use."""
    where = {"species": species}
    if year_from and year_to:
        where["year"] = {
            "type": "between", "value": [int(year_from), int(year_to)]
        }
    if basis and basis != "All":
        where["basisOfRecord"] = basis
    return {
        "schema": "biosift.cube/1.0",
        "docs": SQL_DOC,
        "grid_size_deg": grid,
        "select": [
            f"gbif_eea_cellcode({grid}, decimalLatitude, decimalLongitude) AS eea_cell_code",
            "speciesKey",
            "year",
        ],
        "aggregate": "count(*) AS occurrences",
        "where": where,
    }


def cube_exports(species, year_from=None, year_to=None, basis=None, grid=10):
    """Convenience: returns (sql_text, json_payload_str)."""
    payload = build_cube_payload(species, year_from, year_to, basis, grid)
    sql = build_cube_sql(species, year_from, year_to, basis, grid)
    return sql, json.dumps(payload, indent=2)
