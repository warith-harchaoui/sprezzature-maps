#!/usr/bin/env python3
"""Build the vendored 1:10m river centerlines, ``assets/geo/rivers-10m.geojson``.

Author: Warith HARCHAOUI

The 1:50m rivers the plates had until now hold the trunks of a continent
and little else: on a plate of Czechoslovakia there was no Vltava, on a plate
of Serbia no Morava and no Vardar, and the inside of every country read as
dry ground. Natural Earth's 1:10m centerlines and its European supplement
(both public domain) carry the rivers a regional plate is about.

One repair, and one addition, each kept here where it can be read:

- **The Vardar under the wrong name.** The European supplement names a line
  ``Treska`` with ``name_alt: Vardar``; it runs from the Treska's source
  south of Kičevo to Skopje, then down the Vardar through Veles and
  Gevgelija to the Thermaic Gulf -- a 139 km tributary fused to the main
  stem below their confluence. The line is cut at the confluence and only
  the Treska part kept under that name.
- **The Vardar itself**, from its source at Gostivar to the sea, from
  OpenStreetMap relation 5896030 (ODbL). It carries ``source: osm``, and
  :func:`make_situation_map._attribution_layer` prints the credit ODbL
  requires whenever a plate draws it.

    python scripts/build_rivers_10m.py

downloads the two Natural Earth files and the OSM relation, and writes the
trimmed file: name, scalerank and source per feature, coordinates to three
decimals (about 100 m), simplified to 0.004 degrees.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, shape
from shapely.ops import linemerge, split, unary_union

OUT = Path(__file__).resolve().parents[1] / "assets" / "geo" / "rivers-10m.geojson"
NATURAL_EARTH = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
SOURCES = ("ne_10m_rivers_lake_centerlines.geojson", "ne_10m_rivers_europe.geojson")
#: Tried in order: the public instance answers 502 under load, and a
#: second one answers the same query.
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
VARDAR_RELATION = 5896030
#: Where the Treska meets the Vardar, at Skopje's western edge.
TRESKA_CONFLUENCE = Point(21.333, 42.001)
TOLERANCE = 0.004


def _get(url: str, data: bytes | None = None) -> Any:
    request = urllib.request.Request(url, data=data, headers={"User-Agent": "sprezzature-maps"})
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 (fixed https hosts)
        return json.load(response)


def _feature(geom: Any, name: str, rank: int, source: str) -> dict[str, Any] | None:
    geom = geom.simplify(TOLERANCE)
    if geom.is_empty:
        return None
    lines = [list(part.coords) for part in getattr(geom, "geoms", [geom])]
    coords = [[[round(x, 3), round(y, 3)] for x, y in line] for line in lines if len(line) > 1]
    if not coords:
        return None
    return {
        "type": "Feature",
        "properties": {"name": name, "scalerank": rank, "source": source},
        "geometry": {"type": "MultiLineString", "coordinates": coords},
    }


def _treska(geom: Any) -> Any:
    """The Treska part of the fused line: upstream of the confluence."""
    line = linemerge(geom) if geom.geom_type == "MultiLineString" else geom
    cut = line.interpolate(line.project(TRESKA_CONFLUENCE))
    pieces = split(line, cut.buffer(1e-6)).geoms
    # The Treska rises in the south-west, below Kičevo; the piece that
    # starts nearest its source is the one to keep.
    return min(pieces, key=lambda p: Point(p.coords[0]).distance(Point(20.96, 41.35)))


def _vardar() -> Any:
    query = urllib.parse.urlencode(
        {"data": f"[out:json][timeout:120];rel({VARDAR_RELATION});out geom;"}
    ).encode()
    payload = None
    for attempt in range(3):
        for url in OVERPASS:
            try:
                payload = _get(url, query)
                break
            except OSError as exc:  # urllib's HTTPError and URLError are OSErrors
                print(f"  {url}: {exc} (attempt {attempt + 1})")
        if payload is not None:
            break
    if payload is None:
        raise SystemExit("no Overpass instance answered; run again later")
    relation = payload["elements"][0]
    ways = [
        LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        for m in relation["members"]
        if m.get("type") == "way" and m.get("role") == "main_stream" and m.get("geometry")
    ]
    return linemerge(unary_union(ways))


def main() -> None:
    features: list[dict[str, Any]] = []
    for name in SOURCES:
        for raw in _get(NATURAL_EARTH + name)["features"]:
            props = raw.get("properties") or {}
            label = props.get("name_en") or props.get("name")
            if not label or not raw.get("geometry"):
                continue
            geom = shape(raw["geometry"])
            if label == "Treska" and props.get("name_alt") == "Vardar":
                geom = _treska(geom)
            feat = _feature(geom, str(label), int(props.get("scalerank") or 10), "naturalearth")
            if feat:
                features.append(feat)
    vardar = _feature(_vardar(), "Vardar", 7, "osm")
    if vardar:
        features.append(vardar)
    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    )
    print(f"wrote {OUT.name}: {len(features)} rivers, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
