"""
Site boundary import and export
────────────────────────────────
A site screen is only as good as its boundary, and every discipline keeps
boundaries in a different box: ecologists hand over a GeoJSON from QGIS,
consultants send a KML from Google Earth, engineers paste a WKT from a CAD
export, and field teams keep a CSV of corner coordinates. This module reads
all four into one GeoJSON Polygon/MultiPolygon and writes the boundary back
out in the same set.

Two rules matter here and are enforced rather than assumed:

* Latitude and longitude are never guessed from magnitude alone when the
  source states which is which. A CSV without a header is the one place
  order is inferred, and the inference is stated in the returned note.
* Rings are passed through with winding untouched. GBIF rejects clockwise
  exterior rings outright, and the screening layer re-winds anyway, so
  re-orienting here would only hide what the source actually contained.
"""

import csv
import io
import json
import math
import re
import xml.etree.ElementTree as ET

R_KM = 6371.0088

# KML files in the wild declare the OGC namespace, the Google namespace, or
# none at all. Namespaces are stripped from tag names instead of hard-coded.
_DIMLESS = 2


class BoundaryError(ValueError):
    """Raised when a boundary cannot be read from the supplied text."""


# ────────────────────────────────────────────── constructors


def bbox_polygon(west, south, east, north):
    """Rectangle from four decimal-degree edges."""
    try:
        west, south = float(west), float(south)
        east, north = float(east), float(north)
    except (TypeError, ValueError):
        raise BoundaryError("bounding box edges must be numbers")
    if not (-180 <= west < east <= 180):
        raise BoundaryError("west must be less than east, both within "
                            "-180…180")
    if not (-90 <= south < north <= 90):
        raise BoundaryError("south must be less than north, both within "
                            "-90…90")
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south], [east, south], [east, north],
            [west, north], [west, south],
        ]],
    }


def circle_polygon(lat, lon, radius_km, steps=96):
    """Ring approximating a radius on the sphere.

    GBIF's own `geoDistance` parameter is unusable (a 10 km radius returned
    64 records where the equivalent box returned 2.9 million), so a radius
    is always converted to a real polygon before it is queried.
    """
    try:
        lat, lon, radius_km = float(lat), float(lon), float(radius_km)
    except (TypeError, ValueError):
        raise BoundaryError("latitude, longitude and radius must be numbers")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise BoundaryError("latitude must be within ±90 and longitude ±180")
    if radius_km <= 0:
        raise BoundaryError("radius must be greater than zero")

    angular = radius_km / R_KM
    lat1, lon1 = math.radians(lat), math.radians(lon)
    ring = []
    for i in range(steps + 1):
        bearing = 2 * math.pi * i / steps
        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular)
            + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(angular) * math.cos(lat1),
            math.cos(angular) - math.sin(lat1) * math.sin(lat2),
        )
        ring.append([math.degrees(lon2), math.degrees(lat2)])
    return {"type": "Polygon", "coordinates": [ring]}


# ────────────────────────────────────────────── measures


def _pairs(geometry):
    """Yield (outer_ring, [hole rings]) for a Polygon or MultiPolygon."""
    if geometry.get("type") == "Polygon":
        rings = geometry.get("coordinates") or []
        if not rings:
            return
        yield rings[0], rings[1:]
    elif geometry.get("type") == "MultiPolygon":
        for poly in geometry.get("coordinates") or []:
            if poly:
                yield poly[0], poly[1:]


def ring_area_km2(ring):
    """Spherical ring area — the same formulation turf.js uses."""
    if len(ring) < 4:
        return 0.0
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total * R_KM * R_KM / 2.0)


def area_km2(geometry):
    """Net area: exterior rings minus holes, summed over all parts."""
    total = 0.0
    for outer, holes in _pairs(geometry):
        total += ring_area_km2(outer)
        for hole in holes:
            total -= ring_area_km2(hole)
    return total


def bbox_of(geometry):
    """[west, south, east, north] of every vertex."""
    lons, lats = [], []
    for poly in _all_rings(geometry):
        for lon, lat in poly:
            lons.append(lon)
            lats.append(lat)
    if not lons:
        raise BoundaryError("boundary has no vertices")
    return [min(lons), min(lats), max(lons), max(lats)]


def center_of(geometry):
    """[latitude, longitude] of the bounding-box centre (map-friendly)."""
    w, s, e, n = bbox_of(geometry)
    return [(s + n) / 2.0, (w + e) / 2.0]


def _all_rings(geometry):
    for outer, holes in _pairs(geometry):
        yield outer
        for hole in holes:
            yield hole


def describe(geometry):
    """Everything the UI needs to state about a boundary before querying."""
    parts = list(_pairs(geometry))
    vertices = sum(len(outer) for outer, _ in parts)
    return {
        "type": geometry.get("type"),
        "area_km2": round(area_km2(geometry), 2),
        "bbox": [round(v, 5) for v in bbox_of(geometry)],
        "center": [round(v, 5) for v in center_of(geometry)],
        "parts": len(parts),
        "holes": sum(len(holes) for _, holes in parts),
        "vertices": vertices,
    }


# ────────────────────────────────────────────── importers


def _ring(raw, where):
    """Coerce one ring to a closed list of [lon, lat] floats."""
    if not isinstance(raw, (list, tuple)):
        raise BoundaryError(f"{where}: ring is not a list of coordinates")
    out = []
    for point in raw:
        if not isinstance(point, (list, tuple)) or len(point) < _DIMLESS:
            raise BoundaryError(f"{where}: a vertex is not a lon/lat pair")
        try:
            lon, lat = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            raise BoundaryError(f"{where}: a vertex is not numeric")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise BoundaryError(
                f"{where}: vertex {lon}, {lat} is outside the world — "
                "latitude and longitude may be swapped"
            )
        out.append([lon, lat])
    if len(out) < 3:
        raise BoundaryError(f"{where}: a ring needs at least three vertices")
    if out[0] != out[-1]:
        out.append(list(out[0]))
    return out


def _polygon(raw, where="polygon"):
    if not isinstance(raw, (list, tuple)) or not raw:
        raise BoundaryError(f"{where}: no rings found")
    rings = [_ring(raw[0], f"{where} exterior")]
    for i, hole in enumerate(raw[1:], start=1):
        rings.append(_ring(hole, f"{where} hole {i}"))
    return rings


def from_geojson(obj):
    """Read a geometry, Feature, FeatureCollection or drawn feature."""
    if isinstance(obj, (str, bytes)):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError as e:
            raise BoundaryError(f"not valid GeoJSON: {e.msg}") from e
    if not isinstance(obj, dict):
        raise BoundaryError("GeoJSON must be an object")

    gtype = obj.get("type")

    if gtype == "Feature":
        if not obj.get("geometry"):
            raise BoundaryError("feature has no geometry")
        return from_geojson(obj["geometry"])

    if gtype == "FeatureCollection":
        return _collect(obj.get("features") or [], "featurecollection")

    if gtype == "GeometryCollection":
        return _collect(obj.get("geometries") or [], "geometrycollection")

    if gtype in ("Polygon", "MultiPolygon"):
        coords = obj.get("coordinates")
        if gtype == "Polygon":
            return {"type": "Polygon", "coordinates": _polygon(coords)}
        parts = [_polygon(poly, f"part {i + 1}")
                 for i, poly in enumerate(coords or [])]
        if not parts:
            raise BoundaryError("multipolygon has no parts")
        return {"type": "MultiPolygon", "coordinates": parts}

    if gtype in (None, "") and "coordinates" in obj:
        # Bare coordinate array: depth decides Polygon vs MultiPolygon.
        coords = obj["coordinates"]
        depth = _depth(coords)
        if depth == 3:
            return {"type": "Polygon", "coordinates": _polygon(coords)}
        if depth == 4:
            return {"type": "MultiPolygon",
                    "coordinates": [_polygon(p) for p in coords]}
        raise BoundaryError("coordinates are neither a ring list nor a "
                            "list of rings")

    if gtype == "Point":
        raise BoundaryError(
            "a point is not a boundary — use the point + radius option"
        )

    raise BoundaryError(f"unsupported GeoJSON type: {gtype!r}")


def _depth(value):
    d = 0
    while isinstance(value, (list, tuple)):
        d += 1
        value = value[0] if value else None
    return d


def _collect(items, where):
    """Merge every polygon in a collection into one MultiPolygon."""
    parts = []
    for i, item in enumerate(items, start=1):
        try:
            geom = from_geojson(item)
        except BoundaryError as e:
            raise BoundaryError(f"{where} item {i}: {e}") from e
        if geom["type"] == "Polygon":
            parts.append(geom["coordinates"])
        else:
            parts.extend(geom["coordinates"])
    if not parts:
        raise BoundaryError(f"{where} contains no polygons")
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def from_wkt(text):
    """Read POLYGON or MULTIPOLYGON text, with or without an SRID prefix."""
    body = text.strip()
    m = re.match(r"(?:srid=\d+\s*;\s*)?(multi)?polygon\s*(.*)$", body,
                 re.IGNORECASE | re.DOTALL)
    if not m:
        raise BoundaryError("WKT must start with POLYGON or MULTIPOLYGON")
    multi = bool(m.group(1))
    try:
        nested = _parse_groups(m.group(2))
    except BoundaryError:
        raise
    except Exception as e:                          # noqa: BLE001
        raise BoundaryError(f"could not read WKT coordinates: {e}") from e

    if multi:
        polygons = [_as_polygon(part) for part in nested]
    else:
        polygons = [_as_polygon(nested)]

    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def _as_polygon(value):
    """Turn one parsed WKT polygon group into a list of rings."""
    if not isinstance(value, list) or not value:
        raise BoundaryError("empty polygon in WKT")
    # POLYGON((...)) parses to [[pair, pair, pair]]
    if all(isinstance(p, list) and len(p) == 2
           and isinstance(p[0], (int, float)) for p in value):
        return [_ring(value, "WKT ring")]
    rings = []
    for i, ring in enumerate(value):
        if not all(isinstance(p, list) and len(p) == 2
                   and isinstance(p[0], (int, float)) for p in ring):
            raise BoundaryError(f"WKT ring {i + 1} is not a list of pairs")
        rings.append(_ring(ring, f"WKT ring {i + 1}"))
    return rings


def _parse_groups(text):
    """Parse nested parenthesised coordinate groups into nested lists.

    WKT nests three deep for a polygon (shape / ring / vertex) and four for
    a multipolygon. Numbers inside a group are read as lon/lat pairs, which
    is why a group may hold either pairs or more groups.
    """
    start = text.find("(")
    if start < 0:
        raise BoundaryError("WKT has no coordinate group")

    def flush(token):
        parts = token.split()
        if len(parts) >= 2:
            return [float(parts[0]), float(parts[1])]
        if len(parts) == 1:
            return float(parts[0])
        return None

    def parse(i):
        items, token = [], ""
        i += 1                                        # skip "("
        while i < len(text):
            ch = text[i]
            if ch == "(":
                if token.strip():
                    value = flush(token)
                    if value is not None:
                        items.append(value)
                    token = ""
                sub, i = parse(i)
                items.append(sub)
                continue
            if ch in ",)":
                if token.strip():
                    value = flush(token)
                    if value is not None:
                        items.append(value)
                    token = ""
                if ch == ")":
                    return items, i + 1
                i += 1
                continue
            token += ch
            i += 1
        raise BoundaryError("WKT is missing a closing parenthesis")

    items, _ = parse(start)
    return items


def from_kml(text):
    """Read the first Polygon of a KML or KMZ-extracted XML document."""
    try:
        root = ET.fromstring(text.strip())
    except ET.ParseError as e:
        raise BoundaryError(f"not valid KML/XML: {e}") from e

    polygons = [el for el in root.iter() if _local(el.tag) == "polygon"]
    if not polygons:
        raise BoundaryError("KML contains no <Polygon>")

    parts = []
    for poly in polygons:
        rings = []
        for boundary in _children(poly, "outerboundaryis", "innerboundaryis"):
            coords_el = next((el for el in boundary.iter()
                              if _local(el.tag) == "coordinates"), None)
            if coords_el is None or not (coords_el.text or "").strip():
                continue
            tokens = coords_el.text.replace("\n", " ").split()
            ring = []
            for token in tokens:
                bits = token.split(",")
                if len(bits) < 2:
                    continue
                ring.append([float(bits[0]), float(bits[1])])
            if len(ring) >= 3:
                rings.append(_ring(ring, "KML ring"))
        if rings:
            parts.append(rings)

    if not parts:
        raise BoundaryError("KML polygons have no usable coordinates")
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def _local(tag):
    return tag.rpartition("}")[2].lower()


def _children(element, *names):
    wanted = set(names)
    return [el for el in element.iter()
            if el is not element and _local(el.tag) in wanted]


_LAT_KEYS = {"lat", "latitude", "decimal_latitude", "decimallatitude",
             "y", "lat_dd", "south", "north"}
_LON_KEYS = {"lon", "lng", "long", "longitude", "decimal_longitude",
             "decimallongitude", "x", "lon_dd", "east", "west"}


def from_csv(text):
    """Read a vertex list from CSV.

    Either a header names the latitude and longitude columns, or the first
    two numeric columns are used. Returned metadata records which happened,
    so the UI can say what it assumed instead of leaving it implicit.
    """
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        raise BoundaryError("CSV is empty")
    counts = {d: lines[0].count(d) for d in (",", "\t", ";")}
    delimiter = max(counts, key=counts.get) if max(counts.values()) else ","

    rows = [r for r in csv.reader(io.StringIO(text.strip()),
                                  delimiter=delimiter)
            if any(cell.strip() for cell in r)]
    if len(rows) < 4:
        raise BoundaryError("CSV needs at least three rows of vertices")

    header = [c.strip().lower().replace(" ", "_") for c in rows[0]]
    lat_i = next((i for i, h in enumerate(header) if h in _LAT_KEYS), None)
    lon_i = next((i for i, h in enumerate(header) if h in _LON_KEYS), None)

    if lat_i is not None and lon_i is not None:
        body, note = rows[1:], (
            f"columns taken from the header: “{rows[0][lon_i].strip()}” "
            f"as longitude, “{rows[0][lat_i].strip()}” as latitude")
    else:
        body = rows
        columns = []
        for i in (0, 1):
            try:
                columns.append([float(row[i]) for row in body])
            except (IndexError, ValueError):
                raise BoundaryError(
                    "CSV has no latitude/longitude header and its first two "
                    "columns are not numbers"
                )
        first_is_lon = any(abs(v) > 90 for v in columns[0])
        second_is_lon = any(abs(v) > 90 for v in columns[1])
        if first_is_lon and not second_is_lon:
            lat_i, lon_i = 1, 0
            note = ("no header found: column 1 is beyond ±90 so it is read "
                    "as longitude and column 2 as latitude")
        elif second_is_lon and not first_is_lon:
            lat_i, lon_i = 0, 1
            note = ("no header found: column 2 is beyond ±90 so it is read "
                    "as longitude and column 1 as latitude")
        else:
            # Both columns are inside ±90: the order cannot be decided from
            # the numbers alone, so the common latitude-first convention is
            # assumed and stated, and the preview map shows the result.
            lat_i, lon_i = 0, 1
            note = ("no header found: assumed latitude first, longitude "
                    "second — check the preview, or add a header row")

    ring = []
    for n, row in enumerate(body, start=1):
        try:
            lat = float(row[lat_i])
            lon = float(row[lon_i])
        except (IndexError, ValueError):
            raise BoundaryError(f"CSV row {n} has no usable coordinates")
        ring.append([lon, lat])

    geometry = {"type": "Polygon",
                "coordinates": [_ring(ring, "CSV vertices")]}
    return geometry, note


# ────────────────────────────────────────────── dispatch


def parse_boundary(text):
    """Read a boundary from text, deciding the format from the content.

    Returns (geometry, note). The note is empty unless something was
    inferred (CSV column order, a merged collection of polygons).
    """
    if not isinstance(text, str) or not text.strip():
        raise BoundaryError("nothing to read — paste a boundary or upload "
                            "a file")
    body = text.strip()
    head = body[:2000].lower()

    if body.startswith("{") or body.startswith("["):
        return from_geojson(body), ""

    if "<" in body[:200] and ("<kml" in head or "<polygon" in head
                              or "<gpx" in head):
        return from_kml(body), ""

    if re.match(r"(srid=\d+\s*;\s*)?(multi)?polygon", body, re.IGNORECASE):
        return from_wkt(body), ""

    # A CSV may lead with a header row rather than a number, so the
    # delimiter in the first line is the signal, not the first character.
    if re.match(r"[-+]?\d", body) or any(
            sep in body.splitlines()[0] for sep in (",", "\t", ";")):
        return from_csv(body)

    raise BoundaryError(
        "could not recognise the format — expected GeoJSON, KML, WKT "
        "(POLYGON(...)) or a CSV of latitude/longitude vertices"
    )


def read_upload(filename, data):
    """Decode an uploaded boundary file and parse it."""
    if isinstance(data, bytes):
        text = data.decode("utf-8-sig", errors="replace")
    else:
        text = data
    if filename and filename.lower().endswith(".kmz"):
        raise BoundaryError(
            "KMZ is a zipped KML — unzip it, or export as .kml/.geojson"
        )
    return parse_boundary(text)


# ────────────────────────────────────────────── exporters


def to_geojson(geometry, name="Site boundary"):
    """A single Feature with the site name attached."""
    return json.dumps(
        {"type": "Feature",
         "properties": {"name": name,
                        "area_km2": round(area_km2(geometry), 2)},
         "geometry": geometry},
        indent=2,
    )


def to_kml(geometry, name="Site boundary"):
    """KML 2.2 with every ring, holes included."""
    def ring_xml(ring, tag):
        coords = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in ring)
        return (f"<{tag}><LinearRing><coordinates>{coords}"
                f"</coordinates></LinearRing></{tag}>")

    def polygon_xml(rings):
        body = ring_xml(rings[0], "outerBoundaryIs")
        for hole in rings[1:]:
            body += ring_xml(hole, "innerBoundaryIs")
        return f"<Polygon>{body}</Polygon>"

    if geometry["type"] == "Polygon":
        shape = polygon_xml(geometry["coordinates"])
    else:
        shape = "<MultiGeometry>" + "".join(
            polygon_xml(poly) for poly in geometry["coordinates"]
        ) + "</MultiGeometry>"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "<Document>\n"
        f"<name>{_xml(name)}</name>\n"
        f"<Placemark><name>{_xml(name)}</name>{shape}</Placemark>\n"
        "</Document>\n</kml>\n"
    )


def _xml(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _ring_wkt(ring):
    return "(" + ",".join(f"{lon:.6f} {lat:.6f}" for lon, lat in ring) + ")"


def to_wkt(geometry):
    """WKT in the exact form GBIF's geometry parameter accepts."""
    def poly_wkt(rings):
        return "(" + ",".join(_ring_wkt(ring) for ring in rings) + ")"

    if geometry["type"] == "Polygon":
        return "POLYGON" + poly_wkt(geometry["coordinates"])
    return "MULTIPOLYGON(" + ",".join(
        poly_wkt(poly) for poly in geometry["coordinates"]
    ) + ")"
