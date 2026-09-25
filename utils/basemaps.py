"""
Professional key-free basemaps — explicit XYZ tile URLs.

No CARTO (requires API key for production use), no vendor aliases, no
API keys. Every URL below is a public, key-free endpoint:
  - Esri Light Gray Canvas (default — clean professional cartography)
  - OSM standard tiles (ODbL)
  - Esri ArcGIS Online World Imagery / Ocean (free with attribution)
  - OpenTopoMap (CC-BY-SA)
"""

import folium

# name -> (url template, attribution, max_zoom)
BASEMAPS = {
    "Light Gray (default)": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri, HERE, Garmin, FAO, NOAA, USGS",
        16,
    ),
    "OpenStreetMap": (
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "&copy; OpenStreetMap contributors",
        19,
    ),
    "Satellite (Esri World Imagery)": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Esri, Maxar, Earthstar Geographics",
        18,
    ),
    "Topographic (OpenTopoMap)": (
        "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "&copy; OpenTopoMap (CC-BY-SA)",
        17,
    ),
    "Ocean (Esri)": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri, GEBCO, NOAA",
        13,
    ),
    "Dark (Esri)": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "Esri, HERE, Garmin, FAO, NOAA, USGS",
        16,
    ),
}

DEFAULT = "Light Gray (default)"


def _tile_layer(name, active=False):
    url, attr, max_zoom = BASEMAPS[name]
    return folium.TileLayer(
        tiles=url, attr=attr, name=name, max_zoom=max_zoom,
        control=True, show=active,
    )


def basemap(location, zoom=4, name=None):
    """Create a folium.Map with the chosen basemap pre-loaded."""
    active = name if name in BASEMAPS else DEFAULT
    m = folium.Map(location=location, zoom_start=zoom, tiles=None,
                   control_scale=True)
    _tile_layer(active, active=True).add_to(m)
    return m


def add_layer_control(m, active_name=None):
    """Attach the full basemap switcher (one layer active)."""
    active = active_name if active_name in BASEMAPS else DEFAULT
    # remove pre-added active layer to avoid duplicates
    for key in list(m._children.keys()):
        child = m._children[key]
        if isinstance(child, folium.TileLayer):
            del m._children[key]
    for name in BASEMAPS:
        _tile_layer(name, active=(name == active)).add_to(m)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
