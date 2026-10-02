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

Every configuration key
-----------------------
``validate_config`` refuses any key not on this list, suggesting the one
you probably meant -- which only helps if the list is written down
somewhere. It was not: ``EXAMPLES.md`` sends a reader here "for the full
list of fields it accepts" and this docstring named ten of thirty-one.
``tests/test_config_schema_is_documented.py`` now fails if a key is added
without a line here.

Required
~~~~~~~~
``region``
    ``{bbox: [west, south, east, north]}`` in degrees. The plate's extent,
    and what the projection auto-centres on. Validated: see
    :func:`validate_region`.

The plate itself
~~~~~~~~~~~~~~~~
``title``, ``subtitle``
    Headline and strap, drawn top-left.
``canvas_width``
    Plate width in SVG units; everything else scales from it. Default 1000.
``padding``
    Inset between the projected region and the plate edge. Default 26.
``projection``
    ``"auto"`` (a Lambert conformal conic centred on the region) or an
    EPSG code.
``frame``
    ``{page_color, radius}`` for the card the plate sits on.
``simplify``
    Vertex-thinning tolerance in output units, applied after projection.
    ``0`` keeps every vertex. See ``_simplify``.
``interactivity``
    ``"self-contained"`` (default) gives the plate its own layer switches,
    confidence filter and clickable legend, carried inside the file with no
    page script; ``"external"`` leaves them to a page-level script;
    ``"static"`` ships none. The controls are hidden until the script runs,
    so an ``<img>`` embed or a rasteriser always sees the plain map.

Basemap layers
~~~~~~~~~~~~~~
``basemap``
    ``{relief, sea_color, land_color, coast_color, bathymetry}`` -- the
    physical ground. ``relief: false`` halves render time.
``frontiers``
    International borders: ``{show, color, label_neighbours, focus,
    label_min_area_frac}``.
``internal_borders``
    First-level administrative boundaries where a vendored source covers
    the region: ``{show, color}``.
``rivers``
    ``{show, width, skip, label_min_length_frac, label_color}``.
``lakes``
    ``{show, color, skip, former, historic, always_label,
    label_min_area_frac, depth_rings}``. ``depth_rings`` is how many shelf
    rings step inward from a lake's shore; ``0`` draws none. ``former`` draws water that has gone;
    ``historic`` draws a lake whose vendored polygon is its historic
    maximum.
``cities``
    Automatic populated places: ``{show, size, limit, max_rank,
    hand_placed_clearance}``.
``infrastructure``
    Roads and airports from a caller-supplied source.
``inset``
    Locator inset: ``{show, position, bbox, width, zoom}``.

The assessment
~~~~~~~~~~~~~~
``areas_of_control``
    The thematic layer: ``{source, category_field, confidence_field,
    palette, contested, fill_opacity, casing_width, blend, over_water}``.
    ``over_water: true`` keeps a zone's own shape instead of clipping it to
    land, for a claim that really is maritime.
``front``
    The contact line: ``{line, color, label, legend, legend_label}``.
``arrows``
    Axes of advance: a list of ``{line, color, label, style}``.
``forces``, ``events``
    Point markers; each takes ``lon``, ``lat``, ``color``, ``r``,
    ``label``, ``precision``, ``radius_km``, ``date``, ``time_precision``
    and ``source``.
``annotations``
    Editorial notes: a list of ``{at, text, place, color, circle_km,
    wrap}``.
``labels``
    Hand-placed names: ``{places, waters, territories}``.

Chrome and provenance
~~~~~~~~~~~~~~~~~~~~~
``legend_position``
    ``"bottom-right"`` (default), the other three corners, ``"right"``
    (its own column) , ``"below"`` (a band under the map) or ``"auto"``.
``legend_footer``
    A line under the legend's rows.
``marker_legend``
    A list of ``{color, label, precision}`` keying the point markers.
``caption``
    ``"none"`` (default) or ``"full"``, a provenance block on the plate.
``method``, ``source``, ``as_of``
    The three lines a ``caption: full`` prints.
``attribution``
    Extra credit lines, appended to any the generator adds itself.


Usage
-----
    python make_situation_map.py --config demo.yaml --out demo.svg --render

Style rules for this file: NumPy-style docstrings, full type annotations,
and plain dict-shaped records in preference to purpose-built classes.
"""

from __future__ import annotations

import argparse
import contextlib
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
from _plate_controls import controls_markup, controls_script, tag_layer
from _relief import rgba_to_data_uri, sample_terrain_shade, terrain_shade_for_bbox
from _render import svg_example_path, write_svg
from _simplify import DEFAULT_TOLERANCE, simplify_ring, simplify_screen
from _topojson import decode_arcs, stitch_ring

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
    wrap_no_orphan = sys.modules["_svg_figures_tooltip"].wrap_no_orphan
else:
    _tooltip_spec = importlib.util.spec_from_file_location(
        "_svg_figures_tooltip", figures_scripts_dir() / "_svg.py"
    )
    _svg_figures = importlib.util.module_from_spec(_tooltip_spec)
    sys.modules["_svg_figures_tooltip"] = _svg_figures
    _tooltip_spec.loader.exec_module(_svg_figures)
    tooltip_bubble = _svg_figures.tooltip_bubble
    # Same module, same reason: an annotation is wrapped prose, and wrapping
    # it without leaving a one-word last line is the shared helper's job.
    wrap_no_orphan = _svg_figures.wrap_no_orphan

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

#: What an alpha value is allowed to mean on this plate.
#:
#: Every opacity here used to be its own number, tuned alone in whichever
#: pass added the layer: 0.85 and 0.9 and 0.75 and 0.7 and 0.4 and 0.3,
#: thirty-odd literals with no model behind them. That is not a style, it is
#: an accumulation, and it shows: two things that mean the same to a reader
#: were drawn at different strengths because they were written in different
#: months.
#:
#: So opacity is treated as a statement about *what kind of thing the reader
#: is looking at*, and there are only six kinds:
#:
#: ``ground``
#:     The substrate -- land, sea, the body of a lake. **Opaque**, because
#:     there is nothing beneath it that the reader is entitled to see. A
#:     translucent ground is how a basemap drifts towards the colour of
#:     whatever happens to be under it.
#: ``modulation``
#:     Terrain shading. The one layer that *blends* rather than covers: it
#:     takes the ground's own colour and changes its luminance, never its
#:     hue. Per plate, because the mode differs (multiply on paper, screen
#:     on a night plate).
#: ``depth_cue``
#:     A hint drawn *inside* water -- bathymetry rings, lake shelf rings.
#:     Faint on purpose: it answers a question the reader did not ask yet.
#: ``claim``
#:     Areas of control. **The only fill that is translucent, and it is
#:     translucent for a reason**: the claim is *about* ground the reader
#:     must still be able to see. Everything the confidence ladder does is a
#:     modification of this one value.
#: ``fact_line``
#:     Coastlines, frontiers, administrative borders, rivers. Near-opaque. A
#:     boundary a reader can barely see is a boundary they will doubt, and
#:     these are the parts of the plate nobody is asked to take on trust.
#: ``mark``
#:     The assessment's own marks and all text -- front line, axes of
#:     advance, markers, labels. **Never faded.** Legibility is not a place
#:     to be tasteful.
COMPOSITING: dict[str, float] = {
    "ground": 1.00,
    "depth_cue": 0.30,
    "claim": 0.78,
    "fact_line": 0.85,
    "mark": 1.00,
}

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
        "bathy_opacity": COMPOSITING["depth_cue"],
        "halo": "#ffffff",
        "blend": "multiply",
        "sea": "#a9bccb",
        "land": "#faf6e4",
        "coast": "#7f97a8",
        # Blend strength, not fill opacity. 0.45 was the right number for the
        # old arrangement, where it set how much of a *translucent land fill*
        # the shading showed through; as a multiply strength the same value
        # left the drainage network barely legible. Swept 0.45/0.65/0.85/1.0
        # against the Albertine Rift, the most dissected terrain the bundled
        # examples cover, and then again with the control fills in place --
        # which matters, because the zones blend too and three multiplies
        # stack. Terrain contrast still climbs at 0.85, but the pink starts
        # going muddy in the valleys; 0.72 is where the drainage network is
        # plainly legible *and* the class colour is still unmistakably
        # itself. A plate about who holds the ground does not get to lose
        # the ground's colour to the ground's shape.
        "relief_opacity": 0.72,
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
        "bathy_opacity": COMPOSITING["depth_cue"],
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
    arcs = decode_arcs(topo)

    def stitch(arc_indices: Iterable[int]) -> list[tuple[float, float]]:
        return stitch_ring(arc_indices, arcs)

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


def make_viewport(
    proj: Transformer,
    bbox: list[float],
    width: float,
    pad: float,
    simplify: float = DEFAULT_TOLERANCE,
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
        # Vertex-thinning tolerance in SVG units, carried on the viewport so
        # every layer that draws a path picks it up without a new argument.
        "simplify": simplify,
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


def _projected_ring_to_path(
    coords: Iterable[tuple[float, float]], vp: dict[str, Any], close: bool = True
) -> str:
    """Project one run of planar metres into an SVG path, minus what cannot be seen.

    The vertices are thinned *after* the viewport transform, so the tolerance
    is in the units actually drawn (see ``_simplify``). ``close`` tells the
    thinner whether this run is a ring, which must keep at least three
    points, or an open line, which may legitimately collapse to two.
    """
    to_svg = vp["to_svg"]
    pts = [to_svg(x, y) for x, y in coords]
    thin = simplify_ring if close else simplify_screen
    pts = thin(pts, vp.get("simplify", DEFAULT_TOLERANCE))
    return "".join(
        f"{'M' if i == 0 else 'L'}{sx:.2f},{sy:.2f}" for i, (sx, sy) in enumerate(pts)
    )


def projected_geom_to_path(geom: Any, vp: dict[str, Any], close: bool = True) -> str:
    """Convert a geometry *already in projected metres* into an SVG path string.

    Handles ``GeometryCollection`` by recursing into its parts. That is not
    a nicety: clipping a hand-drawn control zone against a coastline returns
    one whenever the zone's edge grazes the shore -- a polygon plus a stray
    line fragment where the two touch -- and this function used to answer an
    unrecognised type with ``""``, which every caller reads as "nothing to
    draw". Two whole factions vanished from shipped plates that way, the
    Syrian government and the Libyan NTC, while their legend swatches stayed.
    A silent empty string is the worst possible answer to a geometry you do
    not recognise.
    """
    parts: list[str] = []
    if geom.geom_type == "GeometryCollection":
        return " ".join(
            filter(None, (projected_geom_to_path(part, vp, close) for part in geom.geoms))
        )
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            if poly.is_empty:
                continue
            parts.append(_projected_ring_to_path(poly.exterior.coords, vp, True) + "Z")
            for hole in poly.interiors:
                parts.append(_projected_ring_to_path(hole.coords, vp, True) + "Z")
    elif geom.geom_type in ("LineString", "MultiLineString"):
        lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for line in lines:
            if line.is_empty:
                continue
            parts.append(
                _projected_ring_to_path(line.coords, vp, close) + ("Z" if close else "")
            )
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


#: The four fill textures, named and shaped after mapshaper's ``-style
#: fill-pattern=`` vocabulary ("there are four pattern types: hatches, dots,
#: squares and dashes"). One texture is not enough once a zone has to say
#: *how well known* it is as well as *whose* it is, and inventing a fifth
#: ad-hoc hatch every time that need appears is how a legend stops being
#: learnable. These four are distinguishable at plate scale, survive
#: greyscale, and carry no hue of their own -- they take the actor's.
_PATTERN_KINDS: frozenset[str] = frozenset({"hatches", "dots", "squares", "dashes"})


def _pattern_id(kind: str, color: str) -> str:
    """Return a stable, legal SVG id for the ``kind``/``color`` texture.

    The sanitising rule is svgis's: drop everything that is not a letter,
    digit or dash, and make sure the result cannot begin with a digit. A
    colour reaches here as ``#9cc3d5`` or as a CSS name, and both have to
    become an id two elements can agree on.

    Examples
    --------
    >>> _pattern_id("hatches", "#9cc3d5")
    'pat-hatches-9cc3d5'
    >>> _pattern_id("dots", "rgb(1, 2, 3)")
    'pat-dots-rgb123'
    """
    slug = "".join(ch for ch in color if ch.isalnum() or ch == "-")
    return f"pat-{kind}-{slug or 'none'}"


def _pattern_def(kind: str, color: str, scale: float = 1.0) -> str:
    """Return one ``<pattern>`` element drawing ``kind`` in ``color``.

    Every texture is built on the same 7-unit tile so two of them laid over
    neighbouring zones beat at a comparable rhythm, and every one is drawn in
    the zone's own colour rather than a fixed ink: the texture says how sure
    the claim is, the hue says whose it is, and the two must not fight.

    Parameters
    ----------
    kind : str
        One of :data:`_PATTERN_KINDS`.
    color : str
        Any CSS colour; used for the texture's strokes and fills.
    scale : float, optional
        Multiplies the tile, so a large plate's textures do not shrink into
        a flat wash. Tracks the viewport's type scale.

    Raises
    ------
    ValueError
        If ``kind`` is not one of the four. A mistyped texture that silently
        drew nothing would leave a zone looking like plain assessed control,
        which is the one reading this feature exists to prevent.
    """
    if kind not in _PATTERN_KINDS:
        raise ValueError(
            f"unknown fill pattern {kind!r}; known patterns are "
            f"{', '.join(sorted(_PATTERN_KINDS))}"
        )
    t = 7.0 * scale  # tile side
    pid = _pattern_id(kind, color)
    head = (
        f'<pattern id="{pid}" width="{t:.2f}" height="{t:.2f}" '
        'patternUnits="userSpaceOnUse"'
    )
    if kind == "hatches":
        # Rotated so the strokes never run parallel to a frontier dash.
        return (
            f'{head} patternTransform="rotate(45)">'
            f'<line x1="0" y1="0" x2="0" y2="{t:.2f}" stroke="{color}" '
            f'stroke-width="{2.0 * scale:.2f}" stroke-opacity="0.85"/></pattern>'
        )
    if kind == "dots":
        return (
            f"{head}>"
            f'<circle cx="{t / 2:.2f}" cy="{t / 2:.2f}" r="{1.25 * scale:.2f}" '
            f'fill="{color}" fill-opacity="0.9"/></pattern>'
        )
    if kind == "squares":
        return (
            f"{head}>"
            f'<rect x="{t / 2 - 1.5 * scale:.2f}" y="{t / 2 - 1.5 * scale:.2f}" '
            f'width="{3.0 * scale:.2f}" height="{3.0 * scale:.2f}" '
            f'fill="{color}" fill-opacity="0.85"/></pattern>'
        )
    # dashes: short horizontal ticks, offset row to row so they do not line up
    # into readable columns.
    return (
        f"{head}>"
        f'<line x1="0" y1="{t / 4:.2f}" x2="{t / 2:.2f}" y2="{t / 4:.2f}" '
        f'stroke="{color}" stroke-width="{1.6 * scale:.2f}" stroke-opacity="0.85"/>'
        f'<line x1="{t / 2:.2f}" y1="{3 * t / 4:.2f}" x2="{t:.2f}" y2="{3 * t / 4:.2f}" '
        f'stroke="{color}" stroke-width="{1.6 * scale:.2f}" stroke-opacity="0.85"/>'
        "</pattern>"
    )


#: How sure the assessment is, as a rendering rule per tier.
#:
#: Taken from ISW, whose control-of-terrain plates keep three separate things
#: apart that a single "controlled" fill runs together: ground they assess a
#: force actually holds, ground where movement has been *reported* but not
#: assessed as held, and ground a belligerent *claims* and nobody has
#: verified. ISW draws those as solid, as a stripe, and in a hue of their own
#: respectively, and the distinction is the whole reason their maps can be
#: read against a ministry's communiqué. A plate that collapses the three
#: into one fill is not simpler, it is making a stronger claim than its
#: sources support.
#:
#: Each entry gives the fill opacity as a multiple of the zone's configured
#: opacity, the texture laid over it, whether the outline is dashed, and the
#: words the legend uses.
#: Ink for the legend's texture key. Neutral on purpose: the swatch there
#: teaches the *texture*, not a class, and borrowing one class's hue for it
#: would read as "stripes mean the blue side".
_LEGEND_TEXTURE_INK = "#6b7280"

_CONFIDENCE_TIERS: dict[str, dict[str, Any]] = {
    # The default, and what every plate drawn before this option existed means.
    "assessed": {"fill": 1.0, "pattern": None, "dashed": False, "label": "assessed"},
    # Still plainly the same class, plainly less certain: rendered at 0.45 of
    # the zone opacity the stripes read but the band stopped looking like the
    # same actor and started looking like a fifth colour on the plate.
    "reported": {"fill": 0.6, "pattern": "hatches", "dashed": False, "label": "reported, not assessed"},
    # No solid fill at all: a claim nobody has verified should not paint the
    # ground the colour of ground that is held.
    "claimed": {"fill": 0.0, "pattern": "dots", "dashed": True, "label": "claimed, unverified"},
}


def _confidence_of(raw: Any) -> str:
    """Return the confidence tier named by ``raw``, defaulting to ``"assessed"``.

    Parameters
    ----------
    raw : Any
        Whatever the feature's confidence property held: usually a string,
        possibly ``None`` on a feature that never set one.

    Returns
    -------
    str
        A key of :data:`_CONFIDENCE_TIERS`.

    Raises
    ------
    ValueError
        If ``raw`` names a tier this generator does not draw. Falling back to
        "assessed" on a typo would quietly upgrade a claim nobody verified
        into ground a force is assessed to hold -- the single most damaging
        thing this layer can get wrong, and invisible on the finished plate.

    Examples
    --------
    >>> _confidence_of(None), _confidence_of("Reported"), _confidence_of("claimed")
    ('assessed', 'reported', 'claimed')
    >>> _confidence_of("probably")
    Traceback (most recent call last):
      ...
    ValueError: unknown confidence 'probably'; known tiers are assessed, claimed, reported
    """
    if raw is None or raw == "":
        return "assessed"
    tier = str(raw).strip().lower()
    if tier not in _CONFIDENCE_TIERS:
        raise ValueError(
            f"unknown confidence {str(raw)!r}; known tiers are "
            f"{', '.join(sorted(_CONFIDENCE_TIERS))}"
        )
    return tier


def _plate_patterns(cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """Return the ``(kind, colour)`` textures this plate's zones need in ``<defs>``.

    Read off the config, before any geometry is projected, so ``<defs>`` can be
    written at the top of the document the way SVG wants it -- and so a plate
    with no non-assessed zone pays nothing for the feature existing.
    """
    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if not palette:
        return []
    wanted: list[tuple[str, str]] = []
    for tier_name, classes in _zone_tiers(cfg).items():
        kind = _CONFIDENCE_TIERS[tier_name]["pattern"]
        if not kind:
            continue
        for cat in classes:
            wanted.append((str(kind), palette.get(cat, "#dddddd")))
        # The legend keys the texture itself, in a neutral ink, so the reader
        # learns "stripes mean reported" once rather than once per class.
        wanted.append((str(kind), _LEGEND_TEXTURE_INK))
    return list(dict.fromkeys(wanted))


def _zone_tiers(cfg: dict[str, Any]) -> dict[str, set[str]]:
    """Return ``{confidence tier: {class names drawn at it}}`` for this plate.

    The legend needs to show a tier only if a zone actually uses it, and to
    show it in a colour the reader will meet on the map.

    Called from four places that each take only ``cfg`` -- ``<defs>``, the
    legend's sizing and its drawing, and the accessible description -- so a
    config whose ``source`` is a *path* re-reads and re-parses that file once
    per call. Measured on the Sudan example's 39 KB source: +0.07 s against a
    1.50 s render, which is not worth threading a cache through four public
    signatures for. An inline ``FeatureCollection``, which every bundled
    example uses, costs nothing at all.
    """
    aoc = cfg.get("areas_of_control", {})
    field = aoc.get("category_field", "actor")
    conf_field = aoc.get("confidence_field", "confidence")
    try:
        features = _load_features(aoc.get("source"), Path(cfg.get("_config_dir", ".")))
    except Exception:
        return {}
    out: dict[str, set[str]] = {}
    for feat in features:
        props = feat.get("properties", {})
        out.setdefault(_confidence_of(props.get(conf_field)), set()).add(
            str(props.get(field, ""))
        )
    return out


def _tiers_present(cfg: dict[str, Any]) -> list[str]:
    """Return the non-default confidence tiers this plate draws, in ladder order.

    ``assessed`` is left out on purpose: it is what an unmarked zone already
    means, so keying it would add a legend row that says "the normal one".
    """
    present = _zone_tiers(cfg)
    return [t for t in _CONFIDENCE_TIERS if t != "assessed" and t in present]


def svg_defs(contested_hatch: str = "#b03a3a", patterns: Iterable[tuple[str, str]] = ()) -> str:
    """Return the ``<defs>`` block: soft drop-shadows, the contested hatch, markers.

    Parameters
    ----------
    contested_hatch : str
        Stroke colour of the diagonal hatch used to render a contested zone; it
        tracks the map's contested fill so the hatch reads as "the same category,
        emphasised" rather than an unrelated red.
    patterns : iterable of (str, str), optional
        ``(kind, colour)`` pairs to emit as ``<pattern>`` elements, one per
        confidence texture the plate actually uses. Deduplicated here, so a
        caller may pass the same pair once per zone without producing
        duplicate ids.
    """
    extra = "".join(_pattern_def(k, c) for k, c in dict.fromkeys(patterns))
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
        f"{extra}"
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
    """Return a dual-unit (km + mi) scale bar sized to a round distance on the map.

    The distances themselves come from :func:`_scale_bar_lengths`, which
    :func:`_reserved_boxes` also reads so the label layers know exactly how
    much room this takes.
    """
    km, km_len, mi, mi_len = _scale_bar_lengths(vp)
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


def _scale_bar_lengths(vp: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return ``(km, km_units, mi, mi_units)`` for this viewport's scale bar.

    Shared by :func:`scale_bar`, which draws it, and
    :func:`_reserved_boxes`, which keeps labels out of the space it takes.
    One computation, because two would drift and the symptom would be a
    label half-covered by a bar.

    Rounding the mile distance against the *kilometre bar's own length*,
    rather than against the original target, keeps the stacked pair
    comparable: rounded independently they could both land on "200" in
    different units, and a mile is 1.609 km.
    """
    m_per_unit = vp["m_per_unit"]
    target_units = min(vp["width"] * 0.22, 180)  # aim ~1/5 canvas, capped
    ts = vp["ts"]
    fs = 10 * ts

    def fits(length: float, total: str, unit: str) -> bool:
        text = len("0") + len(total) + len(unit)
        return length >= text * fs * _GLYPH_WIDTH_RATIO + 8 * ts

    def grow(value: float, metres: float, unit: str) -> tuple[float, float]:
        for _ in range(6):
            length = value * metres / m_per_unit
            if fits(length, _fmt_num(value), unit):
                return value, length
            value = value * (2.5 if str(_fmt_num(value)).startswith("2") else 2)
        return value, value * metres / m_per_unit

    km, km_len = grow(_nice_round(target_units * m_per_unit / 1000.0), 1000.0, "KM")
    mi, mi_len = grow(_nice_round(km_len * m_per_unit / 1609.34), 1609.34, "MI")
    return km, km_len, mi, mi_len


def _scale_bar_origin(cfg: dict[str, Any], vp: dict[str, Any]) -> tuple[float, float]:
    """Return where :func:`_furniture_layer` will put the scale bar.

    Its home is bottom-left; a bottom-left legend card pushes it to the
    opposite corner. Shared with :func:`_reserved_boxes` so the rectangle
    labels are kept out of is the rectangle the bar actually occupies --
    computing it twice is how a reservation ends up protecting empty paper
    while the bar prints over a name somewhere else.
    """
    ts, W, H = vp["ts"], vp["width"], vp["height"]
    x = 26 * ts
    if _resolve_legend_position(cfg, ts, W) == "bottom-left" and cfg.get(
        "areas_of_control", {}
    ).get("palette"):
        x = W - 176 * ts
    return x, H - 44 * ts - _caption_height(cfg, ts)


def _reserved_boxes(cfg: dict[str, Any], vp: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    """Return the plate rectangles furniture owns, which labels must not enter.

    Furniture wins and labels yield. The alternative -- drawing the bar over
    whatever is there -- is what the plates did before, and it put the scale
    bar straight across ``TANZANIA`` on the eastern-DRC plate and across
    ``Amman`` and ``Jerusalem`` on the Syrian one. A name with a bar through
    it is not a name, while a name that is simply absent costs the reader
    one place out of thirty.

    Only the furniture whose position is fixed before the label layers run
    is listed: the scale bar, and a legend card floating over the map. The
    north arrow sits in a corner the label layers already avoid, and the
    title block sits above the map's own content on every plate rendered so
    far.
    """
    ts, W, H = vp["ts"], vp["width"], vp["height"]
    boxes: list[tuple[float, float, float, float]] = []

    _km, km_len, _mi, mi_len = _scale_bar_lengths(vp)
    bar_x, bar_y = _scale_bar_origin(cfg, vp)
    # The bar draws two rules, 20*ts apart, each labelled 6*ts above its
    # own rule; the pad is the cap height of that 10*ts text plus slack.
    boxes.append(
        (
            bar_x - 4 * ts,
            bar_y - 18 * ts,
            bar_x + max(km_len, mi_len) + 4 * ts,
            bar_y + 26 * ts,
        )
    )

    position = _resolve_legend_position(cfg, ts, W)
    if position in ("bottom-right", "bottom-left", "top-left", "top-right"):
        panel_w, panel_h, margin = _legend_panel_dims(cfg, ts)
        if panel_w:
            px = margin if position in ("bottom-left", "top-left") else W - panel_w - margin
            py = (
                margin
                if position in ("top-left", "top-right")
                else H - panel_h - margin - _caption_height(cfg, ts)
            )
            boxes.append((px, py, px + panel_w, py + panel_h))

    inset = _inset_box(cfg, vp)
    if inset is not None:
        boxes.append(inset)
    return boxes


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
        # The confidence textures are the one thing on this plate a sighted
        # reader gets for free and a screen-reader user gets not at all: a
        # claimed zone and an assessed zone are the same <path> to them unless
        # the description says which tiers are drawn.
        tiers = _tiers_present(cfg)
        if tiers:
            spelled = ", ".join(str(_CONFIDENCE_TIERS[t]["label"]) for t in tiers)
            sentences.append(
                f"Some zones are drawn at a lower confidence than assessed control: {spelled}."
            )

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
    bbox = validate_region(cfg.get("region"))
    proj = build_projection(bbox, cfg.get("projection", "auto"))
    width = float(cfg.get("canvas_width", 1000))
    pad = float(cfg.get("padding", 26))
    vp = make_viewport(proj, bbox, width, pad, float(cfg.get("simplify", DEFAULT_TOLERANCE)))
    # Computed before any layer draws, because the label layers run first and
    # the furniture that would print over them is drawn last.
    vp["reserved"] = _reserved_boxes(cfg, vp)
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
    # Projecting a coastline into a conic can leave the result
    # self-touching, and GEOS answers a boolean op on an invalid operand with
    # a raw "TopologyException: side location conflict" rather than a result.
    # It bites near the poles: a plate of Svalbard and northern Greenland
    # ([-60, 78, 30, 84]) could not be drawn at all. Checked rather than
    # repaired unconditionally, because ``is_valid`` is cheap and
    # ``make_valid`` on a whole coastline is not -- the bundled plates are
    # all valid here and pay nothing.
    if not land_proj.is_valid:
        land_proj = make_valid(land_proj)
    sea_proj = region_proj.difference(land_proj)

    layers: list[str] = []

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
    land_d = projected_geom_to_path(land_proj, vp)
    layers.append(f'<g id="basemap-land"><path d="{land_d}" fill="{land_color}"/></g>')

    # 3a. relief, multiplied onto the land ------------------------------------
    # Terrain shading used to be drawn *under* everything, with the land fill
    # left translucent so it showed through. That works, and it costs two
    # things it need not. The land colour is diluted towards whatever is
    # beneath it, so a warm cream basemap drifts cold; and because the
    # shading is composited by alpha, a dark valley lightens the paper as
    # much as it darkens it, which is the opposite of what a shadow does.
    #
    # Multiply over an opaque land fill is the standard answer and behaves
    # the way terrain actually reads: a lit ridge is near-white in the
    # shading and multiplies to *leave the land colour alone*, while a
    # valley multiplies it down into its own darker, warmer self. Hue is
    # preserved by construction rather than by choosing an opacity that
    # damages it least.
    #
    # Clipped to the land, which the old arrangement did not need: a blend
    # across the whole plate would work shading computed for ground into the
    # sea and the bathymetry halo.
    #
    # The mode comes from the plate, which already knows: ``multiply``
    # darkens a cream day plate the way a shadow does, and ``screen`` lifts a
    # near-black night one the way a lit ridge does. Hardcoding either would
    # have made the night plate black.
    if basemap.get("relief", True):
        relief = _relief_layer(
            vp, proj, pad, W, H, projected_geom_to_path(region_proj, vp), bbox
        )
        layers.append(
            f'<defs><clipPath id="relief-land-clip"><path d="{land_d}"/></clipPath></defs>'
            f'<g id="relief-blend" data-layer-id="relief" '
            f'clip-path="url(#relief-land-clip)" '
            f'style="mix-blend-mode:{palette["blend"]}" '
            f'opacity="{palette["relief_opacity"]:.2f}">'
            f"{relief}</g>"
        )

    water_labels: list[tuple[float, float]] = []

    # 3c. internal-borders (admin-1: US states, FR regions, OSM countries) --- #
    layers.append(_internal_borders_layer(cfg, proj, vp, region_box, plate_region))

    # 3d. admin2-borders (admin-2, currently FR departments, zoom-gated) ----- #
    layers.append(_admin2_borders_layer(cfg, proj, vp, region_box, plate_region))

    # 4. areas-of-control --------------------------------------------------- #
    layers.append(_areas_of_control_layer(cfg, proj, vp, region_box, land))

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
        f'stroke-width="{0.9 * vp["ts"]:.2f}" stroke-opacity="{COMPOSITING["fact_line"]:.2f}" '
        f'stroke-linejoin="round" stroke-linecap="round"/></g>'
        if coast_d
        else '<g id="coastline"></g>'
    )

    # 5. infrastructure ----------------------------------------------------- #
    layers.append(_infrastructure_layer(cfg, proj, vp))

    # 5b. rivers (over the fills so the water reads) ------------------------ #
    # Lakes immediately before the rivers, and both above the control fills.
    # They used to straddle them -- lakes underneath as "basemap", rivers on
    # top -- which put one water system at two depths: on a plate of southern
    # Ukraine the Dnieper crossed a control zone as a blue line and then ran
    # into its own reservoir, which the same zone had painted brown. Water is
    # physical fact and a claim does not move it, so the whole system sits
    # above the claim and reads as one thing.
    layers.append(_lakes_layer(cfg, proj, vp, region_box, water_labels))
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
    # Each drawn group gets a ``data-layer-id`` so the plate's own controls
    # can address it. Not the ``id`` it already carries: an id is
    # document-unique, these plates get inlined several to a page, and two
    # maps in one article would have the script driving the wrong one.
    tagged = "".join(tag_layer(layer) for layer in layers[geo_start:])
    layers[geo_start:] = [
        f'<defs><clipPath id="region-clip"><path d="{region_clip_d}"/></clipPath></defs>'
        f'<g id="geo" clip-path="url(#region-clip)">' + tagged + "</g>"
    ]

    # 6. forces ------------------------------------------------------------- #
    marker_legend = cfg.get("marker_legend", [])
    layers.append(tag_layer(_markers_layer(cfg.get("forces", []), proj, vp, "forces", marker_legend)))

    # 7. events ------------------------------------------------------------- #
    layers.append(tag_layer(_markers_layer(cfg.get("events", []), proj, vp, "events", marker_legend)))

    # 8. annotation-labels -------------------------------------------------- #
    layers.append(tag_layer(_labels_layer(cfg, proj, vp)))
    # Editorial notes ride above every map layer and below the furniture:
    # an annotation that a river or a label can cross is not an annotation.
    layers.append(tag_layer(_annotations_layer(cfg, proj, vp)))

    # 9. annotation-furniture ---------------------------------------------- #
    layers.append(_furniture_layer(cfg, vp))
    # The locator inset is furniture too, and it answers the half of the
    # locator rule the plate itself cannot: where on Earth this is.
    layers.append(_inset_layer(cfg, vp))

    # The caption sits with the furniture, not with the geography: the geo
    # layers are clipped to the region polygon, and a footer under the map
    # falls outside it — drawn there it was silently cut away.
    layers.append(_caption_block(cfg, vp))

    # 10. legend ------------------------------------------------------------ #
    layers.append(_legend_layer(cfg, vp))

    # 12. the plate's own controls -------------------------------------------
    # Drawn last so they sit above every layer they switch, and hidden until
    # the script reveals them -- an <img> embed, a rasteriser or a browser
    # with scripting off all keep exactly the plate that shipped before.
    interactivity = str(cfg.get("interactivity", "self-contained"))
    if interactivity not in ("self-contained", "external", "static"):
        raise ValueError(
            f"unknown interactivity {interactivity!r}; "
            "known: self-contained, external, static"
        )
    has_controls = bool(
        interactivity == "self-contained" and cfg.get("areas_of_control", {}).get("palette")
    )
    if has_controls:
        layers.append(
            controls_markup(
                W,
                H,
                vp["ts"],
                palette,
                # ``_tiers_present`` answers "which tiers need a legend row",
                # and deliberately omits ``assessed`` because an unmarked zone
                # already means that. A *filter* is the other question: the
                # floor has to be offered, or the most useful setting on the
                # whole panel -- show me only what is assessed -- is the one
                # setting a reader cannot reach.
                tiers=("assessed", *_tiers_present(cfg)),
            )
        )

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
    legend_pos = _resolve_legend_position(cfg, vp["ts"], W)
    if legend_pos == "right":
        panel_w, panel_h, corner_margin = _legend_panel_dims(cfg, vp["ts"])
        plate_w = W + corner_margin + panel_w + corner_margin
        plate_h = max(H, panel_h + 2 * corner_margin)
    elif legend_pos == "below":
        # The band is drawn under the map, so the plate grows downwards and
        # the map's own W/H stay untouched for every layer already drawn.
        band_h, _cols, _cw, _rh = _legend_band_dims(cfg, vp["ts"], W)
        plate_w, plate_h = W, H + band_h
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
        f"{svg_defs(hatch, _plate_patterns(cfg))[:-7]}{clip}</defs>"
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
        # ``isolation:isolate`` makes this group its own stacking context, so
        # every blended layer inside it -- the relief, the control fills --
        # composites against the plate and stops there. Without it a plate
        # inlined into an HTML page (which is exactly how the gallery and any
        # CMS embed it, rather than as an <img>) blends against whatever the
        # host page happens to have behind it: the same map comes out
        # different on a white article and a dark one. The relief change made
        # this urgent by giving the blend most of the plate's area.
        f'<g clip-path="url(#plate-clip)" style="isolation:isolate">'
        f'<rect width="{plate_w:.1f}" height="{plate_h:.1f}" fill="{_pal(cfg)["plate"]}"/>'
        f"{''.join(layers)}"
        f"</g></g>"
        # Outside the clip and the isolation boundary: a script is not a
        # drawn thing, and nesting it inside a blended group is asking a
        # renderer to decide something it has no business deciding.
        # No panel, no script: a locator plate has nothing to switch, and
        # four kilobytes of behaviour that returns immediately is weight.
        f"{controls_script(interactivity) if has_controls else ''}"
        f"</svg>"
    )


#: Lakes the vendored basemap draws at an extent the world no longer has.
#:
#: ``lakes.former`` says "this water is gone" and ``lakes.skip`` says "do not
#: draw it". Neither fits a lake that still exists and is a fraction of the
#: polygon on file: drawing it solid asserts water that is not there, and
#: drawing it as former asserts a disappearance that has not happened.
#:
#: Applied by default, because the alternative is that every caller who draws
#: this region is silently wrong until they happen to read a docstring. A
#: config that sets ``lakes.historic`` replaces this list outright, and
#: ``lakes.historic: []`` restores the basemap's own extents.
_HISTORIC_EXTENT_LAKES: frozenset[str] = frozenset({
    # Natural Earth carries roughly its historic ~4 200 km2. It has
    # repeatedly fallen below a fifth of that since the 2010s, with partial
    # recoveries in wet years; there is no single current extent to vendor in
    # its place, which is exactly why the outline is drawn as historic rather
    # than silently corrected to a number that would be wrong by next season.
    "lake urmia",
})


def _lake_water_color(cfg: dict[str, Any]) -> str:
    """Return the colour this plate fills lakes with.

    A reader who has learnt one blue for water should not have to learn a
    second, so lakes follow the sea unless the config says otherwise.
    """
    settings = cfg.get("lakes", {})
    basemap = cfg.get("basemap", {})
    return settings.get("color", basemap.get("sea_color", _pal(cfg)["sea"]))


def _inner_depth_rings(
    geom: Any, vp: dict[str, Any], rings: int, palette: dict[str, Any]
) -> str:
    """Return depth rings buffered *inward* from a water body's own shore.

    The sea gets its halo by buffering outward from the coast into open
    water. A lake has no open water to buffer into, so the same cue has to
    be built the other way round: step inward from the shoreline. That also
    makes the rings say something true about shape, since a wide shallow
    lagoon fills with them and a narrow trench barely takes one.

    Parameters
    ----------
    geom : shapely geometry
        The lake, already projected into planar metres.
    vp : dict
        The viewport, for canvas width and metres-per-unit.
    rings : int
        How many to attempt; fewer are drawn when the lake runs out of room.
    palette : dict
        The plate palette, for the ring colour the sea already uses.

    Returns
    -------
    str
        Zero or more ``<path>`` elements. Empty when the geometry will not
        buffer -- a lake that cannot carry rings is still a lake.
    """
    # One ring every ~0.4% of the plate width, converted to the projected
    # metres the geometry is in, so the spacing looks the same at any size.
    step_m = vp["width"] * 0.004 * vp["m_per_unit"]
    out: list[str] = []
    try:
        for index in range(1, rings + 1):
            inner = geom.buffer(-step_m * index)
            if inner.is_empty:
                break
            drawn = projected_geom_to_path(inner, vp)
            if drawn:
                out.append(
                    f'<path d="{drawn}" fill="none" stroke="{palette["bathy"]}" '
                    f'stroke-width="0.6" stroke-opacity="{COMPOSITING["depth_cue"]:.2f}"/>'
                )
    except Exception:  # a self-touching lake must not cost the plate its water
        return ""
    return "".join(out)


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

    ``lakes.historic``
        A list of names whose vendored polygon is the *historic maximum* of a
        lake that still exists at a fraction of it: faded fill inside a dashed
        edge, the name suffixed ``(historic extent)``. Defaults to
        :data:`_HISTORIC_EXTENT_LAKES` rather than to nothing, because a
        caller who has not read this docstring should not be silently wrong;
        pass ``[]`` to draw the basemap's extents as they are.

    The cases this repo has had to handle, with dates, so the next caller does
    not have to discover them by being wrong in public:

    * **Kakhovka Reservoir** — drained within two weeks of the dam breach of
      6 June 2023. By 2026 the bed is willow and poplar scrub over sand and
      marsh, and is being used for infantry infiltration; it is not water and
      has not been for years. The bundled Ukraine example draws it as former.
    * **Lake Urmia** — the vendored polygon is near its historic extent,
      roughly 4 200 km², and the lake has repeatedly fallen below a fifth of
      that since the 2010s. Neither ``former`` nor ``skip`` fits a lake that
      still exists at a fraction of its outline, so it is drawn by default as
      a *historic extent*: faded fill, dashed edge, name suffixed. See
      :data:`_HISTORIC_EXTENT_LAKES`.
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
    lake_rings = int(settings.get("depth_rings", 4))
    historic = {n.lower() for n in settings.get("historic", _HISTORIC_EXTENT_LAKES)}
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
        is_historic = bool(key) and not is_former and key in historic
        if is_former:
            # No fill, because there is no water: a dashed outline is the
            # cartographic form for a body that was there and is not.
            shapes.append(
                f'<path d="{d}" fill="none" stroke="{edge}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="0.7" '
                f'stroke-dasharray="{3.6 * ts:.1f} {2.8 * ts:.1f}"/>'
            )
        elif is_historic:
            # There *is* water, and much less of it than this outline. A
            # faded fill inside a dashed edge says that without inventing a
            # current shoreline nobody has: the reader is told the water is
            # somewhere in here and does not fill it, and the label names the
            # outline for what it is.
            shapes.append(
                f'<path d="{d}" fill="{color}" fill-opacity="0.4" stroke="{edge}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="0.7" '
                f'stroke-dasharray="{3.6 * ts:.1f} {2.8 * ts:.1f}"/>'
            )
        else:
            shapes.append(
                f'<path d="{d}" fill="{color}" stroke="{edge}" '
                f'stroke-width="{0.6 * ts:.1f}" stroke-opacity="{COMPOSITING["fact_line"]:.2f}"/>'
            )
            # The same depth cue the sea gets, for the same reason: a lake
            # drawn as one flat blue is the only water on the plate with no
            # shape to it.
            if lake_rings:
                shapes.append(_inner_depth_rings(gp, vp, lake_rings, palette))
        if not name:
            continue
        if is_former:
            name = f"{name} (former)"
        elif is_historic:
            name = f"{name} (historic extent)"
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


def _polygonal(geom: Any) -> Any:
    """Return only the areal parts of ``geom``.

    Intersecting a hand-drawn zone with a coastline can return a
    ``GeometryCollection``: the polygon the caller meant, plus line or point
    fragments where the two boundaries touch. A zone is an area, so the
    fragments are an artefact of the clip and not territory -- and carrying
    them downstream is how a tangential touch turns into a stray hairline
    across a plate.

    Examples
    --------
    >>> from shapely.geometry import GeometryCollection, LineString, Polygon
    >>> square = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    >>> mixed = GeometryCollection([square, LineString([(3, 0), (4, 0)])])
    >>> _polygonal(mixed).geom_type
    'Polygon'
    >>> _polygonal(square).geom_type
    'Polygon'
    """
    if geom.geom_type != "GeometryCollection":
        return geom
    areal = [part for part in geom.geoms if part.geom_type in ("Polygon", "MultiPolygon")]
    if not areal:
        return geom
    return areal[0] if len(areal) == 1 else unary_union(areal)


def _areas_of_control_layer(
    cfg: dict[str, Any],
    proj: Transformer,
    vp: dict[str, Any],
    region_box: Any | None = None,
    land: Any | None = None,
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
    # Armies hold ground, not water; see the clip below.
    over_water = bool(aoc.get("over_water", False))
    # How sure the assessment is, read per feature. Orthogonal to the category:
    # "whose ground is this" and "how well do we know that" are two different
    # questions, and a zone answers both. See :data:`_CONFIDENCE_TIERS`.
    conf_field = aoc.get("confidence_field", "confidence")
    palette = aoc.get("palette", {})
    contested = set(aoc.get("contested", []))
    casing_w = float(aoc.get("casing_width", 2.4))
    # Fill opacity: high enough that the pastel classes read as solid territory,
    # low enough that the paper warmth and the coastline still show through.
    fill_op = float(aoc.get("fill_opacity", COMPOSITING["claim"]))
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
        conf = _confidence_of(props.get(conf_field))
        src = shape(feat["geometry"])
        # Clip to the region before projecting. A caller who hands over a whole
        # country's outline for a plate showing one province of it was emitting
        # a path many times the canvas: megabytes of coordinates that are
        # clipped away at draw time, an area share computed against territory
        # nobody can see, and -- found by rendering it -- a shape so far outside
        # the canvas that resvg dropped its ``mix-blend-mode`` fill entirely,
        # so the eastern-DRC plate came out with no control colours at all.
        # Armies hold ground, not water. A control polygon handed in as a
        # rectangle -- which is what a schematic assessment usually is --
        # otherwise paints the sea, the lakes and the lagoons inside it the
        # colour of held territory: the Black Sea came out a muddy
        # purple-brown on a plate of southern Ukraine, with the bathymetry
        # contours still faintly visible underneath it. Clipping to land is
        # the fix, and ``areas_of_control.over_water: true`` is the opt-out
        # for a claim that really is maritime.
        if land is not None and not over_water:
            # A malformed land clip must not lose the zone: the unclipped
            # polygon is still the assessment, it just also covers water.
            with contextlib.suppress(Exception):
                src = _polygonal(src.intersection(land))
            if src.is_empty:
                continue
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
        zones.append({"cat": cat, "conf": conf, "geom": geom, "d": d})
    total_area = sum(z["geom"].area for z in zones) or 1.0

    casings: list[str] = []
    fills: list[str] = []
    for z in zones:
        cat, conf, geom, d = z["cat"], z["conf"], z["geom"], z["d"]
        tier = _CONFIDENCE_TIERS[conf]
        # White casing drawn first (under the fill) so borders read as clean seams.
        casings.append(
            f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{casing_w}" '
            f'stroke-linejoin="round"/>'
        )
        color = palette.get(cat, "#dddddd")
        is_contested = cat in contested
        # A claimed zone gets no solid fill and a dashed edge: painting it the
        # same colour as ground a force is assessed to hold would assert
        # exactly the thing nobody has verified.
        zone_op = fill_op * float(tier["fill"])
        edge = (
            f' stroke-dasharray="{5.0:.1f} {3.2:.1f}"' if tier["dashed"] else ""
        )
        # The zone's claim, readable back out of the file: svgis's
        # ``--data-fields`` idea, kept to the three fields that *are* the
        # claim. ``data-area-share`` is the same number the tooltip shows,
        # computed from the projected geometry rather than asserted.
        data = (
            f' data-category="{_esc(str(cat))}" data-confidence="{conf}"'
            f' data-area-share="{geom.area / total_area:.4f}"'
        )
        fills.append(
            f'<path class="hit" tabindex="0" d="{d}" fill="{color}" fill-opacity="{zone_op:.2f}" '
            f'stroke="{color}" stroke-width="{1.4 if tier["dashed"] else 0.7}" '
            f'stroke-opacity="0.95"{edge}{data}{fill_style}/>'
        )
        # ``pointer-events="none"`` on every texture overlay. A pattern fill is
        # painted, so by default it swallows the pointer -- and these sit
        # *above* the ``.hit`` path, which is what the ``.hit:hover~.tip``
        # rule needs to see the cursor. Without it a textured zone is the one
        # kind of zone whose tooltip never opens, which was already true of
        # every contested zone before the confidence textures arrived.
        if tier["pattern"]:
            fills.append(
                f'<path d="{d}" fill="url(#{_pattern_id(tier["pattern"], color)})" '
                'pointer-events="none"/>'
            )
        if is_contested:
            fills.append(f'<path d="{d}" fill="url(#hatch-contested)" pointer-events="none"/>')
        share_pct = geom.area / total_area * 100
        detail = f"{share_pct:.1f}% of mapped area"
        if conf != "assessed":
            detail += f" · {tier['label']}"
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
    # Every shared border belongs to two countries, so walking the countries
    # and drawing each one's whole outline draws the inland half of this layer
    # **twice** -- measured at 1.63x the real frontier length on the bundled
    # Ukraine plate. Two coincident strokes at 0.85 alpha composite to 0.98,
    # and worse, their dash phases start at different vertices, so the two
    # dash patterns interleave and fill each other's gaps: the inland borders
    # came out darker *and* near-solid, while the coastline next to them
    # stayed properly dashed. The dashed hairline is the international-border
    # convention, and it was being lost precisely on the international
    # borders. So collect the pieces and union them before drawing -- each
    # line once, one dash phase, the same weight everywhere. This is what
    # mapshaper's ``-innerlines`` is for: shared boundaries as their own
    # layer, carrying no per-country attribute data (the labels below are
    # per-country and stay in the loop).
    pieces: list[Any] = []
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
        pieces.append(poly.boundary.intersection(region_box))
        if do_label and name and name.lower() not in focus and vis.area >= min_frac * region_area:
            pt = _label_point(vis)
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            if _label_fits(
                x, y, name, size=9.5 * ts, tracking=2.2, vp=vp, region=region
            ):
                labels.append(
                    tracked_text(x, y, name, size=9.5 * ts, fill="#9ba1a7", tracking=2.2, weight="600")
                )
    if pieces:
        # unary_union nodes the collection and merges the coincident runs, so a
        # border two countries share survives as one line rather than two.
        d = projected_geom_to_path(_project_geom(unary_union(pieces), proj), vp, close=False)
        if d:
            lines.append(
                f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="{COMPOSITING["fact_line"]:.2f}" '
                f'stroke-dasharray="{3.4 * ts:.1f} {2.4 * ts:.1f}"/>'
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
    # Furniture owns its rectangles and labels yield: a name with a scale bar
    # through it is not a name. Read off the viewport rather than passed in,
    # so every layer that places text -- cities, territories, neighbours --
    # obeys the same reservation without a new argument at each call site.
    for rx0, ry0, rx1, ry1 in vp.get("reserved", ()):
        if x0 < rx1 and x1 > rx0 and y0 < ry1 and y1 > ry0:
            return False
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
                f'stroke-width="{0.6 * ts:.1f}" stroke-opacity="{COMPOSITING["fact_line"]:.2f}" '
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
                f'stroke-width="{0.45 * ts:.1f}" stroke-opacity="{COMPOSITING["fact_line"]:.2f}" '
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


#: What a marker's ``precision`` says about where the thing it marks happened.
#:
#: Taken from ACLED's ``geo_precision``, a 1-3 code recorded next to every
#: event "to reflect the fact that the precise location of the incident may
#: not be known": 1 is a named town with coordinates, 2 is a town standing in
#: for a general area ("part of region"), 3 is a *provincial capital standing
#: in for a whole province*. ACLED is explicit that the coordinates "do not
#: reflect a more precise location, like a block or street corner, within the
#: named location".
#:
#: A map that draws all three as the same hard dot throws that away and
#: asserts a street corner its source never gave. The point of this table is
#: that the mark itself carries the code, so a reader does not have to take
#: the analyst's word for which dots are solid reporting.
_GEO_PRECISION: dict[int, str] = {
    1: "named location",
    2: "approximate — a place standing in for a general area",
    3: "approximate — a place standing in for a whole region",
}

#: How a date's precision is spoken, after ACLED's ``time_precision``: 1 is
#: the exact day, 2 is known only to the week, 3 only to the month.
_TIME_PRECISION: dict[int, str] = {1: "{}", 2: "week of {}", 3: "month of {}"}


#: Every key a marker in ``forces`` or ``events`` may carry.
#:
#: Same reasoning as :data:`CONFIG_KEYS` one level down. A marker is a dict
#: hand-written in a YAML file, and ``percision: 3`` would be read as no
#: precision at all -- which draws the confident, solid dot, the exact
#: opposite of what the author asked for, on a plate that still looks
#: finished. The failure is silent and it runs in the dangerous direction.
_MARKER_KEYS: frozenset[str] = frozenset({
    "lon", "lat", "color", "r", "label",
    "precision", "radius_km", "date", "time_precision", "source",
})


def _check_marker(item: dict[str, Any], layer_id: str) -> None:
    """Refuse a marker carrying a key this generator never reads.

    Raises
    ------
    ValueError
        Naming the closest known key, because the realistic cause is a typo
        and the realistic fix is one character.
    """
    unknown = sorted(set(item) - _MARKER_KEYS)
    if not unknown:
        return
    hints = []
    for key in unknown:
        near = get_close_matches(key, sorted(_MARKER_KEYS), n=1, cutoff=0.7)
        hints.append(f"{key!r}" + (f" (did you mean {near[0]!r}?)" if near else ""))
    raise ValueError(
        f"a {layer_id} marker has key(s) this generator never reads, so whatever "
        f"they configure would be silently dropped: {', '.join(hints)}. "
        f"Known marker keys: {', '.join(sorted(_MARKER_KEYS))}"
    )


def _precision_of(raw: Any, table: dict[int, Any], field: str) -> int:
    """Return the 1-3 precision code in ``raw``, defaulting to 1 (exact).

    Raises
    ------
    ValueError
        If ``raw`` is not one of the codes in ``table``. Silently treating an
        unreadable code as "exact" would upgrade an approximate mark into a
        confident one, which is the failure this whole feature exists to stop.

    Examples
    --------
    >>> _precision_of(None, _GEO_PRECISION, "precision")
    1
    >>> _precision_of("3", _GEO_PRECISION, "precision")
    3
    >>> _precision_of(4, _GEO_PRECISION, "precision")
    Traceback (most recent call last):
      ...
    ValueError: marker 'precision' must be one of 1, 2, 3; got 4
    """
    if raw is None or raw == "":
        return 1
    try:
        code = int(raw)
    except (TypeError, ValueError):
        code = -1
    if code not in table:
        raise ValueError(
            f"marker {field!r} must be one of {', '.join(str(k) for k in table)}; got {raw!r}"
        )
    return code


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
        _check_marker(it, layer_id)
        x, y = vp["to_svg"](*proj.transform(it["lon"], it["lat"]))
        color = it.get("color", "#b03a3a")
        r = float(it.get("r", 5))
        precision = _precision_of(it.get("precision"), _GEO_PRECISION, "precision")
        # A stated uncertainty radius, in kilometres on the ground, drawn to
        # the plate's own scale. Deliberately *not* defaulted from the event
        # type: ACLED publishes per-type buffers (5 km for battles and
        # explosions, 2 km for riots), but those measure how far an event's
        # effect reached, not how badly its position is known. Borrowing one
        # for the other would dress a guess as a measurement.
        radius_km = it.get("radius_km")
        halo = ""
        if radius_km is not None:
            rr = float(radius_km) * 1000.0 / vp["m_per_unit"]
            halo = (
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill="{color}" '
                f'fill-opacity="0.12" stroke="{color}" stroke-width="1" '
                f'stroke-opacity="0.55" stroke-dasharray="4 3" pointer-events="none"/>'
            )
        # svgis turns a feature's own fields into ``data-*`` attributes
        # (``--data-fields``) so the drawing stays queryable after it is
        # drawn. Worth copying: a finished plate is an argument, and an
        # argument a reader can only squint at is weaker than one they can
        # read back out of the file. Named for their meaning rather than for
        # whatever the config happened to call the column.
        data = (
            f' data-precision="{precision}"'
            f' data-lon="{it["lon"]:.4f}" data-lat="{it["lat"]:.4f}"'
        )
        if radius_km is not None:
            data += f' data-radius-km="{float(radius_km):g}"'
        # No radius and no precision: the solid dot stays, and it means what it
        # has always meant -- we know the place. An approximate position loses
        # its solid centre instead of gaining a made-up area: a hollow ring is
        # the old cartographic signal for "about here", and unlike a disc of
        # invented radius it claims nothing it cannot support.
        if precision == 1:
            paint = f'fill="{color}" stroke="#fff" stroke-width="1.4"'
        else:
            # Precision 3 is a whole region pinned to its capital, so its ring
            # is broken as well as hollow: one step further from "a place".
            broken = ' stroke-dasharray="3 2.2"' if precision == 3 else ""
            paint = (
                f'fill="#ffffff" fill-opacity="0.65" stroke="{color}" '
                f'stroke-width="{max(1.6, r * 0.45):.1f}"{broken}'
            )
        out.append(
            f'{halo}<circle class="hit" tabindex="0" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{r:.1f}" {paint}{data} filter="url(#marker-shadow)"/>'
        )
        headline = it.get("label") or legend_by_color.get(color) or layer_id.capitalize()
        lines = [headline, f"{it['lat']:.2f}°, {it['lon']:.2f}° · {layer_id}"]
        if precision != 1:
            note = _GEO_PRECISION[precision]
            if radius_km is not None:
                note += f", within {float(radius_km):g} km"
            lines.append(note)
        date = it.get("date")
        if date:
            lines.append(
                _TIME_PRECISION[
                    _precision_of(it.get("time_precision"), _TIME_PRECISION, "time_precision")
                ].format(date)
            )
        # Where this one mark came from. LiveUAMap's discipline: provenance
        # per event, not per plate. A caption saying "open sources" covers
        # the map; it tells a reader nothing about the dot they are looking
        # at, which is the thing they actually want to check.
        if it.get("source"):
            lines.append(f"Source: {it['source']}")
        out.append(
            tooltip_bubble(
                x,
                y - r - 6,
                lines,
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


#: How far an annotation's note sits from the point it annotates, in SVG
#: units at ts=1. Close enough to read as attached, far enough that the
#: leader line is visibly a leader line rather than a tick.
_ANNOTATION_OFFSET = 26.0

#: Characters per line before an annotation wraps. Narrow on purpose: a note
#: on a map is a caption, not a paragraph, and a wide measure invites one.
_ANNOTATION_WRAP = 30


def _annotations_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return the editorial notes: a circled point, a leader, and a sentence.

    This is the layer that makes a map an argument rather than a diagram.
    Every piece of newsroom guidance on the subject says the same thing --
    that the annotation *is* the news map, and that the other layers exist
    to support it -- and the specific conventions here are Datawrapper's:

    * **A circle, not an arrow.** An arrowhead points at a pixel and so
      claims a precision a note about a region does not have; a ring says
      "around here", which is what an annotation almost always means. The
      radius is in kilometres on the ground and drawn to the plate's scale,
      the same honesty the ACLED-style marker halos use.
    * **The data's own colours, not a contrasting one.** A note in the
      colour of the thing it describes sits back onto the map; a note in a
      fresh hue jumps off it and reads as chrome.
    * **Few, and spread out.** Nothing enforces that here -- it is an
      editorial matter -- but the wrap width is deliberately narrow so a
      long note looks wrong while it is being written rather than after it
      is rendered.

    Each note carries a halo (``paint-order="stroke"``), because the one
    place an annotation has to stay legible is over the relief and the
    control fills it is pointing at.

    Parameters
    ----------
    cfg : dict
        Reads ``annotations``: a list of ``{at: [lon, lat], text: str}``,
        each optionally with ``place`` (``"right"``, ``"left"``, ``"above"``
        or ``"below"``), ``color``, ``circle_km`` and ``wrap``.
    proj : pyproj.Transformer
        The plate's lon/lat -> planar-metres transformer.
    vp : dict
        The viewport record.

    Returns
    -------
    str
        An SVG group, empty when no annotation is configured.
    """
    notes = cfg.get("annotations", []) or []
    if not notes:
        return '<g id="annotations"></g>'
    ts = vp["ts"]
    ink = _pal(cfg)["chrome_ink"]
    paper = _pal(cfg)["plate"]
    out: list[str] = []
    for note in notes:
        unknown = sorted(set(note) - {"at", "text", "place", "color", "circle_km", "wrap"})
        if unknown:
            raise ValueError(
                f"an annotation has key(s) this generator never reads: {', '.join(unknown)}. "
                "Known keys: at, text, place, color, circle_km, wrap"
            )
        lon, lat = (float(v) for v in note["at"])
        x, y = vp["to_svg"](*proj.transform(lon, lat))
        color = str(note.get("color", ink))
        ring = 0.0
        if note.get("circle_km"):
            ring = float(note["circle_km"]) * 1000.0 / vp["m_per_unit"]
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{ring:.1f}" fill="none" '
                f'stroke="{color}" stroke-width="{1.4 * ts:.1f}" stroke-opacity="0.9"/>'
            )
        else:
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.0 * ts:.1f}" fill="{color}"/>'
            )
        place = str(note.get("place", "right"))
        gap = ring + _ANNOTATION_OFFSET * ts
        dx, dy = {"right": (gap, 0.0), "left": (-gap, 0.0),
                  "above": (0.0, -gap), "below": (0.0, gap)}.get(place, (gap, 0.0))
        tx, ty = x + dx, y + dy
        out.append(
            f'<line x1="{x + (ring * (1 if dx > 0 else -1 if dx < 0 else 0)):.1f}" '
            f'y1="{y + (ring * (1 if dy > 0 else -1 if dy < 0 else 0)):.1f}" '
            f'x2="{tx:.1f}" y2="{ty:.1f}" stroke="{color}" '
            f'stroke-width="{1.2 * ts:.1f}" stroke-opacity="0.75"/>'
        )
        anchor = {"right": "start", "left": "end"}.get(place, "middle")
        lines = wrap_no_orphan(str(note.get("text", "")), int(note.get("wrap", _ANNOTATION_WRAP)))
        size = 11.5 * ts
        # Vertically centre the block on the leader's end for a side note,
        # and hang it off the end for one above or below.
        first = ty - (len(lines) - 1) * size * 0.62 if place in ("right", "left") else (
            ty - (len(lines) - 1) * size * 1.24 if place == "above" else ty + size * 0.9
        )
        pad = 3 * ts if place == "right" else (-3 * ts if place == "left" else 0.0)
        for i, line in enumerate(lines):
            out.append(
                f'<text x="{tx + pad:.1f}" y="{first + i * size * 1.24:.1f}" '
                f'text-anchor="{anchor}" font-family="{_DEFAULT_FONT}" '
                f'font-size="{size:.1f}" fill="{ink}" '
                f'stroke="{paper}" stroke-width="{3.2 * ts:.1f}" paint-order="stroke" '
                f'stroke-linejoin="round">{_esc(line)}</text>'
            )
    return f'<g id="annotations">{"".join(out)}</g>'


#: How far an inset zooms out from the plate's own region when no context
#: bbox is given. Six is a compromise found by rendering: at three the
#: context is barely wider than the map and answers nothing, at ten a
#: European region lands in a view of the whole Atlantic and the rectangle
#: becomes a dot.
_INSET_ZOOM = 6.0

#: The inset's width as a fraction of the plate's. Small enough to read as
#: furniture, large enough that a country outline in it is still a country.
_INSET_WIDTH = 0.2


def _inset_context_bbox(bbox: list[float], zoom: float = _INSET_ZOOM) -> list[float]:
    """Return the wider extent an inset shows, centred on ``bbox``.

    Clamped to the usable world: past about 84 degrees the vendored basemap
    has nothing to draw and a conic projection stops behaving.

    Examples
    --------
    >>> _inset_context_bbox([0.0, 45.0, 10.0, 50.0], zoom=3.0)
    [-10.0, 40.0, 20.0, 55.0]

    A region near the pole keeps its width and is clipped in latitude:

    >>> _inset_context_bbox([0.0, 70.0, 10.0, 80.0], zoom=4.0)
    [-15.0, 55.0, 25.0, 84.0]
    """
    west, south, east, north = (float(v) for v in bbox)
    cx, cy = (west + east) / 2.0, (south + north) / 2.0
    half_w = max((east - west) * zoom / 2.0, 1.0)
    half_h = max((north - south) * zoom / 2.0, 1.0)
    return [
        max(-180.0, cx - half_w),
        max(-84.0, cy - half_h),
        min(180.0, cx + half_w),
        min(84.0, cy + half_h),
    ]


def _inset_box(cfg: dict[str, Any], vp: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Return the plate rectangle the locator inset occupies, or ``None``.

    Shared by :func:`_inset_layer`, which draws it, :func:`_reserved_boxes`,
    which keeps labels out of it, and the north arrow, which would otherwise
    print straight on top of it: both default to the top-right corner.
    """
    inset = cfg.get("inset")
    if not inset or inset.get("show", True) is False:
        return None
    ts, W, H = vp["ts"], vp["width"], vp["height"]
    region_bbox = [float(v) for v in cfg["region"]["bbox"]]
    context = [float(v) for v in inset["bbox"]] if inset.get("bbox") else _inset_context_bbox(
        region_bbox, float(inset.get("zoom", _INSET_ZOOM))
    )
    box_w = float(inset.get("width", _INSET_WIDTH)) * W
    sub = make_viewport(build_projection(context, "auto"), context, box_w, 0.0)
    box_h = sub["height"]
    margin = 22 * ts
    position = str(inset.get("position", "top-right"))
    ox = margin if position.endswith("-left") else W - box_w - margin
    oy = margin if position.startswith("top") else H - box_h - margin - _caption_height(cfg, ts)
    return ox, oy, ox + box_w, oy + box_h


def _inset_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the locator inset: where on Earth the plate's region actually is.

    "Zoom out for perspective, zoom in for detail" is the locator map's one
    rule, and a plate that only ever zooms in answers the second half of it.
    A reader who does not already know where North Kivu is learns nothing
    from a map of North Kivu; the inset is the sentence that tells them.

    Drawn from the coarsest vendored atlas (110m), because at a sixth of the
    plate's width a finer coastline is noise that costs bytes. The region
    itself is a filled rectangle in the plate's own ink rather than an
    outline: at this size an outline reads as a stray border.

    Parameters
    ----------
    cfg : dict
        Reads ``inset``: ``show`` (default true once the key exists),
        ``bbox`` (the context extent; derived from the region when absent),
        ``position`` (a corner, default ``"top-right"``), ``width`` (a
        fraction of the plate width) and ``zoom``.
    vp : dict
        The viewport record, for size and type scale.

    Returns
    -------
    str
        An SVG group, empty when no inset is configured.
    """
    inset = cfg.get("inset")
    if not inset or inset.get("show", True) is False:
        return '<g id="inset"></g>'
    unknown = sorted(set(inset) - {"show", "bbox", "position", "width", "zoom"})
    if unknown:
        raise ValueError(
            f"inset has key(s) this generator never reads: {', '.join(unknown)}. "
            "Known keys: show, bbox, position, width, zoom"
        )
    palette = _pal(cfg)
    ts, W = vp["ts"], vp["width"]
    region_bbox = [float(v) for v in cfg["region"]["bbox"]]
    context = [float(v) for v in inset["bbox"]] if inset.get("bbox") else _inset_context_bbox(
        region_bbox, float(inset.get("zoom", _INSET_ZOOM))
    )

    box_w = float(inset.get("width", _INSET_WIDTH)) * W
    proj = build_projection(context, "auto")
    # A viewport of its own, with no padding: the inset's frame is its bound.
    sub = make_viewport(proj, context, box_w, 0.0, vp.get("simplify", DEFAULT_TOLERANCE))
    box_h = sub["height"]

    placed = _inset_box(cfg, vp)
    assert placed is not None  # guarded by the early return above
    ox, oy, _x1, _y1 = placed

    land = load_land(context)
    # A malformed clip must not cost the plate its inset: the unclipped land
    # still draws correctly, it is only wider than the frame and the frame
    # clips it anyway.
    with contextlib.suppress(Exception):
        land = land.intersection(box(*context))
    land_d = projected_geom_to_path(_project_geom(land, proj), sub)

    # The region rectangle, projected through the same transform, so it sits
    # exactly where the main map's extent really falls in the context.
    region_d = projected_geom_to_path(_project_geom(box(*region_bbox), proj), sub)

    clip_id = "inset-clip"
    return (
        f'<g id="inset" transform="translate({ox:.1f},{oy:.1f})">'
        f'<clipPath id="{clip_id}"><rect x="0" y="0" width="{box_w:.1f}" '
        f'height="{box_h:.1f}" rx="{3 * ts:.1f}"/></clipPath>'
        f'<g clip-path="url(#{clip_id})">'
        f'<rect x="0" y="0" width="{box_w:.1f}" height="{box_h:.1f}" fill="{palette["sea"]}" '
        f'fill-opacity="0.55"/>'
        f'<path d="{land_d}" fill="{palette["land"]}" stroke="{palette["coast"]}" '
        f'stroke-width="0.5" stroke-opacity="0.7"/>'
        f'<path d="{region_d}" fill="{palette["chrome_ink"]}" fill-opacity="0.22" '
        f'stroke="{palette["chrome_ink"]}" stroke-width="{1.4 * ts:.1f}"/>'
        f"</g>"
        f'<rect x="0" y="0" width="{box_w:.1f}" height="{box_h:.1f}" rx="{3 * ts:.1f}" '
        f'fill="none" stroke="{palette["panel_edge"]}" stroke-width="1"/>'
        f"</g>"
    )


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
    # The caption is furniture, and furniture owns its space. Without a
    # ground it is grey monospace printed straight onto whatever the map
    # happens to end at: on the eastern-DRC plate, which is tall and
    # portrait, two of the three lines came out over a pale green control
    # fill. The hairline rule above it already says "a footer starts here";
    # the band is that promise kept.
    band_top = top - 7 * ts
    out = [
        '<g id="caption">',
        f'<rect x="0" y="{band_top:.1f}" width="{W:.1f}" height="{H - band_top:.1f}" '
        f'fill="{palette["plate"]}"/>',
        f'<line x1="{26 * ts:.1f}" y1="{band_top:.1f}" x2="{W - 26 * ts:.1f}" '
        f'y2="{band_top:.1f}" stroke="{palette["panel_edge"]}" stroke-width="1"/>',
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
    W = vp["width"]
    ts = vp["ts"]
    # North arrow top-right, clear of the title block top-left. When the
    # legend card floats top-right too (``legend_position``), step left of
    # its fixed footprint (262 panel + 22 margin, in ts units) so the
    # arrow never sits on the card.
    arrow_x = W - 30 * ts
    legend_pos = _resolve_legend_position(cfg, ts, W)
    has_legend = bool(cfg.get("areas_of_control", {}).get("palette"))
    if legend_pos == "top-right" and has_legend:
        arrow_x = W - (262 + 22 + 30) * ts
    # The locator inset defaults to the same corner, and an arrow printed on
    # top of a small map reads as part of it.
    inset_box = _inset_box(cfg, vp)
    if inset_box is not None and inset_box[0] > W / 2:
        arrow_x = min(arrow_x, inset_box[0] - 22 * ts)
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
    scale_x, scale_y = _scale_bar_origin(cfg, vp)
    out.append(scale_bar(scale_x, scale_y, vp, _pal(cfg)["chrome_ink"]))
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


#: Past this fraction of the map's width, a floating legend card stops being
#: furniture and becomes an occlusion. Measured on the bundled plates: the
#: 262-unit card is 26% of a 1000-unit map, 44% of a 600 and **70% of a 375**,
#: at which point it covers the thing it exists to explain. The newsroom
#: answer to a narrow column is not a smaller card but a different layout, so
#: ``legend_position: "auto"`` moves the key into a band below the map here.
_LEGEND_MAX_WIDTH_FRACTION = 0.38


def _legend_rows(cfg: dict[str, Any], ts: float) -> list[dict[str, Any]]:
    """Return the legend's rows as records, independent of where it is drawn.

    The floating card and the below-the-map band key the same plate, so the
    rows are defined once here and drawn by :func:`_legend_mark`. Before this
    split the card assembled its rows inline and nothing else could reuse
    them, which is why the only way to make a legend fit a narrow column was
    to shrink the card.

    Parameters
    ----------
    cfg : dict
        The map config.
    ts : float
        Type scale; only needed to resolve marker precision consistently.

    Returns
    -------
    list of dict
        One record per row, each with a ``kind`` of ``"class"``, ``"tier"``,
        ``"front"`` or ``"marker"``, and a ``label``.
    """
    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if not palette:
        return []
    contested = set(aoc.get("contested", []))
    fill_op = float(aoc.get("fill_opacity", COMPOSITING["claim"]))
    rows: list[dict[str, Any]] = [
        {"kind": "class", "label": str(name), "color": color,
         "contested": name in contested, "fill": fill_op}
        for name, color in palette.items()
    ]
    for tier_name in _tiers_present(cfg):
        tier = _CONFIDENCE_TIERS[tier_name]
        label = str(tier["label"])
        rows.append({"kind": "tier", "label": label[0].upper() + label[1:], "tier": tier})
    front = cfg.get("front", {})
    if front.get("line") and front.get("legend", True):
        rows.append({"kind": "front",
                     "label": str(front.get("legend_label", "Approx. front line")),
                     "color": front.get("color", "#3a4149")})
    for mk in cfg.get("marker_legend", []):
        rows.append({"kind": "marker", "label": str(mk.get("label", "")),
                     "color": mk.get("color", "#c0392b"),
                     "precision": _precision_of(
                         mk.get("precision"), _GEO_PRECISION, "precision")})
    return rows


def _legend_mark(row: dict[str, Any], x: float, y: float, sw: float, ts: float) -> str:
    """Draw one row's swatch, left edge at ``x`` and centred on ``y``.

    A swatch has to be the same mark the map uses, or the key keys nothing:
    a contested class carries its hatch, a confidence tier carries its
    texture, and an approximate marker is the same hollow ring it is on the
    page.
    """
    kind = row["kind"]
    sy = y - sw / 2 - 1 * ts
    if kind == "class":
        out = (f'<rect x="{x:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
               f'rx="{2.5 * ts:.1f}" fill="{row["color"]}" fill-opacity="{row["fill"]:.2f}" '
               f'stroke="{row["color"]}" stroke-width="1"/>')
        if row["contested"]:
            out += (f'<rect x="{x:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
                    f'rx="{2.5 * ts:.1f}" fill="url(#hatch-contested)"/>')
        return out
    if kind == "tier":
        tier = row["tier"]
        edge = f' stroke-dasharray="{3.0 * ts:.1f} {2.2 * ts:.1f}"' if tier["dashed"] else ""
        # A pale ground under the texture. The swatch's job is to teach the
        # *texture*, so it is drawn light enough for the stripes or dots to
        # read: at the zone's own 0.47 grey the hatch disappeared into its
        # own background and the row looked like a plain dark square.
        out = (f'<rect x="{x:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
               f'rx="{2.5 * ts:.1f}" fill="{_LEGEND_TEXTURE_INK}" '
               f'fill-opacity="{0.18 * float(tier["fill"]):.2f}" '
               f'stroke="{_LEGEND_TEXTURE_INK}" stroke-width="1"{edge}/>')
        if tier["pattern"]:
            out += (f'<rect x="{x:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
                    f'rx="{2.5 * ts:.1f}" '
                    f'fill="url(#{_pattern_id(str(tier["pattern"]), _LEGEND_TEXTURE_INK)})"/>')
        return out
    if kind == "front":
        return (f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + sw:.1f}" y2="{y:.1f}" '
                f'stroke="{row["color"]}" stroke-width="{2.4 * ts:.1f}" '
                f'stroke-dasharray="{7 * ts:.1f} {3.5 * ts:.1f}" stroke-linecap="round"/>')
    # marker: the swatch mirrors the mark's precision, including its ring.
    if row["precision"] == 1:
        paint = f'fill="{row["color"]}" stroke="#fff" stroke-width="{1.4 * ts:.1f}"'
    else:
        broken = f' stroke-dasharray="{3 * ts:.1f} {2.2 * ts:.1f}"' if row["precision"] == 3 else ""
        paint = (f'fill="#ffffff" fill-opacity="0.65" stroke="{row["color"]}" '
                 f'stroke-width="{2.5 * ts:.1f}"{broken}')
    return f'<circle cx="{x + sw / 2:.1f}" cy="{y:.1f}" r="{5.5 * ts:.1f}" {paint}/>'


def _resolve_legend_position(cfg: dict[str, Any], ts: float, map_w: float) -> str:
    """Return the legend position, expanding ``"auto"`` for this plate's width.

    ``"auto"`` is the only value that depends on how wide the plate is: it
    keeps the floating card while the card is a minority of the width, and
    drops the key into a band below the map once it stops being one.

    Examples
    --------
    >>> cfg = {"areas_of_control": {"palette": {"A": "#111", "B": "#222"}}}
    >>> _resolve_legend_position(cfg, 1.0, 1000.0)
    'bottom-right'
    >>> _resolve_legend_position(dict(cfg, legend_position="auto"), 1.0, 1000.0)
    'bottom-right'
    >>> _resolve_legend_position(dict(cfg, legend_position="auto"), 1.0, 375.0)
    'below'
    """
    position = str(cfg.get("legend_position", "bottom-right"))
    if position != "auto":
        return position
    panel_w, _panel_h, _margin = _legend_panel_dims(cfg, ts)
    if not panel_w:
        return "bottom-right"
    return "below" if panel_w > _LEGEND_MAX_WIDTH_FRACTION * map_w else "bottom-right"


def _legend_panel_dims(cfg: dict[str, Any], ts: float) -> tuple[float, float, float]:
    """Return ``(panel_w, panel_h, corner_margin)`` for the legend card.

    Factored out of :func:`_legend_layer` so :func:`build_map` can also size
    the extra canvas column an ``"outside"`` legend needs, without
    duplicating the row-counting logic (and risking the two drifting apart).
    """
    rows = _legend_rows(cfg, ts)
    if not rows:
        return 0.0, 0.0, 22 * ts
    pad = 15 * ts
    row_h = 25 * ts
    panel_w = 262 * ts
    foot_h = 30 * ts if cfg.get("legend_footer") else 0
    # Count only rows actually drawn below: the marker section's hairline
    # divider tucks between rows and needs no row of its own (a former +1
    # here left a blank row's worth of dead space above the footer).
    panel_h = pad * 2 + 24 * ts + row_h * len(rows) + foot_h
    return panel_w, panel_h, 22 * ts


def _legend_band_dims(
    cfg: dict[str, Any], ts: float, map_w: float
) -> tuple[float, int, float, float]:
    """Return ``(band_h, columns, column_w, row_h)`` for a legend below the map.

    The band is laid out to the width it is given rather than to a fixed card
    size: the rows pack into as many columns as fit, so a wide plate gets one
    shallow strip and a phone-width plate gets a single column.
    """
    rows = _legend_rows(cfg, ts)
    if not rows:
        return 0.0, 0, 0.0, 0.0
    pad = 15 * ts
    row_h = 23 * ts
    sw = 15 * ts
    gutter = 18 * ts
    # No text measurement is available to an SVG writer, so estimate from the
    # same glyph-advance ratio the label layer uses.
    widest = max(len(r["label"]) for r in rows)
    col_w = sw + 10 * ts + widest * 12.0 * ts * _GLYPH_WIDTH_RATIO + gutter
    columns = max(1, min(len(rows), int((map_w - 2 * pad) // col_w) if col_w else 1))
    band_rows = -(-len(rows) // columns)
    foot_h = 20 * ts if cfg.get("legend_footer") else 0.0
    band_h = pad + 20 * ts + band_rows * row_h + foot_h + pad
    return band_h, columns, col_w, row_h


def _legend_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the legend: a swatch per class, confidence key, marker key, source line.

    Swatches are rounded squares (a filled-territory cue, unlike a point dot), a
    contested class also carries the diagonal hatch so the legend mirrors the map
    exactly, and an optional ``front.label`` swatch shows the contact-line style.
    A footer sets the as-of / provenance line so the plate is self-describing.

    ``cfg["legend_position"]`` (``"bottom-right"`` by default, matching every
    plate built before this option existed) picks where the key goes --
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

    ``"below"`` puts the key in a full-width band underneath the map, and
    ``"auto"`` picks between that and the floating card from the plate's own
    width. That exists because a card is a fixed 262 units wide: fine as 26%
    of a 1000-unit plate, an occlusion at 70% of a 375-unit one. A narrow
    column does not want a smaller card, it wants the key somewhere else.
    """
    rows = _legend_rows(cfg, vp["ts"])
    if not rows:
        return '<g id="legend"></g>'
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    footer = cfg.get("legend_footer")
    pad = 15 * ts
    row_fs = 12.5 * ts
    sw = 15 * ts  # swatch side
    position = _resolve_legend_position(cfg, ts, W)

    if position == "below":
        return _legend_band(cfg, vp, rows)

    panel_w, panel_h, corner_margin = _legend_panel_dims(cfg, ts)
    row_h = 25 * ts
    header_fs = 12.5 * ts
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
    seen_marker = False
    for i, row in enumerate(rows):
        ry = py + pad + 26 * ts + i * row_h
        if row["kind"] == "marker" and not seen_marker:
            seen_marker = True
            dv = ry - row_h + 6 * ts
            parts.append(
                f'<line x1="{px + pad:.1f}" y1="{dv:.1f}" x2="{px + panel_w - pad:.1f}" '
                f'y2="{dv:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
            )
        # A class row is also the control that isolates it, when the plate
        # is interactive. Wrapped rather than attributed in place so the hit
        # target is the whole row, not the eleven-unit swatch.
        handle = (
            f' data-legend-category="{_esc(str(row["label"]))}" role="button" tabindex="0"'
            if row["kind"] == "class"
            else ""
        )
        parts.append(f"<g{handle}>" if handle else "<g>")
        parts.append(_legend_mark(row, px + pad, ry, sw, ts))
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" '
            f'fill="{_pal(cfg)["legend_ink"]}">{_esc(row["label"])}</text>'
        )
        parts.append("</g>")
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


def _legend_band(cfg: dict[str, Any], vp: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Draw the key as a full-width band under the map rather than over it.

    No card, no shadow: the band is part of the page furniture, not an object
    floating on the map, so it is separated by a hairline and left flat.
    """
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    band_h, columns, col_w, row_h = _legend_band_dims(cfg, ts, W)
    pad = 15 * ts
    sw = 15 * ts
    row_fs = 12.0 * ts
    parts: list[str] = [
        f'<line x1="0" y1="{H:.1f}" x2="{W:.1f}" y2="{H:.1f}" '
        f'stroke="{_pal(cfg)["panel_edge"]}" stroke-width="1"/>',
        f'<text x="{pad:.1f}" y="{H + pad + 8 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
        f'font-size="{11.5 * ts:.1f}" font-weight="700" fill="{_pal(cfg)["chrome_ink"]}" '
        f'letter-spacing="1.2">AREAS OF CONTROL</text>',
    ]
    top = H + pad + 20 * ts
    for i, row in enumerate(rows):
        cx = pad + (i % columns) * col_w
        ry = top + (i // columns) * row_h + row_h / 2
        parts.append(_legend_mark(row, cx, ry, sw, ts))
        parts.append(
            f'<text x="{cx + sw + 10 * ts:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" '
            f'fill="{_pal(cfg)["legend_ink"]}">{_esc(row["label"])}</text>'
        )
    footer = cfg.get("legend_footer")
    if footer:
        parts.append(
            f'<text x="{pad:.1f}" y="{H + band_h - pad + 2 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{9 * ts:.1f}" '
            f'fill="{_pal(cfg)["chrome_faint"]}">{_esc(footer)}</text>'
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
    "annotations", "inset", "interactivity",
    "areas_of_control", "arrows", "as_of", "attribution", "basemap", "canvas_width",
    "lakes",
    "caption", "events", "forces", "frame", "front", "frontiers",
    "infrastructure", "internal_borders", "labels", "legend_footer",
    "legend_position", "marker_legend", "method", "padding", "projection",
    "cities", "region", "rivers", "simplify", "source", "subtitle", "title",
})

#: Keys the loaders set themselves; a caller never writes these.
_INTERNAL_KEYS: frozenset[str] = frozenset({"_config_dir", "_plate"})


#: The widest longitude span a Lambert conformal conic will take before
#: pyproj refuses the projection outright. A conic is a regional projection
#: by construction; past roughly a hemisphere it stops being one.
_MAX_LCC_SPAN_DEGREES = 150.0


def validate_region(region: Any) -> list[float]:
    """Return the validated ``[west, south, east, north]`` of ``region``.

    ``validate_config`` goes to real trouble over a mistyped *key*, down to
    suggesting the one you meant. It never looked at the one key it
    requires, and the bbox is where the damaging mistakes actually live,
    because most of them do not crash:

    * **west east of east.** ``box(177, -19, -178, -16)`` does not raise.
      Shapely normalises it to ``-178 .. 177``, so asking for a five-degree
      window over Fiji drew **355 degrees of longitude** -- the whole planet
      except the region requested, rendered confidently and looking
      finished. A plain transposition (``30 .. 10``) silently drew a
      different, valid region instead.
    * **south above north**, same silent normalisation.
    * **a degenerate or absurd box**, which reached a bare
      ``ZeroDivisionError`` or a raw ``pyproj`` ``CRSError`` from inside the
      projection machinery rather than a sentence naming the problem.

    The antimeridian case is refused rather than supported: handling a
    wrapped region properly means splitting every layer's geometry at the
    seam, which is a real feature and not an argument check. Refusing says
    so; normalising silently says the opposite.

    Parameters
    ----------
    region : Any
        The config's ``region`` value; must carry a four-number ``bbox``.

    Returns
    -------
    list of float
        ``[west, south, east, north]``, validated.

    Raises
    ------
    ValueError
        With a sentence naming what is wrong and, where the cause is
        ambiguous, both of the things it could be.

    Examples
    --------
    >>> validate_region({"bbox": [-11.0, 35.0, 30.0, 60.0]})
    [-11.0, 35.0, 30.0, 60.0]

    >>> validate_region({"bbox": [30.0, 40.0, 10.0, 50.0]})
    Traceback (most recent call last):
      ...
    ValueError: region bbox has west (30.0) east of east (10.0): either the pair is swapped, or the region crosses the antimeridian, which this generator does not draw -- split it into two plates instead.

    >>> validate_region({"bbox": [10.0, 50.0, 30.0, 40.0]})
    Traceback (most recent call last):
      ...
    ValueError: region bbox has south (50.0) above north (40.0); the pair is swapped.
    """
    if not isinstance(region, dict) or "bbox" not in region:
        raise ValueError(
            "region needs a 'bbox': [west, south, east, north] in degrees. "
            f"Got {region!r}"
        )
    raw = list(region["bbox"])
    if len(raw) != 4:
        raise ValueError(
            f"region bbox needs exactly four numbers [west, south, east, north]; got {len(raw)}"
        )
    try:
        west, south, east, north = (float(v) for v in raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"region bbox must be four numbers; got {raw!r}") from exc
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise ValueError(f"region bbox must be four finite numbers; got {raw!r}")
    if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0):
        raise ValueError(
            f"region bbox longitudes must lie in -180..180; got west={west}, east={east}. "
            "A common cause is a [lat, lon] pair where [lon, lat] was expected."
        )
    if not (-90.0 <= south <= 90.0 and -90.0 <= north <= 90.0):
        raise ValueError(
            f"region bbox latitudes must lie in -90..90; got south={south}, north={north}. "
            "A common cause is a [lat, lon] pair where [lon, lat] was expected."
        )
    if south > north:
        raise ValueError(
            f"region bbox has south ({south}) above north ({north}); the pair is swapped."
        )
    if west > east:
        raise ValueError(
            f"region bbox has west ({west}) east of east ({east}): either the pair is "
            "swapped, or the region crosses the antimeridian, which this generator does "
            "not draw -- split it into two plates instead."
        )
    if east - west <= 0 or north - south <= 0:
        raise ValueError(
            f"region bbox has no area: west={west}, south={south}, east={east}, north={north}"
        )
    if east - west > _MAX_LCC_SPAN_DEGREES:
        raise ValueError(
            f"region spans {east - west:.0f} degrees of longitude, past the "
            f"{_MAX_LCC_SPAN_DEGREES:.0f} a Lambert conformal conic will take. "
            "This generator draws a region, not a world -- use the choropleth kind "
            "for a whole-world view."
        )
    return [west, south, east, north]


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
    if "region" in cfg:
        validate_region(cfg["region"])
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
# generator like every other one. It shows Europe as a clean reference
# situation map -- coastline, international frontiers, country labels, sea
# bathymetry, dual-unit scale bar, north arrow -- straight from the vendored
# Natural Earth basemap, with no thematic overlay invented. Pass a real
# ``config`` dict (or use the ``--config`` CLI) for an actual analysis map.
_DEMO_CONFIG: dict[str, Any] = {
    "title": "Situation map: Europe (demo)",
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
        "region": "Europe",
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
