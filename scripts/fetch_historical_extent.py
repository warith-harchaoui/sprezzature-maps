#!/usr/bin/env python3
"""Fetch a state's dated extent from OpenHistoricalMap, for a ``change`` plate.

Author: Warith HARCHAOUI

A ``change`` plate subtracts two extents, and the subtraction is only as
honest as the two sides: drawn by hand, the earlier one is whatever the
person drawing remembers, and the difference is that memory in a colour
that claims a finding. So the shipped change plates take both sides from
one source under one method -- OpenHistoricalMap, where every state is a
relation with a ``start_date`` and an ``end_date`` -- and this script is
how they were taken, so anyone can take them again.

OpenHistoricalMap data is dedicated to the public domain (CC0) "except
where otherwise noted"; a relation noted otherwise carries a ``license``
tag, and this script refuses one rather than ship it under the wrong terms.

    python scripts/fetch_historical_extent.py 2692764 2747874

writes ``assets/historical-extents/ohm-<id>.geojson`` per relation: one
feature, its outer ways assembled into polygons and simplified to about
half a kilometre, which is below a pixel on any shipped plate.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, mapping
from shapely.ops import polygonize, unary_union

OVERPASS = "https://overpass-api.openhistoricalmap.org/api/interpreter"
OUT = Path(__file__).resolve().parents[1] / "assets" / "historical-extents"
#: Half a kilometre, in degrees at mid-latitudes.
TOLERANCE = 0.005


def _rings(members: list[dict[str, Any]], role: str) -> Any:
    lines = [
        LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        for m in members
        if m.get("type") == "way" and m.get("role", "") == role and m.get("geometry")
    ]
    return unary_union(list(polygonize(unary_union(lines)))) if lines else None


def extent(relation: dict[str, Any]) -> dict[str, Any]:
    """Return one GeoJSON feature for an Overpass relation with geometry."""
    tags = relation.get("tags", {})
    if tags.get("license"):
        raise SystemExit(
            f"relation {relation['id']} is licensed {tags['license']!r}, not "
            "OpenHistoricalMap's default CC0; not shipping it under the wrong terms"
        )
    members = relation["members"]
    outer = unary_union([g for g in (_rings(members, "outer"), _rings(members, "")) if g])
    inner = _rings(members, "inner")
    if inner is not None:
        outer = outer.difference(inner)
    if outer.is_empty:
        raise SystemExit(f"relation {relation['id']} assembled into no polygon")
    shape = outer.simplify(TOLERANCE, preserve_topology=True)
    return {
        "type": "Feature",
        "properties": {
            "actor": tags.get("name:en") or tags.get("name"),
            "start_date": tags.get("start_date"),
            "end_date": tags.get("end_date"),
            "source": f"OpenHistoricalMap relation {relation['id']}",
            "license": "CC0 1.0 (OpenHistoricalMap)",
        },
        "geometry": mapping(shape),
    }


def fetch(relation_id: int) -> Path:
    query = f"[out:json][timeout:120];rel({relation_id});out geom;"
    data = urllib.parse.urlencode({"data": query}).encode()
    request = urllib.request.Request(
        OVERPASS, data=data, headers={"User-Agent": "sprezzature-maps example builder"}
    )
    with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310 (fixed https host)
        payload = json.load(response)
    relation = next(e for e in payload["elements"] if e["type"] == "relation")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"ohm-{relation_id}.geojson"
    feature = extent(relation)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}))
    return path


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    for raw in argv:
        path = fetch(int(raw))
        print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
