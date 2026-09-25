"""
Professional key-free basemaps
──────────────────────────────
Curated basemap registry + folium factory. All providers below work
without an API key. Esri's World Imagery / Gray Canvas / Ocean basemaps
are free with attribution; OSM is ODbL.

Every map in BioSift is created through basemap() so the look stays
consistent, and any key-requiring provider would be opt-in only.
"""

import folium

# name -> (folium tiles id, attribution, max_zoom, note)
BASEMAPS = {
    "Terrain (default)": (
        "CartoDB Voyager",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        19,
    ),
    "Satellite": (
        "Esri.WorldImagery",
        "Tiles &copy; Esri — Source: Esri, i-cubed, USDA, USGS, AEX, "
        "GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP",
        19,
    ),
    "Topographic": (
        "OpenTopoMap",
        "&copy; <a href='https://opentopomap.org'>OpenTopoMap</a> (CC-BY-SA)",
        17,
    ),
    "Minimal Gray": (
        "CartoDB Positron",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        19,
    ),
    "Ocean & Terrain": (
        "Esri.OceanBasemap",
        "Tiles &copy; Esri — Sources: GEBCO, NOAA, National Geographic, "
        "DeLorme, NAVTEQ",
        13,
    ),
    "Dark (reference)": (
        "CartoDB dark_matter",
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        19,
    ),
}

DEFAULT = "Terrain (default)"


def basemap(location, zoom=4, name=None):
    """Create a folium.Map on the chosen basemap (defaults to Terrain)."""
    if name and name in BASEMAPS:
        DEFAULT_CHOICE = name
    else:
        DEFAULT_CHOICE = DEFAULT
    tiles, attr, max_zoom = BASEMAPS[DEFAULT_CHOICE]
    return folium.Map(
        location=location,
        zoom_start=zoom,
        tiles=tiles,
        attr=attr,
        max_zoom=max_zoom,
        control_scale=True,
    )


def add_layer_control(m, name=None):
    """Attach a layer switcher so users can change basemap in-place."""
    from folium import TileLayer
    for label, (tiles, attr, max_zoom) in BASEMAPS.items():
        try:
            TileLayer(
                tiles=tiles, attr=attr, name=label,
                max_zoom=max_zoom, control=True,
            ).add_to(m)
        except Exception:
            continue
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
