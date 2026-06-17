import pandas as pd
import zipfile
import io
from datetime import date

# ── Darwin Core URI term map ──────────────────────────────
DWC_TERMS = {
    "occurrenceID"    : "http://rs.tdwg.org/dwc/terms/occurrenceID",
    "species"         : "http://rs.tdwg.org/dwc/terms/species",
    "decimalLatitude" : "http://rs.tdwg.org/dwc/terms/decimalLatitude",
    "decimalLongitude": "http://rs.tdwg.org/dwc/terms/decimalLongitude",
    "country"         : "http://rs.tdwg.org/dwc/terms/country",
    "countryCode"     : "http://rs.tdwg.org/dwc/terms/countryCode",
    "year"            : "http://rs.tdwg.org/dwc/terms/year",
    "month"           : "http://rs.tdwg.org/dwc/terms/month",
    "eventDate"       : "http://rs.tdwg.org/dwc/terms/eventDate",
    "basisOfRecord"   : "http://rs.tdwg.org/dwc/terms/basisOfRecord",
    "datasetName"     : "http://rs.tdwg.org/dwc/terms/datasetName",
    "issues"          : "http://rs.tdwg.org/dwc/terms/informationWithheld",
    "image_url"       : "http://rs.tdwg.org/dwc/terms/associatedMedia",
}


def build_dwca(df, species, score, clean_only=False):
    """
    Build a Darwin Core Archive ZIP in memory.

    Returns bytes of a ZIP file containing:
      - occurrence.csv  (DwC-compliant occurrence data)
      - meta.xml        (field-to-term mapping)
      - eml.xml         (dataset-level metadata)

    Parameters
    ----------
    df         : DataFrame — occurrence data (already cleaned if clean_only)
    species    : str — scientific name
    score      : float — health score
    clean_only : bool — label the archive as cleaned dataset
    """
    try:
        # ── 1. Prepare occurrence.csv ─────────────────────
        export = df.copy()

        # extract image_url from media
        if "media" in export.columns:
            def extract_url(media_list):
                if isinstance(media_list, list):
                    for item in media_list:
                        if isinstance(item, dict):
                            url = item.get("identifier", "")
                            if url and url.startswith("http"):
                                return url
                return ""
            export.insert(
                export.columns.get_loc("media"),
                "image_url",
                export["media"].apply(extract_url)
            )
            export = export.drop(columns=["media"])

        # clean issues column
        if "issues" in export.columns:
            export["issues"] = export["issues"].apply(
                lambda x: "; ".join(str(i) for i in x)
                if isinstance(x, list) and len(x) > 0 else ""
            )

        # keep only DwC-mappable columns
        dwc_cols = [c for c in export.columns if c in DWC_TERMS]
        export   = export[dwc_cols]

        occ_csv = export.to_csv(index=False)

        # ── 2. Build meta.xml ─────────────────────────────
        field_lines = []
        for i, col in enumerate(dwc_cols):
            term = DWC_TERMS.get(col, "")
            if term:
                if col == dwc_cols[0]:
                    # first column = core ID
                    field_lines.append(
                        f'    <id index="{i}"/>'
                    )
                else:
                    field_lines.append(
                        f'    <field index="{i}" '
                        f'term="{term}"/>'
                    )

        fields_xml = "\n".join(field_lines)

        meta_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://rs.tdwg.org/dwc/text/
         http://rs.tdwg.org/dwc/text/tdwg_dwc_text.xsd">
  <core encoding="UTF-8" fieldsTerminatedBy=","
        linesTerminatedBy="\\n" fieldsEnclosedBy="&quot;"
        ignoreHeaderLines="1"
        rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files>
      <location>occurrence.csv</location>
    </files>
{fields_xml}
  </core>
</archive>"""

        # ── 3. Build eml.xml ──────────────────────────────
        today      = date.today().isoformat()
        label      = "Cleaned" if clean_only else "Full"
        record_count = len(export)

        eml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<eml:eml xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"
         xmlns:dc="http://purl.org/dc/terms/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1
         http://rs.gbif.org/schema/eml-gbif-profile/1.1/eml.xsd"
         packageId="biosift-{species.replace(' ','-').lower()}-{today}"
         system="BioSift"
         scope="system"
         xml:lang="eng">
  <dataset>
    <title>{label} occurrence dataset for {species}
    — exported from BioSift</title>
    <creator>
      <organizationName>BioSift</organizationName>
      <onlineUrl>
        https://github.com/Hansen-arch/biosift
      </onlineUrl>
    </creator>
    <pubDate>{today}</pubDate>
    <language>eng</language>
    <abstract>
      <para>
        {label} Darwin Core Archive for {species},
        containing {record_count:,} occurrence records
        retrieved from GBIF and quality-assessed using
        BioSift (github.com/Hansen-arch/biosift).
        Data health score: {score}%.
        Exported on {today}.
      </para>
    </abstract>
    <intellectualRights>
      <para>
        Source data from GBIF.org under respective
        dataset licences. Quality assessment by BioSift
        under MIT licence.
      </para>
    </intellectualRights>
    <contact>
      <organizationName>BioSift</organizationName>
      <onlineUrl>
        https://github.com/Hansen-arch/biosift
      </onlineUrl>
    </contact>
  </dataset>
</eml:eml>"""

        # ── 4. Package into ZIP ───────────────────────────
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zf:
            zf.writestr("occurrence.csv", occ_csv)
            zf.writestr("meta.xml",       meta_xml)
            zf.writestr("eml.xml",        eml_xml)

        zip_buffer.seek(0)
        return zip_buffer.read(), None

    except Exception as e:
        return None, str(e)