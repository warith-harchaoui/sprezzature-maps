"""
sprezzature-maps: a plate's layers in and out of a GIS, so no work is redone.

Module summary
--------------
A situation plate is configured in YAML, and everything it asserts -- a flow,
a front, a checkpoint, a zone of control -- lives there in longitude and
latitude, independent of the projection, the frame and the scale the plate is
drawn at. That is what makes it worth keeping: the next commission over the
same ground, at another scale and in another projection, should start from it
rather than from a blank page.

This module is the bridge between that YAML and the GIS (geographic
information system, software such as QGIS, ArcGIS or Google Earth that stores
and edits map layers) a cabinet already uses:

* :func:`export_layers` turns a plate's thematic layers into one GeoJSON
  FeatureCollection, every property kept, so QGIS opens it as is;
* :func:`to_kml` writes the same features as KML (Keyhole Markup Language,
  Google Earth's format);
* :func:`import_layers` does the reverse: GeoJSON or KML features become the
  config blocks a plate reads (``arrows``, ``front``, ``events``,
  ``annotations``, ``labels.places``, ``areas_of_control``);
* :func:`merge_layers` reads the config's ``layers:`` list -- files of
  features kept in a layer library -- and folds them into the plate, so a
  checkpoint traced once is drawn by every plate that names its file.

Why it exists, in the words of the researcher who asked for it (2026-11-13):
a cabinet paid for a month on Tripoli's coastline and streets, then another
client asked for the Tripolitania at another scale and projection, and "all
the work done on Tripoli the first time must never be lost" -- "never any
loss". Export, import and the layer library are that rule made mechanical.

The round trip is lossless for everything the plate draws: a feature's
``layer`` property says which block it came from, and every other key of the
block travels as a property and comes back as a key.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

#: The provenance keys a plate prints, carried on the collection itself so a
#: layer file says where its features came from and when they were true.
_PROVENANCE_KEYS = ("title", "subtitle", "as_of", "source", "method")

_KML_NS = "http://www.opengis.net/kml/2.2"


def _point(lon: Any, lat: Any) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [float(lon), float(lat)]}


def _line(coords: Any) -> dict[str, Any]:
    return {"type": "LineString", "coordinates": [[float(x), float(y)] for x, y in coords]}


def _feature(layer: str, geometry: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "geometry": geometry, "properties": {"layer": layer, **props}}


def _load_features(spec: Any, base: Path) -> list[dict[str, Any]]:
    """Features from an inline FeatureCollection, a list, or a file beside the config."""
    if spec is None:
        return []
    if isinstance(spec, str):
        path = Path(spec) if Path(spec).is_absolute() else base / spec
        return list(read_features(path))
    if isinstance(spec, dict) and spec.get("type") == "FeatureCollection":
        return list(spec.get("features", []))
    if isinstance(spec, list):
        return list(spec)
    return []


def export_layers(cfg: dict[str, Any], base: Path | str = ".") -> dict[str, Any]:
    """Return a plate's thematic layers as one GeoJSON FeatureCollection.

    Parameters
    ----------
    cfg : dict
        A situation-plate configuration, as read from its YAML.
    base : path-like, optional
        The config's directory, against which a ``source:`` path is resolved.

    Returns
    -------
    dict
        A FeatureCollection. Each feature's ``layer`` property names the block
        it came from; the plate's provenance (``title``, ``as_of``, ``source``,
        ``method``) and ``region.bbox`` ride on the collection under
        ``sprezzature``.

    Examples
    --------
    >>> cfg = {"title": "T", "as_of": "2026-11-13",
    ...        "arrows": [{"line": [[22.84, 16.07], [25.35, 13.63]], "style": "dashed"}],
    ...        "events": [{"lon": 22.83, "lat": 15.0, "label": "al-Tina"}]}
    >>> fc = export_layers(cfg)
    >>> [f["properties"]["layer"] for f in fc["features"]]
    ['arrow', 'event']
    >>> fc["features"][0]["properties"]["style"], fc["sprezzature"]["as_of"]
    ('dashed', '2026-11-13')
    """
    base = Path(base)
    features: list[dict[str, Any]] = []
    for arrow in cfg.get("arrows") or []:
        props = {k: v for k, v in arrow.items() if k != "line"}
        features.append(_feature("arrow", _line(arrow.get("line") or []), props))
    front = cfg.get("front") or {}
    if front.get("line"):
        props = {k: v for k, v in front.items() if k != "line"}
        features.append(_feature("front", _line(front["line"]), props))
    for event in cfg.get("events") or []:
        props = {k: v for k, v in event.items() if k not in ("lon", "lat")}
        features.append(_feature("event", _point(event["lon"], event["lat"]), props))
    for note in cfg.get("annotations") or []:
        at = note.get("at") or [note.get("lon"), note.get("lat")]
        props = {k: v for k, v in note.items() if k not in ("at", "lon", "lat")}
        features.append(_feature("annotation", _point(*at), props))
    for place in (cfg.get("labels") or {}).get("places") or []:
        props = {k: v for k, v in place.items() if k not in ("lon", "lat")}
        features.append(_feature("place", _point(place["lon"], place["lat"]), props))
    aoc = cfg.get("areas_of_control") or {}
    for feat in _load_features(aoc.get("source"), base):
        props = dict(feat.get("properties") or {})
        features.append(_feature("area", feat["geometry"], props))
    meta = {k: cfg[k] for k in _PROVENANCE_KEYS if cfg.get(k)}
    bbox = (cfg.get("region") or {}).get("bbox")
    if bbox:
        meta["bbox"] = [float(v) for v in bbox]
    return {"type": "FeatureCollection", "sprezzature": meta, "features": features}


def import_layers(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn GeoJSON features into the config blocks a situation plate reads.

    A feature exported by :func:`export_layers` goes back to its own block.
    A feature from elsewhere -- a QGIS layer, a KML from Google Earth -- is
    placed by its geometry: a point becomes an event, a line an arrow, a
    polygon a zone of control.

    Parameters
    ----------
    features : list of dict
        GeoJSON features.

    Returns
    -------
    dict
        A partial configuration: only the blocks the features fill.

    Examples
    --------
    >>> feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [22.83, 15.0]},
    ...           "properties": {"name": "al-Tina"}}]
    >>> import_layers(feats)["events"]
    [{'name': 'al-Tina', 'label': 'al-Tina', 'lon': 22.83, 'lat': 15.0}]
    """
    out: dict[str, Any] = {}
    areas: list[dict[str, Any]] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        props = dict(feat.get("properties") or {})
        layer = props.pop("layer", None)
        if "label" not in props and props.get("name") and layer not in ("annotation", "place"):
            props["label"] = props["name"]
        if layer is None:
            layer = {"Point": "event", "LineString": "arrow"}.get(
                gtype, "area" if gtype in ("Polygon", "MultiPolygon") else None
            )
        if layer is None:
            continue
        if layer == "area":
            areas.append({"type": "Feature", "geometry": geom, "properties": props})
        elif layer in ("arrow", "front") and gtype == "LineString":
            block = {**props, "line": [list(c[:2]) for c in geom["coordinates"]]}
            if layer == "front":
                out["front"] = block
            else:
                out.setdefault("arrows", []).append(block)
        elif gtype == "Point":
            lon, lat = geom["coordinates"][:2]
            if layer == "annotation":
                if "text" not in props and props.get("name"):
                    props["text"] = props.pop("name")
                out.setdefault("annotations", []).append({**props, "at": [lon, lat]})
            elif layer == "place":
                if "text" not in props and props.get("name"):
                    props["text"] = props.pop("name")
                out.setdefault("labels", {}).setdefault("places", []).append(
                    {**props, "lon": lon, "lat": lat}
                )
            else:
                out.setdefault("events", []).append({**props, "lon": lon, "lat": lat})
    if areas:
        out["areas_of_control"] = {"source": {"type": "FeatureCollection", "features": areas}}
    return out


def merge_layers(cfg: dict[str, Any], base: Path | str = ".") -> dict[str, Any]:
    """Fold the files named in ``cfg["layers"]`` into the plate's own blocks.

    ``layers`` is a list of paths, relative to the config, of GeoJSON or KML
    files -- a layer library a cabinet keeps across commissions. Their
    features are appended after the config's own: an arrow written in the
    YAML and one loaded from the library are both drawn. A zone from the
    library joins ``areas_of_control.source``; the config's own palette and
    settings are kept.

    Examples
    --------
    >>> import tempfile, json
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     lib = Path(tmp) / "checkpoints.geojson"
    ...     _ = lib.write_text(json.dumps({"type": "FeatureCollection", "features": [
    ...         {"type": "Feature", "geometry": {"type": "Point", "coordinates": [22.83, 15.0]},
    ...          "properties": {"layer": "event", "label": "al-Tina"}}]}))
    ...     cfg = merge_layers({"layers": ["checkpoints.geojson"], "events": []}, tmp)
    >>> [e["label"] for e in cfg["events"]], "layers" in cfg
    (['al-Tina'], False)
    """
    paths = cfg.get("layers") or []
    if not paths:
        cfg.pop("layers", None)
        return cfg
    base = Path(base)
    merged = {k: v for k, v in cfg.items() if k != "layers"}
    for spec in paths:
        path = Path(spec) if Path(spec).is_absolute() else base / spec
        part = import_layers(list(read_features(path)))
        for key in ("arrows", "events", "annotations"):
            if part.get(key):
                merged[key] = list(merged.get(key) or []) + part[key]
        if part.get("front") and not (merged.get("front") or {}).get("line"):
            merged["front"] = {**(merged.get("front") or {}), **part["front"]}
        places = (part.get("labels") or {}).get("places")
        if places:
            labels = dict(merged.get("labels") or {})
            labels["places"] = list(labels.get("places") or []) + places
            merged["labels"] = labels
        areas = (part.get("areas_of_control") or {}).get("source", {}).get("features")
        if areas:
            aoc = dict(merged.get("areas_of_control") or {})
            own = _load_features(aoc.get("source"), base)
            aoc["source"] = {"type": "FeatureCollection", "features": own + areas}
            merged["areas_of_control"] = aoc
    return merged


def read_features(path: Path | str) -> list[dict[str, Any]]:
    """GeoJSON features from a ``.geojson`` / ``.json`` or a ``.kml`` file.

    Raises
    ------
    ValueError
        For an extension neither format uses.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".geojson", ".json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "Feature":
            return [data]
        return list(data.get("features", []))
    if suffix == ".kml":
        return from_kml(path.read_text(encoding="utf-8"))
    raise ValueError(f"{path.name}: a layer file is .geojson, .json or .kml")


def to_kml(collection: dict[str, Any]) -> str:
    """Write a FeatureCollection as KML, one Placemark per feature.

    The ``layer`` and every other property go into ExtendedData, so a file
    opened in Google Earth and read back by :func:`from_kml` keeps them.

    Examples
    --------
    >>> fc = export_layers({"events": [{"lon": 22.83, "lat": 15.0, "label": "al-Tina"}]})
    >>> "<name>al-Tina</name>" in to_kml(fc)
    True
    """
    ET.register_namespace("", _KML_NS)
    kml = ET.Element(f"{{{_KML_NS}}}kml")
    doc = ET.SubElement(kml, f"{{{_KML_NS}}}Document")
    meta = collection.get("sprezzature") or {}
    if meta.get("title"):
        ET.SubElement(doc, f"{{{_KML_NS}}}name").text = str(meta["title"])
    for feat in collection.get("features", []):
        props = feat.get("properties") or {}
        mark = ET.SubElement(doc, f"{{{_KML_NS}}}Placemark")
        name = props.get("label") or props.get("text") or props.get("actor") or props.get("layer")
        if name:
            ET.SubElement(mark, f"{{{_KML_NS}}}name").text = str(name)
        data = ET.SubElement(mark, f"{{{_KML_NS}}}ExtendedData")
        for key, value in props.items():
            item = ET.SubElement(data, f"{{{_KML_NS}}}Data", name=str(key))
            ET.SubElement(item, f"{{{_KML_NS}}}value").text = json.dumps(value, ensure_ascii=False)
        _kml_geometry(mark, feat.get("geometry") or {})
    return ET.tostring(kml, encoding="unicode", xml_declaration=True)


def _coords(points: Any) -> str:
    return " ".join(f"{float(p[0])},{float(p[1])}" for p in points)


def _kml_geometry(parent: ET.Element, geom: dict[str, Any]) -> None:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "Point":
        point = ET.SubElement(parent, f"{{{_KML_NS}}}Point")
        ET.SubElement(point, f"{{{_KML_NS}}}coordinates").text = _coords([coords])
    elif gtype == "LineString":
        line = ET.SubElement(parent, f"{{{_KML_NS}}}LineString")
        ET.SubElement(line, f"{{{_KML_NS}}}coordinates").text = _coords(coords)
    elif gtype in ("Polygon", "MultiPolygon"):
        polygons = [coords] if gtype == "Polygon" else coords
        holder = parent
        if len(polygons) > 1:
            holder = ET.SubElement(parent, f"{{{_KML_NS}}}MultiGeometry")
        for rings in polygons:
            poly = ET.SubElement(holder, f"{{{_KML_NS}}}Polygon")
            for i, ring in enumerate(rings):
                tag = "outerBoundaryIs" if i == 0 else "innerBoundaryIs"
                boundary = ET.SubElement(poly, f"{{{_KML_NS}}}{tag}")
                lr = ET.SubElement(boundary, f"{{{_KML_NS}}}LinearRing")
                ET.SubElement(lr, f"{{{_KML_NS}}}coordinates").text = _coords(ring)


def from_kml(text: str) -> list[dict[str, Any]]:
    """Read KML Placemarks as GeoJSON features.

    ExtendedData written by :func:`to_kml` is restored; a Placemark from
    elsewhere keeps its ``name`` and ``description``.

    Examples
    --------
    >>> fc = export_layers({"arrows": [{"line": [[0, 0], [1, 1]], "style": "dashed"}]})
    >>> back = from_kml(to_kml(fc))
    >>> back[0]["properties"]["layer"], back[0]["properties"]["style"], back[0]["geometry"]["type"]
    ('arrow', 'dashed', 'LineString')
    """
    root = ET.fromstring(text)
    ns = {"k": _KML_NS} if root.tag.startswith("{") else {}

    def q(tag: str) -> str:
        return f"k:{tag}" if ns else tag

    def coords(node: ET.Element) -> list[list[float]]:
        raw = (node.findtext(q("coordinates"), "", ns) or "").split()
        return [[float(v) for v in c.split(",")[:2]] for c in raw]

    features: list[dict[str, Any]] = []
    for mark in root.iter(f"{{{_KML_NS}}}Placemark" if ns else "Placemark"):
        props: dict[str, Any] = {}
        for item in mark.findall(f"{q('ExtendedData')}/{q('Data')}", ns):
            raw = item.findtext(q("value"), "", ns)
            try:
                props[item.get("name", "")] = json.loads(raw)
            except (TypeError, ValueError):
                props[item.get("name", "")] = raw
        # A Placemark written by `to_kml` carries its whole block in
        # ExtendedData; its <name> is only the label Google Earth shows, and
        # reading it back would add a key the block never had. A Placemark
        # from elsewhere has no ExtendedData, and its name is all it says.
        if not props:
            for tag in ("name", "description"):
                value = mark.findtext(q(tag), None, ns)
                if value:
                    props[tag] = value
        point = mark.find(f".//{q('Point')}", ns)
        line = mark.find(f".//{q('LineString')}", ns)
        polys = mark.findall(f".//{q('Polygon')}", ns)
        if point is not None:
            geom: dict[str, Any] = {"type": "Point", "coordinates": coords(point)[0]}
        elif line is not None:
            geom = {"type": "LineString", "coordinates": coords(line)}
        elif polys:
            rings = []
            for poly in polys:
                outer = poly.find(f"{q('outerBoundaryIs')}/{q('LinearRing')}", ns)
                inner = poly.findall(f"{q('innerBoundaryIs')}/{q('LinearRing')}", ns)
                rings.append(
                    [coords(outer)] + [coords(r) for r in inner] if outer is not None else []
                )
            geom = (
                {"type": "Polygon", "coordinates": rings[0]}
                if len(rings) == 1
                else {"type": "MultiPolygon", "coordinates": rings}
            )
        else:
            continue
        features.append({"type": "Feature", "geometry": geom, "properties": props})
    return features
