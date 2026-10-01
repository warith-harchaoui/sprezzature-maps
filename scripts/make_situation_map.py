#!/usr/bin/env python3
"""Generate a professional, layered "situation map" for any region of the world.

Author: Warith HARCHAOUI

A situation map, in the sense used here, is the kind of "who controls
what" plate that a geopolitics analyst draws over a real map: territory
coloured by which side holds it, plus markers for forces, events, and
infrastructure. This module reverse-engineers that plate structure (works
out its underlying recipe by studying real examples, rather than
following a published specification, since professional cartography
studios do not publish one) into a single generator that takes
parameters instead of being redrawn by hand each time. From one YAML
configuration file (YAML is a human-readable text format for structured
data) describing a region, a map projection, thematic "areas of control"
zones, military or political forces, events, infrastructure, and labels,
it produces one SVG image, built as a stack of layers. Layers are simply
drawn one after another, each painted over the ones before it, and this
module names its layers the way a geopolitics analyst would recognize on
sight, from the bottom (painted first, so it ends up furthest back) to
the top:

1. ``basemap-sea``: the sea's fill colour.
2. ``basemap-bathymetry``: a band of depth-contour shading (bathymetry
   means ocean-floor depth, the sea's equivalent of land elevation)
   radiating out from the coastline.
3. ``basemap-land``: the land's fill colour.
4. ``areas-of-control``: the territory zones, in pastel colours with a
   white outline; contested zones are drawn with a diagonal hatch
   pattern instead of a solid fill, so "contested" is visible even
   without reading a legend.
5. ``infrastructure``: roads, highways, and airports, drawn as thin
   hairlines.
6. ``forces``: point markers for unit or actor positions.
7. ``events``: point markers for incidents (ceasefire points, clashes,
   strikes).
8. ``annotation-labels``: place names and water body names, in
   letter-spaced (extra space added between letters, a typographic
   convention for map labels) type.
9. ``annotation-furniture``: the title block, a north arrow, and a scale
   bar shown in two units at once (kilometres and miles). "Furniture" is
   the cartographic term for these framing elements that aren't the map
   content itself.
10. ``legend``: a floating panel with colour swatches explaining what
    each zone colour and marker means.
11. ``frame``: a rounded-rectangle mask that clips the whole plate to a
    clean panel shape.

The specific craft details this module reproduces, each one a small
signature of professional cartography: a local, equal-angle projection
(the Lambert conformal conic projection, automatically centred on
whichever region is requested; equal-angle, or "conformal," means shapes
and angles stay correct close to the centre, which matters for a
single-region map the way it wouldn't for a whole-world one); a "classed"
pastel colour palette (values sorted into a handful of named categories,
each with its own fixed colour, rather than a continuous gradient);
white outlines, or "casing," between adjacent zones so their edges stay
crisp even when the fill colours are close in hue; bathymetry shading in
the sea; drop shadows under the panel and its markers; letter-spaced
uppercase labels; and a scale bar in two units at once. All of it works
for any part of the world the caller asks for, not just one hardcoded
example region.

The land geometry underneath everything is the vendored, offline Natural
Earth land outline data (``assets/geo/countries-50m.json``); the caller
supplies every thematic layer drawn on top of it.

Each ``areas-of-control`` zone and each ``forces``/``events`` marker
carries a ``.hit`` element (an invisible, larger clickable/hoverable
shape, since the visible shape is sometimes too thin or small to hover
precisely) and a hover-info bubble (the ``.hit``/``.tip`` elements, built
with ``_svg.tooltip_bubble`` from the sprezzature-figures repository): a
zone's bubble shows which actor or category holds it and what share of
the mapped area it covers; a force or event marker's bubble shows its
legend description and coordinates.

Usage
-----
    python make_situation_map.py --config demo.yaml --out demo.svg --render

Style rules for this file: NumPy-style docstrings, full type annotations,
and plain dict-shaped records in preference to purpose-built classes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import warnings
from collections.abc import Iterable
from difflib import get_close_matches
from pathlib import Path
from typing import Any

import numpy as np
from _assets import figures_scripts_dir, geo_dir
from _places import cities_in_view, place_labels
from _relief import rgba_to_data_uri, sample_terrain_shade, terrain_shade_for_bbox
from _render import svg_example_path, write_svg

# tooltip_bubble lives in sprezzature-figures/scripts/_svg.py -- a genuinely
# new capability (see that module's docstring), not something this repo's
# own scripts carry. This generator has no local ``_svg`` module of its own
# (own escaping stays in :func:`_esc` below), but a plain sys.path insert +
# ``from _svg import ...`` is *not* safe here, even so: Python caches
# imports by bare module name, not by path, and ``sprezzature_maps/__init__.py``
# keeps every generator it has ever loaded alive in ``sys.modules`` for the
# life of the process (its own docstring explains why: a FastAPI worker
# handling both routes must not re-``exec`` a generator on every call). If
# ``make_choropleth`` (which owns its *own* local ``scripts/_svg.py``,
# lacking ``tooltip_bubble``) has already run once in this process, the bare
# name ``_svg`` is already claimed in ``sys.modules`` and this import would
# silently reuse that wrong module instead of loading this one -- exactly
# the hazard make_choropleth.py's own neighbouring comment describes,
# just from the other generator's side. Loaded via importlib under the same
# distinct module name make_choropleth.py uses, so whichever generator runs
# first in a process loads the file once and the other one just reuses it.
# _assets.figures_scripts_dir() resolves the installed
# sprezzature_figures_scripts package first (the normal case: pyproject.toml
# declares sprezzature-figures as a real dependency), with a sibling-checkout
# fallback for a from-source dev setup.
if "_svg_figures_tooltip" in sys.modules:
    tooltip_bubble = sys.modules["_svg_figures_tooltip"].tooltip_bubble
else:
    _tooltip_spec = importlib.util.spec_from_file_location(
        "_svg_figures_tooltip", figures_scripts_dir() / "_svg.py"
    )
    _svg_figures = importlib.util.module_from_spec(_tooltip_spec)
    sys.modules["_svg_figures_tooltip"] = _svg_figures
    _tooltip_spec.loader.exec_module(_svg_figures)
    tooltip_bubble = _svg_figures.tooltip_bubble

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
    from shapely.ops import polylabel, unary_union
    from shapely.ops import transform as shp_transform
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "shapely>=2 and pyproj>=3.6 are required: pip install shapely pyproj"
    ) from exc


# --------------------------------------------------------------------------- #
# Vendored basemap (Natural Earth, offline)                                    #
# --------------------------------------------------------------------------- #

_ASSETS = geo_dir()
_LAND_TOPOJSON = _ASSETS / "countries-50m.json"
# 1:10m Natural Earth admin-0 countries, vendored the same way the 50m/110m
# atlases were: downloaded once, simplified (mapshaper, weighted Visvalingam,
# keep-shapes so small islands survive), quantized to TopoJSON. Only used for
# small bboxes -- see _land_topojson_for_bbox -- where the 50m atlas would
# read visibly facetted/over-smoothed at zoom.
_LAND_TOPOJSON_10M = _ASSETS / "countries-10m.json"
_RIVERS_GEOJSON = _ASSETS / "rivers-50m.geojson"
_LAKES_GEOJSON = _ASSETS / "lakes-50m.geojson"

#: The two plates. ``day`` reproduces the values that were hard-coded here,
#: so an existing config renders byte-for-byte as before.
#:
#: ``night`` is not the day palette inverted. Inverting gives a muddy grey
#: sea and cream-coloured land at 8 % lightness, which reads as a mistake.
#: These values were picked so that: the sea is nearly black but not black,
#: leaving room for bathymetry below it; the land sits far enough above the
#: sea to separate at a glance; and the coastline is a light hairline rather
#: than a dark one, because on a dark plate the shore is where light is, not
#: where ink is.
_PLATES: dict[str, dict[str, str]] = {
    "day": {
        "plate": "#ffffff",
        "panel": "#ffffff",
        "panel_edge": "#e4e8ec",
        "chrome_ink": "#1b2733",
        "legend_ink": "#333",
        "chrome_sub": "#5b6169",
        "chrome_faint": "#8b9097",
        "label_ink": "#1b2733",
        "page": "#eef1f3",
        "bathy": "#ffffff",
        "bathy_opacity": 0.5,
        "halo": "#ffffff",
        "blend": "multiply",
        "sea": "#a9bccb",
        "land": "#faf6e4",
        "coast": "#7f97a8",
        "relief_opacity": 0.45,
        "ink": "#1d1d1f",
        "subtle": "#6e6e73",
    },
    "night": {
        "plate": "#0a0f18",
        "panel": "#121a26",
        "panel_edge": "#2a3646",
        "chrome_ink": "#eef2f7",
        "legend_ink": "#eef2f7",
        "chrome_sub": "#a8b2be",
        "chrome_faint": "#7f8b98",
        "label_ink": "#eef2f7",
        # The page is a shade darker than the plate, so the plate still reads
        # as an object sitting on something rather than as a hole in it.
        "page": "#05080d",
        "bathy": "#16324f",
        "bathy_opacity": 0.55,
        # A label halo on a dark plate is dark: a white one would ring every
        # name in the very colour the text is set in.
        "halo": "#0a0f18",
        # Multiply darkens, which is right over a pale plate and wrong here —
        # it dragged the control fills towards the plate instead of lifting
        # them off it. Screen does the equivalent job in the other direction.
        "blend": "screen",
        "sea": "#070d18",
        "land": "#1b2330",
        "coast": "#5d7186",
        # Land sits at ~13 % lightness here, so the relief underneath has the
        # whole range above it to work with. At the day plate's 0.45 the
        # terrain drowned the fill; 0.72 keeps the land reading as land.
        "relief_opacity": 0.88,
        "ink": "#f2f4f7",
        "subtle": "#98a3b0",
    },
}
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
    "CH": (
        _ASSETS / "ch-cantons.json",
        _ASSETS / "ch-cantons-coarse.json",
        (5.96, 45.82, 10.49, 47.81),
        "cantons",
    ),
    "DE": (
        _ASSETS / "de-states.json",
        _ASSETS / "de-states-coarse.json",
        (5.87, 47.27, 15.04, 55.10),
        "states",
    ),
    "IT": (
        _ASSETS / "it-regions.json",
        _ASSETS / "it-regions-coarse.json",
        (6.63, 35.49, 18.52, 47.09),
        "regions",
    ),
}

# Admin-2 (second sub-national tier, one level finer than admin-1) registry,
# same shape as :data:`_OSM_ADMIN1_SOURCES` for the same reason: a registry
# from the start rather than a bespoke loader function per source, since
# admin-1 already proved that pattern stops paying for itself past one
# instance. France's 101 departments (96 metropolitan plus 5 overseas) came
# from the same IGN ADMIN-EXPRESS product admin-1's `fr-regions.json` did,
# via the same `france-geojson` mirror, vendored once more at the finer
# granularity. US counties are TIGER/Line again (public domain), the same
# recipe as `us-states.json` but a substantially heavier pull: 3,235
# records (every county plus county-equivalent, e.g. Louisiana's parishes
# and Alaska's boroughs/census areas), 4.6MB even after 15% weighted
# Visvalingam simplification -- by a wide margin the largest vendored
# vector file in this repo, flagged explicitly rather than vendored
# silently. Switzerland (135 districts), Germany (400 Kreise), and
# Italy (109 province) round this out, all three via OpenStreetMap
# admin_level=6 -- unlike admin_level=4 country boundaries, this level's
# relations carry no ISO3166-2 tag, so noise-filtering used an
# area-overlap check (at least 50% of the assembled geometry's area
# inside the country's own bbox) instead of the ISO-prefix trick
# admin-1's DE/IT sources needed. That filter earned its keep twice:
# Switzerland's 135 candidates were all clean, but Italy's query
# returned a French department (Haute-Savoie, an Alpine neighbor) that
# the area check correctly dropped.
# Each entry: (fine path, coarse path, bounds, TopoJSON object name) --
# same fine/coarse pyramid shape :data:`_OSM_ADMIN1_SOURCES` has, added
# once three admin-2 sources existed and the heaviest of them (US
# counties, 4.6MB fine) made the weight saving worth having twice: once
# via the show/hide gate below, and again via a lighter file for the
# wider end of the window that gate still allows through.
_ADMIN2_SOURCES: dict[str, tuple[Path, Path, tuple[float, float, float, float], str]] = {
    "FR": (
        _ASSETS / "fr-departments.json",
        _ASSETS / "fr-departments-coarse.json",
        (-61.81, -21.39, 55.84, 51.09),
        "departments",
    ),
    "US": (
        _ASSETS / "us-counties.json",
        _ASSETS / "us-counties-coarse.json",
        _US_STATES_BOUNDS,
        "counties",
    ),
    "CH": (
        _ASSETS / "ch-districts.json",
        _ASSETS / "ch-districts-coarse.json",
        (5.96, 45.82, 10.49, 47.81),
        "districts",
    ),
    "DE": (
        _ASSETS / "de-kreise.json",
        _ASSETS / "de-kreise-coarse.json",
        (5.87, 47.27, 15.04, 55.10),
        "kreise",
    ),
    "IT": (
        _ASSETS / "it-province.json",
        _ASSETS / "it-province-coarse.json",
        (6.63, 35.49, 18.52, 47.09),
        "provinces",
    ),
}

# Admin-2 lines are one level more detailed than admin-1 again, so they only
# earn their clutter once a render is zoomed in past a single admin-1 unit,
# not merely past the whole country the way admin-1 itself activates at 25
# degrees. Roughly the angular span of one to a few French regions, chosen
# empirically the same way :data:`_TEN_M_BBOX_DEGREES_THRESHOLD` was: narrow
# enough that a whole-country plate (25deg+) never shows 101 department
# lines at once, wide enough that a single-region zoom still gets them.
_ADMIN2_BBOX_DEGREES_THRESHOLD = 8.0

# A second, finer threshold inside the window the gate above already
# allows: past this span (still under the show/hide gate), admin-2 uses
# its own coarse tier rather than the fine one -- a single large US state
# (California, Texas) can itself approach or exceed this span, at which
# point the fine county file's extra detail is not worth its weight
# either. Deliberately well under _ADMIN2_BBOX_DEGREES_THRESHOLD, not
# equal to it, so there is a real fine-tier zone left, not just coarse
# right up to the show/hide edge.
_ADMIN2_FINE_BBOX_DEGREES_THRESHOLD = 3.0

# A region bbox whose longer side is narrower than this many degrees reads as
# "a single country or a small sub-region" rather than "a continent-scale
# view" -- that is the cutoff where switching from 1:50m to the heavier
# 1:10m basemap actually buys visible coastline/border fidelity instead of
# just more file weight for detail no one will see at that zoom.
_TEN_M_BBOX_DEGREES_THRESHOLD = 25.0


def _land_topojson_for_bbox(bbox: Iterable[float] | None) -> Path:
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
    # repair each rather than a fragile world-wide union: the caller clips to a
    # bounding box, so a MultiPolygon of validated pieces is sufficient.
    fixed = [make_valid(g) for g in geoms]
    return unary_union(fixed)


def load_land(bbox: Iterable[float] | None = None) -> Any:
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


def load_country(name: str, bbox: Iterable[float] | None = None) -> Any:
    """Return the polygon of a single country by Natural Earth ``name`` (WGS84).

    Lets a caller partition a *real* national outline into thematic zones: the
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


def load_countries(bbox: Iterable[float] | None = None) -> list[tuple[str, Any]]:
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


def _bbox_in_united_states(bbox: Iterable[float] | None) -> bool:
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


def load_us_states(bbox: Iterable[float] | None = None) -> list[tuple[str, Any]]:
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


def _bbox_in_france(bbox: Iterable[float] | None) -> bool:
    """Cheaply test whether a region bbox falls inside the vendored IGN extent.

    Same bounds-overlap contract as :func:`_bbox_in_united_states`, against
    :data:`_FR_REGIONS_BOUNDS` instead.
    """
    return _bbox_overlaps(bbox, _FR_REGIONS_BOUNDS)


def load_fr_regions(bbox: Iterable[float] | None = None) -> list[tuple[str, Any]]:
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


def _bbox_overlaps(bbox: Iterable[float] | None, bounds: tuple[float, float, float, float]) -> bool:
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


def _admin1_tier_path(
    bbox: Iterable[float] | None,
    fine_path: Path,
    coarse_path: Path,
    threshold: float = _TEN_M_BBOX_DEGREES_THRESHOLD,
) -> Path:
    """Pick the fine or coarse simplification tier for an admin-1/admin-2 source.

    Same algorithmic-tier-selection pattern as :func:`_land_topojson_for_bbox`
    (which the admin-0 country boundaries already use). The default
    ``threshold`` reuses that function's exact 25-degree constant rather
    than inventing a second magic number for admin-1 sources: an admin-1
    boundary render only needs the coarse tier's lighter weight past the
    same bbox span where the country-boundary tier itself already drops to
    1:50m, since that is where the fine tier's extra vertices stop being
    visible at the render's own pixel density. Admin-2 callers pass
    :data:`_ADMIN2_FINE_BBOX_DEGREES_THRESHOLD` instead, a tighter cutoff
    appropriate to admin-2's own, much narrower, visible zoom window.

    Parameters
    ----------
    bbox : iterable of float or None
        ``(west, south, east, north)`` in degrees. ``None`` keeps the fine
        tier, matching how a missing bbox context is treated elsewhere in
        this module (no info to downgrade on).
    fine_path, coarse_path : pathlib.Path
        The two vendored tiers for one source.
    threshold : float, optional
        The bbox-span cutoff, in degrees, above which the coarse tier is
        picked. Defaults to :data:`_TEN_M_BBOX_DEGREES_THRESHOLD`.

    Returns
    -------
    pathlib.Path
        ``coarse_path`` when the bbox's longer side is at least
        ``threshold``, otherwise ``fine_path``.
    """
    if bbox is None:
        return fine_path
    west, south, east, north = bbox
    span = max(east - west, north - south)
    return coarse_path if span >= threshold else fine_path


def _bbox_in_osm_admin1(bbox: Iterable[float] | None) -> bool:
    """Cheaply test whether a region bbox overlaps *any* vendored OSM country.

    Used by :func:`_attribution_layer` to decide whether the ODbL credit is
    owed, without caring which of :data:`_OSM_ADMIN1_SOURCES` matched.
    """
    return any(_bbox_overlaps(bbox, bounds) for _, _, bounds, _ in _OSM_ADMIN1_SOURCES.values())


def load_osm_admin1(bbox: Iterable[float] | None = None) -> list[tuple[str, Any]]:
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


def load_admin2(bbox: Iterable[float] | None = None) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every admin-2 feature that overlaps a bbox.

    One level finer than :func:`load_us_states`/:func:`load_fr_regions`/
    :func:`load_osm_admin1` -- France's departments, US counties, and
    Swiss districts (see :data:`_ADMIN2_SOURCES`), drawn by
    :func:`_admin2_borders_layer` rather than
    :func:`_internal_borders_layer`, since admin-2 additionally gates on
    zoom level (:data:`_ADMIN2_BBOX_DEGREES_THRESHOLD`), not just bbox
    overlap: a whole-country plate should not show a hundred department
    lines even where the data is available. Within that gate, each source
    also picks its own fine/coarse tier via
    :data:`_ADMIN2_FINE_BBOX_DEGREES_THRESHOLD`, the same pyramid pattern
    :func:`load_us_states` and friends use, just at admin-2's own scale.

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
    for fine_path, coarse_path, bounds, object_name in _ADMIN2_SOURCES.values():
        if not _bbox_overlaps(bbox, bounds):
            continue
        path = _admin1_tier_path(
            bbox, fine_path, coarse_path, threshold=_ADMIN2_FINE_BBOX_DEGREES_THRESHOLD
        )
        topo = json.loads(path.read_text())
        out.extend(_named_polygons_from_topojson(topo, object_name))
    return out


def load_rivers() -> list[tuple[Any, str, int]]:
    """Return ``(geometry, name, scalerank)`` for the vendored river centerlines.

    Natural Earth 50m rivers + lake centerlines, trimmed to named features. Lower
    ``scalerank`` means a more prominent river (used to decide what gets labelled).
    """
    if not _RIVERS_GEOJSON.is_file():
        # Returning [] here is what let a map ship with no rivers at all and
        # no complaint: the plate rendered, the exit code was 0, and the
        # Dnieper was simply absent from a map of Ukraine. A missing vendored
        # asset is a packaging bug, not a legitimate "this region has no
        # rivers", so it is now audible. Still not fatal — a caller who never
        # asked for rivers should not be stopped by them.
        warnings.warn(
            f"river centerlines missing at {_RIVERS_GEOJSON}: the map will be "
            "drawn without rivers. This is a packaging fault, not a property "
            "of the region.",
            RuntimeWarning,
            stacklevel=2,
        )
        return []
    data = json.loads(_RIVERS_GEOJSON.read_text())
    out: list[tuple[Any, str, int]] = []
    for feat in data.get("features", []):
        try:
            geom = shape(feat["geometry"])
        except Exception:  # skip a malformed river feature rather than fail the plate
            continue
        props = feat.get("properties", {})
        out.append((geom, props.get("name", ""), int(props.get("scalerank", 10))))
    return out



def load_lakes() -> list[tuple[Any, str, int]]:
    """Return ``(geometry, name, scalerank)`` for the vendored inland lakes.

    Natural Earth 50m lakes, public domain, trimmed to name + scalerank like
    the river centerlines beside them. The coastline data this generator draws
    from is *land versus ocean* only, so before this every inland water body
    was simply painted as land: a plate of the Kivus put Goma and Bukavu on
    dry ground 100 km apart with nothing between them, when in fact they face
    each other across Lake Kivu, and the lake is why the road between them
    goes where it goes. The same hole swallowed Tanganyika, Victoria, Chad,
    the Caspian and the Great Lakes.

    Returns
    -------
    list of (geometry, str, int)
        Empty, with a warning, when the asset is missing -- the same treatment
        :func:`load_rivers` gives, and for the same reason: a missing vendored
        file is a packaging fault, not a region with no lakes in it.
    """
    if not _LAKES_GEOJSON.is_file():
        warnings.warn(
            f"lake polygons missing at {_LAKES_GEOJSON}: the map will be drawn "
            "with inland water painted as land. This is a packaging fault, not "
            "a property of the region.",
            RuntimeWarning,
            stacklevel=2,
        )
        return []
    data = json.loads(_LAKES_GEOJSON.read_text())
    out: list[tuple[Any, str, int]] = []
    for feat in data.get("features", []):
        try:
            geom = shape(feat["geometry"])
        except Exception:  # skip a malformed lake rather than fail the plate
            continue
        props = feat.get("properties", {})
        out.append((geom, props.get("name") or "", int(props.get("scalerank") or 10)))
    return out



# --------------------------------------------------------------------------- #
# Projection                                                                   #
# --------------------------------------------------------------------------- #


def build_projection(bbox: list[float], epsg: str | None) -> Transformer:
    """Return a lon/lat -> planar-metre transformer suited to ``bbox``.

    When ``epsg`` is ``None`` (or ``"auto"``) a Lambert Conformal Conic is centred
    on the region, with standard parallels at the one-sixth / five-sixth latitudes
    (the classic two-thirds rule): conformal, so shapes and angles stay true at
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


def make_viewport(proj: Transformer, bbox: list[float], width: float, pad: float) -> dict[str, Any]:
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
#: Monospace for the provenance footer: a method note is metadata, and
#: setting it in the same face as the title invites it to be read as
#: part of the argument rather than as its receipt.
_MONO_FONT = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, monospace"


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
        "<defs>"
        '<filter id="panel-shadow" x="-10%" y="-10%" width="120%" height="120%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000" flood-opacity="0.18"/>'
        "</filter>"
        '<filter id="marker-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#000" flood-opacity="0.35"/>'
        "</filter>"
        # A soft label halo used for the front-line callout and title underline.
        '<filter id="soft-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="0.6" stdDeviation="0.9" flood-color="#000" flood-opacity="0.25"/>'
        "</filter>"
        f'<pattern id="hatch-contested" width="6.5" height="6.5" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse">'
        f'<line x1="0" y1="0" x2="0" y2="6.5" stroke="{contested_hatch}" stroke-width="1.25" '
        'stroke-opacity="0.6"/>'
        "</pattern>"
        "</defs>"
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
    """Return a ``<text>`` with letter-spacing: the cartographer's tracked label."""
    label = text.upper() if upper else text
    # Paint-order halo: a white stroke drawn *under* the fill so the label stays
    # legible over land, sea or any zone colour, standard cartographic practice.
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{font}" font-size="{size:.1f}" font-weight="{weight}" '
        f'letter-spacing="{tracking:.2f}" fill="{fill}" '
        f'paint-order="stroke" stroke="#ffffff" stroke-width="{max(2.0, size * 0.28):.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round">{_esc(label)}</text>'
    )


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _nice_round(value: float) -> float:
    """Return a cartographer-friendly round number <= ``value`` (1/2/5 x 10^k)."""
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = 10**exp
    for mult in (5, 2, 1):
        if mult * base <= value:
            return mult * base
    return base


def scale_bar(x: float, y: float, vp: dict[str, Any], ink: str = "#1b2733") -> str:
    """Return a dual-unit (km + mi) scale bar sized to a round distance on the map."""
    m_per_unit = vp["m_per_unit"]
    target_units = min(vp["width"] * 0.22, 180)  # aim ~1/5 canvas, capped
    km = _nice_round(target_units * m_per_unit / 1000.0)
    mi = _nice_round(target_units * m_per_unit / 1609.34)
    km_len = km * 1000.0 / m_per_unit
    mi_len = mi * 1609.34 / m_per_unit

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
        f"{bar(y + 20 * ts, mi_len, _fmt_num(mi), 'MI')}</g>"
    )


def _fmt_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _capital_star(cx: float, cy: float, r: float) -> str:
    """Return a five-point star inside a white ring: the national-capital glyph."""
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
    grid_sx, grid_sy = np.meshgrid(np.arange(plot_w) + pad, np.arange(plot_h) + pad)
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


def _fmt_lon(v: float) -> str:
    """Format a longitude as a signed-free degree string, e.g. ``11.0°W``."""
    return f"{abs(v):.1f}°{'W' if v < 0 else 'E'}"


def _fmt_lat(v: float) -> str:
    """Format a latitude as a signed-free degree string, e.g. ``35.0°N``."""
    return f"{abs(v):.1f}°{'S' if v < 0 else 'N'}"


def accessible_text(cfg: dict[str, Any]) -> tuple[str, str]:
    """Return the ``(title, description)`` pair the root ``<svg>`` exposes to a screen reader.

    ``make_choropleth`` and ``make_density`` have always opened their document
    with ``role="img"`` + ``aria-labelledby`` pointing at a ``<title>``/``<desc>``
    pair; this generator opened with a bare ``<svg>``, so a screen reader
    announced nothing but "image". That mattered more here than on the other
    two, because this plate's whole content *is* a claim -- who holds which
    ground -- and a reader who cannot see it was getting neither the claim nor
    the caveat that it is a claim.

    Everything below is read off ``cfg`` alone: no geometry is loaded and no
    layer is rebuilt, so adding the description costs nothing at render time
    and cannot disagree with what was drawn.

    The last sentence is the contract ``TRIGGERS.md`` states for every consumer
    of this generator -- a situation map draws exactly what it was handed and
    has no view on whether the control it shows is real. A sighted reader gets
    that from the provenance caption and the legend footer; it belongs in the
    accessible description for the same reason.

    Parameters
    ----------
    cfg : dict
        The same parsed config :func:`build_map` renders from.

    Returns
    -------
    tuple of (str, str)
        The ``<title>`` text and the ``<desc>`` text, both unescaped (the
        caller runs them through :func:`_esc`).

    Examples
    --------
    >>> title, desc = accessible_text({
    ...     "title": "Eastern front",
    ...     "region": {"bbox": [22.0, 44.0, 40.0, 52.5]},
    ...     "areas_of_control": {
    ...         "palette": {"Ukraine": "#9cc3d5", "Russia": "#d98880"},
    ...         "contested": ["Russia"],
    ...     },
    ... })
    >>> title
    'Eastern front'
    >>> desc
    'Situation map covering 22.0°E to 40.0°E, 44.0°N to 52.5°N. Areas of control in 2 classes: Ukraine, Russia (contested). The map draws the assessment it was given; it does not verify who holds what.'

    A plain basemap with no control layer carries no claim, so it is described
    without the caveat:

    >>> _, desc = accessible_text({"region": {"bbox": [-11.0, 35.0, 30.0, 60.0]}})
    >>> desc
    'Situation map covering 11.0°W to 30.0°E, 35.0°N to 60.0°N.'
    """
    title = str(cfg.get("title") or "Situation map")

    west, south, east, north = (float(v) for v in cfg["region"]["bbox"])
    sentences = [
        f"Situation map covering {_fmt_lon(west)} to {_fmt_lon(east)}, "
        f"{_fmt_lat(south)} to {_fmt_lat(north)}."
    ]

    subtitle = cfg.get("subtitle")
    if subtitle:
        sentences.append(f"{str(subtitle).rstrip('.')}.")

    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if palette:
        contested = set(aoc.get("contested", []))
        # "(contested)" after a class name is the legend's own hatch, spelled
        # out: the legend draws that distinction and the description must too.
        named = ", ".join(
            f"{name} (contested)" if name in contested else str(name) for name in palette
        )
        sentences.append(f"Areas of control in {len(palette)} classes: {named}.")

    if cfg.get("front", {}).get("line"):
        sentences.append("An approximate front line is drawn.")

    markers = [str(mk.get("label", "")) for mk in cfg.get("marker_legend", [])]
    markers = [m for m in markers if m]
    if markers:
        sentences.append(f"Marked: {', '.join(markers)}.")

    # The provenance the plate already carries in its caption and legend
    # footer, repeated here because that is text a screen reader reaches only
    # as three disconnected <text> runs somewhere in the middle of the file.
    provenance = [
        str(x).rstrip(".")
        for x in (cfg.get("method"), cfg.get("source"), cfg.get("as_of"))
        if x
    ]
    if provenance:
        sentences.append(f"{'. '.join(provenance)}.")

    if palette:
        sentences.append(
            "The map draws the assessment it was given; it does not verify who holds what."
        )

    return title, " ".join(sentences)


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
    # ── plate ────────────────────────────────────────────────────────────
    # "day" is the default and stays exactly as it was: cream land, muted
    # blue sea, a plate that prints. "night" is the other tradition — the
    # one a screen is actually good at. On black, a saturated fill glows
    # instead of flattening, and the relief reads as terrain rather than as
    # a wash, because the eye has the whole dark end of the range to work
    # with rather than the compressed top of it.
    #
    # Nothing here is a default. A caller who does not ask for a plate gets
    # the plate they had yesterday.
    plate = str(basemap.get("plate", "day")).lower()
    if plate not in _PLATES:
        raise ValueError(f"unknown plate {plate!r}; known: {sorted(_PLATES)}")
    palette = _PLATES[plate]

    # A named plate outranks the individual colours. Any config written
    # before plates existed carries day values, and honouring them would mean
    # answering "plate: night" with a cream map — the silent-wrong-answer
    # failure this codebase keeps running into. The override is announced so
    # it is never a mystery.
    _PLATE_KEYS = ("sea_color", "land_color", "coast_color")
    if plate != "day":
        overridden = [k for k in _PLATE_KEYS if k in basemap]
        if overridden:
            warnings.warn(
                f"plate {plate!r} overrides {', '.join(overridden)} from the config; "
                "remove them to silence this, or drop the plate to keep them.",
                RuntimeWarning,
                stacklevel=2,
            )
        sea_color, land_color, coast_color = palette["sea"], palette["land"], palette["coast"]
    else:
        sea_color = basemap.get("sea_color", palette["sea"])
        land_color = basemap.get("land_color", palette["land"])
        coast_color = basemap.get("coast_color", palette["coast"])

    # The chrome builders take cfg, not a palette; stashing it here beats
    # threading a new argument through nine call sites.
    cfg["_plate"] = palette

    region_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
    # bbox already carries the region's real extent -- reuse it to pick the
    # 10m/50m basemap tier instead of re-deriving it from region_box.
    land = load_land(bbox=bbox).intersection(region_box)
    land_proj = _project_geom(land, proj)
    region_proj = _project_geom(region_box, proj)
    # The same polygon the geographic layers are clipped to, in plate
    # coordinates: every label layer tests against this rather than the
    # plate rectangle, which is wider than the drawn map under a conic.
    plate_region = Polygon(
        [vp["to_svg"](px, py) for px, py in region_proj.exterior.coords]
    )
    sea_proj = region_proj.difference(land_proj)

    layers: list[str] = []

    # 0. relief --------------------------------------------------------------
    # Drawn first (bottom of the stack) so the sea and land fills paint over
    # it -- basemap-land's fill-opacity below is what lets it peek through.
    if basemap.get("relief", True):
        layers.append(
            _relief_layer(vp, proj, pad, W, H, projected_geom_to_path(region_proj, vp), bbox)
        )

    # Every geographic layer below is clipped to the projected region bbox
    # (the same trapezoid the relief already clips to): LCC's meridians fan
    # out from the cone apex, so neighbour geometry drawn for context
    # otherwise pokes out past the region's bottom edge into the plate
    # margin (caught via the Ralph Eyeball Loop: the Western-Europe demo
    # rendered a loose strip of the North-African coast under the frame).
    geo_start = len(layers)

    # 1. basemap-sea -------------------------------------------------------- #
    layers.append(
        f'<g id="basemap-sea">'
        f'<path d="{projected_geom_to_path(sea_proj, vp)}" fill="{sea_color}"/></g>'
    )

    # 2. basemap-bathymetry ------------------------------------------------- #
    bath = basemap.get("bathymetry", {"rings": 7, "step_km": None})
    layers.append(_bathymetry_layer(land_proj, sea_proj, vp, bath, palette))

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
    land_fill_opacity = palette["relief_opacity"] if basemap.get("relief", True) else 1.0
    layers.append(
        f'<g id="basemap-land">'
        f'<path d="{projected_geom_to_path(land_proj, vp)}" fill="{land_color}" '
        f'fill-opacity="{land_fill_opacity}"/></g>'
    )

    # 3b. lakes --------------------------------------------------------------
    # Over the land fill, because the coastline data is land-versus-ocean only
    # and paints every inland water body as dry ground; under the borders and
    # the control zones, because a lake is basemap, not thematic.
    water_labels: list[tuple[float, float]] = []
    layers.append(_lakes_layer(cfg, proj, vp, region_box, water_labels))

    # 3c. internal-borders (admin-1: US states, FR regions, OSM countries) --- #
    layers.append(_internal_borders_layer(cfg, proj, vp, region_box, plate_region))

    # 3d. admin2-borders (admin-2, currently FR departments, zoom-gated) ----- #
    layers.append(_admin2_borders_layer(cfg, proj, vp, region_box, plate_region))

    # 4. areas-of-control --------------------------------------------------- #
    layers.append(_areas_of_control_layer(cfg, proj, vp, region_box))

    # 4a. frontiers (international borders + neighbour labels), drawn over the
    #     control fills for the same reason the coastline below is: a national
    #     border is base geography, and on a map *about* who holds what, which
    #     side of a frontier a zone sits on is the question being asked. Drawn
    #     under the fills it disappeared wherever a zone touched it — and where
    #     the same class held both sides, it vanished entirely.
    layers.append(_frontiers_layer(cfg, proj, vp, region_box, plate_region))

    # 4b. coastline: a crisp hairline where land meets the sea, drawn over the
    #     control fills so the shore reads sharply against the water. Placed here
    #     (not with the land) so a coastal control zone does not paint over it.
    coast = land_proj.boundary.intersection(sea_proj.buffer(vp["m_per_unit"] * 1.5))
    coast_d = projected_geom_to_path(coast, vp, close=False)
    layers.append(
        f'<g id="coastline"><path d="{coast_d}" fill="none" stroke="{coast_color}" '
        f'stroke-width="{0.9 * vp["ts"]:.2f}" stroke-opacity="0.75" '
        f'stroke-linejoin="round" stroke-linecap="round"/></g>'
        if coast_d
        else '<g id="coastline"></g>'
    )

    # 5. infrastructure ----------------------------------------------------- #
    layers.append(_infrastructure_layer(cfg, proj, vp))

    # 5b. rivers (over the fills so the water reads) ------------------------ #
    layers.append(_rivers_layer(cfg, proj, vp, region_box, water_labels))

    # 5b-bis. cities: the map is populated by default, so a reader always has
    #         somewhere to stand.
    layers.append(_cities_layer(cfg, proj, vp, bbox, plate_region))

    # 5c. front line: the emphasised contact line between the control zones,
    #     the single most-read feature of a situation plate.
    layers.append(_front_line_layer(cfg, proj, vp))

    # 5d. axes of advance: drawn last of the geographic layers, because an
    #     arrow that the coastline or a control fill crossed would stop
    #     reading as movement.
    layers.append(_arrows_layer(cfg, proj, vp))

    # Close the geographic stack: wrap layers 1..5d in the region clip.
    # Markers, labels, furniture, legend and frame stay unclipped -- they
    # are annotations allowed to sit in the plate margin.
    region_clip_d = projected_geom_to_path(region_proj, vp)
    layers[geo_start:] = [
        f'<defs><clipPath id="region-clip"><path d="{region_clip_d}"/></clipPath></defs>'
        f'<g id="geo" clip-path="url(#region-clip)">' + "".join(layers[geo_start:]) + "</g>"
    ]

    # 6. forces ------------------------------------------------------------- #
    marker_legend = cfg.get("marker_legend", [])
    layers.append(_markers_layer(cfg.get("forces", []), proj, vp, "forces", marker_legend))

    # 7. events ------------------------------------------------------------- #
    layers.append(_markers_layer(cfg.get("events", []), proj, vp, "events", marker_legend))

    # 8. annotation-labels -------------------------------------------------- #
    layers.append(_labels_layer(cfg, proj, vp))

    # 9. annotation-furniture ---------------------------------------------- #
    layers.append(_furniture_layer(cfg, vp))

    # The caption sits with the furniture, not with the geography: the geo
    # layers are clipped to the region polygon, and a footer under the map
    # falls outside it — drawn there it was silently cut away.
    layers.append(_caption_block(cfg, vp))

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
    # panel, and a rounded clip, the premium "printed plate" cue of the reference.
    frame = cfg.get("frame", {})
    margin = float(frame.get("margin", 22))
    page_color = frame.get("page_color", _pal(cfg)["page"])
    radius = float(frame.get("radius", 8))
    # ``legend_position: "right"`` moves the legend off the map entirely into
    # its own column: the plate grows wide enough to hold it (rather than the
    # legend floating over map content), so the map's own W/H stay untouched
    # for every layer already drawn above -- only the outer plate/canvas size
    # changes here.
    legend_pos = str(cfg.get("legend_position", "bottom-right"))
    if legend_pos == "right":
        panel_w, panel_h, corner_margin = _legend_panel_dims(cfg, vp["ts"])
        plate_w = W + corner_margin + panel_w + corner_margin
        plate_h = max(H, panel_h + 2 * corner_margin)
    else:
        plate_w, plate_h = W, H
    outer_w = plate_w + 2 * margin
    outer_h = plate_h + 2 * margin
    clip = (
        f'<clipPath id="plate-clip"><rect x="0" y="0" width="{plate_w:.1f}" height="{plate_h:.1f}" '
        f'rx="{radius}" ry="{radius}"/></clipPath>'
    )
    hatch = cfg.get("areas_of_control", {}).get("hatch_color", "#b03a3a")
    # role="img" + aria-labelledby is what the other two generators have always
    # emitted (see _svg.svg_open); without it a screen reader announces this
    # plate as an unlabelled graphic and the reader learns nothing at all.
    a11y_title, a11y_desc = accessible_text(cfg)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {outer_w:.1f} {outer_h:.1f}" '
        f'width="{outer_w:.1f}" height="{outer_h:.1f}" '
        f'role="img" aria-labelledby="sm-title sm-desc">'
        f'<title id="sm-title">{_esc(a11y_title)}</title>'
        f'<desc id="sm-desc">{_esc(a11y_desc)}</desc>'
        f"{svg_defs(hatch)[:-7]}{clip}</defs>"
        # Hover-info bubbles for areas-of-control zones and forces/events
        # markers: same .hit/.tip convention as case-studies/financial-markets
        # and make_choropleth.py.
        "<style>"
        ".tip{opacity:0;pointer-events:none;transition:opacity .12s ease;}"
        ".hit:hover~.tip,.hit:focus~.tip{opacity:1;}"
        ".hit{cursor:crosshair;}"
        ".hit:focus-visible{outline:2px solid #1b2733;outline-offset:1px;}"
        "@media (prefers-reduced-motion: reduce){.tip{transition:none;}}"
        "</style>"
        f'<rect width="{outer_w:.1f}" height="{outer_h:.1f}" fill="{page_color}"/>'
        f'<g transform="translate({margin:.1f},{margin:.1f})">'
        f'<rect x="0" y="0" width="{plate_w:.1f}" height="{plate_h:.1f}" rx="{radius}" ry="{radius}" '
        f'fill="{_pal(cfg)["plate"]}" filter="url(#panel-shadow)"/>'
        f'<g clip-path="url(#plate-clip)">'
        f'<rect width="{plate_w:.1f}" height="{plate_h:.1f}" fill="{_pal(cfg)["plate"]}"/>'
        f"{''.join(layers)}"
        f"</g></g>"
        f"</svg>"
    )


def _lakes_layer(
    cfg: dict[str, Any],
    proj: Transformer,
    vp: dict[str, Any],
    region_box: Any,
    placed: list[tuple[float, float]] | None = None,
) -> str:
    """Return inland lakes, filled as water and labelled in italic like the rivers.

    Drawn over the land fill and under the control zones: a lake is part of the
    physical basemap, not a thematic overlay, and a control zone that extends
    across open water is a claim the map should keep visible rather than hide.

    Colour follows the sea (``basemap.sea_color``) unless ``lakes.color`` says
    otherwise, because a reader who has learnt one blue for water should not
    have to learn a second. Labels use the same italic the rivers use, the
    cartographic convention for water, and are placed only on lakes big enough
    in view to carry one -- ``lakes.label_min_area_frac`` of the plate.

    Set ``lakes.show: false`` to suppress the layer.

    **The vendored extents have a date, and a dated plate may disagree with
    them.** Natural Earth is a snapshot, and some of the world's best-known
    inland water has moved since it was taken. Two options exist for saying so
    rather than drawing water that is not there:

    ``lakes.skip``
        A list of names not to draw at all, mirroring ``rivers.skip``.

    ``lakes.former``
        A list of names to draw as *former* water: the outline dashed, no
        fill, the name suffixed ``(former)``. This is usually the better
        answer, because the absence is itself information — a reader who knows
        the geography will look for the water, and an empty space answers
        nothing while a dashed outline answers exactly.

    The cases this repo has had to handle, with dates, so the next caller does
    not have to discover them by being wrong in public:

    * **Kakhovka Reservoir** — drained within two weeks of the dam breach of
      6 June 2023. By 2026 the bed is willow and poplar scrub over sand and
      marsh, and is being used for infantry infiltration; it is not water and
      has not been for years. The bundled Ukraine example draws it as former.
    * **Lake Urmia** — the vendored polygon is near its historic extent,
      roughly 4 200 km². It has repeatedly fallen below a fifth of that.
    * **Lake Chad** — already the modern, shrunken lake here (~1 300 km²), so
      no correction is needed; noted because it is the one most people expect
      to be wrong.
    * **Aral Sea** — already split into ``North Aral Sea`` and ``South Aral
      Sea``, which is the post-2000s state rather than the 1960s one.
    """
    settings = cfg.get("lakes", {})
    if settings.get("show", True) is False:
        return '<g id="lakes"></g>'
    basemap = cfg.get("basemap", {})
    palette = cfg.get("_plate", _PLATES["day"])
    color = settings.get("color", basemap.get("sea_color", palette["sea"]))
    edge = settings.get("edge_color", basemap.get("coast_color", palette["coast"]))
    ts = vp["ts"]
    label_color = settings.get("label_color", cfg.get("rivers", {}).get("label_color", "#4f7290"))
    min_frac = float(settings.get("label_min_area_frac", 0.0012))
    always = {n.lower() for n in settings.get("always_label", [])}
    skip = {n.lower() for n in settings.get("skip", [])}
    former = {n.lower() for n in settings.get("former", [])}
    plate_area = float(vp["width"]) * float(vp["height"])

    shapes: list[str] = []
    labels: list[str] = []
    placed = placed if placed is not None else []
    for geom, name, _rank in load_lakes():
        key = name.lower()
        if key and key in skip:
            continue
        try:
            clipped = geom.intersection(region_box)
        except Exception:  # skip a malformed lake rather than fail the plate
            continue
        if clipped.is_empty:
            continue
        gp = _project_geom(clipped, proj)
        d = projected_geom_to_path(gp, vp)
        if not d:
            continue
        is_former = bool(key) and key in former
        if is_former:
            # No fill, because there is no water: a dashed outline is the
            # cartographic form for a body that was there and is not.
            shapes.append(
                f'<path d="{d}" fill="none" stroke="{edge}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="0.7" '
                f'stroke-dasharray="{3.6 * ts:.1f} {2.8 * ts:.1f}"/>'
            )
        else:
            shapes.append(
                f'<path d="{d}" fill="{color}" stroke="{edge}" '
                f'stroke-width="{0.6 * ts:.1f}" stroke-opacity="0.75"/>'
            )
        if not name:
            continue
        if is_former:
            name = f"{name} (former)"
        biggest = max(getattr(gp, "geoms", [gp]), key=lambda g: g.area)
        # Area in plate units: the same "is it big enough to carry a name"
        # question the river layer asks about length.
        px_area = biggest.area / (vp["m_per_unit"] ** 2)
        # ``key`` and not ``name``: the "(former)" suffix is appended above,
        # and an always_label naming the real lake must still match.
        if px_area < min_frac * plate_area and key not in always:
            continue
        pt = _label_point(biggest)
        x, y = vp["to_svg"](pt.x, pt.y)
        size = 10.5 * ts
        if not _label_fits(x, y, name, size=size, vp=vp):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < (58 * ts) ** 2 for px, py in placed):
            continue
        placed.append((x, y))
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-family="{_DEFAULT_FONT}" font-size="{size:.1f}" font-style="italic" '
            f'fill="{label_color}" paint-order="stroke" stroke="#ffffff" '
            f'stroke-width="{2.2 * ts:.1f}" stroke-linejoin="round">{_esc(name)}</text>'
        )
    return f'<g id="lakes">{"".join(shapes)}{"".join(labels)}</g>'


def _bathymetry_layer(
    land_proj: Any, sea_proj: Any, vp: dict[str, Any], bath: dict[str, Any],
    palette: dict[str, Any] | None = None,
) -> str:
    """Return concentric depth-contour halos buffered out from the coast into the sea."""
    palette = palette or _PLATES["day"]
    rings = int(bath.get("rings", 7))
    if rings <= 0 or sea_proj.is_empty:
        return '<g id="basemap-bathymetry"></g>'
    m_per_unit = vp["m_per_unit"]
    step_km = bath.get("step_km")
    if not step_km:
        step_km = (vp["width"] * 0.02 * m_per_unit) / 1000.0  # ~2% of canvas
    step_m = step_km * 1000.0
    # White rings read as depth on a pale sea and as harsh contour lines on
    # a near-black one, so the plate supplies its own value.
    # Same rule as the plate colours: a named plate outranks values a config
    # inherited for the other one. White rings read as depth on a pale sea
    # and as harsh contour lines drawn over a near-black one.
    if palette is not _PLATES["day"]:
        color, opacity = palette["bathy"], palette["bathy_opacity"]
    else:
        color = bath.get("color", palette["bathy"])
        opacity = float(bath.get("opacity", palette["bathy_opacity"]))
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
        data = json.loads(
            (base / spec).read_text() if not Path(spec).is_absolute() else Path(spec).read_text()
        )
        return data.get("features", [])
    if isinstance(spec, dict) and spec.get("type") == "FeatureCollection":
        return spec.get("features", [])
    if isinstance(spec, list):
        return spec
    return []


def _areas_of_control_layer(
    cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any], region_box: Any | None = None
) -> str:
    """Return the territory zones: pastel fill under a white casing; contested = hatch.

    Each zone's fill carries ``class="hit"`` and a :func:`tooltip_bubble`
    sibling (revealed via the ``.hit:hover~.tip`` pattern): the actor/
    category name, whether the zone is marked contested, and its share of
    the mapped region's total area -- computed from the projected geometry
    already at hand here, not a fabricated stat.
    """
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
    # How the control colour meets the terrain underneath it. A flat alpha
    # fill averages the hillshade towards a single tone: measured on the
    # 0.78 default, a full black-to-white relief ramp survives as 14 levels
    # of variation, against 53 under a multiply blend — the mountains inside
    # a controlled area effectively flatten out while the same mountains
    # just across the border stay visible. Multiply keeps the class hue and
    # takes its luminance from the terrain, which is the standard treatment
    # for an areas-of-control plate and the reason relief is drawn at all.
    #
    # Only worth doing when there *is* relief underneath; over flat paper a
    # multiply of a pastel is just the pastel, and alpha is more predictable.
    has_relief = bool(cfg.get("basemap", {}).get("relief", True))
    plate_blend = cfg.get("_plate", _PLATES["day"])["blend"]
    blend = aoc.get("blend", plate_blend if has_relief else "none")
    fill_style = f' style="mix-blend-mode:{blend}"' if blend in ("multiply", "screen") else ""
    # Under multiply the alpha is what keeps a dark valley from dragging the
    # pastel down to mud; the two work together rather than either alone.
    if blend == "multiply":
        fill_op = float(aoc.get("fill_opacity", 0.88))
    W, H = vp["width"], vp["height"]

    zones: list[dict[str, Any]] = []
    for feat in features:
        props = feat.get("properties", {})
        cat = props.get(field, "")
        src = shape(feat["geometry"])
        # Clip to the region before projecting. A caller who hands over a whole
        # country's outline for a plate showing one province of it was emitting
        # a path many times the canvas: megabytes of coordinates that are
        # clipped away at draw time, an area share computed against territory
        # nobody can see, and -- found by rendering it -- a shape so far outside
        # the canvas that resvg dropped its ``mix-blend-mode`` fill entirely,
        # so the eastern-DRC plate came out with no control colours at all.
        if region_box is not None:
            try:
                src = src.intersection(region_box)
            except Exception:  # a malformed zone clips to nothing, not to a crash
                continue
            if src.is_empty:
                continue
        geom = _project_geom(src, proj)
        d = projected_geom_to_path(geom, vp)
        if not d:
            continue
        zones.append({"cat": cat, "geom": geom, "d": d})
    total_area = sum(z["geom"].area for z in zones) or 1.0

    casings: list[str] = []
    fills: list[str] = []
    for z in zones:
        cat, geom, d = z["cat"], z["geom"], z["d"]
        # White casing drawn first (under the fill) so borders read as clean seams.
        casings.append(
            f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{casing_w}" '
            f'stroke-linejoin="round"/>'
        )
        color = palette.get(cat, "#dddddd")
        is_contested = cat in contested
        fills.append(
            f'<path class="hit" tabindex="0" d="{d}" fill="{color}" fill-opacity="{fill_op:.2f}" '
            f'stroke="{color}" stroke-width="0.7" stroke-opacity="0.95"{fill_style}/>'
        )
        if is_contested:
            fills.append(f'<path d="{d}" fill="url(#hatch-contested)"/>')
        share_pct = geom.area / total_area * 100
        detail = f"{share_pct:.1f}% of mapped area"
        if is_contested:
            detail += " · contested"
        rp = geom.representative_point()
        tx, ty = vp["to_svg"](rp.x, rp.y)
        fills.append(
            tooltip_bubble(
                tx,
                ty,
                [cat or "Unclaimed", detail],
                anchor="middle",
                canvas_w=W,
                canvas_h=H,
                ink="#1b2733",
                secondary="#5b6169",
                border="#e4e8ec",
            )
        )
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
            out.append(
                f'<path d="{d}" fill="none" stroke="#8a8f96" stroke-width="0.7" '
                f'stroke-opacity="0.7"/>'
            )
    for ap in infra.get("airports", []):
        x, y = vp["to_svg"](*proj.transform(ap["lon"], ap["lat"]))
        out.append(
            f'<g transform="translate({x:.1f},{y:.1f})">'
            f'<path d="M-4,0 L4,0 M0,-4 L0,4" stroke="#5b6169" stroke-width="1.1"/>'
            f'<circle r="2.4" fill="none" stroke="#5b6169" stroke-width="1"/></g>'
        )
    return f'<g id="infrastructure">{"".join(out)}</g>'


def _frontiers_layer(
    cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any], region_box: Any,
    region: Any | None = None,
) -> str:
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
    # A frontier now rides *over* the control fills (see layer 4a), so it has
    # to hold its own against a saturated pastel rather than a beige paper.
    # Measured with sprezzature-colors against the three surfaces this line
    # crosses on a typical plate, the old #b7bbc0 scored 1.51 on paper, 1.33
    # on the government blue and **1.05** on the occupied pink — which is to
    # say it stopped existing exactly where the map is most read. #5c636b is
    # the lightest value clearing 3:1 on all three (WCAG 1.4.11, non-text
    # contrast) while staying plainly subordinate to the near-black front line.
    color = fr.get("color", "#5c636b")
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
        except Exception:  # skip a malformed country geometry rather than fail the plate
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
            pt = _label_point(vis)
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            if _label_fits(
                x, y, name, size=9.5 * ts, tracking=2.2, vp=vp, region=region
            ):
                labels.append(
                    tracked_text(x, y, name, size=9.5 * ts, fill="#9ba1a7", tracking=2.2, weight="600")
                )
    return f'<g id="frontiers">{"".join(lines)}{"".join(labels)}</g>'


#: Average glyph advance as a fraction of font size, for the house sans at the
#: weights territory labels use. Same constant, same purpose, as
#: ``_places._GLYPH_WIDTH_RATIO``: estimating a label's width without
#: measuring text, which an SVG writer cannot do.
_GLYPH_WIDTH_RATIO = 0.55


def _label_fits(
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    tracking: float = 0.0,
    vp: dict[str, Any],
    region: Any | None = None,
    anchor: str = "middle",
) -> bool:
    """Return whether a label lands wholly inside the drawn map, not merely inside the plate.

    The automatic city layer has clipped its labels to the plate rectangle
    since ``Istanbul`` came out as ``Ista``. That is the wrong rectangle. The
    geographic layers are clipped to the *projected region polygon*, which
    under a conic projection is a trapezoid narrower than the plate at top and
    bottom -- so a label can sit inside the plate, pass that check, and still
    be sliced by the region clip. On the Sudan plate that took ``Asmara`` down
    to ``Asm`` and ``Jeddah`` to ``J``, and it dropped ``CENTRAL AFRICAN
    REPUBLIC`` off the left edge as ``NTRAL ... REP``, which reads as a
    different country rather than as a cropped name.

    Dropping the name is the right answer rather than nudging it inward, for
    the reason the city layer already gives: a name moved off the thing it
    names points at the wrong ground. A territory label is centred on the pole
    of inaccessibility, so sliding it to fit would walk it towards, and then
    across, a border.

    Parameters
    ----------
    x, y : float
        Plate coordinates of the text anchor.
    text : str
        The label, before :func:`tracked_text` upper-cases it.
    size : float
        Font size in user units, already scaled by ``vp["ts"]``.
    tracking : float, optional
        Extra letter-spacing in user units, as passed to :func:`tracked_text`.
    vp : dict
        The viewport, for its ``width``/``height``.
    region : shapely Polygon, optional
        The region clip in plate coordinates. When given, the label box must
        fit inside it; when ``None``, the plate rectangle is used.
    anchor : str, optional
        ``"middle"`` (the territory labels) or ``"start"`` (the city layer).

    Returns
    -------
    bool
        True when the whole label lies inside the clip.

    Examples
    --------
    >>> vp = {"width": 200.0, "height": 100.0}
    >>> _label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp)
    True

    The same label centred near the edge does not fit, and is dropped rather
    than cropped:

    >>> _label_fits(6, 50, "CHAD", size=10, tracking=2, vp=vp)
    False

    And a label well inside the plate still fails when the region clip does
    not reach it:

    >>> from shapely.geometry import box as _box
    >>> _label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp,
    ...             region=_box(0, 0, 60, 100))
    False
    """
    width = len(text) * (size * _GLYPH_WIDTH_RATIO + tracking)
    x0 = x - width / 2.0 if anchor == "middle" else x
    x1 = x0 + width
    # Cap height above the baseline, a little descender room below.
    y0, y1 = y - 0.78 * size, y + 0.24 * size
    if region is None:
        return x0 >= 0.0 and x1 <= float(vp["width"]) and y0 >= 0.0 and y1 <= float(vp["height"])
    try:
        return bool(region.contains(box(x0, y0, x1, y1)))
    except Exception:  # a degenerate clip must not cost the plate its labels
        return x0 >= 0.0 and x1 <= float(vp["width"])


def _label_point(vis: Any) -> Any:
    """Return the point to hang a territory's name on: deepest inside its **largest** part.

    ``shapely``'s ``representative_point()`` promises only that the point is
    *inside* the geometry, and on real basemap data it fails a label twice
    over. It may pick any component of a ``MultiPolygon``, and it sits on a
    horizontal line through the centroid, which on a ragged outline can be a
    fraction of a degree from the border. Measured on the vendored Natural
    Earth countries at region boxes this generator actually renders:

    * a Ukraine view puts ``RUSSIA`` on the Crimean peninsula (3.1 deg^2)
      instead of the mainland east of the Donbas (31.4 deg^2), so the name of
      a neighbour lands inside territory the areas-of-control layer has just
      classified -- the plate ends up asserting a sovereignty its own data
      never claimed;
    * a Nordic view puts ``RUSSIA`` on a 0.47 deg^2 speck off northern Norway
      instead of the 100 deg^2 landmass filling the right of the frame, a
      factor of 200;
    * and on that same Ukraine view, even the right landmass leaves the label
      0.36 deg from the frontier, close enough that it collided with the
      ``LUHANSK`` city label and was painted over by it.

    So this takes the largest component (a name belongs on the body of the
    thing it names, not on an offshore fragment of it), then the **pole of
    inaccessibility** within that component -- the interior point furthest
    from any edge, which is the standard placement for an area label and
    what puts ``RUSSIA`` 1.55 deg clear of the border instead of 0.36.
    ``polylabel`` is an approximation refined to ``tolerance``; that is scaled
    to the part's own size here so a large country and a small one are
    approximated equally well, and costs well under a millisecond either way.

    Parameters
    ----------
    vis : shapely geometry
        The territory already clipped to the visible region box.

    Returns
    -------
    shapely.geometry.Point
        A point inside the largest component of ``vis``.

    Examples
    --------
    A mainland with a small offshore island: the label goes on the mainland,
    which is *not* the part ``representative_point()`` happens to choose here.

    >>> from shapely.geometry import MultiPolygon, box
    >>> mainland, island = box(0, 0, 10, 10), box(20, 20, 21, 21)
    >>> pt = _label_point(MultiPolygon([island, mainland]))
    >>> mainland.contains(pt)
    True

    And it sits deep inside rather than merely inside. A territory with a
    notch cut into it -- the shape of a country whose neighbour reaches in --
    strands ``representative_point()`` against the notch, which is where the
    real ``RUSSIA`` label ended up; the pole of inaccessibility is six times
    further from any edge:

    >>> from shapely.geometry import Polygon
    >>> notched = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 6), (8, 5), (0, 4)])
    >>> round(notched.exterior.distance(notched.representative_point()), 3)
    0.372
    >>> round(notched.exterior.distance(_label_point(notched)), 3)
    2.461
    """
    if getattr(vis, "geom_type", "") == "MultiPolygon":
        vis = max(vis.geoms, key=lambda g: g.area)
    try:
        minx, miny, maxx, maxy = vis.bounds
        # A hundredth of the part's own span: fine enough that the point is
        # visually the pole, coarse enough that the search terminates fast.
        tolerance = max(max(maxx - minx, maxy - miny) / 100.0, 1e-9)
        return polylabel(vis, tolerance=tolerance)
    except Exception:
        # polylabel wants a simple, non-degenerate Polygon. Vendored data that
        # is neither should cost the plate a slightly worse label, not a crash.
        return vis.representative_point()


def _polygonal_boundary_source(poly: Any) -> Any | None:
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


def _internal_borders_layer(
    cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any], region_box: Any,
    region: Any | None = None,
) -> str:
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
        except Exception:  # skip a malformed admin-1 geometry rather than fail the plate
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
            pt = _label_point(vis)
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            if _label_fits(
                x, y, name, size=8.0 * ts, tracking=1.6, vp=vp, region=region
            ):
                labels.append(
                    tracked_text(x, y, name, size=8.0 * ts, fill="#a7abaf", tracking=1.6, weight="500")
                )
    return f'<g id="internal-borders">{"".join(lines)}{"".join(labels)}</g>'


def _admin2_borders_layer(
    cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any], region_box: Any,
    region: Any | None = None,
) -> str:
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
        except Exception:  # skip a malformed admin-2 geometry rather than fail the plate
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
            pt = _label_point(vis)
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            if _label_fits(
                x, y, name, size=6.8 * ts, tracking=1.2, vp=vp, region=region
            ):
                labels.append(
                    tracked_text(x, y, name, size=6.8 * ts, fill="#b5b9bc", tracking=1.2, weight="500")
                )
    return f'<g id="admin2-borders">{"".join(lines)}{"".join(labels)}</g>'


#: Stroke weight per Natural Earth scalerank, in ``ts`` units. Rank 1 is a
#: continental trunk, rank 6 a minor tributary.
#:
#: Deliberately *not* called hydraulic width. Hydraulic width means
#: discharge, and the vendored file carries no discharge — only ``name`` and
#: ``scalerank``, which is a cartographic prominence rank. Sizing by it
#: gives the same read at a glance, and claiming it measured water would be
#: a lie a reader could not check.
_RIVER_WIDTHS: dict[int, float] = {1: 3.0, 2: 2.3, 3: 1.8, 4: 1.4, 5: 1.1, 6: 0.85}


def _river_width(rank: int, mode: str, ts: float) -> float:
    """
    Stroke weight for one river reach.

    Parameters
    ----------
    rank : int
        Natural Earth ``scalerank``; 1 is most prominent.
    mode : str
        ``"even"`` for the single weight this always used, ``"ranked"`` to
        taper by prominence.
    ts : float
        The plate's type scale.

    Returns
    -------
    float
        Stroke width in user units.
    """
    if mode != "ranked":
        return 1.3 * ts
    return _RIVER_WIDTHS.get(max(1, min(6, int(rank))), 1.0) * ts


def _rivers_layer(
    cfg: dict[str, Any],
    proj: Transformer,
    vp: dict[str, Any],
    region_box: Any,
    placed: list[tuple[float, float]] | None = None,
) -> str:
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
    # "even" is the default and draws every river at one weight, which is
    # what this has always done. "ranked" tapers them, so a trunk reads
    # thick and a tributary thin — the single change that turns a tangle of
    # blue lines into a drainage network you can read at a glance.
    width_mode = str(rv.get("width", "even")).lower()
    if width_mode not in ("even", "ranked"):
        raise ValueError(f"unknown rivers.width {width_mode!r}; known: even, ranked")
    label_color = rv.get("label_color", "#4f7290")
    max_rank = int(rv.get("label_max_scalerank", 6))
    min_px = float(rv.get("label_min_length_frac", 0.14)) * vp["width"]
    always = {n.lower() for n in rv.get("always_label", [])}
    skip = {n.lower() for n in rv.get("skip", [])}
    m_per_unit = vp["m_per_unit"]
    lines: list[str] = []
    labels: list[str] = []
    # Shared with the lakes layer when build_map passes its list in: the two
    # name the same water from two datasets, and each one dodging only its own
    # labels printed "Dnieper" straight through "Kakhovka Reservoir".
    placed = placed if placed is not None else []
    labeled: set[str] = set()  # one label per named river
    for geom, name, rank in sorted(load_rivers(), key=lambda r: -r[2]):
        try:
            clipped = geom.intersection(region_box)
        except Exception:  # skip a malformed river geometry rather than fail the plate
            continue
        if clipped.is_empty:
            continue
        gp = _project_geom(clipped, proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if not d:
            continue
        lines.append(
            f'<path d="{d}" fill="none" stroke="{line_color}" '
            f'stroke-width="{_river_width(rank, width_mode, ts):{".2f" if width_mode == "ranked" else ".1f"}}" '
            f'stroke-opacity="0.85" '
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

    The line is given by ``front.line`` (a list of ``[lon, lat]`` vertices, north
    to south). It is drawn as a two-part stroke: a soft white casing under a bold
    coloured line, the standard way a data desk makes the front read above the
    pastel control fills without adding a hard black rule. A small callout label
    (``front.label``) is set beside a chosen vertex when given.
    """
    fr = cfg.get("front", {})
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
        # White casing so the front lifts off the pastel zones.
        f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{5.4 * ts:.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round" stroke-linecap="round"/>',
        # The contact line itself: bold, slightly dashed so it reads as a *front*,
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


def _markers_layer(
    items: list[dict[str, Any]],
    proj: Transformer,
    vp: dict[str, Any],
    layer_id: str,
    marker_legend: list[dict[str, Any]] | None = None,
) -> str:
    """Return point markers (forces or events) as drop-shadowed, hoverable dots.

    Each marker carries a ``class="hit"`` and, right after it, a
    :func:`tooltip_bubble` sibling revealed on hover/focus (the
    ``.hit:hover~.tip`` pattern). A marker's own dict rarely names the
    place it sits at (``lon``/``lat``/``color``/``r`` only -- see the
    module's example configs), but its fill ``color`` already keys into
    ``cfg["marker_legend"]`` (a color -> description mapping every config
    already sets, e.g. "Contested flashpoint (approx.)") -- the headline
    reuses that real, existing data plus the marker's coordinates and
    layer (forces/events), rather than inventing a per-marker name.
    """
    legend_by_color = {m.get("color"): m.get("label", "") for m in (marker_legend or [])}
    W, H = vp["width"], vp["height"]
    out: list[str] = []
    for it in items:
        x, y = vp["to_svg"](*proj.transform(it["lon"], it["lat"]))
        color = it.get("color", "#b03a3a")
        r = float(it.get("r", 5))
        out.append(
            f'<circle class="hit" tabindex="0" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{color}" stroke="#fff" stroke-width="1.4" filter="url(#marker-shadow)"/>'
        )
        headline = it.get("label") or legend_by_color.get(color) or layer_id.capitalize()
        out.append(
            tooltip_bubble(
                x,
                y - r - 6,
                [headline, f"{it['lat']:.2f}°, {it['lon']:.2f}° · {layer_id}"],
                anchor="middle",
                canvas_w=W,
                canvas_h=H,
                ink="#1b2733",
                secondary="#5b6169",
                border="#e4e8ec",
            )
        )
    return f'<g id="{layer_id}">{"".join(out)}</g>'


def _catmull_rom(points: list[tuple[float, float]], per_segment: int = 14) -> list[tuple[float, float]]:
    """Return ``points`` densified into a smooth curve through every one of them.

    A hand-typed axis of advance is four or five coordinates, and drawn as
    straight segments it reads as a dogleg -- a claim about where the advance
    turned that the author never made. A Catmull-Rom spline passes exactly
    through the given points (unlike a Bezier, whose controls pull it off
    them) and rounds the corners between, which is the shape every published
    advance arrow has.

    Parameters
    ----------
    points : list of (float, float)
        Two or more control points, tail first.
    per_segment : int, optional
        Samples emitted per input segment. 14 is smooth at plate scale.

    Returns
    -------
    list of (float, float)
        The densified polyline, starting at ``points[0]`` and ending at
        ``points[-1]``.

    Examples
    --------
    >>> pts = _catmull_rom([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)], per_segment=4)
    >>> pts[0], pts[-1]
    ((0.0, 0.0), (20.0, 0.0))

    A straight input stays straight:

    >>> all(abs(y) < 1e-9 for _, y in pts)
    True
    """
    if len(points) < 3:
        return list(points)
    # Duplicate the endpoints so the first and last segments are defined.
    pad = [points[0], *points, points[-1]]
    out: list[tuple[float, float]] = []
    for i in range(len(pad) - 3):
        p0, p1, p2, p3 = pad[i], pad[i + 1], pad[i + 2], pad[i + 3]
        for step in range(per_segment):
            t = step / per_segment
            t2, t3 = t * t, t * t * t
            out.append(
                (
                    0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                           + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                           + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                    0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                           + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                           + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
                )
            )
    out.append(points[-1])
    return out


def _tapered_arrow_path(
    pts: list[tuple[float, float]], *, head_w: float, taper: float, head_len: float
) -> tuple[str, str]:
    """Return ``(shaft_path, head_path)`` for a tapered axis-of-advance arrow.

    An SVG stroke is one width for its whole length, so a shaft that thickens
    towards the point has to be a *filled outline*, not a stroked line: this
    walks the curve, offsets each sample along its own normal by a half-width
    that grows from ``taper * head_w`` at the tail to ``head_w`` at the base of
    the head, and closes the two offset sides into one polygon. The head is a
    separate triangle so it keeps a crisp point no matter how the shaft curves
    into it.

    The growing shaft is not decoration. On a control map it is the one mark
    that carries direction without a caption -- which end is the origin and
    which is the objective -- and it is why every published offensive map uses
    the same form rather than a line with a chevron stuck on the end.

    Parameters
    ----------
    pts : list of (float, float)
        The densified curve in plate coordinates, tail first.
    head_w : float
        Shaft half-width where it meets the head, in user units.
    taper : float
        Tail half-width as a fraction of ``head_w``.
    head_len : float
        Length of the arrowhead triangle, in user units.

    Returns
    -------
    tuple of (str, str)
        SVG ``d`` attributes for the shaft polygon and the head triangle.
        Both are empty strings when ``pts`` is too short to have a direction.

    Examples
    --------
    >>> shaft, head = _tapered_arrow_path(
    ...     [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)], head_w=6, taper=0.3, head_len=18
    ... )
    >>> shaft.startswith("M") and shaft.endswith("Z")
    True
    >>> head.count(",") == 3  # three vertices
    True

    A degenerate input draws nothing rather than raising:

    >>> _tapered_arrow_path([(0.0, 0.0)], head_w=6, taper=0.3, head_len=18)
    ('', '')
    """
    if len(pts) < 2:
        return "", ""
    # Walk back from the tip by head_len to find where the shaft stops and the
    # head begins, so the two never overlap and the point stays sharp.
    tip = pts[-1]
    base_i = len(pts) - 1
    acc = 0.0
    while base_i > 0:
        dx = pts[base_i][0] - pts[base_i - 1][0]
        dy = pts[base_i][1] - pts[base_i - 1][1]
        acc += math.hypot(dx, dy)
        base_i -= 1
        if acc >= head_len:
            break
    shaft_pts = pts[: base_i + 1]
    if len(shaft_pts) < 2:
        shaft_pts = pts[:2]
    base = shaft_pts[-1]

    total = 0.0
    lengths = [0.0]
    for a, b in zip(shaft_pts, shaft_pts[1:], strict=False):
        total += math.hypot(b[0] - a[0], b[1] - a[1])
        lengths.append(total)
    if total <= 0:
        return "", ""

    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []
    for i, (x, y) in enumerate(shaft_pts):
        # Tangent from the neighbouring samples, so the normal is stable at
        # the ends as well as in the middle.
        a = shaft_pts[max(i - 1, 0)]
        b = shaft_pts[min(i + 1, len(shaft_pts) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / norm, tx / norm
        half = head_w * (taper + (1.0 - taper) * (lengths[i] / total))
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))

    outline = left + right[::-1]
    shaft = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in outline) + "Z"

    # Head: an isoceles triangle on the tail->tip direction at the base.
    hx, hy = tip[0] - base[0], tip[1] - base[1]
    hnorm = math.hypot(hx, hy) or 1.0
    ux, uy = hx / hnorm, hy / hnorm
    px, py = -uy, ux
    half_head = head_w * 1.95
    head = (
        f"M{tip[0]:.1f},{tip[1]:.1f}"
        f"L{base[0] + px * half_head:.1f},{base[1] + py * half_head:.1f}"
        f"L{base[0] - px * half_head:.1f},{base[1] - py * half_head:.1f}Z"
    )
    return shaft, head


def _arrows_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return axes of advance: tapered, cased arrows over the control fills.

    The one element every published offensive map has that this generator did
    not. Areas of control say where the line *is*; an arrow says which way it
    is moving, and without it a plate can only ever describe a frozen moment.

    Each entry in ``cfg["arrows"]`` takes ``line`` (a list of ``[lon, lat]``,
    tail first), and optionally ``color``, ``width`` (shaft half-width at the
    head, in ``ts`` units), ``label``, ``legend_label``, ``opacity``, and
    ``style``: ``"solid"`` for an assessed advance, ``"dashed"`` for a
    reported or projected one -- a distinction worth drawing, since the two
    are not the same claim and a reader of a plate like this will act on it.

    Every arrow is drawn twice: a white casing underneath, then the colour on
    top. That is the same paint-order halo the labels use, and it is what lets
    a dark red arrow stay legible crossing a dark red control zone.
    """
    arrows = cfg.get("arrows", [])
    if not arrows:
        return '<g id="arrows"></g>'
    ts = vp["ts"]
    out: list[str] = []
    for arrow in arrows:
        line = arrow.get("line") or []
        if len(line) < 2:
            continue
        plate = [vp["to_svg"](*proj.transform(float(lon), float(lat))) for lon, lat in line]
        curve = _catmull_rom(plate)
        head_w = float(arrow.get("width", 6.0)) * ts
        shaft, head = _tapered_arrow_path(
            curve,
            head_w=head_w,
            taper=float(arrow.get("taper", 0.30)),
            head_len=head_w * 3.1,
        )
        if not shaft:
            continue
        color = arrow.get("color", "#b03a3a")
        opacity = float(arrow.get("opacity", 0.92))
        dashed = str(arrow.get("style", "solid")).lower() == "dashed"
        casing = 2.6 * ts
        # Near-opaque, not a wash: a dashed arrow is mostly its own outline, and
        # over a control fill of a similar hue a translucent casing left the
        # outline invisible -- the reported SPLM-N axis vanished into the green
        # zone it crossed. The casing has to make its own ground.
        for d in (shaft, head):
            out.append(
                f'<path d="{d}" fill="#ffffff" fill-opacity="{0.94 if dashed else 0.85:.2f}" '
                f'stroke="#ffffff" stroke-width="{casing:.1f}" stroke-linejoin="round"/>'
            )
        if dashed:
            # A reported axis reads as an outline: the shape is the same claim,
            # drawn as one the map is not asserting.
            for d in (shaft, head):
                out.append(
                    f'<path d="{d}" fill="{color}" fill-opacity="{opacity * 0.22:.2f}" '
                    f'stroke="{color}" stroke-width="{2.2 * ts:.1f}" '
                    f'stroke-dasharray="{5.5 * ts:.1f} {3.5 * ts:.1f}" stroke-linejoin="round"/>'
                )
        else:
            for d in (shaft, head):
                out.append(f'<path d="{d}" fill="{color}" fill-opacity="{opacity:.2f}"/>')
        label = arrow.get("label")
        if label:
            # Offset along the arrow's own normal at its midpoint, not sat on
            # the tail: the tail is the origin town, which already carries a
            # name ("SAF ADVANCE" landed on top of "EL OBEID"). Side is the
            # caller's, since which flank is clear is a question about the map.
            mid = curve[len(curve) // 2]
            ahead = curve[min(len(curve) // 2 + 1, len(curve) - 1)]
            tx, ty = ahead[0] - mid[0], ahead[1] - mid[1]
            tnorm = math.hypot(tx, ty) or 1.0
            side = -1.0 if str(arrow.get("label_side", "left")).lower() == "left" else 1.0
            offset = (head_w * 2.0 + 7 * ts) * side
            lx = mid[0] + (-ty / tnorm) * offset
            ly = mid[1] + (tx / tnorm) * offset
            # Anchored away from the shaft rather than centred on the offset
            # point: a centred label is only half-cleared, and a name half on
            # top of the arrow it names is worse than no name. Which way it
            # runs follows the offset's own direction, so it is always the far
            # side of the arrow that the text grows into.
            out.append(
                tracked_text(
                    lx,
                    ly,
                    str(label),
                    size=9.0 * ts,
                    fill=color,
                    tracking=1.4,
                    weight="700",
                    anchor="end" if (-ty / tnorm) * offset < 0 else "start",
                )
            )
    return f'<g id="arrows">{"".join(out)}</g>'


def _cities_layer(
    cfg: dict[str, Any],
    proj: Transformer,
    vp: dict[str, Any],
    bbox: tuple[float, float, float, float],
    region: Any | None = None,
) -> str:
    """
    Return automatic populated places for the region in view.

    A plate carrying terrain, borders and control zones and no cities leaves a
    reader with nowhere to stand: they can see which valley is contested and
    not which town is in it. The `labels` layer above places names by hand,
    which is right for the handful a plate argues about — this draws the rest
    from the vendored list, selected by Natural Earth's cartographic
    prominence, so the map is populated by default and the hand-placed names
    stay for what the author actually wants to say.

    Set ``cities.show: false`` to suppress it, or ``cities.max_rank`` /
    ``cities.limit`` to widen or narrow the selection.
    """
    settings = cfg.get("cities", {})
    if settings.get("show", True) is False:
        return '<g id="cities"></g>'

    west, south, east, north = bbox
    ts = vp["ts"]
    size = float(settings.get("size", 11)) * ts

    def to_svg(lon: float, lat: float) -> tuple[float, float]:
        return vp["to_svg"](*proj.transform(lon, lat))

    # A place the author named by hand wins outright: this layer must not draw
    # it twice, at two positions, in two styles. Two separate tests, because
    # either one alone leaks:
    #
    #  * by name, since the hand label and the vendored list usually agree --
    #    but the key read here was ``name`` while every config in this repo
    #    (and every example in the module docstring) writes ``text``, so the
    #    set was a set of empty strings and nothing was ever suppressed;
    #  * by position, since where they disagree they disagree on the *name*,
    #    not the place: Natural Earth calls El Obeid "Al-Ubayyid" and Khartoum's
    #    conurbation carries a separate "Omdurman" 3 km away. A name test alone
    #    printed both, overlapping, in two different faces.
    hand_named = {
        str(place.get("text", place.get("name", ""))).strip().lower()
        for place in cfg.get("labels", {}).get("places", [])
    }
    hand_named.discard("")
    hand_points = [
        to_svg(float(place["lon"]), float(place["lat"]))
        for place in cfg.get("labels", {}).get("places", [])
        if "lon" in place and "lat" in place
    ]
    # Generous enough to catch a twin city the hand label already stands for,
    # tight enough to keep two genuinely distinct towns that happen to be close.
    near_px = float(settings.get("hand_placed_clearance", 26)) * ts

    def is_duplicate(city: Any) -> bool:
        if city.name.lower() in hand_named:
            return True
        cx, cy = to_svg(city.lon, city.lat)
        return any(abs(cx - hx) < near_px and abs(cy - hy) < near_px for hx, hy in hand_points)

    chosen = [
        city
        for city in cities_in_view(
            west,
            south,
            east,
            north,
            limit=int(settings.get("limit", 28)),
            rank_ceiling=settings.get("max_rank"),
        )
        if not is_duplicate(city)
    ]

    out: list[str] = []
    # Without the plate's own bounds a label near the edge runs off it --
    # "Istanbul" came out as "Ista". A name half outside the frame is worse
    # than no name: the reader sees a dot with a truncated word beside it.
    plate = (0.0, 0.0, float(vp["width"]), float(vp["height"]))
    for city, dot_x, dot_y, label_x, label_y in place_labels(
        chosen, to_svg, font_size=size, dot_radius=2.0 * ts, bounds_px=plate
    ):
        # The plate rectangle is the outer bound; the region clip is the real
        # one, and it is narrower wherever the projection bends the frame in.
        # "Asmara" survived the rectangle and came out of the clip as "Asm".
        if not _label_fits(
            label_x, label_y, city.name, size=size, vp=vp, region=region, anchor="start"
        ):
            continue
        out.append(
            f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="{2.0 * ts:.1f}" '
            f'fill="#2B2B2E" fill-opacity="0.8"/>'
        )
        out.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" font-size="{size:.1f}" '
            f'fill="#2B2B2E" paint-order="stroke" stroke="#FFFFFF" '
            f'stroke-width="{2.4 * ts:.1f}" stroke-linejoin="round">'
            f"{_esc(city.name)}</text>"
        )
    return '<g id="cities">' + "".join(out) + "</g>"



def _labels_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return populated-place dots with offset names, plus a tracked water label.

    Each place is a small dot at its true location and a letter-spaced name set
    *beside* the dot (never on top of it). ``place["anchor"]`` steers the name,
    one of ``"start"`` (right, default), ``"end"`` (left), ``"above"``,
    or ``"below"``, so labels can dodge the coast, the frame, and one another.
    ``dot: false``
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
        # marker (e.g. a red flashpoint): then dot:false and `clear` is set to
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
        else:  # "start": name to the right of the marker
            lx, ly, ta = x + clear + gap, y + 0.32 * size, "start"
        weight = "700" if place.get("capital") else "600"
        out.append(
            tracked_text(
                lx,
                ly,
                place["text"],
                size=size,
                fill="#2f363d",
                tracking=tracking,
                weight=weight,
                anchor=ta,
            )
        )
    # Water labels: a single ``water`` (back-compat) and/or a list ``waters``,
    # seas and gulfs, set in the letter-spaced blue-grey water convention.
    waters = list(labels.get("waters", []))
    if labels.get("water"):
        waters.append(labels["water"])
    for w in waters:
        x, y = vp["to_svg"](*proj.transform(w["lon"], w["lat"]))
        angle = w.get("rotate", 0)
        txt = tracked_text(
            x,
            y,
            w["text"],
            size=w.get("size", 19) * ts,
            fill="#5c7c90",
            tracking=w.get("tracking", 6),
            weight="400",
            upper=w.get("upper", True),
        )
        if angle:
            out.append(f'<g transform="rotate({angle} {x:.1f} {y:.1f})">{txt}</g>')
        else:
            out.append(txt)
    return f'<g id="annotation-labels">{"".join(out)}</g>'


def _caption_height(cfg: dict[str, Any], ts: float) -> float:
    """
    Vertical space the caption occupies, or 0 when it is off.

    The furniture needs this before drawing: the scale bar sits at the same
    bottom-left corner, and the two landed on top of each other the first
    time — legible text over a legible bar, both unreadable.
    """
    if str(cfg.get("caption", "none")).lower() != "full":
        return 0.0
    lines = [x for x in (cfg.get("method"), cfg.get("source"), cfg.get("as_of")) if x]
    return len(lines) * 11.5 * ts + 17 * ts


def _caption_block(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """
    A provenance footer inside the plate, for a figure that travels alone.

    A map gets screenshotted, pasted into a deck, forwarded. By the time
    somebody asks "what is this, and when is it from", the page that carried
    the method note is gone. mapped.earth answers that by putting the method
    on the plate itself, in small monospace under the map, and the result
    stays honest wherever it ends up.

    Off by default: an existing plate that suddenly grew a footer would have
    its layout changed under it. ``caption: full`` opts in.

    Parameters
    ----------
    cfg : dict
        The map config. Reads ``caption`` (``"none"`` or ``"full"``),
        ``source``, ``method``, ``as_of``.
    vp : dict
        Viewport, for width and type scale.

    Returns
    -------
    str
        An SVG group, empty when the caption is off.
    """
    mode = str(cfg.get("caption", "none")).lower()
    if mode == "none":
        # Nothing at all, not an empty group: a plate that never asked for
        # a caption has to come out of this byte-for-byte as it did before,
        # and twenty bytes of empty <g> is still a difference.
        return ""
    if mode != "full":
        raise ValueError(f"unknown caption {mode!r}; known: none, full")

    palette = _pal(cfg)
    ts, W, H = vp["ts"], vp["width"], vp["height"]
    lines = [x for x in (cfg.get("method"), cfg.get("source"), cfg.get("as_of")) if x]
    if not lines:
        # Refusing beats printing an empty rule: a caption that says nothing
        # is worse than no caption, because it looks like provenance.
        raise ValueError(
            'caption: full needs at least one of "method", "source" or "as_of"'
        )

    size = 8.2 * ts
    leading = 11.5 * ts
    top = H - (len(lines) * leading) - 10 * ts
    out = [
        '<g id="caption">',
        f'<line x1="{26 * ts:.1f}" y1="{top - 7 * ts:.1f}" x2="{W - 26 * ts:.1f}" '
        f'y2="{top - 7 * ts:.1f}" stroke="{palette["panel_edge"]}" stroke-width="1"/>',
    ]
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{26 * ts:.1f}" y="{top + i * leading:.1f}" '
            f'font-family="{_MONO_FONT}" font-size="{size:.1f}" '
            f'fill="{palette["chrome_faint"]}" letter-spacing="0.4">{_esc(line)}</text>'
        )
    out.append("</g>")
    return "".join(out)


def _furniture_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the title block, north arrow and dual-unit scale bar."""
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    # North arrow top-right, clear of the title block top-left. When the
    # legend card floats top-right too (``legend_position``), step left of
    # its fixed footprint (262 panel + 22 margin, in ts units) so the
    # arrow never sits on the card.
    arrow_x = W - 30 * ts
    legend_pos = str(cfg.get("legend_position", "bottom-right"))
    has_legend = bool(cfg.get("areas_of_control", {}).get("palette"))
    if legend_pos == "top-right" and has_legend:
        arrow_x = W - (262 + 22 + 30) * ts
    out: list[str] = [north_arrow(arrow_x, 34 * ts, ts)]
    title = cfg.get("title")
    subtitle = cfg.get("subtitle")
    if title:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{22 * ts:.0f}" font-weight="700" fill="{_pal(cfg)["chrome_ink"]}">{_esc(title)}</text>'
        )
    if subtitle:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts + 20 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{12.5 * ts:.0f}" fill="{_pal(cfg)["chrome_sub"]}">{_esc(subtitle)}</text>'
        )
    # Same rule as the north arrow above, for the other corner the legend can
    # take: the scale bar's home is bottom-left, so a bottom-left card lands
    # straight on it (found on the eastern-DRC plate, where the card was moved
    # there to clear the caption and buried the bar instead). The bar is about
    # 150ts wide, so stepping to the opposite corner is enough.
    scale_x = 26 * ts
    if legend_pos == "bottom-left" and has_legend:
        scale_x = W - 176 * ts
    out.append(
        scale_bar(scale_x, H - 44 * ts - _caption_height(cfg, ts), vp, _pal(cfg)["chrome_ink"])
    )
    return f'<g id="annotation-furniture">{"".join(out)}</g>'


def _attribution_layer(
    cfg: dict[str, Any], vp: dict[str, Any], bbox: Iterable[float] | None
) -> str:
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
        f'fill="{_pal(cfg)["chrome_sub"]}">{_esc(text)}</text></g>'
    )


def _pal(cfg: dict[str, Any]) -> dict[str, str]:
    """The resolved plate palette, or the day plate for a caller that never set one."""
    return cfg.get("_plate", _PLATES["day"])


def _legend_panel_dims(cfg: dict[str, Any], ts: float) -> tuple[float, float, float]:
    """Return ``(panel_w, panel_h, corner_margin)`` for the legend card.

    Factored out of :func:`_legend_layer` so :func:`build_map` can also size
    the extra canvas column an ``"outside"`` legend needs, without
    duplicating the row-counting logic (and risking the two drifting apart).
    """
    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if not palette:
        return 0.0, 0.0, 22 * ts
    rows = palette.items()
    markers = cfg.get("marker_legend", [])
    front = cfg.get("front", {})
    show_front = bool(front.get("line") and front.get("legend", True))
    footer = cfg.get("legend_footer")
    pad = 15 * ts
    row_h = 25 * ts
    panel_w = 262 * ts
    # Count only rows actually drawn below: the marker section's hairline
    # divider tucks between rows and needs no row of its own (a former +1
    # here left a blank row's worth of dead space above the footer).
    extra = len(markers) + (1 if show_front else 0)
    n_rows = len(list(rows)) + extra
    foot_h = 30 * ts if footer else 0
    panel_h = pad * 2 + 24 * ts + row_h * n_rows + foot_h
    corner_margin = 22 * ts
    return panel_w, panel_h, corner_margin


def _legend_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the legend card: a swatch per class, marker key, source line.

    Swatches are rounded squares (a filled-territory cue, unlike a point dot), a
    contested class also carries the diagonal hatch so the legend mirrors the map
    exactly, and an optional ``front.label`` swatch shows the contact-line style.
    A footer sets the as-of / provenance line so the plate is self-describing.

    ``cfg["legend_position"]`` (``"bottom-right"`` by default, matching every
    plate built before this option existed) picks where the card goes --
    ``"bottom-left"``, ``"top-left"`` and ``"top-right"`` float it over a
    corner of the map itself, same as before. The default corner is not
    always the right one: on a real analysis map a labelled city or a
    stretch of occupied territory can sit exactly where a fixed
    bottom-right card would land (found by rendering the bundled Ukraine
    example: Mariupol, a real city this product exists to let an analyst
    locate, was fully hidden behind the legend).

    ``"right"`` avoids that class of collision entirely: it moves the card
    off the map altogether, into a dedicated column :func:`build_map` adds
    to the right of the plate (see its ``legend_col_w`` handling), so the
    legend can never cover map content no matter what the underlying data
    looks like.
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
    front = cfg.get("front", {})
    show_front = bool(front.get("line") and front.get("legend", True))
    footer = cfg.get("legend_footer")
    pad = 15 * ts
    row_h = 25 * ts
    header_fs = 12.5 * ts
    row_fs = 12.5 * ts
    sw = 15 * ts  # swatch side
    panel_w, panel_h, corner_margin = _legend_panel_dims(cfg, ts)
    position = str(cfg.get("legend_position", "bottom-right"))
    if position == "right":
        px = W + corner_margin
        py = corner_margin
    else:
        px = (
            corner_margin
            if position in ("bottom-left", "top-left")
            else W - panel_w - corner_margin
        )
        # A bottom-corner card has to clear the provenance caption, which the
        # scale bar already accounts for and the legend did not: on the eastern
        # DRC plate the card sat straight on top of all three caption lines.
        py = (
            corner_margin
            if position in ("top-left", "top-right")
            else H - panel_h - corner_margin - _caption_height(cfg, ts)
        )
    tx = px + pad + sw + 10 * ts  # label x
    parts: list[str] = [
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="{_pal(cfg)["panel"]}" fill-opacity="0.96" '
        f'filter="url(#panel-shadow)"/>',
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="none" stroke="{_pal(cfg)["panel_edge"]}" stroke-width="1"/>',
        f'<text x="{px + pad:.1f}" y="{py + pad + 10 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
        f'font-size="{header_fs:.1f}" font-weight="700" fill="{_pal(cfg)["chrome_ink"]}" letter-spacing="1.2">'
        f"AREAS OF CONTROL</text>",
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
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="{_pal(cfg)["legend_ink"]}">{_esc(name)}</text>'
        )
    idx = len(rows)
    # Front-line key row.
    if show_front:
        ry = py + pad + 26 * ts + idx * row_h
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{ry:.1f}" x2="{px + pad + sw:.1f}" y2="{ry:.1f}" '
            f'stroke="{front.get("color", "#3a4149")}" stroke-width="{2.4 * ts:.1f}" '
            f'stroke-dasharray="{7 * ts:.1f} {3.5 * ts:.1f}" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{row_fs:.1f}" fill="{_pal(cfg)["legend_ink"]}">{_esc(front.get("legend_label", "Approx. front line"))}</text>'
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
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="{_pal(cfg)["legend_ink"]}">'
            f"{_esc(mk.get('label', ''))}</text>"
        )
    if footer:
        fy = py + panel_h - 11 * ts
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{fy - 13 * ts:.1f}" x2="{px + panel_w - pad:.1f}" '
            f'y2="{fy - 13 * ts:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px + pad:.1f}" y="{fy:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{9 * ts:.1f}" fill="{_pal(cfg)["chrome_faint"]}">{_esc(footer)}</text>'
        )
    return f'<g id="legend">{"".join(parts)}</g>'


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


#: Every key ``build_map`` reads. A situation plate is configured by a YAML
#: file with two dozen optional keys, hand-edited, and an unrecognised key is
#: simply never read -- so a one-letter slip silently drops a whole layer and
#: the plate still looks like a finished intelligence product. That is the
#: worst possible response to a typo, and it is why this list exists.
CONFIG_KEYS: frozenset[str] = frozenset({
    "areas_of_control", "arrows", "as_of", "attribution", "basemap", "canvas_width",
    "lakes",
    "caption", "events", "forces", "frame", "front", "frontiers",
    "infrastructure", "internal_borders", "labels", "legend_footer",
    "legend_position", "marker_legend", "method", "padding", "projection",
    "cities", "region", "rivers", "source", "subtitle", "title",
})

#: Keys the loaders set themselves; a caller never writes these.
_INTERNAL_KEYS: frozenset[str] = frozenset({"_config_dir", "_plate"})


def validate_config(cfg: dict[str, Any]) -> None:
    """
    Refuse a config with keys this generator does not read.

    Raises
    ------
    ValueError
        If a required key is missing, or a key is not one this generator
        reads. Unknown keys name their closest known neighbour, because the
        realistic cause is a typo and the realistic fix is one character.
    """
    if "region" not in cfg:
        raise ValueError(
            "situation map config needs a 'region': the area the plate covers, "
            "which is what the projection auto-centres on. "
            f"Got keys: {sorted(k for k in cfg if not k.startswith('_')) or 'none'}"
        )

    unknown = sorted(set(cfg) - CONFIG_KEYS - _INTERNAL_KEYS)
    if unknown:
        hints = []
        for key in unknown:
            near = get_close_matches(key, sorted(CONFIG_KEYS), n=1, cutoff=0.7)
            hints.append(f"{key!r}" + (f" (did you mean {near[0]!r}?)" if near else ""))
        raise ValueError(
            "situation map config has key(s) this generator never reads, so "
            "whatever they configure would be silently dropped: "
            + ", ".join(hints)
            + f". Known keys: {', '.join(sorted(CONFIG_KEYS))}"
        )


# A neutral, self-contained demo config so the figure registry can render this
# generator like every other one. It shows Western Europe as a clean reference
# situation map -- coastline, international frontiers, country labels, sea
# bathymetry, dual-unit scale bar, north arrow -- straight from the vendored
# Natural Earth basemap, with no thematic overlay invented. Pass a real
# ``config`` dict (or use the ``--config`` CLI) for an actual analysis map.
_DEMO_CONFIG: dict[str, Any] = {
    "title": "Situation map: Western Europe (demo)",
    "region": {"bbox": [-11.0, 35.0, 30.0, 60.0]},
    "canvas_width": 1000,
    "projection": "auto",
}

#: Row-record demo data, the contract's ``list[dict[str, Any]]`` shape.
#: This generator is config-driven (a whole layered basemap, not a table
#: of rows, see :func:`make_situation_map`), so ``data`` is accepted for
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
    data: Any | None = None,
    *,
    out: Path | str | None = None,
    title: str = "",
    config: dict[str, Any] | None = None,
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
    # `build_map` resolves any relative feature files against this (see
    # `_areas_of_control_layer`/`_infrastructure_layer`'s own
    # `cfg.get("_config_dir", ".")`). A `config` dict passed straight to this
    # Python entry point has no source file to anchor to, so "." (the
    # process's current working directory) is the only sensible default --
    # this used to hardcode `Path(__file__).parent.parent / "assets"`, the
    # source tree's `assets/` directory, which does not exist at all under an
    # installed wheel (that data ships as the sibling package
    # `sprezzature_maps_geo/`) and was never the right anchor for a
    # caller-supplied dict regardless.
    cfg.setdefault("_config_dir", ".")
    if title:
        cfg["title"] = title
    validate_config(cfg)
    svg = build_map(cfg)
    dest = Path(out) if out else svg_example_path(__file__, "situation_map")
    return write_svg(dest, svg)


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the generator."""
    p = argparse.ArgumentParser(description="Generate a layered situation map for any region.")
    p.add_argument("--config", required=True, help="YAML config describing the map.")
    p.add_argument("--out", required=True, help="Output SVG path.")
    p.add_argument(
        "--render",
        action="store_true",
        help="Also rasterise to PNG next to --out via render_diagram.py.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: read config, build the SVG, optionally rasterise."""
    args = build_parser().parse_args(argv)
    cfg = yaml.safe_load(Path(args.config).read_text())
    cfg["_config_dir"] = str(Path(args.config).resolve().parent)
    svg = build_map(cfg)
    out = Path(args.out)
    out.write_text(svg)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    if args.render:
        # Was: shell out to render_diagram.py, a script that lives in
        # sprezzature-figures and has never existed in this repository. With
        # ``check=False`` the failure was swallowed and the line below printed
        # "rendered <path>" for a PNG that was never written — the command
        # reported success for work it had not done. This repo owns a
        # rasteriser (``_render._svg_to_png_bytes``, resvg via Rust); calling
        # it directly removes the cross-repo dependency and the false report.
        from _render import _svg_to_png_bytes

        png = out.with_suffix(".png")
        try:
            png.write_bytes(_svg_to_png_bytes(svg))
        except Exception as exc:  # a rasteriser fault must not look like a success
            print(f"could not rasterise {png}: {exc}", file=sys.stderr)
            return 1
        print(f"rendered {png}  ({png.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
