"""
BioSift: Site Screening page

Site-level screening, folded in from the SiteSift prototype: draw, import or
generate a boundary and every GBIF record inside it is summarised — species
of concern, IUCN composition, native/introduced coverage, survey effort,
record quality, publishing datasets, and which countries the records are
attributed to.

The engine lives in ``sitesift.screening`` so the standalone API and this
page cannot drift apart.
"""

import json
import math

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

import sitesift.screening as S
import utils.theme as T
from utils.theme import C, D
from utils.basemaps import basemap, add_layer_control
from utils.gbif_fetch import fetch_countries, country_code_from_label, \
    country_options
from utils.polygon import (
    BoundaryError, bbox_polygon, circle_polygon, read_upload,
    parse_boundary, describe, to_geojson, to_kml, to_wkt, from_geojson,
)

MODES = ("Draw on map", "Point & radius", "Bounding box", "Paste or upload")

BASIS = ["All", "HUMAN_OBSERVATION", "PRESERVED_SPECIMEN", "MACHINE_OBSERVATION",
         "LIVING_SPECIMEN", "LITERATURE", "FOSSIL_SPECIMEN"]

# Where the map opens when nothing has been drawn yet.
DEFAULT_CENTER = (20.0, 0.0)


# ────────────────────────────────────────────── map helpers


def _zoom_for(bbox):
    """A zoom level that fits a boundary's width, clamped to sane limits."""
    span = max(bbox[2] - bbox[0], 1e-4)
    return max(2, min(14, int(math.log2(360.0 / span)) - 1))


def _boundary_layer(m, geometry):
    folium.GeoJson(
        geometry,
        name="Boundary",
        style_function=lambda _: {
            "color": C["accent"], "weight": 2, "fillOpacity": 0.10,
            "fillColor": C["accent"],
        },
    ).add_to(m)


def _view_polygon(bounds):
    """The map's visible extent as a boundary, plus why it can't be one.

    streamlit-folium reports the viewport as ``{"_southWest": {lat, lng},
    "_northEast": {lat, lng}}``. A view that has wrapped across the
    antimeridian has east < west, which no single lon/lat ring can express,
    so it is refused with an explanation instead of being silently turned
    into a 360-degree band.
    """
    if not bounds:
        return None, ("No viewport reported yet — pan or zoom the map once, "
                      "then press this.")
    sw = bounds.get("_southWest") or {}
    ne = bounds.get("_northEast") or {}
    try:
        west, south = float(sw["lng"]), float(sw["lat"])
        east, north = float(ne["lng"]), float(ne["lat"])
    except (KeyError, TypeError, ValueError):
        return None, ("No viewport reported yet — pan or zoom the map once, "
                      "then press this.")

    # At the opening zoom the map shows the whole world, whose bounds run
    # past ±180 on both sides; that is not an antimeridian crossing.
    if east - west >= 360.0:
        return None, ("The whole world is showing — zoom in until the site "
                      "fills the map, then press this.")

    # A view panned past the date line can sit entirely outside ±180.
    if west < -180 or east > 180:
        shift = -360.0 * round(west / 360.0)
        west, east = west + shift, east + shift
    south = max(-90.0, min(90.0, south))
    north = max(-90.0, min(90.0, north))

    if not (-180 <= west < east <= 180):
        return None, ("This view crosses the antimeridian, which one "
                      "boundary cannot express — pan until the site sits "
                      "on one side of 180°.")
    if south >= north:
        return None, ("This view is too small to turn into a boundary — "
                      "zoom out a step, or use the bounding box instead.")
    try:
        return bbox_polygon(west, south, east, north), None
    except BoundaryError as e:
        return None, str(e)


def _apply_view_extent():
    """Button callback: adopt the visible map extent as the boundary."""
    geometry = st.session_state.get("ss_view_ready")
    if geometry is not None:
        st.session_state["ss_geometry"] = geometry
        st.session_state["ss_geometry_source"] = "view"


def _input_map(geometry, draw):
    """The map the boundary is drawn on or previewed in."""
    info = describe(geometry) if geometry else None
    center, zoom = (DEFAULT_CENTER, 2)
    if info:
        center = (info["center"][0], info["center"][1])
        zoom = _zoom_for(info["bbox"])

    m = basemap(center, zoom=zoom)
    if geometry:
        _boundary_layer(m, geometry)
    if draw:
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": False, "circle": False,
                "circlemarker": False, "marker": False,
                "polygon": True, "rectangle": True,
            },
        ).add_to(m)
    add_layer_control(m)
    return m


def _results_map(bundle, geometry):
    """Boundary plus the sampled records, coloured by conservation status."""
    info = describe(geometry)
    m = basemap((info["center"][0], info["center"][1]),
                zoom=_zoom_for(info["bbox"]))
    _boundary_layer(m, geometry)
    threatened = set(S.THREATENED)
    for point in bundle.get("points") or []:
        colour = (D["flag"] if point.get("iucn") in threatened
                  else D["clean"])
        folium.CircleMarker(
            location=[point["lat"], point["lon"]],
            radius=3,
            color=colour, fill=True, fill_color=colour, fill_opacity=0.75,
            weight=0,
            popup=folium.Popup(
                f"<b>{point.get('species') or 'Unidentified'}</b><br>"
                f"Year: {point.get('year') or 'n/a'}<br>"
                f"IUCN: {point.get('iucn') or 'not assessed'}<br>"
                f"Basis: {point.get('basis') or 'n/a'}",
                max_width=220,
            ),
        ).add_to(m)
    add_layer_control(m)
    return m


# ────────────────────────────────────────────── boundary input


def _boundary_from_upload(uploaded):
    try:
        geometry, note = read_upload(uploaded.name, uploaded.getvalue())
    except BoundaryError as e:
        st.error(f"Could not read **{uploaded.name}**: {e}")
        return None
    except Exception as e:                          # noqa: BLE001
        st.error(f"Could not read **{uploaded.name}**: {e}")
        return None
    if note:
        st.caption(f"Read {uploaded.name} — {note}.")
    return geometry


def _boundary_from_paste(text):
    if not text.strip():
        return None
    try:
        geometry, note = parse_boundary(text)
    except BoundaryError as e:
        st.error(f"Could not read the pasted boundary: {e}")
        return None
    if note:
        st.caption(f"Read the pasted boundary — {note}.")
    return geometry


def _collect_boundary(mode, draw_result, uploaded, pasted, bbox_vals,
                      point_vals):
    """Resolve every input mode to one GeoJSON geometry (or None)."""
    if mode == "Draw on map":
        if draw_result is None:
            # The map component has not reported yet (first paint, or a
            # runtime without it): keep whatever boundary already exists.
            return st.session_state.get("ss_geometry")
        drawings = draw_result.get("all_drawings") or []
        if drawings:
            try:
                geometry = from_geojson(drawings[-1])
            except BoundaryError as e:
                st.error(f"That drawing cannot be used: {e}")
            else:
                st.session_state["ss_geometry_source"] = "draw"
                return geometry
        if st.session_state.get("ss_geometry_source") != "draw":
            # A boundary taken from the map extent (or from another mode)
            # survives: no drawing was made, so nothing has been cleared.
            return st.session_state.get("ss_geometry")
        # An empty drawing list after drawing means the user cleared it.
        st.session_state.pop("ss_geometry", None)
        return None

    if mode == "Point & radius":
        lat, lon, radius = point_vals
        try:
            return circle_polygon(lat, lon, radius)
        except BoundaryError as e:
            st.error(str(e))
            return None

    if mode == "Bounding box":
        try:
            return bbox_polygon(*bbox_vals)
        except BoundaryError as e:
            st.error(str(e))
            return None

    geometry = _boundary_from_upload(uploaded) if uploaded is not None else None
    if geometry is None:
        geometry = _boundary_from_paste(pasted)
    return geometry


# ────────────────────────────────────────────── results


def _species_of_concern(bundle):
    rows = []
    for cat in bundle["threatened"]["categories"]:
        for sp in cat["species"]:
            rows.append({"Category": cat["code"], "Species": sp["name"],
                         "Records": sp["records"]})
    return rows


def _country_names(bundle, lookup):
    rows = []
    total = bundle["summary"]["records"] or 1
    for row in bundle.get("countries") or []:
        code = row["code"]
        rows.append({
            "Country": lookup.get(code, code),
            "Code": code,
            "Records": row["records"],
            "Share": round(row["records"] / total * 100, 1),
        })
    return rows


def _render_bundle(bundle, geometry, lookup):
    summary = bundle["summary"]
    if not summary["records"]:
        T.alert("warn", "No records inside this boundary",
                "GBIF holds no georeferenced PRESENT records here for the "
                "selected filters. That is a statement about the data, not "
                "about the site — widen the boundary, drop the year or "
                "country filter, or check the bounding box.")
        _render_exports(bundle, geometry)
        return

    m = st.columns(5)
    T.metric_card("Records inside", f"{summary['records']:,}",
                  "georeferenced, PRESENT", col=m[0])
    T.metric_card("Species recorded", f"{summary['species_observed']:,}",
                  "distinct scientific names", col=m[1])
    T.metric_card("Threatened records", f"{summary['threatened_records']:,}",
                  "CR · EN · VU", col=m[2])
    T.metric_card("Publishing datasets", f"{summary['datasets']:,}"
                  + ("+" if summary["datasets_truncated"] else ""),
                  "attribution below", col=m[3])
    T.metric_card("Records per km²", f"{summary['records_per_km2']:,}",
                  f"across {bundle['site']['area_km2']:,} km²", col=m[4])

    # ── species of concern ────────────────────────────────
    T.section("Species of concern")
    rows = _species_of_concern(bundle)
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True,
                     use_container_width=True,
                     column_config={
                         "Category": st.column_config.TextColumn(width="small"),
                     })
    else:
        st.caption("No CR, EN or VU species are recorded inside this "
                   "boundary for the selected filters.")
    st.caption(bundle["threatened"]["note"])

    # ── composition ───────────────────────────────────────
    T.section("IUCN composition")
    iucn = [row for row in bundle["iucn"] if row["records"]]
    if iucn:
        st.plotly_chart(
            T.bar_fig([f"{r['code']} · {r['label']}" for r in iucn],
                      [r["records"] for r in iucn], horizontal=True,
                      height=120 + 34 * len(iucn)),
            use_container_width=True,
        )
    else:
        st.caption("GBIF carries no IUCN category for the records here.")

    T.section("Native or introduced")
    est = bundle["establishment"]
    ec = st.columns(4)
    T.metric_card("With establishment data", f"{est['recorded']:,}",
                  f"{est['coverage_pct']}% of records", col=ec[0])
    T.metric_card("Native", f"{est['native']:,}", "of those records", col=ec[1])
    T.metric_card("Introduced", f"{est['introduced']:,}",
                  "incl. naturalised, vagrant", col=ec[2])
    T.metric_card("Uncertain", f"{est['uncertain']:,}", "", col=ec[3])
    st.caption(
        "Reported as coverage, never applied as a filter: the field is "
        "recorded on only a small fraction of records, so filtering on it "
        "would discard almost all the evidence."
    )

    T.section("Most recorded species")
    species = pd.DataFrame(bundle["species"],
                           columns=["name", "records"])
    species.columns = ["Species", "Records"]
    st.dataframe(species, hide_index=True, use_container_width=True,
                 height=min(600, 38 + 35 * len(species)))
    if summary["species_truncated"]:
        st.caption(f"Showing the 30 best-recorded of {summary['species_observed']}+ "
                   "species — the facet was truncated at 300 names.")

    # ── where the records come from ───────────────────────
    T.section("Country attribution")
    country_rows = _country_names(bundle, lookup)
    if country_rows:
        st.dataframe(pd.DataFrame(country_rows), hide_index=True,
                     use_container_width=True,
                     column_config={
                         "Share": st.column_config.ProgressColumn(
                             "Share of records", format="%.1f%%",
                             min_value=0, max_value=100),
                     })
    st.caption(
        "GBIF's interpreted country — derived from the coordinates when the "
        "publisher left the field blank. Border sites, marine records and "
        "records held by foreign institutions can sit outside the country "
        "you expect, which is what the country filter acts on."
    )

    # ── survey effort ─────────────────────────────────────
    T.section("Survey effort over time")
    temporal = bundle["temporal"]
    decades = temporal["decades"]
    if decades:
        tc1, tc2 = st.columns([3, 2])
        with tc1:
            st.plotly_chart(
                T.bar_fig([f"{d['decade']}s" for d in decades],
                          [d["records"] for d in decades], height=300),
                use_container_width=True,
            )
        with tc2:
            st.markdown(f"""
            <div class="card" style="min-height:290px">
                <div class="card-t">Reading effort, not abundance</div>
                <div class="card-d">
                    Records span <b>{temporal['first_year']}</b> to
                    <b>{temporal['last_year']}</b> across
                    <b>{temporal['years_with_records']}</b> years.
                    <b>{temporal['recent_pct']}%</b> of records are from 2000
                    or later, and <b>{temporal['pre_1950_pct']}%</b> pre-date
                    1950.
                    <br><br>
                    Record counts measure how often someone looked. A thin
                    decade means a thin survey, not a quiet decade.
                </div>
            </div>
            """, unsafe_allow_html=True)

    T.section("Seasonality")
    months = bundle["months"]
    st.plotly_chart(
        T.bar_fig([["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                    "Sep", "Oct", "Nov", "Dec"][m["month"] - 1]
                   for m in months],
                  [m["records"] for m in months], height=260),
        use_container_width=True,
    )

    # ── record quality ────────────────────────────────────
    T.section("Record quality")
    material = [i for i in bundle["issues"] if i["material"]]
    if material:
        issues_df = pd.DataFrame([
            {"Issue": i["label"], "Severity": i["severity"],
             "Records": i["records"], "% of records": i["pct"]}
            for i in material
        ])
        st.dataframe(issues_df, hide_index=True, use_container_width=True)
    else:
        st.caption("No material quality flags are present in these records.")
    if bundle["other_flag_count"]:
        st.caption(
            f"{bundle['other_flag_count']} further GBIF flags affect these "
            "records (institution matching, rounded coordinates, assumed "
            "datum and similar bookkeeping). They are counted but not "
            "treated as evidence problems."
        )

    T.section("Which datasets")
    datasets = pd.DataFrame([
        {"Dataset": d["title"], "Records": d["records"],
         "% of records": d["pct"], "GBIF": d["url"]}
        for d in bundle["datasets"]
    ])
    if not datasets.empty:
        st.dataframe(
            datasets, hide_index=True, use_container_width=True,
            column_config={
                "GBIF": st.column_config.LinkColumn(
                    "GBIF", display_text="Open dataset"),
            },
        )
    st.caption("Cite these publishers, not BioSift, for the underlying "
               "records.")

    # ── map ───────────────────────────────────────────────
    T.section("Where the records are")
    if bundle.get("points_error"):
        st.caption(f"Map sample unavailable: {bundle['points_error']}")
    else:
        st_folium(_results_map(bundle, geometry), height=420,
                  use_container_width=True, returned_objects=[],
                  key="ss_results_map")
        st.caption(f"{bundle['points_sampled']} sampled records plotted. "
                   "Red marks a CR/EN/VU record, green an assessed "
                   "non-threatened one.")

    # ── caveats + exports ─────────────────────────────────
    T.section("Read before you cite")
    st.markdown(
        '<div class="card"><div class="card-d"><ul style="margin:0;'
        'padding-left:1.1rem">'
        + "".join(f"<li style='margin-bottom:0.45rem'>{c}</li>"
                  for c in bundle["caveats"])
        + "</ul></div></div>",
        unsafe_allow_html=True,
    )

    _render_exports(bundle, geometry)


def _render_exports(bundle, geometry):
    T.section("Export")
    label = bundle["site"]["label"]
    file_stem = "".join(
        ch if ch.isalnum() or ch in "-_" else "_"
        for ch in label.lower()
    ).strip("_") or "site"

    cols = st.columns(4)
    with cols[0]:
        st.download_button(
            "Boundary GeoJSON",
            data=to_geojson(geometry, label),
            file_name=f"{file_stem}_boundary.geojson",
            mime="application/geo+json",
            width="stretch",
        )
    with cols[1]:
        st.download_button(
            "Boundary KML",
            data=to_kml(geometry, label),
            file_name=f"{file_stem}_boundary.kml",
            mime="application/vnd.google-earth.kml+xml",
            width="stretch",
        )
    with cols[2]:
        st.download_button(
            "Boundary WKT",
            data=to_wkt(geometry),
            file_name=f"{file_stem}_boundary.wkt",
            mime="text/plain",
            width="stretch",
        )
    with cols[3]:
        st.download_button(
            "Screen bundle (JSON)",
            data=json.dumps(bundle, indent=2),
            file_name=f"{file_stem}_screen.json",
            mime="application/json",
            width="stretch",
        )
    st.caption(
        "The bundle contains the boundary WKT, every count, the filters "
        "applied and the method statement — enough for a colleague to "
        "reproduce the screen."
    )


# ────────────────────────────────────────────── page


def render():
    T.inject_css()
    T.page_head(
        "Site Screening",
        "Draw, import or generate a site boundary and screen every GBIF "
        "record inside it."
    )

    countries, source = fetch_countries()
    lookup = {c["code"]: c["name"] for c in countries}
    if source == "fallback":
        st.caption("Country list is the built-in short list — GBIF's "
                   "country enumeration is unreachable right now.")

    T.section("Site boundary")
    mode = st.radio("Boundary source", MODES, horizontal=True,
                    key="ss_mode", label_visibility="collapsed")

    uploaded = None
    pasted = ""
    bbox_vals = (0.0, 0.0, 0.0, 0.0)
    point_vals = (0.0, 0.0, 0.0)
    draw_result = None

    if mode == "Draw on map":
        st.caption("Use the polygon or rectangle tool in the map's top-left "
                   "corner. Draw it with either vertex order — clockwise "
                   "rings are re-wound before the query.")
        existing = st.session_state.get("ss_geometry")
        draw_result = st_folium(
            _input_map(existing, draw=True), height=440,
            use_container_width=True,
            returned_objects=["all_drawings", "bounds"], key="ss_draw_map",
        )
        view_geometry, view_problem = _view_polygon(
            (draw_result or {}).get("bounds"))
        st.session_state["ss_view_ready"] = view_geometry
        vc1, vc2 = st.columns([3, 1])
        with vc1:
            st.caption(view_problem or
                       "Or screen what the map is showing: pan and zoom, "
                       "then take the visible extent as the boundary.")
        with vc2:
            st.button("Use current map view", key="ss_use_view",
                      on_click=_apply_view_extent,
                      disabled=view_geometry is None,
                      width="stretch")
    elif mode == "Point & radius":
        c1, c2, c3 = st.columns(3)
        with c1:
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0,
                                  value=0.0, step=0.01, format="%.4f",
                                  key="ss_lat")
        with c2:
            lon = st.number_input("Longitude", min_value=-180.0,
                                  max_value=180.0, value=0.0, step=0.01,
                                  format="%.4f", key="ss_lon")
        with c3:
            radius = st.number_input("Radius (km)", min_value=0.1,
                                     max_value=500.0, value=5.0, step=0.5,
                                     key="ss_radius")
        point_vals = (lat, lon, radius)
        st.caption("GBIF's own `geoDistance` parameter returns unusable "
                   "counts, so the radius is converted to a polygon before "
                   "it is queried.")
    elif mode == "Bounding box":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            west = st.number_input("West", min_value=-180.0, max_value=180.0,
                                   value=-0.15, step=0.01, format="%.4f",
                                   key="ss_west")
        with c2:
            south = st.number_input("South", min_value=-90.0, max_value=90.0,
                                    value=51.47, step=0.01, format="%.4f",
                                    key="ss_south")
        with c3:
            east = st.number_input("East", min_value=-180.0, max_value=180.0,
                                   value=-0.09, step=0.01, format="%.4f",
                                   key="ss_east")
        with c4:
            north = st.number_input("North", min_value=-90.0, max_value=90.0,
                                    value=51.53, step=0.01, format="%.4f",
                                    key="ss_north")
        bbox_vals = (west, south, east, north)
    else:
        uploaded = st.file_uploader(
            "Upload a boundary file",
            type=["geojson", "json", "kml", "wkt", "txt", "csv"],
            key="ss_upload",
        )
        pasted = st.text_area(
            "…or paste one",
            placeholder='{"type": "Polygon", "coordinates": [...]}\n'
                        "POLYGON ((...))\n"
                        "<kml ...>\n"
                        "lat,lon\n51.50,-0.12",
            height=140, key="ss_paste",
        )

    geometry = _collect_boundary(mode, draw_result, uploaded, pasted,
                                 bbox_vals, point_vals)
    if geometry is not None:
        st.session_state["ss_geometry"] = geometry
        if mode != "Draw on map":
            st.session_state["ss_geometry_source"] = "input"
        info = describe(geometry)
        st.caption(
            f"{info['type']} · {info['vertices']} vertices · "
            f"{info['area_km2']:,} km² · bbox "
            f"{info['bbox'][0]}, {info['bbox'][1]} → "
            f"{info['bbox'][2]}, {info['bbox'][3]}"
        )

    if mode != "Draw on map" and geometry is not None:
        st_folium(_input_map(geometry, draw=False), height=300,
                  use_container_width=True, returned_objects=[],
                  key="ss_preview_map")

    T.section("Screen settings")
    s1, s2 = st.columns(2)
    with s1:
        label = st.text_input("Site name", value="Untitled site",
                              key="ss_label")
    with s2:
        country_label = st.selectbox(
            "Country", country_options(countries), key="ss_country",
            help="Limits the screen to records GBIF attributes to one "
                 "country. A polygon already bounds the site, so this is "
                 "for border sites and for confirming attribution.",
        )
    country_code = country_code_from_label(country_label, countries)

    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        year_from = st.number_input("From year", min_value=1000,
                                    max_value=2026, value=1900,
                                    key="ss_year_from")
    with f2:
        year_to = st.number_input("To year", min_value=1000, max_value=2026,
                                  value=2026, key="ss_year_to")
    with f3:
        basis = st.selectbox("Record type", BASIS, key="ss_basis")

    years_valid = year_from <= year_to
    if not years_valid:
        st.warning("The from-year is after the to-year; fix that before "
                   "screening.")

    run = st.button("Screen site", type="primary", width="stretch",
                    disabled=(geometry is None or not years_valid))
    if geometry is None and not run:
        st.caption("No boundary yet — draw one, or switch to another "
                   "boundary source.")

    if run and geometry is not None:
        with st.spinner("Querying GBIF for this boundary…"):
            try:
                bundle = S.screen(
                    geometry, label=label,
                    year_from=int(year_from), year_to=int(year_to),
                    basis=basis, country=country_code,
                )
            except (ValueError, RuntimeError) as e:
                st.error(f"Screen failed: {e}")
                bundle = None
        if bundle is not None:
            st.session_state["ss_bundle"] = bundle
            st.session_state["ss_bundle_geom"] = geometry
            st.session_state["ss_bundle_lookup"] = lookup

    if "ss_bundle" in st.session_state:
        bundle = st.session_state["ss_bundle"]
        st.caption(
            f"{bundle['site']['label']} · {bundle['site']['area_km2']:,} km² · "
            f"{bundle['elapsed_s']} s"
            + (" · served from the one-hour cache" if bundle.get("cached")
               else "")
        )
        _render_bundle(bundle, st.session_state["ss_bundle_geom"],
                       st.session_state.get("ss_bundle_lookup", lookup))

    T.footer()
