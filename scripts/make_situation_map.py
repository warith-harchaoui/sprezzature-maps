#!/usr/bin/env python3
"""Generate a professional, layered *situation map* for any region of the world.

Author: Warith Harchaoui

This reverse-engineers the plate structure that geopolitics data desks use into a
parameterized generator. From one YAML config (a region, a projection, thematic
*areas of control*, forces, events, infrastructure, labels) it emits a single SVG
built as a stack of layers whose names a geopolitics analyst recognizes on sight
(bottom -> top paint order):

1. ``basemap-sea``        — sea fill.
2. ``basemap-bathymetry`` — depth-contour halo radiating from the coast.
3. ``basemap-land``       — land fill.
4. ``areas-of-control``   — territory zones, pastel + white casing; contested = hatch.
5. ``infrastructure``     — roads / highways / airports as hairlines.
6. ``forces``             — unit / actor positions (point markers).
7. ``events``             — incidents (ceasefire points, clashes, strikes).
8. ``annotation-labels``  — letter-spaced place + water labels.
9. ``annotation-furniture`` — title block, north arrow, dual-unit (km + mi) scale bar.
10. ``legend``            — floating legend panel with swatches.
11. ``frame``             — rounded-rectangle panel mask.

The craft signatures reproduced here: an equal-angle **local projection**
(Lambert Conformal Conic auto-centred on the region), a **classed pastel palette**,
**white boundary casing** between adjacent zones, **bathymetry** contours in the
sea, **drop-shadowed** panel + markers, **letter-spaced** uppercase labels, and a
**dual-unit scale bar** — reachable for *any* part of the world, not one example.

Basemap geometry is the vendored, offline Natural Earth land polygon
(``assets/geo/countries-50m.json``); the caller supplies the thematic layers.

Usage
-----
    python make_situation_map.py --config demo.yaml --out demo.svg --render

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np

from _relief import rgba_to_data_uri, sample_terrain_shade, terrain_shade_for_bbox
from _render import svg_example_path, write_svg

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guard
    # ImportError, not SystemExit: this guard fires at module import time,
    # not just when run as a script, so it must stay a catchable Exception
    # subclass for callers like make_figure() or the generator audit that
    # import this module programmatically rather than executing it.
    raise ImportError("PyYAML is required: pip install pyyaml") from exc

try:
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import (
        MultiPolygon,
        Polygon,
        box,
        shape,
    )
    from shapely.ops import transform as shp_transform
    from shapely.ops import unary_union
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "shapely>=2 and pyproj>=3.6 are required: pip install shapely pyproj"
    ) from exc


# --------------------------------------------------------------------------- #
# Vendored basemap (Natural Earth, offline)                                    #
# --------------------------------------------------------------------------- #

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "geo"
_LAND_TOPOJSON = _ASSETS / "countries-50m.json"
# 1:10m Natural Earth admin-0 countries, vendored the same way the 50m/110m
# atlases were: downloaded once, simplified (mapshaper, weighted Visvalingam,
# keep-shapes so small islands survive), quantized to TopoJSON. Only used for
# small bboxes -- see _land_topojson_for_bbox -- where the 50m atlas would
# read visibly facetted/over-smoothed at zoom.
_LAND_TOPOJSON_10M = _ASSETS / "countries-10m.json"
_RIVERS_GEOJSON = _ASSETS / "rivers-50m.geojson"
# Sub-national (admin-1) tier, first of the national/regional cadastral
# sources (task #31: TIGER/IGN/OSM) layered above Natural Earth's admin-0
# atlases -- US Census TIGER/Line state boundaries, public domain, vendored
# the same way (mapshaper, 15% weighted Visvalingam keep-shapes, quantized
# TopoJSON). Only ever consulted when a region's bbox actually falls inside
# the United States -- see _bbox_in_united_states -- so a France or Himalaya
# situation map never pays to load it.
_US_STATES_TOPOJSON = _ASSETS / "us-states.json"
# Coarse pyramid tier (3% weighted Visvalingam, re-derived from the same raw
# TIGER shapefile rather than re-simplifying the fine TopoJSON, to avoid
# compounding two simplification passes) for whole-country-or-wider US
# renders, where the fine tier's extra detail cannot survive the render's
# own pixel density anyway -- same rationale, and the same bbox-span
# threshold, as _land_topojson_for_bbox's 50m/10m country-boundary choice.
_US_STATES_TOPOJSON_COARSE = _ASSETS / "us-states-coarse.json"
# The vendored file's own bounds (CONUS + Alaska + Hawaii + PR/Guam/USVI/
# N. Mariana Is., i.e. every TIGER "state" record) -- used as a cheap bbox
# pre-filter so non-US callers skip the TopoJSON load entirely.
_US_STATES_BOUNDS = (-179.24, -14.61, 179.86, 71.44)

# Second admin-1 source (task #31): France's 18 regions (13 metropolitan +
# 5 overseas -- Guadeloupe, Martinique, Guyane, La Reunion, Mayotte), sourced
# from IGN's ADMIN EXPRESS (the same national mapping-agency database TIGER
# is for the US) via the community-maintained gregoiredavid/france-geojson
# GeoJSON mirror, Licence Ouverte / Etalab 2.0. Vendored the same way as
# every other tier here: mapshaper, 15% weighted Visvalingam keep-shapes,
# quantized TopoJSON.
_FR_REGIONS_TOPOJSON = _ASSETS / "fr-regions.json"
# Coarse pyramid tier -- same rationale as _US_STATES_TOPOJSON_COARSE.
_FR_REGIONS_TOPOJSON_COARSE = _ASSETS / "fr-regions-coarse.json"
# Metropolitan France plus every overseas region -- Guyane (South America)
# pushes the west bound out to the Americas and La Reunion/Mayotte (Indian
# Ocean) push the east bound past Africa, so this bbox is wide for the same
# reason _US_STATES_BOUNDS is (a scattered national territory), not a bug.
_FR_REGIONS_BOUNDS = (-61.81, -21.39, 55.84, 51.09)

# Third admin-1 source (task #31), and the only one that is a registry of
# several countries rather than a single file: OpenStreetMap (c)
# OpenStreetMap contributors, ODbL 1.0 -- the first ODbL-licensed data
# this repo vendors, unlike TIGER (public domain) and IGN/ADMIN-EXPRESS
# (Licence Ouverte 2.0). ODbL's share-alike clause binds a *produced
# work* (a rendered map) only to attribution, not redistribution of the
# underlying data under ODbL -- but each vendored file below *is* a
# derivative database extracted from OSM, so it is itself ODbL-licensed
# and must carry the same attribution; see the provenance table in
# doc/CARTOGRAPHY.tex and the README credit.
#
# Every entry was fetched the same way: one Overpass API query
# (boundary=administrative at the country's state-equivalent
# admin_level, "out geom" so each way member carries its own lon/lat
# geometry inline) -- no OSM PBF/osmium/GDAL needed. Assembled with
# shapely.ops.polygonize (outer-role ways unioned, inner-role ways
# subtracted as holes) since Overpass returns each multipolygon relation
# as loose way segments, not ready-made rings. A registry keyed by
# country, not one loader function per country, since three near-
# identical (path, bounds, admin_level, feature-count) tuples is the
# point past which copy-pasting :func:`load_us_states`-style boilerplate
# a third time stops paying for itself; adding a fourth OSM country is a
# vendoring pass (Overpass query + mapshaper) and one registry entry,
# not new code.
#
# Switzerland (26 cantons) was the pilot specifically because several
# cantons, Appenzell Innerrhoden/Ausserrhoden most notably, interleave
# into mutual enclaves rather than forming simple single-ring shapes, a
# real test of the outer/inner assembly rather than a token one. Germany
# (16 Bundesländer) and Italy (20 regioni) followed once that path was
# proven, both also admin_level=4 in OSM's tagging scheme like
# Switzerland (the level is a national convention, not a global
# constant -- worth re-verifying per country before adding a fifth).
# Each entry: (fine-tier path, coarse-tier path, bounds, TopoJSON object
# name). The coarse tier (3% weighted Visvalingam, re-derived from the same
# raw Overpass extract rather than re-simplifying the fine TopoJSON) is
# picked instead of the fine one past the same bbox-span threshold as
# _US_STATES_TOPOJSON_COARSE -- see _admin1_tier_path.
_OSM_ADMIN1_SOURCES: dict[str, tuple[Path, Path, tuple[float, float, float, float], str]] = {
    "CH": (_ASSETS / "ch-cantons.json", _ASSETS / "ch-cantons-coarse.json",
           (5.96, 45.82, 10.49, 47.81), "cantons"),
    "DE": (_ASSETS / "de-states.json", _ASSETS / "de-states-coarse.json",
           (5.87, 47.27, 15.04, 55.10), "states"),
    "IT": (_ASSETS / "it-regions.json", _ASSETS / "it-regions-coarse.json",
           (6.63, 35.49, 18.52, 47.09), "regions"),
}

# Admin-2 (second sub-national tier, one level finer than admin-1) registry,
# same shape as :data:`_OSM_ADMIN1_SOURCES` for the same reason: a registry
# from the start rather than a bespoke loader function per source, since
# admin-1 already proved that pattern stops paying for itself past one
# instance. The only entry so far is France's 101 departments (96
# metropolitan plus 5 overseas), the same IGN ADMIN-EXPRESS product
# admin-1's `fr-regions.json` came from, via the same `france-geojson`
# mirror -- vendored once more at the finer granularity. US counties
# (3000+, a much heavier vendoring pass) and Swiss districts remain
# unvendored; see the roadmap in doc/CARTOGRAPHY.tex.
_ADMIN2_SOURCES: dict[str, tuple[Path, tuple[float, float, float, float], str]] = {
    "FR": (_ASSETS / "fr-departments.json", (-61.81, -21.39, 55.84, 51.09), "departments"),
}

# Admin-2 lines are one level more detailed than admin-1 again, so they only
# earn their clutter once a render is zoomed in past a single admin-1 unit,
# not merely past the whole country the way admin-1 itself activates at 25
# degrees. Roughly the angular span of one to a few French regions, chosen
# empirically the same way :data:`_TEN_M_BBOX_DEGREES_THRESHOLD` was: narrow
# enough that a whole-country plate (25deg+) never shows 101 department
# lines at once, wide enough that a single-region zoom still gets them.
_ADMIN2_BBOX_DEGREES_THRESHOLD = 8.0

# A region bbox whose longer side is narrower than this many degrees reads as
# "a single country or a small sub-region" rather than "a continent-scale
# view" -- that is the cutoff where switching from 1:50m to the heavier
# 1:10m basemap actually buys visible coastline/border fidelity instead of
# just more file weight for detail no one will see at that zoom.
_TEN_M_BBOX_DEGREES_THRESHOLD = 25.0


def _land_topojson_for_bbox(bbox: Optional[Iterable[float]]) -> Path:
    """Pick the 50m or 10m vendored basemap tier to match a region's bbox.

    Parameters
    ----------
    bbox : iterable of float or None
        ``(west, south, east, north)`` in degrees. ``None`` means the
        caller has no region context (e.g. a bare ``load_country`` call
        with no surrounding map) -- falls back to the pre-existing 50m
        default so that behaviour does not silently change for callers
        written before this tier selection existed.

    Returns
    -------
    pathlib.Path
        :data:`_LAND_TOPOJSON_10M` when the bbox's longer side is
        narrower than :data:`_TEN_M_BBOX_DEGREES_THRESHOLD`, otherwise
        :data:`_LAND_TOPOJSON`.

    Examples
    --------
    >>> _land_topojson_for_bbox((-5.0, 41.0, 10.0, 51.0)).name
    'countries-10m.json'
    >>> _land_topojson_for_bbox((-11.0, 35.0, 30.0, 60.0)).name
    'countries-50m.json'
    >>> _land_topojson_for_bbox(None).name
    'countries-50m.json'
    """
    if bbox is None:
        return _LAND_TOPOJSON
    west, south, east, north = bbox
    # The "longer side" (not the area) is what determines whether a
    # viewer will actually zoom in far enough to see 10m-vs-50m detail --
    # a very wide-but-short strip (e.g. a coastline survey) still reads
    # as continent-scale on its long axis even if its short axis is small.
    span_degrees = max(east - west, north - south)
    return _LAND_TOPOJSON_10M if span_degrees < _TEN_M_BBOX_DEGREES_THRESHOLD else _LAND_TOPOJSON


def _decode_topojson_object(topo: dict[str, Any], name: str) -> Any:
    """Decode one object of a TopoJSON topology into a shapely geometry (lon/lat).

    Implements the minimal TopoJSON contract: quantised delta-encoded arcs plus a
    ``scale``/``translate`` transform, stitched into GeoJSON-style rings and unioned.

    Parameters
    ----------
    topo : dict
        Parsed TopoJSON topology.
    name : str
        Key inside ``topo["objects"]`` to decode (e.g. ``"land"``).

    Returns
    -------
    shapely geometry
        The dissolved geometry of the requested object, in WGS84 lon/lat.
    """
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        # Negative index => reversed arc (~index).
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        points: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            points.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return points[::-1] if reverse else points

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    geoms = []
    obj = topo["objects"][name]
    for geom in obj["geometries"]:
        gtype = geom["type"]
        if gtype == "Polygon":
            rings = [stitch(part) for part in geom["arcs"]]
            geoms.append(Polygon(rings[0], rings[1:]))
        elif gtype == "MultiPolygon":
            polys = []
            for poly in geom["arcs"]:
                rings = [stitch(part) for part in poly]
                polys.append(Polygon(rings[0], rings[1:]))
            geoms.append(MultiPolygon(polys))
    # Natural Earth polygons can be individually invalid (self-touching rings);
    # repair each rather than a fragile world-wide union — the caller clips to a
    # bounding box, so a MultiPolygon of validated pieces is sufficient.
    fixed = [make_valid(g) for g in geoms]
    return unary_union(fixed)


def load_land(bbox: Optional[Iterable[float]] = None) -> Any:
    """Return the dissolved world land polygon (WGS84), from the vendored basemap.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees of the region this land
        polygon will be clipped to by the caller. Selects the 10m or 50m
        basemap tier via :func:`_land_topojson_for_bbox`; ``None`` (the
        default) keeps the pre-existing 50m behaviour.

    Returns
    -------
    shapely geometry
        The dissolved land polygon, WGS84 lon/lat.
    """
    topo_path = _land_topojson_for_bbox(bbox)
    topo = json.loads(topo_path.read_text())
    # The 50m/110m atlases carry a pre-dissolved "land" object; the 10m
    # atlas only carries "countries" (dissolving 258 country polygons here
    # gives the identical silhouette a dedicated "land" object would, so
    # there is no need to vendor a second, redundant object for it).
    object_name = "land" if "land" in topo["objects"] else "countries"
    return _decode_topojson_object(topo, object_name)


def load_country(name: str, bbox: Optional[Iterable[float]] = None) -> Any:
    """Return the polygon of a single country by Natural Earth ``name`` (WGS84).

    Lets a caller partition a *real* national outline into thematic zones — the
    honest way to build a situation map for a named country rather than tracing
    borders by hand.

    Parameters
    ----------
    name : str
        Country name as spelled in the vendored ``countries`` object
        (e.g. ``"Ukraine"``, ``"France"``).
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees, forwarded to
        :func:`_land_topojson_for_bbox` to pick the 10m or 50m tier.
        ``None`` (the default) keeps the pre-existing 50m behaviour.

    Returns
    -------
    shapely geometry
        The (repaired) country polygon.

    Raises
    ------
    KeyError
        If no country with that name exists in the basemap.
    """
    topo = json.loads(_land_topojson_for_bbox(bbox).read_text())
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    for geom in topo["objects"]["countries"]["geometries"]:
        if geom.get("properties", {}).get("name") != name:
            continue
        if geom["type"] == "Polygon":
            rings = [stitch(part) for part in geom["arcs"]]
            return make_valid(Polygon(rings[0], rings[1:]))
        polys = []
        for poly in geom["arcs"]:
            rings = [stitch(part) for part in poly]
            polys.append(Polygon(rings[0], rings[1:]))
        return make_valid(MultiPolygon(polys))
    raise KeyError(f"country not found in basemap: {name!r}")


def load_countries(bbox: Optional[Iterable[float]] = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every country in the vendored basemap (WGS84).

    Lets the map draw real international frontiers and label the neighbours, so a
    situation plate carries its surrounding geography instead of a lone outline.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees, forwarded to
        :func:`_land_topojson_for_bbox` to pick the 10m or 50m tier.
        ``None`` (the default) keeps the pre-existing 50m behaviour.
    """
    topo = json.loads(_land_topojson_for_bbox(bbox).read_text())
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    out: list[tuple[str, Any]] = []
    for geom in topo["objects"]["countries"]["geometries"]:
        name = geom.get("properties", {}).get("name", "")
        try:
            if geom["type"] == "Polygon":
                rings = [stitch(part) for part in geom["arcs"]]
                poly = make_valid(Polygon(rings[0], rings[1:]))
            else:
                polys = []
                for part in geom["arcs"]:
                    rings = [stitch(r) for r in part]
                    polys.append(Polygon(rings[0], rings[1:]))
                poly = make_valid(MultiPolygon(polys))
        except Exception:  # skip a malformed geometry rather than fail the plate
            continue
        out.append((name, poly))
    return out


def _bbox_in_united_states(bbox: Optional[Iterable[float]]) -> bool:
    """Cheaply test whether a region bbox falls inside the vendored TIGER extent.

    Parameters
    ----------
    bbox : iterable of float or None
        ``(west, south, east, north)`` in degrees, or ``None`` (no region
        context -- returns ``False``, matching how the other tier
        selectors treat a missing bbox as "no info, do not opt in").

    Returns
    -------
    bool
        ``True`` when the bbox overlaps :data:`_US_STATES_BOUNDS`. A
        bounds overlap, not a true point-in-polygon test: cheap, and the
        caller (:func:`load_us_states`) already discards any state whose
        real geometry does not intersect the region, so a false positive
        here only costs one extra TopoJSON load, never a wrong border.
    """
    return _bbox_overlaps(bbox, _US_STATES_BOUNDS)


def _named_polygons_from_topojson(topo: dict[str, Any], object_name: str) -> list[tuple[str, Any]]:
    """Decode every feature of one TopoJSON object into ``(name, polygon)`` pairs.

    Shared arc-decoding core for the admin-1 loaders (:func:`load_us_states`,
    :func:`load_fr_regions`) -- each vendored the same way (mapshaper,
    delta-encoded quantized arcs) but from a different national source, so the
    stitching/repair logic is written once here rather than per source.

    Parameters
    ----------
    topo : dict
        Parsed TopoJSON topology.
    object_name : str
        Key inside ``topo["objects"]`` to decode.

    Returns
    -------
    list of (str, shapely geometry)
        Feature ``name`` property paired with its (repaired) polygon, WGS84
        lon/lat. A feature whose geometry cannot be repaired is skipped
        rather than failing the whole plate.
    """
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    out: list[tuple[str, Any]] = []
    for geom in topo["objects"][object_name]["geometries"]:
        name = geom.get("properties", {}).get("name", "")
        try:
            if geom["type"] == "Polygon":
                rings = [stitch(part) for part in geom["arcs"]]
                poly = make_valid(Polygon(rings[0], rings[1:]))
            else:
                polys = []
                for part in geom["arcs"]:
                    rings = [stitch(r) for r in part]
                    polys.append(Polygon(rings[0], rings[1:]))
                poly = make_valid(MultiPolygon(polys))
        except Exception:  # skip a malformed geometry rather than fail the plate
            continue
        out.append((name, poly))
    return out


def load_us_states(bbox: Optional[Iterable[float]] = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every US state/territory that overlaps a bbox.

    The admin-1 (sub-national) counterpart to :func:`load_countries`, from the
    vendored TIGER/Line basemap -- lets a US-region situation map draw real
    state boundaries instead of stopping at the national frontier.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees. When the bbox does not
        overlap the vendored TIGER extent (see :func:`_bbox_in_united_states`),
        the TopoJSON is not even loaded and an empty list is returned --
        this is what makes calling it unconditionally cheap for non-US maps.

    Returns
    -------
    list of (str, shapely geometry)
        State/territory name paired with its (repaired) polygon, WGS84
        lon/lat.
    """
    if not _bbox_in_united_states(bbox):
        return []
    path = _admin1_tier_path(bbox, _US_STATES_TOPOJSON, _US_STATES_TOPOJSON_COARSE)
    topo = json.loads(path.read_text())
    return _named_polygons_from_topojson(topo, "states")


def _bbox_in_france(bbox: Optional[Iterable[float]]) -> bool:
    """Cheaply test whether a region bbox falls inside the vendored IGN extent.

    Same bounds-overlap contract as :func:`_bbox_in_united_states`, against
    :data:`_FR_REGIONS_BOUNDS` instead.
    """
    return _bbox_overlaps(bbox, _FR_REGIONS_BOUNDS)


def load_fr_regions(bbox: Optional[Iterable[float]] = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every French region that overlaps a bbox.

    The IGN/ADMIN-EXPRESS counterpart to :func:`load_us_states` -- lets a
    France-region situation map draw real regional boundaries instead of
    stopping at the national frontier.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees. When the bbox does not
        overlap the vendored extent (see :func:`_bbox_in_france`), the
        TopoJSON is not even loaded and an empty list is returned -- this is
        what makes calling it unconditionally cheap for non-France maps.

    Returns
    -------
    list of (str, shapely geometry)
        Region name paired with its (repaired) polygon, WGS84 lon/lat.
    """
    if not _bbox_in_france(bbox):
        return []
    path = _admin1_tier_path(bbox, _FR_REGIONS_TOPOJSON, _FR_REGIONS_TOPOJSON_COARSE)
    topo = json.loads(path.read_text())
    return _named_polygons_from_topojson(topo, "regions")


def _bbox_overlaps(bbox: Optional[Iterable[float]],
                   bounds: tuple[float, float, float, float]) -> bool:
    """Cheap bounds-overlap test shared by every admin-1 source's bbox pre-filter.

    Parameters
    ----------
    bbox : iterable of float or None
        ``(west, south, east, north)`` in degrees, or ``None`` (no region
        context -- returns ``False``, so a missing bbox never opts in).
    bounds : (float, float, float, float)
        The candidate source's own ``(west, south, east, north)`` extent.

    Returns
    -------
    bool
        A bounds overlap, not a true point-in-polygon test: cheap, and
        deliberately biased toward false positives over false negatives,
        since every caller already re-checks with a real per-feature
        intersection before drawing anything.
    """
    if bbox is None:
        return False
    west, south, east, north = bbox
    b_west, b_south, b_east, b_north = bounds
    return west <= b_east and east >= b_west and south <= b_north and north >= b_south


def _admin1_tier_path(bbox: Optional[Iterable[float]], fine_path: Path, coarse_path: Path) -> Path:
    """Pick the fine or coarse simplification tier for an admin-1/admin-2 source.

    Same algorithmic-tier-selection pattern as :func:`_land_topojson_for_bbox`
    (which the admin-0 country boundaries already use), reusing its exact
    threshold rather than inventing a second magic number: an admin-1
    boundary render only needs the coarse tier's lighter weight past the
    same bbox span where the country-boundary tier itself already drops to
    1:50m, since that is where the fine tier's extra vertices stop being
    visible at the render's own pixel density.

    Parameters
    ----------
    bbox : iterable of float or None
        ``(west, south, east, north)`` in degrees. ``None`` keeps the fine
        tier, matching how a missing bbox context is treated elsewhere in
        this module (no info to downgrade on).
    fine_path, coarse_path : pathlib.Path
        The two vendored tiers for one source.

    Returns
    -------
    pathlib.Path
        ``coarse_path`` when the bbox's longer side is at least
        :data:`_TEN_M_BBOX_DEGREES_THRESHOLD`, otherwise ``fine_path``.
    """
    if bbox is None:
        return fine_path
    west, south, east, north = bbox
    span = max(east - west, north - south)
    return coarse_path if span >= _TEN_M_BBOX_DEGREES_THRESHOLD else fine_path


def _bbox_in_osm_admin1(bbox: Optional[Iterable[float]]) -> bool:
    """Cheaply test whether a region bbox overlaps *any* vendored OSM country.

    Used by :func:`_attribution_layer` to decide whether the ODbL credit is
    owed, without caring which of :data:`_OSM_ADMIN1_SOURCES` matched.
    """
    return any(_bbox_overlaps(bbox, bounds) for _, _, bounds, _ in _OSM_ADMIN1_SOURCES.values())


def load_osm_admin1(bbox: Optional[Iterable[float]] = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every OSM admin-1 feature that overlaps a bbox.

    The OpenStreetMap counterpart to :func:`load_us_states` /
    :func:`load_fr_regions` -- lets a situation map in any country listed in
    :data:`_OSM_ADMIN1_SOURCES` draw real sub-national boundaries instead of
    stopping at the national frontier. Data (c) OpenStreetMap contributors,
    ODbL 1.0 -- any rendered map using this layer must carry that
    attribution; :func:`_attribution_layer` adds it automatically to any
    plate that actually draws from one of these sources.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees. Only the registry
        entries whose own extent overlaps this bbox are even read from
        disk (see :func:`_bbox_overlaps`) -- this is what makes calling it
        unconditionally cheap for a situation map outside every vendored
        OSM country, and cheap-per-extra-country as the registry grows.

    Returns
    -------
    list of (str, shapely geometry)
        Feature name paired with its (repaired) polygon, WGS84 lon/lat,
        pooled across every matching country.
    """
    out: list[tuple[str, Any]] = []
    for fine_path, coarse_path, bounds, object_name in _OSM_ADMIN1_SOURCES.values():
        if not _bbox_overlaps(bbox, bounds):
            continue
        path = _admin1_tier_path(bbox, fine_path, coarse_path)
        topo = json.loads(path.read_text())
        out.extend(_named_polygons_from_topojson(topo, object_name))
    return out


def load_admin2(bbox: Optional[Iterable[float]] = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every admin-2 feature that overlaps a bbox.

    One level finer than :func:`load_us_states`/:func:`load_fr_regions`/
    :func:`load_osm_admin1` -- currently France's departments only (see
    :data:`_ADMIN2_SOURCES`), drawn by :func:`_admin2_borders_layer` rather
    than :func:`_internal_borders_layer`, since admin-2 additionally gates
    on zoom level (:data:`_ADMIN2_BBOX_DEGREES_THRESHOLD`), not just bbox
    overlap: a whole-country plate should not show a hundred department
    lines even where the data is available.

    Parameters
    ----------
    bbox : iterable of float or None, optional
        ``(west, south, east, north)`` in degrees. Only registry entries
        whose own extent overlaps this bbox are read from disk.

    Returns
    -------
    list of (str, shapely geometry)
        Feature name paired with its (repaired) polygon, WGS84 lon/lat.
    """
    out: list[tuple[str, Any]] = []
    for topo_path, bounds, object_name in _ADMIN2_SOURCES.values():
        if not _bbox_overlaps(bbox, bounds):
            continue
        topo = json.loads(topo_path.read_text())
        out.extend(_named_polygons_from_topojson(topo, object_name))
    return out


def load_rivers() -> list[tuple[Any, str, int]]:
    """Return ``(geometry, name, scalerank)`` for the vendored river centerlines.

    Natural Earth 50m rivers + lake centerlines, trimmed to named features. Lower
    ``scalerank`` means a more prominent river (used to decide what gets labelled).
    """
    if not _RIVERS_GEOJSON.is_file():
        return []
    data = json.loads(_RIVERS_GEOJSON.read_text())
    out: list[tuple[Any, str, int]] = []
    for feat in data.get("features", []):
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        props = feat.get("properties", {})
        out.append((geom, props.get("name", ""), int(props.get("scalerank", 10))))
    return out


# --------------------------------------------------------------------------- #
# Projection                                                                   #
# --------------------------------------------------------------------------- #


def build_projection(bbox: list[float], epsg: Optional[str]) -> Transformer:
    """Return a lon/lat -> planar-metre transformer suited to ``bbox``.

    When ``epsg`` is ``None`` (or ``"auto"``) a Lambert Conformal Conic is centred
    on the region, with standard parallels at the one-sixth / five-sixth latitudes
    (the classic two-thirds rule) — conformal, so shapes and angles stay true at
    the scale of a city or a province.

    Parameters
    ----------
    bbox : list of float
        ``[west, south, east, north]`` in degrees.
    epsg : str or None
        An explicit CRS such as ``"EPSG:3857"``, or ``None``/``"auto"``.

    Returns
    -------
    pyproj.Transformer
        Transformer from ``EPSG:4326`` to the chosen projected CRS.
    """
    if epsg and epsg.lower() != "auto":
        return Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    west, south, east, north = bbox
    lon0 = (west + east) / 2.0
    lat0 = (south + north) / 2.0
    lat1 = south + (north - south) / 6.0
    lat2 = north - (north - south) / 6.0
    proj4 = (
        f"+proj=lcc +lat_1={lat1} +lat_2={lat2} +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    return Transformer.from_crs("EPSG:4326", proj4, always_xy=True)


# --------------------------------------------------------------------------- #
# Viewport: project + fit to an SVG canvas (y flipped)                          #
# --------------------------------------------------------------------------- #


def make_viewport(
    proj: Transformer, bbox: list[float], width: float, pad: float
) -> dict[str, Any]:
    """Project ``bbox`` and return a viewport mapping planar metres -> SVG units.

    Returns a dict-record with the canvas size, a ``to_svg(x, y)`` closure (flips y),
    and ``m_per_unit`` so the scale bar can be drawn in true kilometres.
    """
    west, south, east, north = bbox
    # Sample the projected outline (edges, not just corners) so a curved projection
    # is bounded correctly.
    xs: list[float] = []
    ys: list[float] = []
    steps = 24
    for t in range(steps + 1):
        f = t / steps
        for lon, lat in (
            (west + (east - west) * f, south),
            (west + (east - west) * f, north),
            (west, south + (north - south) * f),
            (east, south + (north - south) * f),
        ):
            x, y = proj.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span_x = maxx - minx
    span_y = maxy - miny
    inner_w = width - 2 * pad
    scale = inner_w / span_x
    height = span_y * scale + 2 * pad

    def to_svg(x: float, y: float) -> tuple[float, float]:
        sx = pad + (x - minx) * scale
        sy = pad + (maxy - y) * scale  # flip: projected up -> SVG down
        return sx, sy

    def to_world(sx: Any, sy: Any) -> tuple[Any, Any]:
        """Invert :func:`to_svg`: SVG pixel(s) -> planar metres.

        Exact algebraic inverse of ``to_svg`` (no iteration needed, unlike
        Equal Earth's inverse projection in ``make_choropleth.py`` -- this
        only undoes the *viewport* fit, not the map projection itself).
        Accepts plain floats or numpy arrays -- the relief compositing in
        :func:`build_map` calls this vectorised over a whole pixel grid.
        """
        x = minx + (sx - pad) / scale
        y = maxy - (sy - pad) / scale
        return x, y

    return {
        "width": width,
        "height": height,
        "to_svg": to_svg,
        "to_world": to_world,
        "m_per_unit": 1.0 / scale,
        # Type scale: label/furniture sizes track the plate width so a large
        # plate does not end up with tiny print. Calibrated to a 1000-unit plate.
        "ts": max(1.0, width / 1000.0),
        "bbox": bbox,
        "proj": proj,
    }


# --------------------------------------------------------------------------- #
# Geometry -> SVG path                                                          #
# --------------------------------------------------------------------------- #


def _ring_to_path(coords: Iterable[tuple[float, float]], vp: dict[str, Any]) -> str:
    to_svg = vp["to_svg"]
    proj = vp["proj"]
    out: list[str] = []
    for i, (lon, lat) in enumerate(coords):
        x, y = proj.transform(lon, lat)
        sx, sy = to_svg(x, y)
        out.append(f"{'M' if i == 0 else 'L'}{sx:.2f},{sy:.2f}")
    out.append("Z")
    return "".join(out)


def geom_to_path(geom: Any, vp: dict[str, Any]) -> str:
    """Convert a (Multi)Polygon in lon/lat into an SVG path ``d`` string."""
    parts: list[str] = []
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        if poly.is_empty:
            continue
        parts.append(_ring_to_path(poly.exterior.coords, vp))
        for hole in poly.interiors:
            parts.append(_ring_to_path(hole.coords, vp))
    return " ".join(parts)


def _project_geom(geom: Any, proj: Transformer) -> Any:
    """Return ``geom`` reprojected from lon/lat into the projected CRS (metres)."""
    return shp_transform(lambda xs, ys: proj.transform(xs, ys), geom)


def _projected_ring_to_path(coords: Iterable[tuple[float, float]], vp: dict[str, Any]) -> str:
    to_svg = vp["to_svg"]
    out: list[str] = []
    for i, (x, y) in enumerate(coords):
        sx, sy = to_svg(x, y)
        out.append(f"{'M' if i == 0 else 'L'}{sx:.2f},{sy:.2f}")
    return "".join(out)


def projected_geom_to_path(geom: Any, vp: dict[str, Any], close: bool = True) -> str:
    """Convert a geometry *already in projected metres* into an SVG path string."""
    parts: list[str] = []
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            if poly.is_empty:
                continue
            parts.append(_projected_ring_to_path(poly.exterior.coords, vp) + "Z")
            for hole in poly.interiors:
                parts.append(_projected_ring_to_path(hole.coords, vp) + "Z")
    elif geom.geom_type in ("LineString", "MultiLineString"):
        lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for line in lines:
            if line.is_empty:
                continue
            parts.append(_projected_ring_to_path(line.coords, vp) + ("Z" if close else ""))
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# SVG helpers: defs, letter-spaced text, scale bar, north arrow                 #
# --------------------------------------------------------------------------- #

# Cartographic sans; falls back gracefully. Honors the three-Roboto rule of the
# stack when no font is pinned in the config.
_DEFAULT_FONT = "Roboto, 'Helvetica Neue', Arial, sans-serif"


def svg_defs(contested_hatch: str = "#b03a3a") -> str:
    """Return the ``<defs>`` block: soft drop-shadows, the contested hatch, markers.

    Parameters
    ----------
    contested_hatch : str
        Stroke colour of the diagonal hatch used to render a contested zone; it
        tracks the map's contested fill so the hatch reads as "the same category,
        emphasised" rather than an unrelated red.
    """
    return (
        '<defs>'
        '<filter id="panel-shadow" x="-10%" y="-10%" width="120%" height="120%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000" flood-opacity="0.18"/>'
        '</filter>'
        '<filter id="marker-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#000" flood-opacity="0.35"/>'
        '</filter>'
        # A soft label halo used for the front-line callout and title underline.
        '<filter id="soft-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="0.6" stdDeviation="0.9" flood-color="#000" flood-opacity="0.25"/>'
        '</filter>'
        f'<pattern id="hatch-contested" width="6.5" height="6.5" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse">'
        f'<line x1="0" y1="0" x2="0" y2="6.5" stroke="{contested_hatch}" stroke-width="1.25" '
        'stroke-opacity="0.6"/>'
        '</pattern>'
        '</defs>'
    )


def tracked_text(
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    fill: str,
    tracking: float,
    weight: str = "400",
    anchor: str = "middle",
    upper: bool = True,
    font: str = _DEFAULT_FONT,
) -> str:
    """Return a ``<text>`` with letter-spacing — the cartographer's tracked label."""
    label = text.upper() if upper else text
    # Paint-order halo: a white stroke drawn *under* the fill so the label stays
    # legible over land, sea or any zone colour — standard cartographic practice.
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{font}" font-size="{size:.1f}" font-weight="{weight}" '
        f'letter-spacing="{tracking:.2f}" fill="{fill}" '
        f'paint-order="stroke" stroke="#ffffff" stroke-width="{max(2.0, size * 0.28):.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round">{_esc(label)}</text>'
    )


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _nice_round(value: float) -> float:
    """Return a cartographer-friendly round number <= ``value`` (1/2/5 x 10^k)."""
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for mult in (5, 2, 1):
        if mult * base <= value:
            return mult * base
    return base


def scale_bar(x: float, y: float, vp: dict[str, Any]) -> str:
    """Return a dual-unit (km + mi) scale bar sized to a round distance on the map."""
    m_per_unit = vp["m_per_unit"]
    target_units = min(vp["width"] * 0.22, 180)  # aim ~1/5 canvas, capped
    km = _nice_round(target_units * m_per_unit / 1000.0)
    mi = _nice_round(target_units * m_per_unit / 1609.34)
    km_len = km * 1000.0 / m_per_unit
    mi_len = mi * 1609.34 / m_per_unit
    ink = "#1b2733"
    ts = vp["ts"]
    fs = 10 * ts
    hw = 2.8 * ts  # bar half-height

    def bar(y0: float, length: float, total: str, unit: str) -> str:
        half = length / 2
        return (
            f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x + length:.1f}" y2="{y0:.1f}" '
            f'stroke="{ink}" stroke-width="{2.2 * ts:.1f}"/>'
            f'<rect x="{x:.1f}" y="{y0 - hw:.1f}" width="{half:.1f}" height="{2 * hw:.1f}" '
            f'fill="#fff" stroke="{ink}" stroke-width="0.8"/>'
            f'<rect x="{x + half:.1f}" y="{y0 - hw:.1f}" width="{half:.1f}" height="{2 * hw:.1f}" '
            f'fill="{ink}"/>'
            f'<text x="{x:.1f}" y="{y0 - 6 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{fs:.1f}" fill="{ink}">0</text>'
            f'<text x="{x + length:.1f}" y="{y0 - 6 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{fs:.1f}" fill="{ink}" text-anchor="end">{total}{unit}</text>'
        )

    return (
        f'<g id="scale-bar">{bar(y, km_len, _fmt_num(km), "KM")}'
        f'{bar(y + 20 * ts, mi_len, _fmt_num(mi), "MI")}</g>'
    )


def _fmt_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _capital_star(cx: float, cy: float, r: float) -> str:
    """Return a five-point star inside a white ring — the national-capital glyph."""
    pts: list[str] = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 2.2:.1f}" fill="#ffffff" '
        f'fill-opacity="0.9"/>'
        f'<polygon points="{" ".join(pts)}" fill="#2f343a" stroke="#ffffff" '
        f'stroke-width="1.1" stroke-linejoin="round"/>'
    )


def north_arrow(x: float, y: float, ts: float = 1.0) -> str:
    """Return a filled north arrow with an 'N', scaled by ``ts``."""
    ink = "#1b2733"
    return (
        f'<g id="north-arrow" transform="translate({x:.1f},{y:.1f}) scale({ts:.2f})">'
        f'<path d="M0,-14 L5,6 L0,1 L-5,6 Z" fill="{ink}"/>'
        f'<text x="0" y="20" text-anchor="middle" font-family="{_DEFAULT_FONT}" '
        f'font-size="11" font-weight="600" fill="{ink}">N</text></g>'
    )


# --------------------------------------------------------------------------- #
# Plate assembly                                                                #
# --------------------------------------------------------------------------- #


def _relief_layer(
    vp: dict[str, Any],
    proj: Transformer,
    pad: float,
    width: float,
    height: float,
    clip_path_d: str,
    bbox: list[float],
) -> str:
    """Return a base64 ``<image>`` of real-elevation terrain shading, reprojected to this plate's LCC.

    Computes a hillshade + fractional-Laplacian "texture shading" blend
    (:func:`_relief.terrain_shade_for_bbox`) from the vendored GMTED2010
    elevation grid, on the *region's own* equirectangular window -- not the
    pre-rendered world raster ``make_choropleth.py`` samples -- then
    reprojects that into this plate's Lambert Conformal Conic. LCC has an
    exact analytic inverse (``pyproj`` provides it directly), unlike Equal
    Earth, which needed Newton-Raphson (see ``_equal_earth_invert_batch`` in
    ``make_choropleth.py``). Every point in the plotted rectangle is also
    guaranteed valid (a real (lon, lat) exists) since LCC is well-behaved
    across any bounded region near its own centre -- no validity mask is
    needed the way Equal Earth's curved world outline required one.

    Parameters
    ----------
    vp : dict
        The viewport record from :func:`make_viewport` (uses ``to_world``).
    proj : pyproj.Transformer
        The same lon/lat -> planar-metres transformer the rest of the plate
        uses, inverted here via ``direction="INVERSE"``.
    pad : float
        Panel padding in SVG units -- the relief image is placed inside it,
        matching where ``basemap-sea``/``basemap-land`` are drawn.
    width, height : float
        The plate's full SVG canvas size (``vp["width"]``/``vp["height"]``).
    clip_path_d : str
        SVG path ``d`` string for the projected region bbox (the same
        shape ``basemap-sea``'s fill would cover if there were no land).
        LCC's meridians fan out from its cone apex, so a rectangular pixel
        grid covers a *wider* area than the requested bbox -- without
        clipping, the relief image bleeds into the plate's corner
        triangles that ``basemap-sea``/``basemap-land`` deliberately leave
        blank (caught via the Ralph Eyeball Loop: those corners rendered
        as a flagrant flat grey rectangle poking out past the plate's
        trapezoid on the first pass).
    bbox : list of float
        ``[west, south, east, north]`` -- the region this plate covers,
        forwarded to :func:`_relief.terrain_shade_for_bbox` to select and
        shade the matching elevation window.

    Returns
    -------
    str
        A ``<defs>`` clip-path definition plus a clipped ``<g id="relief">``
        wrapping one ``<image>`` element.
    """
    plot_w = int(width - 2 * pad)
    plot_h = int(height - 2 * pad)
    # Build the pixel grid once, offset by pad so it lines up exactly with
    # where the <image> element gets placed below.
    grid_sx, grid_sy = np.meshgrid(
        np.arange(plot_w) + pad, np.arange(plot_h) + pad
    )
    world_x, world_y = vp["to_world"](grid_sx, grid_sy)
    # pyproj's Transformer.transform accepts numpy arrays directly and
    # applies the exact inverse LCC formula element-wise -- no iterative
    # solve needed, unlike Equal Earth's forward-only closed form.
    lon_grid, lat_grid = proj.transform(world_x, world_y, direction="INVERSE")
    valid_grid = np.ones_like(lon_grid, dtype=bool)
    shade, shade_bounds = terrain_shade_for_bbox(*bbox, plot_w, plot_h)
    relief_rgba = sample_terrain_shade(lon_grid, lat_grid, valid_grid, shade, shade_bounds)
    return (
        '<defs><clipPath id="relief-clip">'
        f'<path d="{clip_path_d}"/></clipPath></defs>'
        f'<g id="relief" clip-path="url(#relief-clip)">'
        f'<image x="{pad:.1f}" y="{pad:.1f}" width="{plot_w}" height="{plot_h}" '
        f'href="{rgba_to_data_uri(relief_rgba)}" preserveAspectRatio="none"/></g>'
    )


def build_map(cfg: dict[str, Any]) -> str:
    """Assemble the full layered situation-map SVG from a config dict.

    Parameters
    ----------
    cfg : dict
        Parsed YAML config. See the module docstring / bundled demo for the schema.

    Returns
    -------
    str
        A complete standalone SVG document.
    """
    bbox = cfg["region"]["bbox"]
    proj = build_projection(bbox, cfg.get("projection", "auto"))
    width = float(cfg.get("canvas_width", 1000))
    pad = float(cfg.get("padding", 26))
    vp = make_viewport(proj, bbox, width, pad)
    W, H = vp["width"], vp["height"]

    basemap = cfg.get("basemap", {})
    sea_color = basemap.get("sea_color", "#a9bccb")
    land_color = basemap.get("land_color", "#faf6e4")
    coast_color = basemap.get("coast_color", "#7f97a8")

    region_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
    # bbox already carries the region's real extent -- reuse it to pick the
    # 10m/50m basemap tier instead of re-deriving it from region_box.
    land = load_land(bbox=bbox).intersection(region_box)
    land_proj = _project_geom(land, proj)
    region_proj = _project_geom(region_box, proj)
    sea_proj = region_proj.difference(land_proj)

    layers: list[str] = []

    # 0. relief --------------------------------------------------------------
    # Drawn first (bottom of the stack) so the sea and land fills paint over
    # it -- basemap-land's fill-opacity below is what lets it peek through.
    if basemap.get("relief", True):
        layers.append(
            _relief_layer(vp, proj, pad, W, H, projected_geom_to_path(region_proj, vp), bbox)
        )

    # 1. basemap-sea -------------------------------------------------------- #
    layers.append(
        f'<g id="basemap-sea">'
        f'<path d="{projected_geom_to_path(sea_proj, vp)}" fill="{sea_color}"/></g>'
    )

    # 2. basemap-bathymetry ------------------------------------------------- #
    bath = basemap.get("bathymetry", {"rings": 7, "step_km": None})
    layers.append(_bathymetry_layer(land_proj, sea_proj, vp, bath))

    # 3. basemap-land --------------------------------------------------------
    # fill-opacity < 1 (not the default opaque fill) lets the relief layer
    # underneath read as terrain texture -- same technique as
    # make_choropleth.py's country fills, but tuned to a *lower* opacity
    # (more peek-through) here: 0.7 (choropleth's value) washed out almost
    # completely on an all-land, mountain-only plate (Himalaya test render)
    # -- land_color is a light neutral cream (~248 luminance), and the same
    # relief delta reads as much smaller near-white than it does against
    # choropleth's darker data ramp (Weber-Fechner: identical luminance
    # deltas are less perceptible closer to white). There is also no data
    # ramp here for stronger relief to visually compete with, so there is
    # more headroom to let it dominate. 0.45 was the empirical sweet spot
    # (0.55 was still muted; the Himalaya ridge line only became clearly
    # legible at 0.45).
    land_fill_opacity = 0.45 if basemap.get("relief", True) else 1.0
    layers.append(
        f'<g id="basemap-land">'
        f'<path d="{projected_geom_to_path(land_proj, vp)}" fill="{land_color}" '
        f'fill-opacity="{land_fill_opacity}"/></g>'
    )

    # 3b. frontiers (international borders + neighbour labels) --------------- #
    layers.append(_frontiers_layer(cfg, proj, vp, region_box))

    # 3c. internal-borders (admin-1: US states, FR regions, OSM countries) --- #
    layers.append(_internal_borders_layer(cfg, proj, vp, region_box))

    # 3d. admin2-borders (admin-2, currently FR departments, zoom-gated) ----- #
    layers.append(_admin2_borders_layer(cfg, proj, vp, region_box))

    # 4. areas-of-control --------------------------------------------------- #
    layers.append(_areas_of_control_layer(cfg, proj, vp))

    # 4b. coastline — a crisp hairline where land meets the sea, drawn over the
    #     control fills so the shore reads sharply against the water. Placed here
    #     (not with the land) so a coastal control zone does not paint over it.
    coast = land_proj.boundary.intersection(sea_proj.buffer(vp["m_per_unit"] * 1.5))
    coast_d = projected_geom_to_path(coast, vp, close=False)
    layers.append(
        f'<g id="coastline"><path d="{coast_d}" fill="none" stroke="{coast_color}" '
        f'stroke-width="{0.9 * vp["ts"]:.2f}" stroke-opacity="0.75" '
        f'stroke-linejoin="round" stroke-linecap="round"/></g>'
        if coast_d else '<g id="coastline"></g>'
    )

    # 5. infrastructure ----------------------------------------------------- #
    layers.append(_infrastructure_layer(cfg, proj, vp))

    # 5b. rivers (over the fills so the water reads) ------------------------ #
    layers.append(_rivers_layer(cfg, proj, vp, region_box))

    # 5c. sprezzature line — the emphasised contact line between the control zones,
    #     the single most-read feature of a situation plate.
    layers.append(_front_line_layer(cfg, proj, vp))

    # 6. forces ------------------------------------------------------------- #
    layers.append(_markers_layer(cfg.get("forces", []), proj, vp, "forces"))

    # 7. events ------------------------------------------------------------- #
    layers.append(_markers_layer(cfg.get("events", []), proj, vp, "events"))

    # 8. annotation-labels -------------------------------------------------- #
    layers.append(_labels_layer(cfg, proj, vp))

    # 9. annotation-furniture ---------------------------------------------- #
    layers.append(_furniture_layer(cfg, vp))

    # 10. legend ------------------------------------------------------------ #
    layers.append(_legend_layer(cfg, vp))

    # 10b. attribution -------------------------------------------------------- #
    layers.append(_attribution_layer(cfg, vp, bbox))

    # 11. frame ------------------------------------------------------------- #
    layers.append(
        f'<g id="frame"><rect x="1" y="1" width="{W - 2:.1f}" height="{H - 2:.1f}" '
        f'rx="6" ry="6" fill="none" stroke="#fff" stroke-width="2"/></g>'
    )

    # Float the plate on a light page: an outer margin, a soft-shadowed white
    # panel, and a rounded clip — the premium "printed plate" cue of the reference.
    frame = cfg.get("frame", {})
    margin = float(frame.get("margin", 22))
    page_color = frame.get("page_color", "#eef1f3")
    radius = float(frame.get("radius", 8))
    outer_w = W + 2 * margin
    outer_h = H + 2 * margin
    clip = (
        f'<clipPath id="plate-clip"><rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" '
        f'rx="{radius}" ry="{radius}"/></clipPath>'
    )
    hatch = cfg.get("areas_of_control", {}).get("hatch_color", "#b03a3a")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {outer_w:.1f} {outer_h:.1f}" '
        f'width="{outer_w:.1f}" height="{outer_h:.1f}">'
        f'{svg_defs(hatch)[:-7]}{clip}</defs>'
        f'<rect width="{outer_w:.1f}" height="{outer_h:.1f}" fill="{page_color}"/>'
        f'<g transform="translate({margin:.1f},{margin:.1f})">'
        f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" rx="{radius}" ry="{radius}" '
        f'fill="#ffffff" filter="url(#panel-shadow)"/>'
        f'<g clip-path="url(#plate-clip)">'
        f'<rect width="{W:.1f}" height="{H:.1f}" fill="#ffffff"/>'
        f'{"".join(layers)}'
        f'</g></g>'
        f'</svg>'
    )


def _bathymetry_layer(
    land_proj: Any, sea_proj: Any, vp: dict[str, Any], bath: dict[str, Any]
) -> str:
    """Return concentric depth-contour halos buffered out from the coast into the sea."""
    rings = int(bath.get("rings", 7))
    if rings <= 0 or sea_proj.is_empty:
        return '<g id="basemap-bathymetry"></g>'
    m_per_unit = vp["m_per_unit"]
    step_km = bath.get("step_km")
    if not step_km:
        step_km = (vp["width"] * 0.02 * m_per_unit) / 1000.0  # ~2% of canvas
    step_m = step_km * 1000.0
    color = bath.get("color", "#ffffff")
    opacity = float(bath.get("opacity", 0.5))
    coast = land_proj.boundary
    paths: list[str] = []
    for i in range(1, rings + 1):
        ring = coast.buffer(step_m * i).boundary.intersection(sea_proj)
        if ring.is_empty:
            continue
        d = projected_geom_to_path(ring, vp, close=False)
        if d:
            paths.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="0.8" '
                f'stroke-opacity="{opacity:.2f}"/>'
            )
    return f'<g id="basemap-bathymetry">{"".join(paths)}</g>'


def _load_features(spec: Any, base: Path) -> list[dict[str, Any]]:
    """Return a list of GeoJSON features from an inline list or a file path."""
    if spec is None:
        return []
    if isinstance(spec, str):
        data = json.loads((base / spec).read_text() if not Path(spec).is_absolute()
                          else Path(spec).read_text())
        return data.get("features", [])
    if isinstance(spec, dict) and spec.get("type") == "FeatureCollection":
        return spec.get("features", [])
    if isinstance(spec, list):
        return spec
    return []


def _areas_of_control_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return the territory zones: pastel fill under a white casing; contested = hatch."""
    aoc = cfg.get("areas_of_control", {})
    base = Path(cfg.get("_config_dir", "."))
    features = _load_features(aoc.get("source"), base)
    if not features:
        return '<g id="areas-of-control"></g>'
    field = aoc.get("category_field", "actor")
    palette = aoc.get("palette", {})
    contested = set(aoc.get("contested", []))
    casing_w = float(aoc.get("casing_width", 2.4))
    # Fill opacity: high enough that the pastel classes read as solid territory,
    # low enough that the paper warmth and the coastline still show through.
    fill_op = float(aoc.get("fill_opacity", 0.78))

    casings: list[str] = []
    fills: list[str] = []
    for feat in features:
        props = feat.get("properties", {})
        cat = props.get(field, "")
        geom = _project_geom(shape(feat["geometry"]), proj)
        d = projected_geom_to_path(geom, vp)
        if not d:
            continue
        # White casing drawn first (under the fill) so borders read as clean seams.
        casings.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{casing_w}" '
                       f'stroke-linejoin="round"/>')
        color = palette.get(cat, "#dddddd")
        fills.append(
            f'<path d="{d}" fill="{color}" fill-opacity="{fill_op:.2f}" stroke="{color}" '
            f'stroke-width="0.7" stroke-opacity="0.95"/>'
        )
        if cat in contested:
            fills.append(f'<path d="{d}" fill="url(#hatch-contested)"/>')
    return f'<g id="areas-of-control">{"".join(casings)}{"".join(fills)}</g>'


def _infrastructure_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return roads / highways as hairlines and airports as small ticks."""
    infra = cfg.get("infrastructure", {})
    base = Path(cfg.get("_config_dir", "."))
    out: list[str] = []
    for feat in _load_features(infra.get("roads"), base):
        geom = _project_geom(shape(feat["geometry"]), proj)
        d = projected_geom_to_path(geom, vp, close=False)
        if d:
            out.append(f'<path d="{d}" fill="none" stroke="#8a8f96" stroke-width="0.7" '
                      f'stroke-opacity="0.7"/>')
    for ap in infra.get("airports", []):
        x, y = vp["to_svg"](*proj.transform(ap["lon"], ap["lat"]))
        out.append(
            f'<g transform="translate({x:.1f},{y:.1f})">'
            f'<path d="M-4,0 L4,0 M0,-4 L0,4" stroke="#5b6169" stroke-width="1.1"/>'
            f'<circle r="2.4" fill="none" stroke="#5b6169" stroke-width="1"/></g>'
        )
    return f'<g id="infrastructure">{"".join(out)}</g>'


def _frontiers_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                     region_box: Any) -> str:
    """Return real international frontiers (hairline dashes) + neighbour labels.

    Every country in the vendored basemap whose outline crosses the region is
    drawn as a dashed hairline (the international-border convention, distinct
    from the solid white casing of the control zones), and the neighbours large
    enough to read are labelled. ``frontiers.focus`` names the country the plate
    is about, so it is not labelled again (its name is already in the title).
    """
    fr = cfg.get("frontiers", {})
    if fr.get("show", True) is False:
        return '<g id="frontiers"></g>'
    ts = vp["ts"]
    color = fr.get("color", "#b7bbc0")
    do_label = fr.get("label_neighbours", True)
    focus_raw = fr.get("focus", [])
    focus = {focus_raw.lower()} if isinstance(focus_raw, str) else {n.lower() for n in focus_raw}
    min_frac = float(fr.get("label_min_area_frac", 0.02))
    region_area = region_box.area
    lines: list[str] = []
    labels: list[str] = []
    # region_box.bounds is (minx, miny, maxx, maxy) == (west, south, east,
    # north) -- exactly the bbox shape _land_topojson_for_bbox expects, so
    # the frontier layer picks the same 10m/50m tier the basemap itself did.
    for name, poly in load_countries(bbox=region_box.bounds):
        try:
            vis = poly.intersection(region_box)
        except Exception:
            continue
        if vis.is_empty:
            continue
        gp = _project_geom(poly.boundary.intersection(region_box), proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if d:
            lines.append(
                f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="0.85" '
                f'stroke-dasharray="{3.4 * ts:.1f} {2.4 * ts:.1f}"/>'
            )
        if do_label and name and name.lower() not in focus and vis.area >= min_frac * region_area:
            pt = vis.representative_point()
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            labels.append(tracked_text(x, y, name, size=9.5 * ts, fill="#9ba1a7",
                                       tracking=2.2, weight="600"))
    return f'<g id="frontiers">{"".join(lines)}{"".join(labels)}</g>'


def _polygonal_boundary_source(poly: Any) -> Optional[Any]:
    """Return a geometry whose ``.boundary`` is well-defined, or ``None`` if it has none.

    TIGER's self-touching rings near complex coastlines (observed on Texas,
    Oklahoma) make ``make_valid()`` return a ``GeometryCollection`` mixing
    the repaired polygon with degenerate point/line artifacts; a
    ``GeometryCollection`` has no well-defined ``.boundary`` (``None`` in
    shapely, not an empty geometry), so this extracts just the polygonal
    part first. Shared by every admin-1/admin-2 border layer rather than
    inlined per layer, since it is a defensive fix for a real vendored-data
    quirk, not an arbitrary style choice each layer could reasonably repeat.
    """
    if poly.geom_type != "GeometryCollection":
        return poly
    polys = [g for g in poly.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(polys) if polys else None


def _internal_borders_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                            region_box: Any) -> str:
    """Return sub-national admin-1 borders (US states, French regions) for covered areas.

    A finer, lighter dashed line than :func:`_frontiers_layer`'s international
    frontiers -- the cartographic convention for internal administrative
    borders, which read as secondary to national ones. Draws from every
    vendored admin-1 source whose bbox overlaps the region: TIGER
    (:func:`load_us_states`, US), IGN/ADMIN-EXPRESS (:func:`load_fr_regions`,
    France), and OpenStreetMap (:func:`load_osm_admin1`, currently
    Switzerland, Germany, Italy). Silently a no-op wherever none of them
    cover the region: each loader already skips its own TopoJSON load when
    the bbox does not overlap its extent, so a situation map of, say, the
    Himalaya pays nothing for this layer beyond a handful of bounds checks.

    The OSM sources carry a real obligation the other two do not: ODbL
    requires attribution on any produced work (a rendered map) that uses
    it. :func:`_attribution_layer` adds that credit automatically whenever
    this layer would actually draw from one of them -- this function does
    not add it itself, since it has no rendered text layer of its own to
    attach a footer to.
    """
    ib = cfg.get("internal_borders", {})
    if ib.get("show", True) is False:
        return '<g id="internal-borders"></g>'
    ts = vp["ts"]
    color = ib.get("color", "#c7cbcf")
    do_label = ib.get("label_names", False)
    min_frac = float(ib.get("label_min_area_frac", 0.02))
    region_area = region_box.area
    lines: list[str] = []
    labels: list[str] = []
    admin1 = (
        load_us_states(bbox=region_box.bounds)
        + load_fr_regions(bbox=region_box.bounds)
        + load_osm_admin1(bbox=region_box.bounds)
    )
    for name, poly in admin1:
        try:
            vis = poly.intersection(region_box)
        except Exception:
            continue
        if vis.is_empty:
            continue
        boundary_source = _polygonal_boundary_source(poly)
        if boundary_source is None:
            continue
        gp = _project_geom(boundary_source.boundary.intersection(region_box), proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if d:
            lines.append(
                f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{0.6 * ts:.1f}" stroke-opacity="0.75" '
                f'stroke-dasharray="{2.0 * ts:.1f} {1.8 * ts:.1f}"/>'
            )
        if do_label and name and vis.area >= min_frac * region_area:
            pt = vis.representative_point()
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            labels.append(tracked_text(x, y, name, size=8.0 * ts, fill="#a7abaf",
                                       tracking=1.6, weight="500"))
    return f'<g id="internal-borders">{"".join(lines)}{"".join(labels)}</g>'


def _admin2_borders_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                          region_box: Any) -> str:
    """Return admin-2 borders (French departments) for a sufficiently zoomed-in region.

    A second, finer tier below :func:`_internal_borders_layer`'s admin-1
    lines, in an even lighter hairline, drawn only once the region bbox is
    zoomed in past :data:`_ADMIN2_BBOX_DEGREES_THRESHOLD` -- unlike admin-1
    (gated purely on which vendored source overlaps the bbox), admin-2 also
    gates on zoom, since a whole-country plate should never show a hundred
    department lines even where the data exists for it.
    """
    ib = cfg.get("admin2_borders", {})
    if ib.get("show", True) is False:
        return '<g id="admin2-borders"></g>'
    west, south, east, north = region_box.bounds
    if max(east - west, north - south) >= _ADMIN2_BBOX_DEGREES_THRESHOLD:
        return '<g id="admin2-borders"></g>'
    ts = vp["ts"]
    color = ib.get("color", "#d6d9db")
    do_label = ib.get("label_names", False)
    min_frac = float(ib.get("label_min_area_frac", 0.02))
    region_area = region_box.area
    lines: list[str] = []
    labels: list[str] = []
    for name, poly in load_admin2(bbox=region_box.bounds):
        try:
            vis = poly.intersection(region_box)
        except Exception:
            continue
        if vis.is_empty:
            continue
        boundary_source = _polygonal_boundary_source(poly)
        if boundary_source is None:
            continue
        gp = _project_geom(boundary_source.boundary.intersection(region_box), proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if d:
            lines.append(
                f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{0.45 * ts:.1f}" stroke-opacity="0.7" '
                f'stroke-dasharray="{1.4 * ts:.1f} {1.4 * ts:.1f}"/>'
            )
        if do_label and name and vis.area >= min_frac * region_area:
            pt = vis.representative_point()
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            labels.append(tracked_text(x, y, name, size=6.8 * ts, fill="#b5b9bc",
                                       tracking=1.2, weight="500"))
    return f'<g id="admin2-borders">{"".join(lines)}{"".join(labels)}</g>'


def _rivers_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                  region_box: Any) -> str:
    """Return river centerlines (water blue) with italic names for the major ones.

    A river is drawn if it crosses the region; it is *labelled* when it is
    prominent enough (``scalerank <= label_max_scalerank``) and its in-view run
    is long enough, or when it is named in ``rivers.always_label``. Labels dodge
    each other and are set in italic, the cartographic convention for water.
    """
    rv = cfg.get("rivers", {})
    if rv.get("show", True) is False:
        return '<g id="rivers"></g>'
    ts = vp["ts"]
    line_color = rv.get("color", "#6f93b0")
    label_color = rv.get("label_color", "#4f7290")
    max_rank = int(rv.get("label_max_scalerank", 6))
    min_px = float(rv.get("label_min_length_frac", 0.14)) * vp["width"]
    always = {n.lower() for n in rv.get("always_label", [])}
    skip = {n.lower() for n in rv.get("skip", [])}
    m_per_unit = vp["m_per_unit"]
    lines: list[str] = []
    labels: list[str] = []
    placed: list[tuple[float, float]] = []
    labeled: set[str] = set()   # one label per named river
    for geom, name, rank in sorted(load_rivers(), key=lambda r: -r[2]):
        try:
            clipped = geom.intersection(region_box)
        except Exception:
            continue
        if clipped.is_empty:
            continue
        gp = _project_geom(clipped, proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if not d:
            continue
        lines.append(
            f'<path d="{d}" fill="none" stroke="{line_color}" '
            f'stroke-width="{1.3 * ts:.1f}" stroke-opacity="0.85" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        if not name or name.lower() in skip or name.lower() in labeled:
            continue
        comp = max(getattr(gp, "geoms", [gp]), key=lambda g: g.length)
        length_px = comp.length / m_per_unit
        if not ((rank <= max_rank and length_px >= min_px) or name.lower() in always):
            continue
        mid = comp.interpolate(0.55, normalized=True)
        x, y = vp["to_svg"](mid.x, mid.y)
        if any((x - px) ** 2 + (y - py) ** 2 < (58 * ts) ** 2 for px, py in placed):
            continue
        placed.append((x, y))
        labeled.add(name.lower())
        size = 10.5 * ts
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-family="{_DEFAULT_FONT}" font-size="{size:.1f}" font-style="italic" '
            f'font-weight="500" fill="{label_color}" paint-order="stroke" '
            f'stroke="#ffffff" stroke-width="{max(2.0, size * 0.3):.1f}" '
            f'stroke-opacity="0.9" stroke-linejoin="round">{_esc(name)}</text>'
        )
    return f'<g id="rivers">{"".join(lines)}{"".join(labels)}</g>'


def _front_line_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return the emphasised contact line between the belligerents.

    The line is given by ``sprezzature.line`` (a list of ``[lon, lat]`` vertices, north
    to south). It is drawn as a two-part stroke: a soft white casing under a bold
    coloured line, the standard way a data desk makes the sprezzature read above the
    pastel control fills without adding a hard black rule. A small callout label
    (``sprezzature.label``) is set beside a chosen vertex when given.
    """
    fr = cfg.get("sprezzature", {})
    line = fr.get("line")
    if not line:
        return '<g id="front-line"></g>'
    ts = vp["ts"]
    color = fr.get("color", "#3a4149")
    from shapely.geometry import LineString  # local import: only this layer needs it

    geom = _project_geom(LineString([(p[0], p[1]) for p in line]), proj)
    d = projected_geom_to_path(geom, vp, close=False)
    if not d:
        return '<g id="front-line"></g>'
    parts = [
        # White casing so the sprezzature lifts off the pastel zones.
        f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{5.4 * ts:.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round" stroke-linecap="round"/>',
        # The contact line itself: bold, slightly dashed so it reads as a *sprezzature*,
        # not a fixed administrative boundary.
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{2.4 * ts:.1f}" '
        f'stroke-linejoin="round" stroke-linecap="round" '
        f'stroke-dasharray="{9 * ts:.1f} {4.5 * ts:.1f}"/>',
    ]
    label = fr.get("label")
    if label:
        at = fr.get("label_at", line[0])
        x, y = vp["to_svg"](*proj.transform(at[0], at[1]))
        dx = fr.get("label_dx", 10) * ts
        dy = fr.get("label_dy", -6) * ts
        parts.append(
            f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="start" '
            f'font-family="{_DEFAULT_FONT}" font-size="{10.5 * ts:.1f}" '
            f'font-weight="700" fill="{color}" letter-spacing="1.4" '
            f'paint-order="stroke" stroke="#ffffff" stroke-width="{3.2 * ts:.1f}" '
            f'stroke-opacity="0.9" stroke-linejoin="round">{_esc(label.upper())}</text>'
        )
    return f'<g id="front-line">{"".join(parts)}</g>'


def _markers_layer(items: list[dict[str, Any]], proj: Transformer,
                   vp: dict[str, Any], layer_id: str) -> str:
    """Return point markers (forces or events) as drop-shadowed dots."""
    out: list[str] = []
    for it in items:
        x, y = vp["to_svg"](*proj.transform(it["lon"], it["lat"]))
        color = it.get("color", "#b03a3a")
        r = float(it.get("r", 5))
        out.append(
            f'<g transform="translate({x:.1f},{y:.1f})" filter="url(#marker-shadow)">'
            f'<circle r="{r:.1f}" fill="{color}" stroke="#fff" stroke-width="1.4"/></g>'
        )
    return f'<g id="{layer_id}">{"".join(out)}</g>'


def _labels_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return populated-place dots with offset names, plus a tracked water label.

    Each place is a small dot at its true location and a letter-spaced name set
    *beside* the dot (never on top of it). ``place["anchor"]`` steers the name —
    ``"start"`` (right, default), ``"end"`` (left), ``"above"``, ``"below"`` —
    so labels can dodge the coast, the frame, and one another. ``dot: false``
    renders a centred area label with no dot (for a region rather than a city).
    """
    out: list[str] = []
    ts = vp["ts"]
    labels = cfg.get("labels", {})
    for place in labels.get("places", []):
        x, y = vp["to_svg"](*proj.transform(place["lon"], place["lat"]))
        size = place.get("size", 13) * ts
        anchor = place.get("anchor", "start")
        tracking = place.get("tracking", 1.6)
        # A dark populated-place dot, unless this point already carries another
        # marker (e.g. a red flashpoint) — then dot:false and `clear` is set to
        # that marker's radius so the name still dodges it.
        clear = place.get("clear", 2.6) * ts
        gap = 4 * ts
        if place.get("capital"):
            # A capital gets a ringed star, the classic cartographic capital glyph.
            clear = max(clear, 7.5 * ts)
            out.append(_capital_star(x, y, 7.0 * ts))
        elif place.get("dot", True):
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6 * ts:.1f}" fill="#2f343a" '
                f'stroke="#ffffff" stroke-width="{1.1 * ts:.1f}"/>'
            )
        if anchor == "center":  # centred, no offset (region / free label)
            lx, ly, ta = x, y, "middle"
        elif anchor == "end":
            lx, ly, ta = x - clear - gap, y + 0.32 * size, "end"
        elif anchor == "above":
            lx, ly, ta = x, y - clear - gap, "middle"
        elif anchor == "below":
            lx, ly, ta = x, y + clear + gap + 0.72 * size, "middle"
        else:  # "start" — name to the right of the marker
            lx, ly, ta = x + clear + gap, y + 0.32 * size, "start"
        weight = "700" if place.get("capital") else "600"
        out.append(tracked_text(lx, ly, place["text"], size=size, fill="#2f363d",
                                tracking=tracking, weight=weight, anchor=ta))
    # Water labels: a single ``water`` (back-compat) and/or a list ``waters`` —
    # seas and gulfs, set in the letter-spaced blue-grey water convention.
    waters = list(labels.get("waters", []))
    if labels.get("water"):
        waters.append(labels["water"])
    for w in waters:
        x, y = vp["to_svg"](*proj.transform(w["lon"], w["lat"]))
        angle = w.get("rotate", 0)
        txt = tracked_text(x, y, w["text"], size=w.get("size", 19) * ts,
                           fill="#5c7c90", tracking=w.get("tracking", 6),
                           weight="400", upper=w.get("upper", True))
        if angle:
            out.append(f'<g transform="rotate({angle} {x:.1f} {y:.1f})">{txt}</g>')
        else:
            out.append(txt)
    return f'<g id="annotation-labels">{"".join(out)}</g>'


def _furniture_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the title block, north arrow and dual-unit scale bar."""
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    # North arrow top-right, clear of the title block top-left — no collision.
    out: list[str] = [north_arrow(W - 30 * ts, 34 * ts, ts)]
    title = cfg.get("title")
    subtitle = cfg.get("subtitle")
    if title:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{22 * ts:.0f}" font-weight="700" fill="#1b2733">{_esc(title)}</text>'
        )
    if subtitle:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts + 20 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{12.5 * ts:.0f}" fill="#5b6169">{_esc(subtitle)}</text>'
        )
    out.append(scale_bar(26 * ts, H - 44 * ts, vp))
    return f'<g id="annotation-furniture">{"".join(out)}</g>'


def _attribution_layer(cfg: dict[str, Any], vp: dict[str, Any],
                       bbox: Optional[Iterable[float]]) -> str:
    """Return a small bottom-right credit line for any ODbL-licensed layer in view.

    Natural Earth (public domain) and TIGER/IGN (public domain / Licence
    Ouverte) need no runtime attribution, but OpenStreetMap's ODbL requires
    one on any produced work -- so whenever :func:`load_osm_admin1` would
    actually draw something for this ``bbox`` (see
    :func:`_bbox_in_osm_admin1`), the required "(c) OpenStreetMap
    contributors" credit is added automatically, rather than left for the
    caller to remember. ``cfg["attribution"]`` (a string or list of strings)
    appends further caller-supplied credits to the same line, for callers
    who bring their own additional licensed sources.
    """
    credits: list[str] = []
    if _bbox_in_osm_admin1(bbox) and cfg.get("internal_borders", {}).get("show", True) is not False:
        credits.append("© OpenStreetMap contributors (ODbL)")
    extra = cfg.get("attribution")
    if isinstance(extra, str) and extra:
        credits.append(extra)
    elif extra:
        credits.extend(str(c) for c in extra)
    if not credits:
        return '<g id="attribution"></g>'
    ts = vp["ts"]
    W, H = vp["width"], vp["height"]
    text = " · ".join(credits)
    return (
        f'<g id="attribution"><text x="{W - 16 * ts:.1f}" y="{H - 12 * ts:.1f}" '
        f'text-anchor="end" font-family="{_DEFAULT_FONT}" font-size="{8.5 * ts:.1f}" '
        f'fill="#9aa0a6">{_esc(text)}</text></g>'
    )


def _legend_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return a floating legend card: a swatch per class, marker key, source line.

    Swatches are rounded squares (a filled-territory cue, unlike a point dot), a
    contested class also carries the diagonal hatch so the legend mirrors the map
    exactly, and an optional ``sprezzature.label`` swatch shows the contact-line style.
    A footer sets the as-of / provenance line so the plate is self-describing.
    """
    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if not palette:
        return '<g id="legend"></g>'
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    contested = set(aoc.get("contested", []))
    rows = list(palette.items())
    markers = cfg.get("marker_legend", [])
    sprezzature = cfg.get("sprezzature", {})
    show_front = bool(sprezzature.get("line") and sprezzature.get("legend", True))
    footer = cfg.get("legend_footer")
    pad = 15 * ts
    row_h = 25 * ts
    panel_w = 262 * ts
    header_fs = 12.5 * ts
    row_fs = 12.5 * ts
    sw = 15 * ts        # swatch side
    extra = (len(markers) + 1 if markers else 0) + (1 if show_front else 0)
    n_rows = len(rows) + extra
    foot_h = 30 * ts if footer else 0
    panel_h = pad * 2 + 24 * ts + row_h * n_rows + foot_h
    px = W - panel_w - 22 * ts
    py = H - panel_h - 22 * ts
    tx = px + pad + sw + 10 * ts   # label x
    parts: list[str] = [
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="#ffffff" fill-opacity="0.96" filter="url(#panel-shadow)"/>',
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="none" stroke="#e4e8ec" stroke-width="1"/>',
        f'<text x="{px + pad:.1f}" y="{py + pad + 10 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
        f'font-size="{header_fs:.1f}" font-weight="700" fill="#1b2733" letter-spacing="1.2">'
        f'AREAS OF CONTROL</text>',
    ]
    fill_op = float(aoc.get("fill_opacity", 0.78))
    for i, (name, color) in enumerate(rows):
        ry = py + pad + 26 * ts + i * row_h
        sy = ry - sw / 2 - 1 * ts
        parts.append(
            f'<rect x="{px + pad:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
            f'rx="{2.5 * ts:.1f}" fill="{color}" fill-opacity="{fill_op:.2f}" '
            f'stroke="{color}" stroke-width="1"/>'
        )
        if name in contested:
            parts.append(
                f'<rect x="{px + pad:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
                f'rx="{2.5 * ts:.1f}" fill="url(#hatch-contested)"/>'
            )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="#333">{_esc(name)}</text>'
        )
    idx = len(rows)
    # Front-line key row.
    if show_front:
        ry = py + pad + 26 * ts + idx * row_h
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{ry:.1f}" x2="{px + pad + sw:.1f}" y2="{ry:.1f}" '
            f'stroke="{sprezzature.get("color", "#3a4149")}" stroke-width="{2.4 * ts:.1f}" '
            f'stroke-dasharray="{7 * ts:.1f} {3.5 * ts:.1f}" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{row_fs:.1f}" fill="#333">{_esc(sprezzature.get("legend_label", "Approx. sprezzature line"))}</text>'
        )
        idx += 1
    # Marker key, separated by a hairline divider.
    for j, mk in enumerate(markers):
        ry = py + pad + 26 * ts + (idx + j) * row_h
        if j == 0:
            dv = ry - row_h + 6 * ts
            parts.append(
                f'<line x1="{px + pad:.1f}" y1="{dv:.1f}" x2="{px + panel_w - pad:.1f}" '
                f'y2="{dv:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
            )
        parts.append(
            f'<circle cx="{px + pad + sw / 2:.1f}" cy="{ry:.1f}" r="{5.5 * ts:.1f}" '
            f'fill="{mk.get("color", "#c0392b")}" stroke="#fff" stroke-width="{1.4 * ts:.1f}"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="#333">'
            f'{_esc(mk.get("label", ""))}</text>'
        )
    if footer:
        fy = py + panel_h - 11 * ts
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{fy - 13 * ts:.1f}" x2="{px + panel_w - pad:.1f}" '
            f'y2="{fy - 13 * ts:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px + pad:.1f}" y="{fy:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{9 * ts:.1f}" fill="#8b9097">{_esc(footer)}</text>'
        )
    return f'<g id="legend">{"".join(parts)}</g>'


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


# A neutral, self-contained demo config so the figure registry can render this
# generator like every other one. It shows Western Europe as a clean reference
# situation map -- coastline, international frontiers, country labels, sea
# bathymetry, dual-unit scale bar, north arrow -- straight from the vendored
# Natural Earth basemap, with no thematic overlay invented. Pass a real
# ``config`` dict (or use the ``--config`` CLI) for an actual analysis map.
_DEMO_CONFIG: dict[str, Any] = {
    "title": "Situation map — Western Europe (demo)",
    "region": {"bbox": [-11.0, 35.0, 30.0, 60.0]},
    "canvas_width": 1000,
    "projection": "auto",
}

#: Row-record demo data, the contract's ``list[dict[str, Any]]`` shape.
#: This generator is config-driven (a whole layered basemap, not a table
#: of rows — see :func:`make_situation_map`), so ``data`` is accepted for
#: dispatcher parity and unused; this constant exists to satisfy the
#: ``DEMO_DATA`` contract and documents the demo region as a row.
DEMO_DATA: list[dict[str, Any]] = [
    {
        "region": "Western Europe",
        "west": -11.0,
        "south": 35.0,
        "east": 30.0,
        "north": 60.0,
    }
]


def make_situation_map(
    data: "Any | None" = None,
    *,
    out: "Path | str | None" = None,
    title: str = "",
    config: "dict[str, Any] | None" = None,
) -> Path:
    """Render a situation map and write it to ``out``.

    The standard ``make_<kind>`` entry the figure registry dispatches to, so
    ``make-figure situation_map`` and the Studio work like every other figure.
    With no ``config`` it renders the bundled Western-Europe demo (a neutral
    reference basemap, no invented thematic layers); pass a config dict -- the
    same schema the ``--config`` YAML uses -- to build a real analysis map.
    ``data`` is accepted for dispatcher parity and unused (this generator is
    config-driven, not row-driven).
    """
    cfg = dict(config) if config else dict(_DEMO_CONFIG)
    # `build_map` resolves any relative feature files against this; the demo has
    # none, but the key must exist.
    cfg.setdefault("_config_dir", str(Path(__file__).resolve().parent.parent / "assets"))
    if title:
        cfg["title"] = title
    svg = build_map(cfg)
    dest = Path(out) if out else svg_example_path(__file__, "situation_map")
    return write_svg(dest, svg)


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the generator."""
    p = argparse.ArgumentParser(description="Generate a layered situation map for any region.")
    p.add_argument("--config", required=True, help="YAML config describing the map.")
    p.add_argument("--out", required=True, help="Output SVG path.")
    p.add_argument("--render", action="store_true",
                   help="Also rasterise to PNG next to --out via render_diagram.py.")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point: read config, build the SVG, optionally rasterise."""
    args = build_parser().parse_args(argv)
    cfg = yaml.safe_load(Path(args.config).read_text())
    cfg["_config_dir"] = str(Path(args.config).resolve().parent)
    svg = build_map(cfg)
    out = Path(args.out)
    out.write_text(svg)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    if args.render:
        import subprocess

        png = out.with_suffix(".png")
        script = Path(__file__).with_name("render_diagram.py")
        subprocess.run(["python3", str(script), str(out), "--out", str(png)], check=False)
        print(f"rendered {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
