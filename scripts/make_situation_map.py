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
    ``{page_color, radius, margin}`` for the card the plate sits on.
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
    ``{relief, relief_strength, hypsometric, plate, sea_color, land_color,
    coast_color, bathymetry}`` -- the physical ground. ``plate`` is ``"day"`` or
    ``"night"`` and outranks the individual colours. ``relief: false``
    removes the terrain cost. ``relief_strength`` (0--1) overrides how hard
    the hillshade blends; left unset it follows the visual hierarchy, full
    strength on a plate with no thematic layer and held back under one.
    ``hypsometric`` colours the ground by elevation as well as by light,
    and follows the same hierarchy by default.
``frontiers``
    International borders: ``{show, color, label_neighbours, focus,
    label_min_area_frac}``, plus ``{source, as_of, fields}`` to draw the
    borders of a past year from a caller-supplied historical GeoJSON
    instead of the present-day basemap.
``internal_borders``
    First-level administrative boundaries where a vendored source covers
    the region: ``{show, color, label_names, label_min_area_frac}``.
``admin2_borders``
    The second administrative tier, where a vendored source covers the
    region and the zoom warrants it: ``{show, color, label_names,
    label_min_area_frac}``. The layer has always drawn it; the validator
    refused the key until 0.10.2, so none of these could be set.
``rivers``
    ``{show, width, color, skip, always_label, label_color,
    label_min_length_frac, label_max_scalerank}``.
``lakes``
    ``{show, color, edge_color, skip, former, historic, always_label,
    label_color, label_min_area_frac, depth_rings}``. ``depth_rings`` is how many shelf
    rings step inward from a lake's shore; ``0`` draws none. ``former`` draws water that has gone;
    ``historic`` draws a lake whose vendored polygon is its historic
    maximum.
``cities``
    Automatic populated places: ``{show, size, limit, max_rank,
    hand_placed_clearance}``.
``infrastructure``
    ``{roads, airports}``, each a caller-supplied GeoJSON source.
``inset``
    Locator inset: ``{show, position, bbox, width, zoom}``.

The assessment
~~~~~~~~~~~~~~
``areas_of_control``
    The thematic layer: ``{source, category_field, confidence_field,
    palette, contested, fill_opacity, casing_width, blend, over_water,
    hatch_color}``. ``over_water: true`` keeps a zone's own shape instead of
    clipping it to land, for a claim that really is maritime.
    ``hatch_color`` sets the diagonal rule a contested zone is struck with.
``front``
    The contact line: ``{line, color, label, label_at, label_dx, label_dy,
    legend, legend_label}``. The three ``label_*`` offsets place the callout
    by hand when the automatic position lands badly.
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
``legend_title``
    The legend's heading. Defaults to ``AREAS OF CONTROL`` when the plate
    has control classes and ``KEY`` when it is marks alone, so a plate drawn
    from an event export stops titling a layer it does not have.
``small_multiples``
    Cut the plate into one panel per window of time:
    ``{by, from, to, columns, panel_width}``. ``by`` is ``"day"``,
    ``"week"``, ``"month"``, ``"quarter"`` or ``"year"``. Every panel is
    built from this one config, so the extent, the projection and the
    marker scale are shared and the panels really are comparable; a window
    with nothing in it is still drawn, and a mark whose own
    ``time_precision`` is coarser than the window is not placed in any
    panel -- the sheet prints how many and why.
``print_width``
    The figure's physical width, e.g. ``"90mm"`` (a journal's single column)
    or ``"190mm"`` (a double one); ``mm``, ``cm``, ``in`` and ``pt`` are
    understood. The root carries it instead of a pixel count, and the plate
    says how small its smallest label will actually print.
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
import re
import sys
import warnings
from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from difflib import get_close_matches
from pathlib import Path
from typing import Any

import numpy as np
from _assets import figures_scripts_dir, geo_dir
from _places import cities_in_view, place_labels
from _plate_controls import (
    controls_markup,
    controls_script,
    controls_size,
    tag_layer,
)
from _relief import (
    rgba_to_data_uri,
    sample_terrain_shade,
    terrain_relief_for_bbox,
    terrain_shade_for_bbox,
)
from _render import svg_example_path, write_svg
from _simplify import DEFAULT_TOLERANCE, simplify_ring, simplify_screen
from _textbox import box_inside, boxes_overlap, text_box, text_width
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
    # A None spec or loader means the sibling checkout moved or lost the file:
    # say so here rather than let it surface as an AttributeError one line down.
    if _tooltip_spec is None or _tooltip_spec.loader is None:
        raise ImportError(
            f"cannot load _svg.py from {figures_scripts_dir()}: "
            "the sprezzature-figures checkout this script borrows from is "
            "missing or incomplete."
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
        Point,
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

# Values are colour strings except `bathy_opacity`, which carries a number
# straight out of COMPOSITING so the two stay in step.
_PLATES: dict[str, dict[str, str | float]] = {
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


#: Property names CShapes 2.0 uses for a polygon's validity window and name.
#:
#: Taken from that dataset because it is the one historical-boundary source
#: this field actually uses -- it is the only GIS dataset mapping state
#: borders worldwide back to 1886 -- but the names are a default and not a
#: requirement: ``frontiers.fields`` overrides any of them for another source.
_CSHAPES_FIELDS: dict[str, Any] = {
    "name": ("cntry_name", "country_name", "name", "NAME"),
    "start": ("gwsyear", "gwsmonth", "gwsday"),
    "end": ("gweyear", "gwemonth", "gweday"),
}


def parse_as_of(raw: Any) -> date:
    """Return the date a historical map is drawn for, refusing a bare year.

    A year is not a date, and for this feature it is ambiguous in exactly the
    cases the feature exists for. "1991" is the Soviet Union on 1 January and
    is not the Soviet Union on 31 December; "1992" is Yugoslavia at either
    end of a year it spent dissolving. A loader that silently picked one of
    those would draw a map of a world that is defensible and unstated, which
    is the failure mode this repository keeps closing.

    Examples
    --------
    >>> parse_as_of("1995-07-01")
    datetime.date(1995, 7, 1)
    >>> parse_as_of(1991)
    Traceback (most recent call last):
      ...
    ValueError: frontiers.as_of 1991 is a year, not a date, and a year is ambiguous for exactly the borders this draws: the Soviet Union existed on 1991-01-01 and did not on 1991-12-31. Give a full date, e.g. '1991-06-30'.
    """
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if re.fullmatch(r"\d{4}", text):
        raise ValueError(
            f"frontiers.as_of {text} is a year, not a date, and a year is ambiguous "
            "for exactly the borders this draws: the Soviet Union existed on "
            "1991-01-01 and did not on 1991-12-31. Give a full date, e.g. "
            f"'{text}-06-30'."
        )
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"frontiers.as_of {raw!r} is not a date this reads; use YYYY-MM-DD."
        ) from None


def _window(props: dict[str, Any], keys: Sequence[str], fallback: date) -> date:
    """Return the date in ``props`` under ``keys`` (year, month, day), or ``fallback``."""
    year = props.get(keys[0])
    if year is None or year == "":
        return fallback
    try:
        # Month and day default to 1: CShapes carries all three, but a source
        # that dates its polygons only to the year is still a dated source,
        # and the first of January is the reading that keeps the window
        # widest rather than one that silently excludes a border.
        return date(int(year), int(props.get(keys[1]) or 1), int(props.get(keys[2]) or 1))
    except (TypeError, ValueError):
        return fallback


def countries_as_of(
    features: list[dict[str, Any]], as_of: date, fields: dict[str, Any] | None = None
) -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for the states that existed on ``as_of``.

    The same shape :func:`load_countries` returns, so the frontier layer does
    not know or care which one it was handed.

    Why this takes a caller-supplied source rather than a vendored one is a
    licensing fact and not a technical one, and it is worth stating where
    somebody will read it: CShapes 2.0 -- the only GIS dataset that maps
    state borders worldwide from 1886 -- is published under CC BY-NC-SA 4.0.
    Vendoring it into a BSD-licensed package would attach a non-commercial
    clause to the package and a share-alike obligation to anything built on
    it. It is free for the academic use this feature is for, so the honest
    arrangement is that the user downloads it and the licence stays with
    them.

    Parameters
    ----------
    features : list of dict
        GeoJSON features carrying a validity window in their properties.
    as_of : datetime.date
        The day to draw.
    fields : dict, optional
        Overrides for the property names, keyed ``name``, ``start``, ``end``.
        The defaults are CShapes 2.0's.

    Returns
    -------
    list of (str, polygon)

    Raises
    ------
    ValueError
        When no feature is valid on that date. Drawing an empty frontier
        layer would look exactly like a region with no neighbours.
    """
    spec = {**_CSHAPES_FIELDS, **(fields or {})}
    names = spec["name"] if isinstance(spec["name"], (list, tuple)) else (spec["name"],)
    far_past, far_future = date(1, 1, 1), date(9999, 12, 31)

    out: list[tuple[str, Any]] = []
    for feat in features:
        props = feat.get("properties") or {}
        if not (
            _window(props, spec["start"], far_past)
            <= as_of
            <= _window(props, spec["end"], far_future)
        ):
            continue
        name = next((str(props[k]) for k in names if props.get(k)), "")
        try:
            geom = make_valid(shape(feat["geometry"]))
        except (KeyError, TypeError, ValueError):
            continue
        if not geom.is_empty:
            out.append((name, geom))

    if not out:
        raise ValueError(
            f"no feature in the frontiers source is valid on {as_of.isoformat()}. "
            "An empty frontier layer looks exactly like a region with no "
            "neighbours, so this is an error rather than a blank map. Check the "
            "date, and check that the source carries "
            f"{spec['start'][0]}/{spec['end'][0]} properties (or pass "
            "frontiers.fields to name the ones it does)."
        )
    return out


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


#: Where the title and subtitle sit, in SVG units at ts=1, and how much room
#: each needs below its baseline. Kept next to :func:`_header_inset` because
#: the two must agree: these are the same numbers ``_furniture_layer`` draws
#: at, and a plate whose header is reserved at one height and drawn at
#: another is worse than one that never reserved anything.
_TITLE_BASELINE: float = 40.0
_SUBTITLE_BASELINE: float = 60.0
_HEADER_CLEARANCE: float = 14.0


def _header_inset(cfg: dict[str, Any], pad: float, width: float) -> float:
    """Return how far down the plate must start to clear its own title.

    The title is drawn at a fixed baseline and the plate was fitted from
    ``padding`` alone, so the two were laid out as if the other did not
    exist. With the default padding of 26 the map began 14 units *above* the
    title's own baseline, and every plate in the gallery had its subtitle
    printed across the ground -- on the Ukraine plate, straight through a
    frontier and the Dnieper.

    It had been that way since the generator was written, on every plate,
    and no test noticed because no test asks where text lands. Someone has
    to look at the picture.

    Returns ``pad`` unchanged for a plate with no header, so a bare plate
    is still fitted edge to edge.
    """
    ts = max(1.0, width / 1000.0)
    if cfg.get("subtitle"):
        return max(pad, (_SUBTITLE_BASELINE + _HEADER_CLEARANCE) * ts)
    if cfg.get("title"):
        return max(pad, (_TITLE_BASELINE + _HEADER_CLEARANCE) * ts)
    return pad


def make_viewport(
    proj: Transformer,
    bbox: list[float],
    width: float,
    pad: float,
    simplify: float = DEFAULT_TOLERANCE,
    pad_top: float | None = None,
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
    top = pad if pad_top is None else pad_top
    height = span_y * scale + top + pad

    def to_svg(x: float, y: float) -> tuple[float, float]:
        sx = pad + (x - minx) * scale
        sy = top + (maxy - y) * scale  # flip: projected up -> SVG down
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
        y = maxy - (sy - top) / scale
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
        # "0" at the left end of the bar, the rounded distance at the right,
        # and the unit after it: the bar has to be at least as long as those
        # three runs set end to end, with a little air.
        return length >= text_width(f"0{total}{unit}", fs) + 8 * ts

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


def _controls_origin(
    cfg: dict[str, Any], vp: dict[str, Any], size: tuple[float, float]
) -> tuple[float, float]:
    """Return a corner for the control panel that nothing else has taken.

    The panel sat in a fixed bottom-left corner, which is also where the
    scale bar lives and where a ``bottom-left`` legend lands. On the eastern
    DRC plate -- the one portrait plate, and the one whose legend is
    bottom-left -- the two overlapped by about 50 by 20 units and both
    became unreadable. Found in a browser by a reader, not by the suite.

    Tries the four corners in order of preference and takes the first whose
    box clears everything :func:`_reserved_boxes` already knows about: the
    scale bar, a floating legend card, and the locator inset. Falls back to
    bottom-left if a plate is so crowded that nothing is free, because a
    panel in a bad corner is still better than no panel.
    """
    ts, W, H = vp["ts"], vp["width"], vp["height"]
    panel_w, panel_h = size
    margin = 16 * ts
    # Top-left holds the title block; it is last, and only if nothing else
    # is free, which is why it is offset below the strapline.
    candidates = (
        (margin, H - panel_h - margin),
        (W - panel_w - margin, H - panel_h - margin),
        (W - panel_w - margin, 70 * ts),
        (margin, 70 * ts),
    )
    taken = _reserved_boxes(cfg, vp)
    for x, y in candidates:
        box_ = (x, y, x + panel_w, y + panel_h)
        if not any(
            box_[0] < rx1 and box_[2] > rx0 and box_[1] < ry1 and box_[3] > ry0
            for rx0, ry0, rx1, ry1 in taken
        ):
            return x, y
    return margin, H - panel_h - margin



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
    if cfg.get("_panel"):  # a panel has no furniture, so it owns no ground
        return []
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


def _wants_hypsometry(cfg: dict[str, Any]) -> bool:
    """Whether to colour the terrain by height as well as by light.

    Same hierarchy argument as :func:`_relief_strength`, and the same
    default: a plate carrying a thematic layer wants the quietest possible
    base, because a hypsometric ramp is a second colour scheme competing
    with the one that encodes who holds the ground. A plate carrying no
    thematic layer has no such competitor, and without the tint it cannot
    show elevation at all -- only slope.

    ``basemap.hypsometric`` settles it either way for a caller who disagrees.
    """
    basemap = cfg.get("basemap") or {}
    if "hypsometric" in basemap:
        return bool(basemap["hypsometric"])
    return not (cfg.get("areas_of_control") or {}).get("source")


def _relief_strength(cfg: dict[str, Any], palette: dict[str, Any]) -> float:
    """Return how hard to blend the hillshade, given what is drawn over it.

    The palette's ``relief_opacity`` was swept against the Albertine Rift
    *with the control fills in place*, and its comment says so: three
    multiplies stack, so the terrain has to give way or the class colour goes
    muddy. That is the correct number for a plate whose subject is who holds
    the ground.

    It is the wrong number for a plate that has no thematic layer at all.
    Restraint in the base exists to protect the theme; with no theme to
    protect, it just throws away contrast. Measured on the Himalaya plate --
    eight kilometres of relief, the most this generator will ever be asked to
    draw -- the tuned-for-conflict strength rendered the whole range inside
    13% of the available tonal range. The plateau and the plain came out the
    same colour.

    So the strength follows the hierarchy rather than a constant: full when
    the terrain *is* the subject, held back when something sits on top of it.
    ``basemap.relief_strength`` overrides both, for the plate that wants to
    argue with this.
    """
    override = (cfg.get("basemap") or {}).get("relief_strength")
    if override is not None:
        value = float(override)
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"basemap.relief_strength must be between 0 and 1, got {value}"
            )
        return value
    thematic = (cfg.get("areas_of_control") or {}).get("source")
    return float(palette["relief_opacity"]) if thematic else 1.0


def _relief_layer(
    vp: dict[str, Any],
    proj: Transformer,
    pad: float,
    width: float,
    height: float,
    clip_path_d: str,
    bbox: list[float],
    hypsometric: bool = False,
) -> tuple[str, tuple[int, int, int]]:
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
    # Named rather than splatted: both callees take four bounds and two pixel
    # extents, and `*bbox` on a list hides that arity from the type checker --
    # which then reads the two pixel arguments as overflow.
    west, south, east, north = bbox
    if hypsometric:
        shade, elevation, shade_bounds = terrain_relief_for_bbox(
            west, south, east, north, plot_w, plot_h
        )
    else:
        shade, shade_bounds = terrain_shade_for_bbox(
            west, south, east, north, plot_w, plot_h
        )
        elevation = None
    relief_rgba = sample_terrain_shade(
        lon_grid, lat_grid, valid_grid, shade, shade_bounds, elevation=elevation
    )
    # What this plate's terrain actually averages, so the legend can show a
    # class the colour that class comes out on the page. Measured off the
    # pixels about to be drawn rather than modelled from the ramp: a model
    # would be one more thing that can drift away from the picture.
    # Median, not mean. The array spans the whole padded canvas, including
    # everything the land clip is about to throw away, and a mean is dragged
    # about by those tails; the median answers "what does this plate's
    # terrain typically look like", which is the question a swatch asks.
    median_rgb = np.median(relief_rgba[..., :3].reshape(-1, 3), axis=0)
    tone = (int(median_rgb[0]), int(median_rgb[1]), int(median_rgb[2]))
    markup = (
        '<defs><clipPath id="relief-clip">'
        f'<path d="{clip_path_d}"/></clipPath></defs>'
        f'<g id="relief" clip-path="url(#relief-clip)">'
        f'<image x="{pad:.1f}" y="{pad:.1f}" width="{plot_w}" height="{plot_h}" '
        f'href="{rgba_to_data_uri(relief_rgba)}" preserveAspectRatio="none"/></g>'
    )
    return markup, tone


def _fmt_lon(v: float) -> str:
    """Format a longitude as a signed-free degree string, e.g. ``11.0°W``."""
    return f"{abs(v):.1f}°{'W' if v < 0 else 'E'}"


def _fmt_lat(v: float) -> str:
    """Format a latitude as a signed-free degree string, e.g. ``35.0°N``."""
    return f"{abs(v):.1f}°{'S' if v < 0 else 'N'}"


def _share_phrase(share: float) -> str:
    """Return ``"18% of the mapped area"``, or ``"under 1%..."`` when it rounds to nothing.

    Examples
    --------
    >>> _share_phrase(0.1842)
    '18% of the mapped area'
    >>> _share_phrase(0.0031)
    'under 1% of the mapped area'
    """
    pct = share * 100.0
    return (
        "under 1% of the mapped area" if pct < 0.5 else f"{pct:.0f}% of the mapped area"
    )


def zone_label(category: str, confidence: str, share: float) -> str:
    """Return what a screen reader should say when focus reaches a control zone.

    The three things the zone's own ``data-*`` attributes already carry, in
    the order a reader needs them: whose it is, how much ground that is, and
    -- only when it is not the default -- how well the claim is held up.

    Examples
    --------
    >>> zone_label("Russian-occupied (approx.)", "assessed", 0.1842)
    'Russian-occupied (approx.), 18% of the mapped area'
    >>> zone_label("SPLM-N (al-Hilu)", "claimed", 0.04)
    'SPLM-N (al-Hilu), 4% of the mapped area, claimed, unverified'
    """
    parts = [category, _share_phrase(share)]
    tier = _CONFIDENCE_TIERS.get(confidence, _CONFIDENCE_TIERS["assessed"])
    if confidence != "assessed":
        parts.append(str(tier["label"]))
    return ", ".join(parts)


def marker_label(
    headline: str, precision: int, date: str | None, time_precision: int
) -> str:
    """Return what a screen reader should say when focus reaches a marker.

    The same facts the hover tooltip shows a sighted reader, in one sentence
    and without the coordinates: six decimal places read aloud are noise, and
    the whole point of the precision code is that they were never that exact.

    Examples
    --------
    >>> marker_label("Avdiivka", 1, "2024-02-17", 1)
    'Avdiivka, named location, 2024-02-17'
    >>> marker_label("El Fasher", 3, "2024-06", 3)
    'El Fasher, approximate \u2014 a place standing in for a whole region, month of 2024-06'
    >>> marker_label("Unnamed", 2, None, 1)
    'Unnamed, approximate \u2014 a place standing in for a general area'
    """
    parts = [headline, _GEO_PRECISION[precision]]
    if date:
        parts.append(_TIME_PRECISION[time_precision].format(date))
    return ", ".join(parts)


#: Physical-length units a ``print_width`` may be written in, in millimetres.
_PRINT_UNITS: dict[str, float] = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.0}

#: The smallest type a journal will print, in points, and who says so.
#:
#: Nature asks for 5 to 7 pt at its 90 mm single column; Science states a 5 pt
#: minimum and recommends 7; Elsevier recommends 6 as the minimum and 8 as the
#: safer choice. 5 is therefore the floor below which no major publisher will
#: take the figure, and 6 the floor below which the most common one will not.
_TYPE_FLOOR_PT: float = 5.0
_TYPE_SAFE_PT: float = 6.0


def parse_length_mm(raw: Any) -> float:
    """Return ``raw`` as millimetres, or raise naming what it accepts.

    Examples
    --------
    >>> parse_length_mm("90mm")
    90.0
    >>> parse_length_mm("18.4 cm")
    184.0
    >>> round(parse_length_mm("7in"), 1)
    177.8
    >>> parse_length_mm(90)
    90.0
    >>> parse_length_mm("90px")
    Traceback (most recent call last):
      ...
    ValueError: print_width '90px' has no unit this understands; use mm, cm, in or pt
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().lower().replace(" ", "")
    for unit, factor in _PRINT_UNITS.items():
        if text.endswith(unit):
            try:
                return float(text[: -len(unit)]) * factor
            except ValueError:
                break
    raise ValueError(
        f"print_width {raw!r} has no unit this understands; use mm, cm, in or pt"
    )


def smallest_type_pt(svg: str, print_width_mm: float) -> tuple[float, float]:
    """Return ``(smallest font-size in user units, its size in points when printed)``.

    Read off the finished markup rather than from the type scale, for the
    reason the rest of this file keeps returning to: what the generator meant
    to emit and what reached the file are two different claims, and only the
    second one is printed.

    Examples
    --------
    A 10.8-unit label on a 1768-unit canvas, printed 90 mm wide:

    >>> svg = '<svg viewBox="0 0 1767.9 1000"><text font-size="10.8">x</text></svg>'
    >>> units, pt = smallest_type_pt(svg, 90.0)
    >>> units, round(pt, 2)
    (10.8, 1.56)
    """
    sizes = [float(m) for m in re.findall(r'font-size="([\d.]+)"', svg)]
    if not sizes:
        return 0.0, 0.0
    view = re.search(r'viewBox="0 0 ([\d.]+)', svg)
    if view is None:
        return min(sizes), 0.0
    units = min(sizes)
    return units, units / float(view.group(1)) * print_width_mm / 25.4 * 72.0


def _warn_if_unprintable(svg: str, print_width_mm: float, canvas_width: float) -> None:
    """Say, in points, how small this plate's smallest label will actually print.

    A plate is designed in user units and printed in millimetres, and nothing
    on screen connects the two. The bundled Ukraine plate is 1\u202f768 units
    wide with 10.8-unit labels: dropped into a journal's 90 mm single column
    that is **1.6 pt**, a third of the floor any major publisher accepts, and
    it renders without complaint because a vector file always does.

    This is a warning and not a refusal: the caller may be printing a poster,
    or may have a reason. But it names the number and the canvas width that
    would fix it, because "build the figure at its printed size" is advice
    nobody can follow without being told what their current size *is*.
    """
    units, pt = smallest_type_pt(svg, print_width_mm)
    if not units or pt >= _TYPE_SAFE_PT:
        return
    wanted = units * print_width_mm * 72.0 / (25.4 * _TYPE_FLOOR_PT)
    verdict = (
        "below every major publisher's floor"
        if pt < _TYPE_FLOOR_PT
        else "below Elsevier's 6 pt minimum"
    )
    warnings.warn(
        f"at {print_width_mm:.0f} mm this plate's smallest label is {pt:.1f} pt "
        f"({verdict}; Nature and Science ask 5 to 7 pt, Elsevier 6). The label is "
        f"{units:.1f} units on a {canvas_width:.0f}-unit canvas; designing the same "
        f"plate at canvas_width around {wanted:.0f} would print it at "
        f"{_TYPE_FLOOR_PT:.0f} pt.",
        RuntimeWarning,
        stacklevel=3,
    )


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
    'Situation map covering 22.0°E to 40.0°E, 44.0°N to 52.5°N. Areas of control in 2 classes: Ukraine, Russia (contested). 2 mapped features can be reached with the Tab key, each one naming what it is. The map draws the assessment it was given; it does not verify who holds what.'

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

    # Orientation, for the reader who cannot see that there is anything to
    # reach. A plate whose zones and marks are keyboard-reachable is useless
    # to someone who never learns they are: the description is the only place
    # that fact can be stated once, before the thirty tab stops begin.
    reachable = len(palette) + len(cfg.get("events", [])) + len(cfg.get("forces", []))
    if reachable:
        sentences.append(
            f"{reachable} mapped features can be reached with the Tab key, each one "
            "naming what it is."
        )

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
    # A sheet of small multiples is still "the situation map this config
    # describes", so it is reached through the same call every consumer
    # already makes -- the CLI, the Python entry point, the HTTP route and
    # the MCP tool -- rather than through a second generator they would
    # each have to learn about. The recursion terminates because the panel
    # configs are built without this key.
    if cfg.get("small_multiples"):
        return build_small_multiples(cfg)
    bbox = validate_region(cfg.get("region"))
    proj = build_projection(bbox, cfg.get("projection", "auto"))
    width = float(cfg.get("canvas_width", 1000))
    pad = float(cfg.get("padding", 26))
    vp = make_viewport(
        proj, bbox, width, pad, float(cfg.get("simplify", DEFAULT_TOLERANCE)),
        pad_top=_header_inset(cfg, pad, width),
    )
    # Computed before any layer draws, because the label layers run first and
    # the furniture that would print over them is drawn last.
    vp["reserved"] = _reserved_boxes(cfg, vp)
    W, H = vp["width"], vp["height"]

    # The plate's own control panel is furniture too, and it was the one
    # piece of furniture nothing yielded to. It ships ``display:none`` and
    # the script turns it on, so a rasteriser never sees it and neither did
    # any check -- but a reader with scripting on does, and on the Sudan
    # plate the river label "Blue Nile" sat under the word "Terrain" in it.
    # Decided here, before the labels, and handed to the drawing call far
    # below rather than worked out twice.
    interactivity = str(cfg.get("interactivity", "self-contained"))
    if interactivity not in ("self-contained", "external", "static"):
        raise ValueError(
            f"unknown interactivity {interactivity!r}; "
            "known: self-contained, external, static"
        )
    has_controls = bool(
        interactivity == "self-contained" and cfg.get("areas_of_control", {}).get("palette")
    )
    controls_at: tuple[float, float] | None = None
    # ``_tiers_present`` answers "which tiers need a legend row", and
    # deliberately omits ``assessed`` because an unmarked zone already means
    # that. A *filter* is the other question: the floor has to be offered,
    # or the most useful setting on the whole panel -- show me only what is
    # assessed -- is the one setting a reader cannot reach.
    tier_steps = ("assessed", *_tiers_present(cfg))
    if has_controls:
        panel = controls_size(vp["ts"], tiers=tier_steps)
        controls_at = _controls_origin(cfg, vp, panel)
        vp["reserved"].append(
            (controls_at[0], controls_at[1], controls_at[0] + panel[0], controls_at[1] + panel[1])
        )

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

    # The rectangle every name is measured against, built before any layer
    # runs. Under a conic the drawn map is a trapezoid narrower than the
    # plate at top and bottom, so the plate rectangle is the wrong shape to
    # ask "will the reader see this" -- it answers yes for paper the map
    # does not cover. It lives on the viewport rather than travelling as an
    # argument for the same reason ``reserved`` and ``ink`` do: a rule that
    # has to be passed at each call site is a rule that gets missed at one,
    # and it was. The river layer asked without it and set ``Danube`` half
    # outside the Western-Europe plate's edge, where the region clip then
    # cut the last letter off; the hand-placed layer asked the plate and let
    # ``EL GENEINA``, ``MEDITERRANEAN SEA`` and ``LISBON`` begin out on the
    # margin, and ``BLACK SEA`` rest its whole baseline on the neat line.
    region_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
    region_proj = _project_geom(region_box, proj)
    plate_region = vp["region"] = Polygon(
        [vp["to_svg"](px, py) for px, py in region_proj.exterior.coords]
    )

    # The author's own names are drawn near the top of the stack and must be
    # decided at the bottom of it. Every automatic layer below asks the
    # ledger "is this paper free", and a hand-placed name that is not in it
    # yet reads as free paper -- which is how "Zuwara" came out of the city
    # list straight into "TRIPOLI". So these two layers run now, before any
    # of them, and their markup is held until its turn comes to be drawn.
    # One call, not two: a layer asked where it will draw and then asked
    # again later is a layer that can answer differently twice.
    vp["ink"] = []
    marker_legend = cfg.get("marker_legend", [])
    force_marks = tag_layer(_markers_layer(cfg.get("forces", []), proj, vp, "forces", marker_legend))
    event_marks = tag_layer(_markers_layer(cfg.get("events", []), proj, vp, "events", marker_legend))
    hand_names = tag_layer(_labels_layer(cfg, proj, vp))
    hand_notes = tag_layer(_annotations_layer(cfg, proj, vp))
    # The contact line and the axes of advance carry the author's words too
    # -- "Approx. Kordofan front", "SPLM-N (REPORTED)" -- and until they
    # were in the ledger the river layer wrote straight over them.
    front = _front_line_layer(cfg, proj, vp)
    advances = _arrows_layer(cfg, proj, vp)

    # bbox already carries the region's real extent -- reuse it to pick the
    # 10m/50m basemap tier instead of re-deriving it from region_box.
    land = load_land(bbox=bbox).intersection(region_box)
    land_proj = _project_geom(land, proj)
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
        # The panels of one sheet are the same plate with different marks
        # on it, so they share a terrain raster exactly. It is the most
        # expensive thing here to compute and the largest thing in the
        # file; computing it once per sheet instead of once per panel is
        # also what makes the copies byte-identical, which is what lets
        # the sheet collapse them to a single <use>.
        shared = cfg.get("_relief_cache")
        if shared is not None and "markup" in shared:
            relief, cfg["_relief_tone"] = shared["markup"], shared["tone"]
        else:
            relief, cfg["_relief_tone"] = _relief_layer(
                vp, proj, pad, W, H, projected_geom_to_path(region_proj, vp), bbox,
                hypsometric=_wants_hypsometry(cfg),
            )
            if shared is not None:
                shared["markup"] = relief
                shared["tone"] = cfg["_relief_tone"]
        layers.append(
            f'<defs><clipPath id="relief-land-clip"><path d="{land_d}"/></clipPath></defs>'
            f'<g id="relief-blend" data-layer-id="relief" '
            f'clip-path="url(#relief-land-clip)" '
            f'style="mix-blend-mode:{palette["blend"]}" '
            f'opacity="{_relief_strength(cfg, palette):.2f}">'
            f"{relief}</g>"
        )

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
    layers.append(_lakes_layer(cfg, proj, vp, region_box))
    # Built before the rivers and drawn after them. A town's name is nailed
    # to its dot and a river's is free to slide along the water, so the
    # layer that cannot move chooses first; claim order is not draw order.
    # Asked the other way round, "Yamuna" took the paper and Agra, Kanpur
    # and Allahabad all lost their names to keep it.
    cities = _cities_layer(cfg, proj, vp, bbox, plate_region)
    layers.append(_rivers_layer(cfg, proj, vp, region_box))

    # 5b-bis. cities: the map is populated by default, so a reader always has
    #         somewhere to stand.
    layers.append(cities)

    # 5c. front line: the emphasised contact line between the control zones,
    #     the single most-read feature of a situation plate.
    layers.append(front)

    # 5d. axes of advance: drawn last of the geographic layers, because an
    #     arrow that the coastline or a control fill crossed would stop
    #     reading as movement.
    layers.append(advances)

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
    # Built at the top of build_map with the other hand-placed layers, so the
    # names below could be kept off them; drawn here, in their own order.
    layers.append(force_marks)

    # 7. events ------------------------------------------------------------- #
    layers.append(event_marks)

    # 8. annotation-labels -------------------------------------------------- #
    # Built at the top of build_map, drawn here: see the note there.
    layers.append(hand_names)
    # Editorial notes ride above every map layer and below the furniture:
    # an annotation that a river or a label can cross is not an annotation.
    layers.append(hand_notes)

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
    if has_controls:
        layers.append(
            controls_markup(W, H, vp["ts"], palette, origin=controls_at, tiers=tier_steps)
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
    # The root's role follows what the plate actually holds, and getting this
    # wrong is worse than leaving it off.
    #
    # ``role="img"`` is right for a plate that is one picture, and it is what
    # the other two generators emit (see ``_svg.svg_open``); without it a
    # screen reader announces an unlabelled graphic and the reader learns
    # nothing. But ``img`` is a role whose children are *presentational*: the
    # accessibility tree drops everything inside. Every thematic plate this
    # generator draws puts ``tabindex="0"`` on its claim polygons and its
    # marks, and measured across the five bundled ones that was 85 focusable
    # elements, 55 of them with no name at all -- keyboard stops a screen
    # reader walks into and announces as nothing, inside an element it has
    # been told is a single image. That combination has a name and a
    # checkpoint of its own in the accessibility literature.
    #
    # So: a plate with focusable content is a ``graphics-document`` (WAI-ARIA
    # Graphics Module), whose children are real nodes; a plate that is only a
    # basemap stays an ``img``, because that is what it is. Where the Graphics
    # Module is unsupported the role degrades to a generic group and the
    # children are still announced, which is strictly better than today.
    a11y_title, a11y_desc = accessible_text(cfg)
    navigable = bool(cfg.get("areas_of_control", {}).get("palette")) or bool(
        cfg.get("events") or cfg.get("forces")
    )
    role = "graphics-document" if navigable else "img"
    # ``print_width`` states the figure's physical width, and the root carries
    # it instead of a pixel count. The viewBox is untouched, so nothing about
    # the drawing changes -- but the file now lands at exactly that width in a
    # page layout or a LaTeX ``\includegraphics`` rather than at whatever a
    # consumer guesses from its pixel dimensions, which is the whole of
    # "build the figure at its printed size".
    size = f'width="{outer_w:.1f}" height="{outer_h:.1f}"'
    if cfg.get("print_width"):
        mm_w = parse_length_mm(cfg["print_width"])
        size = f'width="{mm_w:.4g}mm" height="{mm_w * outer_h / outer_w:.4g}mm"'
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {outer_w:.1f} {outer_h:.1f}" '
        f'{size} '
        f'role="{role}" aria-labelledby="sm-title sm-desc">'
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
    # Measured on the finished markup, once, and only when the caller has said
    # what width they are printing at. Nothing is refused: a plate is still a
    # plate at 2 pt, it is just not one a journal will set.
    if cfg.get("print_width"):
        _warn_if_unprintable(svg, parse_length_mm(cfg["print_width"]), outer_w)
    return svg


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
        # The plate's ink ledger has replaced the circle of exclusion the
        # water layers used to keep around each other's names: a radius is
        # the right shape for a dot and the wrong one for a word, and 58
        # units of it rejected "Lake Kivu" six characters clear of "Bukavu"
        # while letting "Blue Nile" sit inside "AD-DAMAZIN", which is 56
        # units long and was written by a different layer the radius never
        # saw.
        #
        # A lake is an area, so its name moves inside it rather than being
        # dropped -- ``biggest`` is already projected, so the check needs
        # ``to_world`` and no inverse projection. The Kakhovka Reservoir is
        # why: its deepest point is under a marker on the Ukraine plate, and
        # "(former)" is the one word on that plate saying the water is gone.
        at = _claim_area_label(
            biggest, name, size=size, tracking=0.0, vp=vp, caps=False,
            anchor_xy=(x, y),
            # One line-height of water's worth of slack, in ground metres.
            # A name a line outside its own shoreline still reads as that
            # water's name; a name a line outside a border reads as the
            # neighbouring country's, which is why only water gets this.
            slack=size * vp["m_per_unit"],
        )
        if at is None:
            continue
        x, y = at
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-family="{_DEFAULT_FONT}" font-size="{size:.1f}" font-style="italic" '
            f'fill="{label_color}" paint-order="stroke" stroke="#ffffff" '
            f'stroke-width="{2.2 * ts:.1f}" stroke-linejoin="round">{_esc(name)}</text>'
        )
    return f'<g id="lakes">{"".join(shapes)}{"".join(labels)}</g>'


def _bathymetry_layer(
    land_proj: Any, sea_proj: Any, vp: dict[str, Any], bath: dict[str, Any],
    palette: dict[str, str | float] | None = None,
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
        # The zone is focusable, so it has to say what it is when focus
        # lands on it. Without this it was a silent tab stop: reachable by
        # keyboard, announced as nothing. ``graphics-symbol`` is the WAI-ARIA
        # Graphics Module's role for "a graphic with meaning", which is what
        # a claim polygon is.
        label = _esc(zone_label(str(cat), conf, geom.area / total_area))
        fills.append(
            f'<path class="hit" tabindex="0" role="graphics-symbol" '
            f'aria-label="{label}" d="{d}" fill="{color}" fill-opacity="{zone_op:.2f}" '
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
    # Where the countries come from. The vendored basemap is present-day, and
    # for most plates that is what "international frontiers" means. It is
    # exactly wrong for a plate of 1995: a map of the Bosnian war drawn over
    # 2026 borders is not an approximation, it is a different claim. So a
    # caller may hand in a historical source and the date to read it at, and
    # the rest of this layer does not know which one it got.
    #
    # region_box.bounds is (minx, miny, maxx, maxy) == (west, south, east,
    # north) -- exactly the bbox shape _land_topojson_for_bbox expects, so
    # the frontier layer picks the same 10m/50m tier the basemap itself did.
    if fr.get("source"):
        if not fr.get("as_of"):
            raise ValueError(
                "frontiers.source needs frontiers.as_of: a historical boundary "
                "file holds every border the world has had, and without a date "
                "there is no way to know which of them to draw."
            )
        countries = countries_as_of(
            _load_features(fr["source"], Path(cfg.get("_config_dir") or ".")),
            parse_as_of(fr["as_of"]),
            fr.get("fields"),
        )
    else:
        countries = load_countries(bbox=region_box.bounds)
    for name, poly in countries:
        try:
            vis = poly.intersection(region_box)
        except Exception:  # skip a malformed country geometry rather than fail the plate
            continue
        if vis.is_empty:
            continue
        pieces.append(poly.boundary.intersection(region_box))
        if do_label and name and name.lower() not in focus and vis.area >= min_frac * region_area:
            at = _claim_area_label(
                vis, name, size=9.5 * ts, tracking=2.2, vp=vp, proj=proj, region=region
            )
            if at is not None:
                labels.append(
                    tracked_text(*at, name, size=9.5 * ts, fill="#9ba1a7", tracking=2.2, weight="600")
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


#: Breathing room between two pieces of text, in units at ``ts=1``. Touching
#: boxes are not a collision -- two names a hair apart read as two names --
#: but a hair is all it takes for the white halo of one to eat the stem of
#: the other, so the ledger keeps a little more than nothing between them.
_LABEL_CLEARANCE = 1.5


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
    caps: bool = False,
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
        The viewport, for its ``width``/``height``, the furniture rectangles
        in ``reserved`` and the names already drawn in ``ink``.
    region : shapely Polygon, optional
        The region clip in plate coordinates. When given, the label box must
        fit inside it; when ``None``, the plate rectangle is used.
    anchor : str, optional
        ``"middle"`` (the territory labels) or ``"start"`` (the city layer).
    caps : bool, optional
        True when the drawing call upper-cases the label, as
        :func:`tracked_text` does. It changes the answer by a fifth of the
        label's width, so it is passed rather than guessed.

    Returns
    -------
    bool
        True when the whole label lies inside the clip and touches nothing
        already on the plate.

    Examples
    --------
    >>> vp = {"width": 200.0, "height": 100.0, "ts": 1.0}
    >>> _label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp)
    True

    The same label centred near the edge does not fit, and is dropped rather
    than cropped:

    >>> _label_fits(6, 50, "CHAD", size=10, tracking=2, vp=vp)
    False

    A label well inside the plate still fails when the region clip does not
    reach it:

    >>> from shapely.geometry import box as _box
    >>> _label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp,
    ...             region=_box(0, 0, 60, 100))
    False

    And it fails when another layer has already inked that paper:

    >>> vp["ink"] = [(90.0, 44.0, 110.0, 52.0)]
    >>> _label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp)
    False
    """
    x0, y0, x1, y1 = text_box(
        x, y, text, size=size, tracking=tracking, anchor=anchor, caps=caps
    )
    # Furniture owns its rectangles and labels yield: a name with a scale bar
    # through it is not a name. Read off the viewport rather than passed in,
    # so every layer that places text -- cities, territories, neighbours --
    # obeys the same reservation without a new argument at each call site.
    #
    # ``ink`` is the same idea one step further: every name already committed
    # to this plate, whichever layer wrote it. Before it existed each layer
    # dodged only its own output, which is how a river name and a town name
    # drawn by two different layers ended up sharing the same paper on four
    # of the nine plates -- found by measuring the shipped SVGs, not by the
    # suite, because nothing had ever compared two layers' boxes.
    for other in (*vp.get("reserved", ()), *vp.get("ink", ())):
        if boxes_overlap((x0, y0, x1, y1), other, pad=_LABEL_CLEARANCE * vp.get("ts", 1.0)):
            return False
    # An explicit ``region`` wins; otherwise take the plate's own, so a call
    # site that forgets the argument still gets the drawn map rather than
    # quietly falling back to the wider plate. Only a viewport built without
    # one -- the doctests above, and nothing the generator ships -- reaches
    # the rectangle.
    if region is None:
        region = vp.get("region")
    if region is None:
        return x0 >= 0.0 and x1 <= float(vp["width"]) and y0 >= 0.0 and y1 <= float(vp["height"])
    try:
        return bool(region.contains(box(x0, y0, x1, y1)))
    except Exception:  # a degenerate clip must not cost the plate its labels
        return x0 >= 0.0 and x1 <= float(vp["width"])


def _claim_label(
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    tracking: float = 0.0,
    vp: dict[str, Any],
    region: Any | None = None,
    anchor: str = "middle",
    caps: bool = False,
) -> bool:
    """Ask :func:`_label_fits`, and on a yes take the paper as well.

    Asking and taking are one call on purpose. The alternative -- a layer
    that tests and then forgets to record -- is the failure this whole
    mechanism exists to stop, and this repository has already paid for the
    two-call version once: :func:`_scale_bar_origin` was split out of
    :func:`_furniture_layer` precisely because a rectangle computed twice
    drifts, and then the reservation protects empty paper while the thing
    itself prints over a name somewhere else.

    Parameters are :func:`_label_fits`'s, unchanged.

    Returns
    -------
    bool
        True when the label was placed *and* its box is now in the plate's
        ink ledger, so every later layer will see it.
    """
    if not _label_fits(
        x, y, text, size=size, tracking=tracking, vp=vp,
        region=region, anchor=anchor, caps=caps,
    ):
        return False
    vp.setdefault("ink", []).append(
        text_box(x, y, text, size=size, tracking=tracking, anchor=anchor, caps=caps)
    )
    return True


def _claim_area_label(
    vis: Any,
    name: str,
    *,
    size: float,
    tracking: float,
    vp: dict[str, Any],
    proj: Transformer | None = None,
    region: Any | None = None,
    caps: bool = True,
    anchor_xy: tuple[float, float] | None = None,
    slack: float = 0.0,
) -> tuple[float, float] | None:
    """Place the name of an area, letting it move *within* that area.

    An area label has no one correct point the way a town's does. It wants
    the deepest spot inside the shape (:func:`_label_point`), but if that
    paper is taken, any other spot inside the same shape still names the
    same thing -- which is more than a town's name can say about being
    moved. So the name steps up and down the shape rather than being
    dropped, and every step is checked back against the geometry, so it can
    never walk out of the country it names.

    ``PORTUGAL`` is the case that asked for this: its deepest point sits
    two units above the author's ``ATLANTIC OCEAN``, close enough that the
    two read as one block, and the first version of the ledger answered by
    deleting the country's name from a plate of Iberia.

    Parameters
    ----------
    vis : shapely geometry
        The part of the area inside the region, in lon/lat.
    name : str
        The label, upper-cased by :func:`tracked_text` when drawn.
    size, tracking : float
        Type size and letter-spacing, in plate units.
    vp : dict
        The viewport, for ``to_svg``/``to_world`` and the ink ledger.
    proj : pyproj.Transformer, optional
        The plate's projection, when ``vis`` is in lon/lat: used forwards to
        place and backwards to check that a moved label is still over its
        own ground. Leave it out when ``vis`` has already been projected,
        as the water layers' geometry has -- then ``vp["to_world"]`` alone
        answers the same question.
    region : shapely Polygon or None, optional
        The region clip, passed through to :func:`_label_fits`.
    caps : bool, optional
        Whether the drawing call upper-cases the name.
    anchor_xy : tuple of float, optional
        The starting point in plate coordinates, when the caller has
        already computed it.
    slack : float, optional
        How far outside the shape a moved label may still sit, in the units
        ``vis`` is expressed in. Zero for a country, where a name past the
        border names the wrong country. Water is the exception the atlases
        all make: a lake too narrow to hold its own name is named *beside*
        the water, and on these plates the Kakhovka Reservoir is exactly
        that -- a 191-unit name over a basin 19 units deep.

    Returns
    -------
    tuple of float, or None
        The ``(x, y)`` the label was placed at, or ``None`` when every
        candidate inside the shape was already taken.
    """
    if anchor_xy is not None:
        x, y = anchor_xy
    else:
        pt = _label_point(vis)
        x, y = vp["to_svg"](*(proj.transform(pt.x, pt.y) if proj else (pt.x, pt.y)))

    # Down the page by a line and a third: far enough to clear whatever
    # blocked the label, near enough that the name is still visibly on the
    # same ground. Across the page by rather more, because a label is many
    # times wider than it is tall and a half-step sideways clears nothing:
    # what blocked "Kakhovka Reservoir (former)" was a 10-unit marker dot
    # in the middle of a 191-unit name, and only a shift of about half the
    # name's own width takes the name off it. An elongated lake has that
    # room sideways and none at all up and down, and a tall country is the
    # other way about, which is why both axes are offered.
    down = size * 1.35
    wide = text_width(name.upper() if caps else name, size, tracking)
    # Three sideways steps rather than one. Half the name's width clears a
    # blocker sitting dead centre, but most blockers are not dead centre,
    # and the nearest step that works is the one to take: the Kakhovka
    # Reservoir's name clears the marker beside it at 0.42 of its width and
    # would have been thrown away by a list that only offered 0.56.
    offsets = (
        (0.0, 0.0),
        (0.0, -down), (0.0, down),
        (-0.28 * wide, 0.0), (0.28 * wide, 0.0),
        (-0.42 * wide, 0.0), (0.42 * wide, 0.0),
        (-0.56 * wide, 0.0), (0.56 * wide, 0.0),
        (0.0, -2.0 * down), (0.0, 2.0 * down),
        (-0.42 * wide, -down), (0.42 * wide, -down),
        (-0.42 * wide, down), (0.42 * wide, down),
    )
    for dx, dy in offsets:
        cx, cy = x + dx, y + dy
        if (dx or dy):
            wx, wy = vp["to_world"](cx, cy)
            if proj is not None:
                wx, wy = proj.transform(wx, wy, direction="INVERSE")
            # Checked back against the geometry every time, so a name can
            # never walk out of the thing it names.
            point = Point(wx, wy)
            if not (vis.contains(point) if slack <= 0 else vis.distance(point) <= slack):
                continue
        if _claim_label(
            cx, cy, name, size=size, tracking=tracking, vp=vp, region=region, caps=caps
        ):
            return cx, cy
    return None


def _rotated_box(
    box_: tuple[float, float, float, float], angle_deg: float, cx: float, cy: float
) -> tuple[float, float, float, float]:
    """Return the upright box that contains ``box_`` turned about ``(cx, cy)``.

    A water or territory name may be set at an angle to follow the thing it
    names. The ledger stores upright rectangles, so a turned label is stored
    as the smallest upright one that covers it -- generous by the corners,
    which is the right direction to be wrong in when the question is whether
    two names touch.

    Examples
    --------
    A square turned a quarter-circle about its own centre is itself:

    >>> tuple(round(v, 6) for v in _rotated_box((-1, -1, 1, 1), 90, 0, 0))
    (-1.0, -1.0, 1.0, 1.0)

    Turned an eighth, it needs a box wider by root two:

    >>> tuple(round(v, 4) for v in _rotated_box((-1, -1, 1, 1), 45, 0, 0))
    (-1.4142, -1.4142, 1.4142, 1.4142)
    """
    rad = math.radians(angle_deg)
    cos, sin = math.cos(rad), math.sin(rad)
    xs, ys = [], []
    for px, py in (
        (box_[0], box_[1]), (box_[2], box_[1]), (box_[2], box_[3]), (box_[0], box_[3])
    ):
        dx, dy = px - cx, py - cy
        xs.append(cx + dx * cos - dy * sin)
        ys.append(cy + dx * sin + dy * cos)
    return min(xs), min(ys), max(xs), max(ys)


def _ink_mark(x: float, y: float, radius: float, vp: dict[str, Any]) -> None:
    """Record a solid mark -- a dot, a capital's star -- in the plate's ledger.

    Stored as the square around it rather than as a circle: the ledger
    compares rectangles, and the corners it adds are a couple of units of
    extra clearance around a glyph that is about to have a name set beside
    it anyway.
    """
    vp.setdefault("ink", []).append((x - radius, y - radius, x + radius, y + radius))


def _ink_hand_label(
    box_: tuple[float, float, float, float], vp: dict[str, Any], what: str
) -> None:
    """Record a hand-placed label, refusing one the drawn map does not cover.

    Hand-placed names are the author's argument and are never dropped for
    want of room -- they go in the ledger unconditionally, and it is the
    automatic layers that yield to them. But a name the author placed where
    the map is not drawn is not a name the reader gets: it is set out on the
    margin, or sliced by the region clip, and nothing says so.

    Three of the nine bundled plates shipped it at its worst. ``Kalemie``
    sat 1.2 degrees south of the eastern-DRC region, ``Kolkata`` 1.9 degrees
    south of the Himalaya one, and ``Black Sea`` -- a 19-unit tracked name,
    the plate's whole orientation cue -- 0.9 degrees south of the Ukraine
    one, all three written in good faith, accepted in full, and drawn where
    no reader could find them.

    Measuring the plate rectangle caught those and stopped there, which is
    the wrong rectangle and left the quieter half of the same fault in
    place: under a conic the drawn map is a trapezoid, so a name can sit
    well inside the plate and still begin out on the paper. Eight more
    hand-placed names did, on five plates -- ``EL GENEINA`` opened on the
    margin, ``LISBON`` and ``ATLANTIC OCEAN`` lost letters to it on two
    plates apiece, ``MEDITERRANEAN SEA`` lost two, ``LUHANSK`` ran off the
    right-hand edge, and ``BLACK SEA`` laid its baseline along the neat
    line. The answer is the one this repository gives a config key nobody
    reads: one error message, naming the label, rather than silence.

    Parameters
    ----------
    box_ : tuple of float
        The label's ink rectangle in plate coordinates.
    vp : dict
        The viewport. ``region`` is the drawn map in plate coordinates and
        is what the label is tested against; a viewport without one falls
        back to the ``width``/``height`` rectangle.
    what : str
        How to name the label in the error, e.g. ``labels.places "Kalemie"``.

    Raises
    ------
    ValueError
        When any part of the label falls outside the drawn map.
    """
    plate = (0.0, 0.0, float(vp["width"]), float(vp["height"]))
    region = vp.get("region")
    inside = box_inside(box_, plate) if region is None else region.contains(box(*box_))
    if not inside:
        where = "plate" if region is None else "drawn map"
        raise ValueError(
            f"{what} is drawn at ({box_[0]:.0f}, {box_[1]:.0f})-({box_[2]:.0f}, "
            f"{box_[3]:.0f}), outside the {where}, so the reader gets at best "
            "part of it. Move it inside the region, widen region.bbox to "
            "include it, or remove it."
        )
    vp.setdefault("ink", []).append(box_)


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
            at = _claim_area_label(
                vis, name, size=8.0 * ts, tracking=1.6, vp=vp, proj=proj, region=region
            )
            if at is not None:
                labels.append(
                    tracked_text(*at, name, size=8.0 * ts, fill="#a7abaf", tracking=1.6, weight="500")
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
            at = _claim_area_label(
                vis, name, size=6.8 * ts, tracking=1.2, vp=vp, proj=proj, region=region
            )
            if at is not None:
                labels.append(
                    tracked_text(*at, name, size=6.8 * ts, fill="#b5b9bc", tracking=1.2, weight="500")
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
        size = 10.5 * ts
        # A river name is the one label on the plate with somewhere else to
        # go. A town's name must stay beside its dot or it points at the
        # wrong town; a river's can sit anywhere along the water, and a name
        # set along the course is the older convention anyway. So when the
        # midpoint is taken, walk the reach instead of dropping the name --
        # and because this layer can move, it is asked last, after the
        # cities have taken the paper they cannot leave.
        #
        # The fractions run outward from the middle: the centre of the
        # in-view reach is where the name belongs if nothing is in the way.
        for frac in (0.55, 0.42, 0.68, 0.3, 0.8, 0.2, 0.9):
            mid = comp.interpolate(frac, normalized=True)
            x, y = vp["to_svg"](mid.x, mid.y)
            if _claim_label(x, y, name, size=size, vp=vp):
                break
        else:
            continue
        labeled.add(name.lower())
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
        _ink_hand_label(
            text_box(x + dx, y + dy, label, size=10.5 * ts, tracking=1.4,
                     anchor="start", caps=True),
            vp,
            f'the front label "{label}"',
        )
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

#: The same three codes as a key reads them, rather than as a sentence speaks
#: them.
#:
#: :data:`_GEO_PRECISION` is written to be *spoken*: it lands mid-clause in a
#: tooltip and in an accessible name -- "Battle, approximate -- a place
#: standing in for a general area, 3 May 2024" -- where there is room for it
#: and a reader has context. A legend row has neither. Dropped into the
#: floating card verbatim, the longest of them inked 74 units past the right
#: edge of the Ukraine plate: a key that ran off the page it was keying,
#: caught by ``test_every_name_is_on_the_plate``.
#:
#: These are the same statements with the explanatory middle taken out, not
#: different ones. Both halves keep the word "approximate" and keep which of
#: the two approximations is meant, so a reader who meets the long form in a
#: tooltip recognises the short form in the key.
_GEO_PRECISION_KEY: dict[int, str] = {
    1: "Named location",
    2: "Approximate — a general area",
    3: "Approximate — a whole region",
}

#: How a date's precision is spoken, after ACLED's ``time_precision``: 1 is
#: the exact day, 2 is known only to the week, 3 only to the month.
#:
#: The fourth level is UCDP's, not ACLED's. ``date_prec`` 5 in the
#: Georeferenced Event Dataset means "known only within a range longer than
#: one month but not more than one calendar year", and there was no step for
#: it here. Rounding a year down to "month of" would have stated something
#: the source never did, in the direction that overstates -- so the scale
#: grew a step instead. A config that never names 4 is unaffected: 1 to 3
#: still mean exactly what they meant.
_TIME_PRECISION: dict[int, str] = {1: "{}", 2: "week of {}", 3: "month of {}", 4: "in {}"}


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
        # A stated uncertainty radius, in kilometres on the ground, drawn
        # to the plate's own scale. Deliberately *not* defaulted from the
        # event type: ACLED publishes per-type buffers (5 km for battles
        # and explosions, 2 km for riots), but those measure how far an
        # event's effect reached, not how badly its position is known.
        # Borrowing one for the other would dress a guess as a measurement.
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
        # The mark itself goes in the ledger; the uncertainty halo does not.
        # A halo is a hollow ring that can be kilometres across, and
        # reserving its whole disc would clear half a plate of names to
        # protect paper that is empty. The dot is small, solid, and the one
        # thing a name must never land on: "Blue Nile" came to rest exactly
        # on the red mark at Ad-Damazin the first time this ledger ran,
        # because the ledger knew about words and not about ink.
        vp.setdefault("ink", []).append((x - r, y - r, x + r, y + r))
        headline = it.get("label") or legend_by_color.get(color) or layer_id.capitalize()
        # Same reasoning as the zones: a focusable mark that announces
        # nothing is worse than one that cannot be focused at all. The label
        # carries the precision code, because that is the thing a reader who
        # cannot see the broken ring would otherwise never learn.
        mark_label = _esc(
            marker_label(
                str(headline),
                precision,
                str(it["date"]) if it.get("date") else None,
                _precision_of(it.get("time_precision"), _TIME_PRECISION, "time_precision"),
            )
        )
        out.append(
            f'{halo}<circle class="hit" tabindex="0" role="graphics-symbol" '
            f'aria-label="{mark_label}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{r:.1f}" {paint}{data} filter="url(#marker-shadow)"/>'
        )
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
            anchor = "end" if (-ty / tnorm) * offset < 0 else "start"
            _ink_hand_label(
                text_box(lx, ly, str(label), size=9.0 * ts, tracking=1.4,
                         anchor=anchor, caps=True),
                vp,
                f'the arrow label "{label}"',
            )
            out.append(
                tracked_text(
                    lx,
                    ly,
                    str(label),
                    size=9.0 * ts,
                    fill=color,
                    tracking=1.4,
                    weight="700",
                    anchor=anchor,
                )
            )
    return f'<g id="arrows">{"".join(out)}</g>'


def _cities_layer(
    cfg: dict[str, Any],
    proj: Transformer,
    vp: dict[str, Any],
    bbox: Sequence[float],
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
    # Handing the ledger to the placer, rather than only filtering what it
    # returns, is what lets a crowded town keep its name: the placer has a
    # second position to try (the name to the *left* of the dot), and a
    # caller that only vetoes the first one throws that away. Zuwara lost
    # its name to TRIPOLI this way, with its left side free the whole time.
    for city, dot_x, dot_y, label_x, label_y in place_labels(
        chosen,
        to_svg,
        font_size=size,
        dot_radius=2.0 * ts,
        bounds_px=plate,
        avoid=[*vp.get("reserved", ()), *vp.get("ink", ())],
        clearance=_LABEL_CLEARANCE * ts,
    ):
        # The plate rectangle is the outer bound; the region clip is the real
        # one, and it is narrower wherever the projection bends the frame in.
        # "Asmara" survived the rectangle and came out of the clip as "Asm".
        if not _claim_label(
            label_x, label_y, city.name, size=size, vp=vp, region=region, anchor="start"
        ):
            continue
        _ink_mark(dot_x, dot_y, 2.0 * ts, vp)
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
            _ink_mark(x, y, 7.0 * ts + 2.2 * ts, vp)  # the star plus its white ring
            out.append(_capital_star(x, y, 7.0 * ts))
        elif place.get("dot", True):
            _ink_mark(x, y, 2.6 * ts, vp)
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
        _ink_hand_label(
            text_box(lx, ly, place["text"], size=size, tracking=tracking,
                     anchor=ta, caps=True),
            vp,
            f'labels.places "{place["text"]}"',
        )
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
        _ink_hand_label(
            _rotated_box(
                text_box(x, y, w["text"], size=w.get("size", 19) * ts,
                         tracking=w.get("tracking", 6), anchor="middle",
                         caps=w.get("upper", True)),
                angle, x, y,
            ),
            vp,
            f'labels.waters "{w["text"]}"',
        )
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
    # Territory labels: the names of physical regions -- a range, a plateau,
    # a desert, a plain. They are the oldest convention on any physical map
    # and the one with the firmest rule: a region has no point, so its name
    # is set wide and faint *across* the ground it names, never beside a dot.
    # Wide tracking is what tells a reader "this names an area"; a tight
    # setting would read as a town.
    #
    # ``labels.territories`` was in the schema, in the validator and in the
    # module docstring for months, and no layer read it. A config that set it
    # was accepted in full and silently drew nothing -- the same shape of
    # failure as the ``admin2_borders`` section that the validator rejected,
    # only inverted: promised here, absent there.
    for region in labels.get("territories", []):
        x, y = vp["to_svg"](*proj.transform(region["lon"], region["lat"]))
        size = region.get("size", 12) * ts
        _ink_hand_label(
            _rotated_box(
                text_box(x, y, region["text"], size=size,
                         tracking=region.get("tracking", 4), anchor="middle",
                         caps=region.get("upper", True)),
                region.get("rotate", 0), x, y,
            ),
            vp,
            f'labels.territories "{region["text"]}"',
        )
        txt = tracked_text(
            x,
            y,
            region["text"],
            size=size,
            # Warm grey rather than the water layer's blue-grey: these names
            # belong to the land, and a reader scanning for a sea should not
            # stop on a mountain range.
            fill=region.get("color", "#8a8070"),
            tracking=region.get("tracking", 4),
            weight="500",
            upper=region.get("upper", True),
            anchor="middle",
        )
        angle = region.get("rotate", 0)
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
            _ink_hand_label(
                text_box(tx + pad, first + i * size * 1.24, line,
                         size=size, anchor=anchor),
                vp,
                f'the annotation "{line}"',
            )
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
    """Return the title block, north arrow and dual-unit scale bar.

    Empty for one panel of a sheet of small multiples: the sheet draws the
    title, the arrow and the ruler once. Nine identical rulers do not tell
    a reader the scale nine times, they take nine panels' worth of room to
    say one thing.
    """
    if cfg.get("_panel"):
        return '<g id="annotation-furniture"></g>'
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
        # Read off the card rather than restating its width: the 262 that used
        # to be written here twice is now a floor the card can exceed.
        card_w, _card_h, corner = _legend_panel_dims(cfg, ts)
        arrow_x = W - (card_w + corner + 30 * ts)
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
            f'<text x="{26 * ts:.0f}" y="{_TITLE_BASELINE * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{22 * ts:.0f}" font-weight="700" fill="{_pal(cfg)["chrome_ink"]}">{_esc(title)}</text>'
        )
    if subtitle:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{_SUBTITLE_BASELINE * ts:.0f}" font-family="{_DEFAULT_FONT}" '
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
    if cfg.get("_panel"):  # credited once on the sheet, not once per panel
        return '<g id="attribution"></g>'
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


def _legend_heading(cfg: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Return the legend card's heading, in capitals, for what it actually keys.

    It was the string ``AREAS OF CONTROL``, always, because for a long time
    that was the only thing a legend could hold. A plate drawn from an event
    export has no areas of control and every one of them printed the heading
    anyway -- a title that names a layer the map does not have, which is a
    cheaper version of the same lie as a label in the margin.

    ``legend_title`` in the config wins; otherwise the heading is read off
    the rows: control classes make it areas of control, and marks alone make
    it a key.

    Examples
    --------
    >>> _legend_heading({}, [{"kind": "class"}, {"kind": "marker"}])
    'AREAS OF CONTROL'
    >>> _legend_heading({}, [{"kind": "marker"}])
    'KEY'
    >>> _legend_heading({"legend_title": "Recorded events"}, [{"kind": "marker"}])
    'RECORDED EVENTS'
    """
    title = cfg.get("legend_title")
    if title:
        return str(title).upper()
    return "AREAS OF CONTROL" if any(r["kind"] == "class" for r in rows) else "KEY"


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
    # No early return on an empty palette. A plate can be nothing but marks
    # -- which is exactly what a plate drawn from an ACLED or UCDP export is
    # -- and that version of this function answered "no legend" for every one
    # of them: ``marker_legend`` was accepted by the validator, carried
    # through ``build_map``, handed to the marker layer for its tooltips, and
    # never keyed, because an unrelated section was missing. The reader got a
    # page of coloured dots and no way to learn what a colour meant. The rule
    # is the one this file applies everywhere else: build what there is.
    contested = set(aoc.get("contested", []))
    fill_op = float(aoc.get("fill_opacity", COMPOSITING["claim"]))
    rows: list[dict[str, Any]] = [
        {"kind": "class", "label": str(name),
         "color": _as_rendered(color, cfg, fill_op),
         "contested": name in contested, "fill": 1.0}
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
    # The rows above key the *colour* -- which class a mark belongs to -- and
    # on an event plate they are all drawn at the confident solid disc. The
    # ring vocabulary is the other half, and it is the half this generator
    # exists for: hollow means "about here", broken means "a place standing in
    # for a whole region". Nothing on the page said so. A plate could draw all
    # three symbols and key one of them, which teaches the colour correctly
    # and the shape not at all -- the same defect the aggregated plate had in
    # its key, found the same way, by rendering one and looking at it.
    #
    # Keyed only when the plate actually draws more than the confident symbol:
    # a plate whose marks are all exact does not need a lesson in rings it
    # never draws. The wording is :data:`_GEO_PRECISION`'s own, so the key,
    # the tooltip and the accessible name say the same sentence.
    codes = sorted({
        _precision_of(it.get("precision"), _GEO_PRECISION, "precision")
        for layer in ("events", "forces")
        for it in (cfg.get(layer) or [])
    })
    if codes != [1]:
        for code in codes:
            rows.append({"kind": "marker", "precision": code,
                         "label": _GEO_PRECISION_KEY[code],
                         "color": _pal(cfg)["chrome_sub"]})
    return rows


def _as_rendered(color: str, cfg: dict[str, Any], fill_op: float) -> str:
    """Return ``color`` as it will actually come out on the page.

    A legend swatch exists so a reader can match it to the ground. Once the
    terrain is blended under the control fills, it stops matching: the
    Ukraine plate declares its government class as ``#bcd4ec``, a pale blue
    with the blue channel 24 levels above the green, and the ground renders
    at ``#b1ba b2`` -- blue five levels *below* green. The hue is not
    attenuated, it is gone, and a reader pairing swatch to territory has to
    guess. That was found by someone opening the plate in a browser and
    sampling it, not by any test here.

    The arithmetic below is the SVG's, not an approximation of it: a
    ``multiply`` group at ``opacity`` s over the land, then the class fill at
    ``fill_opacity`` f over that. The terrain tone is whatever this plate's
    own relief averaged, measured in :func:`_relief_layer` off the pixels it
    was about to draw.

    The alternative was to leave the swatch alone and say in prose that it
    gives the class and not the colour. That is the documentation fixing a
    picture, which is the wrong way round.
    """
    tone = cfg.get("_relief_tone")
    if not tone:
        return color
    palette = cfg.get("_plate", _PLATES["day"])
    blend = (cfg.get("areas_of_control") or {}).get(
        "blend", palette["blend"] if tone else "none"
    )
    if blend != "multiply":  # only multiply shifts the hue; screen is the night plate
        return color
    land = _hex_to_rgb((cfg.get("basemap") or {}).get("land_color", palette["land"]))
    klass = _hex_to_rgb(color)
    strength = _relief_strength(cfg, palette)
    shaded = [
        (1.0 - strength) * lc + strength * (lc * tc / 255.0)
        for lc, tc in zip(land, tone, strict=True)
    ]
    out = [
        round((1.0 - fill_op) * bc + fill_op * (bc * kc / 255.0))
        for bc, kc in zip(shaded, klass, strict=True)
    ]
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in out)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """``"#bcd4ec"`` -> ``(188, 212, 236)``."""
    h = value.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


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
    sw = 15 * ts
    # 262 was a constant and the rows were drawn into it unmeasured, so a label
    # wider than the card simply drew past the card -- and, on a plate whose
    # card floats over a corner, past the plate. The floor stays 262, so every
    # key that fits today is untouched to the unit; a wider row now widens the
    # card instead of escaping it. Measured at the size the card actually draws
    # it (``row_fs`` in :func:`_legend_layer` is 12.5 * ts), which is the same
    # discipline :func:`_legend_band_dims` already applies to its columns.
    widest = max(text_width(r["label"], 12.5 * ts) for r in rows)
    panel_w = max(262 * ts, pad + sw + 10 * ts + widest + pad)
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
    # The widest row sets the column, measured at the size the band actually
    # draws it (``row_fs`` below is 12.0 * ts). Counting characters and
    # multiplying by a flat advance put "SPLM-N (al-Hilu)" and "Russian-
    # occupied (approx.)" in the same column as "RSF", which is how a label
    # ends up over its neighbour's swatch.
    col_w = sw + 10 * ts + max(text_width(r["label"], 12.0 * ts) for r in rows) + gutter
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
    if cfg.get("_panel"):  # the sheet keys all of its panels at once
        return '<g id="legend"></g>'
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
        f"{_legend_heading(cfg, rows)}</text>",
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
        # A class row is a button, and a button names what pressing it does.
        # ``role="button"`` on a <g> does not compute a name from the text
        # inside it the way a real <button> would, so the name is explicit.
        handle = (
            f' data-legend-category="{_esc(str(row["label"]))}" role="button" tabindex="0"'
            f' aria-label="Show only {_esc(str(row["label"]))}"'
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
        f'letter-spacing="1.2">{_legend_heading(cfg, rows)}</text>',
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
# Small multiples: the same plate, once per window of time                      #
# --------------------------------------------------------------------------- #


#: The windows a sheet can be cut into, finest first.
_SM_STEPS: tuple[str, ...] = ("day", "week", "month", "quarter", "year")

#: Three-letter month names, so a label does not depend on the host's locale.
_SM_MONTHS: tuple[str, ...] = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

#: How coarse each ``time_precision`` code is, phrased for a refusal message.
#:
#: The codes are :data:`_TIME_PRECISION`'s own: 1 a day, 2 a week, 3 a month,
#: 4 a year.
_SM_GRAIN: dict[int, str] = {1: "a day", 2: "a week", 3: "a month", 4: "a year"}

#: Past this many panels, refuse rather than emit a sheet nobody can read.
_SM_MAX_PANELS: int = 60

#: How wide one panel is, in SVG units, when the config does not say.
#:
#: The viewport's type scale floors at 1.0 (``ts = max(1.0, width / 1000)``),
#: so a panel narrower than this keeps full-size type on a shrinking plate and
#: the names start colliding. 420 is the width at which the bundled plates
#: still read.
_SM_PANEL_WIDTH: float = 420.0

#: Matches one embedded raster, so the sheet can draw the terrain once.
_SM_IMAGE_RE = re.compile(r'<image\b[^>]*href="data:image/[^"]*"[^>]*/>')

#: Matches an ``id="..."`` that is a whole attribute, not the tail of one.
#:
#: Without the lookbehind this also rewrites ``data-layer-id="relief"``, which
#: is a *value* the control panel matches on, not an identifier.
_SM_ID_RE = re.compile(r'(?<![\w-])id="([^"]+)"')


def _sm_date(raw: Any, where: str) -> date:
    """Return ``raw`` as a calendar date, or refuse it by name.

    Parameters
    ----------
    raw : any
        What the config put there.
    where : str
        The config path, e.g. ``events[12].date``, so a refusal names the row.

    Raises
    ------
    ValueError
        If ``raw`` is not an ISO date. A free-text date is refused rather
        than guessed at: "early 2024" belongs to no window, and picking one
        for it would invent exactly the thing a sheet of small multiples
        exists to show.
    """
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        raise ValueError(
            f"{where} is {raw!r}, which is not a date this sheet can bin. "
            "small_multiples needs ISO dates (YYYY-MM-DD). A mark dated in "
            "prose belongs to no window, and choosing one for it would invent "
            "the very thing the sheet is drawn to show."
        ) from None


def _sm_add_months(d: date, n: int) -> date:
    """Return the first of the month ``n`` months after ``d``'s month."""
    index = d.year * 12 + (d.month - 1) + n
    return date(index // 12, index % 12 + 1, 1)


def _sm_step_start(d: date, by: str) -> date:
    """Return the first day of the ``by`` window that contains ``d``."""
    if by == "year":
        return date(d.year, 1, 1)
    if by == "quarter":
        return date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
    if by == "month":
        return date(d.year, d.month, 1)
    if by == "week":
        # ISO weeks, so a sheet cut by week agrees with every calendar the
        # reader has; ``weekday()`` is 0 on Monday.
        return d - timedelta(days=d.weekday())
    return d


def _sm_step_next(start: date, by: str) -> date:
    """Return the first day of the window after the one beginning at ``start``."""
    if by == "year":
        return date(start.year + 1, 1, 1)
    if by == "quarter":
        return _sm_add_months(start, 3)
    if by == "month":
        return _sm_add_months(start, 1)
    if by == "week":
        return start + timedelta(days=7)
    return start + timedelta(days=1)


def _sm_window_label(start: date, by: str) -> str:
    """Return the heading one panel prints, e.g. ``"2023 Q2"``.

    Examples
    --------
    >>> _sm_window_label(date(2023, 4, 1), "quarter")
    '2023 Q2'
    >>> _sm_window_label(date(2023, 4, 1), "month")
    'Apr 2023'
    >>> _sm_window_label(date(2023, 4, 3), "week")
    'Week of 3 Apr 2023'
    """
    if by == "year":
        return str(start.year)
    if by == "quarter":
        return f"{start.year} Q{(start.month - 1) // 3 + 1}"
    if by == "month":
        return f"{_SM_MONTHS[start.month - 1]} {start.year}"
    if by == "week":
        return f"Week of {start.day} {_SM_MONTHS[start.month - 1]} {start.year}"
    return f"{start.day} {_SM_MONTHS[start.month - 1]} {start.year}"


def _sm_mark_span(d: date, precision: int) -> tuple[date, date]:
    """Return the first and last day a mark dated ``d`` at ``precision`` could mean.

    This is the whole of the honesty argument for a sheet of small multiples,
    and it is the time axis's version of the rule the marker symbology already
    applies to space. A dataset that says *month of March 2023* has not said
    which day; binning that row into a March panel is fine, and binning it
    into a *week* panel means choosing one of five weeks on the reader's
    behalf. So a mark is not a point in time here, it is the interval its own
    ``time_precision`` admits, and :func:`build_small_multiples` places it only
    where that whole interval fits inside one window.

    The codes are :data:`_TIME_PRECISION`'s. Code 2 reads "week of {date}",
    so its interval is the seven days beginning at the date given, not the
    calendar week containing it -- that is what the wording on the plate and
    in the tooltip has always claimed.
    """
    if precision <= 1:
        return d, d
    if precision == 2:
        return d, d + timedelta(days=6)
    if precision == 3:
        return date(d.year, d.month, 1), _sm_add_months(d, 1) - timedelta(days=1)
    return date(d.year, 1, 1), date(d.year, 12, 31)


def _sm_namespace(markup: str, suffix: str) -> str:
    """Return ``markup`` with every identifier it defines and uses made unique.

    Nine panels built from one config define the same ``plate-clip``,
    ``relief-clip`` and ``marker-shadow`` nine times. Duplicate identifiers are
    invalid, and what a renderer does with them -- first definition wins -- is
    a convention rather than a guarantee: every panel would be clipped by the
    first panel's clip path, which is right only for as long as the panels
    happen to be identical in size. Renaming per panel removes the question.
    """
    markup = _SM_ID_RE.sub(lambda m: f'id="{m.group(1)}-{suffix}"', markup)
    markup = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{m.group(1)}-{suffix})", markup)
    return re.sub(r'href="#([^"]+)"', lambda m: f'href="#{m.group(1)}-{suffix}"', markup)


def _sm_strip_root(svg: str) -> tuple[str, float, float]:
    """Return one panel's drawable content and the ``(width, height)`` it was drawn at."""
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if box is None:  # build_map always writes one; a missing one is a bug, not input
        raise ValueError("a panel came back without a viewBox")
    inner = svg[svg.index(">", svg.index("<svg")) + 1 : svg.rindex("</svg>")]
    # The root's own name and description go with the root: the sheet writes
    # its own, and nine copies of "Situation map of ..." in the accessibility
    # tree is nine things a screen-reader user has to walk past.
    inner = re.sub(r"<title id=\"sm-title\">.*?</title>", "", inner, flags=re.S)
    inner = re.sub(r"<desc id=\"sm-desc\">.*?</desc>", "", inner, flags=re.S)
    return inner, float(box.group(1)), float(box.group(2))


def build_small_multiples(cfg: dict[str, Any]) -> str:
    """Return one sheet holding the same plate drawn once per window of time.

    A situation plate is a snapshot, and most of what a researcher wants to
    say about a conflict is a change. The usual answers are an animation
    (which asks the reader to hold two frames in memory and compare them from
    memory) or one plate per window exported separately (which lets the
    extent, the projection and the symbol scale drift apart between frames,
    so the panels are no longer comparable and nothing on the page says so).
    A sheet built here cannot drift: every panel is built from **one** config,
    so the region, the projection, the basemap and the palette are the same
    object, and the marker radii were computed by the loader over the whole
    file before the split -- which is why the split happens here, on a loaded
    config, rather than by calling :func:`acled_events` once per window. Doing
    that would give each window its own largest value, and a disc in the 2016
    panel would mean something different from the same disc in 2017 with
    nothing on the page admitting it.

    Two things this does that a plate-per-window export cannot:

    **An empty window is still a panel.** A year with no events is evidence,
    and dropping it compresses the time axis so that the gap disappears and
    the remaining panels read as consecutive.

    **A mark is placed only where its own date precision allows.** See
    :func:`_sm_mark_span`: a row dated *month of March* is an interval, not a
    day, and it goes in a March panel but in no week panel. What cannot be
    placed is not drawn, and the sheet prints how many and why -- the same
    answer :mod:`_conflict` gives to a coordinate known only to the country.

    Parameters
    ----------
    cfg : dict
        A situation-map config carrying a ``small_multiples`` section:
        ``{by, from, to, columns, panel_width}``. ``by`` is one of
        :data:`_SM_STEPS`; the rest default from the data.

    Returns
    -------
    str
        A complete standalone SVG document.
    """
    sm = dict(cfg.get("small_multiples") or {})
    by = str(sm.get("by", "year")).lower()
    if by not in _SM_STEPS:
        raise ValueError(
            f"unknown small_multiples.by {by!r}; known: {', '.join(_SM_STEPS)}"
        )

    # ── which window, if any, holds each mark ──────────────────────────────
    layer_names = ("events", "forces")
    marks = [
        (name, i, it)
        for name in layer_names
        for i, it in enumerate(cfg.get(name) or [])
    ]
    spans: dict[tuple[str, int], tuple[date, date, int]] = {}
    withheld: dict[str, int] = {}
    for name, i, it in marks:
        if not it.get("date"):
            withheld["with no date"] = withheld.get("with no date", 0) + 1
            continue
        when = _sm_date(it["date"], f"{name}[{i}].date")
        code = _precision_of(it.get("time_precision"), _TIME_PRECISION, "time_precision")
        low, high = _sm_mark_span(when, code)
        spans[(name, i)] = (low, high, code)

    if sm.get("from"):
        first = _sm_date(sm["from"], "small_multiples.from")
    elif spans:
        first = min(low for low, _high, _code in spans.values())
    else:
        raise ValueError(
            "small_multiples has nothing to lay out: no mark on this plate "
            "carries a date, and no `from` was given. A sheet of time windows "
            "needs to know what time it is covering."
        )
    if sm.get("to"):
        last = _sm_date(sm["to"], "small_multiples.to")
    elif spans:
        last = max(high for _low, high, _code in spans.values())
    else:
        last = first
    if last < first:
        raise ValueError(
            f"small_multiples.to {last.isoformat()} is before .from {first.isoformat()}."
        )

    windows: list[tuple[date, date, str]] = []
    cursor = _sm_step_start(first, by)
    while cursor <= last:
        following = _sm_step_next(cursor, by)
        windows.append((cursor, following, _sm_window_label(cursor, by)))
        if len(windows) > _SM_MAX_PANELS:
            raise ValueError(
                f"small_multiples.by={by!r} over {first.isoformat()} to "
                f"{last.isoformat()} is more than {_SM_MAX_PANELS} panels. A sheet "
                "that large is not one anybody reads: choose a coarser `by`, or "
                "narrow the span with `from` and `to`."
            )
        cursor = following

    holds: dict[tuple[str, int], int] = {}
    for key, (low, high, code) in spans.items():
        for index, (start, stop, _label) in enumerate(windows):
            if low >= start and high < stop:
                holds[key] = index
                break
        else:
            if high < windows[0][0] or low >= windows[-1][1]:
                reason = "outside the span this sheet covers"
            else:
                reason = (
                    f"dated only to {_SM_GRAIN[code]}, which no single "
                    f"{by} panel contains"
                )
            withheld[reason] = withheld.get(reason, 0) + 1

    # ── one plate per window, all from the same config ─────────────────────
    # The terrain is the same raster in every panel, and it is also by far the
    # most expensive thing on the plate to compute and the largest thing in
    # the file (2.3 MB of the Himalaya plate's 2.4). Computed once, handed to
    # the rest through this dict, and -- because that makes the nine copies
    # byte-identical -- collapsed to one <use> below.
    cache: dict[str, Any] = {}
    panel_w = float(sm.get("panel_width", _SM_PANEL_WIDTH))
    base = {k: v for k, v in cfg.items() if k != "small_multiples"}
    inners: list[str] = []
    counts: list[int] = []
    cell_w = cell_h = 0.0
    for index in range(len(windows)):
        panel = dict(base)
        for name in layer_names:
            panel[name] = [
                it for (owner, i, it) in marks
                if owner == name and holds.get((owner, i)) == index
            ]
        counts.append(sum(len(panel[name]) for name in layer_names))
        panel["canvas_width"] = panel_w
        # A panel is a plate without its own chrome: the sheet draws the
        # title, the key, the ruler, the arrow and the credits once, because
        # nine identical rulers teach a reader nothing nine times.
        panel["title"] = ""
        panel.pop("subtitle", None)
        panel.pop("print_width", None)
        panel["caption"] = "none"
        # Explicit, not inherited: "right" grows the plate a legend column and
        # "below" grows it a band, and a panel whose legend is empty would get
        # the room anyway. "auto" resolves to "below" at a panel's width, so
        # leaving it unset is the same bug by a longer route.
        panel["legend_position"] = "bottom-right"
        panel["inset"] = {"show": False}
        panel["interactivity"] = "static"
        panel["frame"] = {**(cfg.get("frame") or {}), "margin": 6}
        panel["_panel"] = True
        panel["_relief_cache"] = cache
        inner, cell_w, cell_h = _sm_strip_root(build_map(panel))
        inners.append(_sm_namespace(inner, f"p{index}"))

    # One stylesheet, one raster, one page. Each panel still paints its own
    # plate card; what goes is the page behind it, which is the sheet's.
    for i in range(1, len(inners)):
        inners[i] = re.sub(r"<style>.*?</style>", "", inners[i], flags=re.S)
    for i, markup in enumerate(inners):
        inners[i] = re.sub(
            r'<rect width="[\d.]+" height="[\d.]+" fill="[^"]*"/>(?=<g transform="translate\()',
            "",
            markup,
            count=1,
        )
    raster = _SM_IMAGE_RE.search(inners[0])
    if raster is not None:
        once = raster.group(0)
        inners[0] = inners[0].replace(once, once.replace("<image ", '<image id="sm-relief" ', 1), 1)
        for i in range(1, len(inners)):
            # A no-op if the panels' rasters ever stop being identical, which
            # is the right failure: a sheet twice the size beats a sheet
            # showing one panel's terrain under every panel's marks.
            inners[i] = inners[i].replace(once, '<use href="#sm-relief"/>')

    return _sm_sheet(cfg, sm, windows, counts, withheld, inners, cell_w, cell_h, by, cache)


def _sm_sheet(
    cfg: dict[str, Any],
    sm: dict[str, Any],
    windows: list[tuple[date, date, str]],
    counts: list[int],
    withheld: dict[str, int],
    inners: list[str],
    cell_w: float,
    cell_h: float,
    by: str,
    cache: dict[str, Any],
) -> str:
    """Lay the finished panels out on one sheet, with the chrome drawn once."""
    plate = str((cfg.get("basemap") or {}).get("plate", "day")).lower()
    if plate not in _PLATES:
        raise ValueError(f"unknown plate {plate!r}; known: {sorted(_PLATES)}")
    # The terrain tone travels with the plate: a legend swatch is drawn as the
    # colour it will actually come out as once the relief has multiplied over
    # it, and the sheet's key has to be the key to the panels' ground.
    sheet = dict(cfg, _plate=_PLATES[plate], _relief_tone=cache.get("tone"))
    pal = _pal(sheet)
    frame = cfg.get("frame") or {}
    margin = float(frame.get("margin", 22))
    page_color = str(frame.get("page_color", pal["page"]))

    panel_count = len(windows)
    columns = int(sm.get("columns") or 0) or min(4, panel_count)
    columns = max(1, min(columns, panel_count))
    row_count = -(-panel_count // columns)
    gutter = 14.0
    grid_w = columns * cell_w + (columns - 1) * gutter
    width = grid_w + 2 * margin
    ts = max(1.0, width / 1000.0)
    label_h = 20.0 * ts

    chrome: list[str] = []
    cursor_y = margin
    title = cfg.get("title")
    subtitle = cfg.get("subtitle")
    if title:
        chrome.append(
            f'<text x="{margin:.1f}" y="{cursor_y + 22 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{22 * ts:.0f}" font-weight="700" fill="{pal["chrome_ink"]}">'
            f"{_esc(str(title))}</text>"
        )
        cursor_y += 30 * ts
    if subtitle:
        chrome.append(
            f'<text x="{margin:.1f}" y="{cursor_y + 12 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{12.5 * ts:.0f}" fill="{pal["chrome_sub"]}">'
            f"{_esc(str(subtitle))}</text>"
        )
        cursor_y += 20 * ts
    # The arrow is drawn whether or not the sheet is titled, and the header
    # band keeps a floor, so a bare sheet does not put north through the
    # first row's window headings.
    chrome.append(north_arrow(width - margin - 14 * ts, margin + 24 * ts, ts))
    grid_top = max(cursor_y + 10 * ts, margin + 40 * ts)

    cells: list[str] = []
    for index, markup in enumerate(inners):
        label = windows[index][2]
        drawn_here = counts[index]
        column, row = index % columns, index // columns
        x = margin + column * (cell_w + gutter)
        y = grid_top + row * (cell_h + label_h + gutter)
        tally = (
            "nothing drawn" if not drawn_here
            else f"{drawn_here:,} mark{'s' if drawn_here != 1 else ''}"
        )
        cells.append(
            # A panel is an object in the graphics tree and says which window
            # it is and how much is on it, so a reader who tabs into it is
            # not left to infer either from marks they cannot see.
            f'<g role="graphics-object" aria-label="{_esc(f"{label}: {tally}")}">'
            f'<text x="{x + 6 * ts:.1f}" y="{y + 13 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{12 * ts:.1f}" font-weight="700" fill="{pal["chrome_ink"]}">'
            f"{_esc(label)}</text>"
            f'<text x="{x + cell_w - 6 * ts:.1f}" y="{y + 13 * ts:.1f}" text-anchor="end" '
            f'font-family="{_DEFAULT_FONT}" font-size="{10 * ts:.1f}" '
            f'fill="{pal["chrome_faint"]}">{_esc(tally)}</text>'
            f'<g transform="translate({x:.1f},{y + label_h:.1f})">{markup}</g>'
            f"</g>"
        )
    foot_y = grid_top + row_count * (cell_h + label_h + gutter) - gutter

    # One ruler for the sheet, sized from a panel's own viewport -- every
    # panel has the same one, which is the point of the exercise.
    #
    # It is drawn in *panel* units and placed directly under the grid, aligned
    # with the left-hand column, rather than scaled up to the sheet's type and
    # dropped in the footer. The panels are placed on the sheet at 1:1, so a
    # bar drawn at the panel's scale is the only one whose length is a true
    # distance; enlarging it to match the footer's type would have made it
    # legible and wrong. It sits next to the maps it measures instead.
    bbox = validate_region(cfg.get("region"))
    pad = float(cfg.get("padding", 26))
    panel_vp = make_viewport(
        build_projection(bbox, cfg.get("projection", "auto")),
        bbox,
        float(sm.get("panel_width", _SM_PANEL_WIDTH)),
        pad,
        float(cfg.get("simplify", DEFAULT_TOLERANCE)),
        pad_top=pad,
    )
    foot_y += 20 * ts
    chrome.append(scale_bar(margin + 6.0, foot_y, panel_vp, pal["chrome_ink"]))
    foot_y += 30 * ts

    rows = _legend_rows(sheet, ts)
    if rows:
        band_h, *_rest = _legend_band_dims(sheet, ts, grid_w)
        chrome.append(
            f'<g transform="translate({margin:.1f},{foot_y:.1f})">'
            + _legend_band(sheet, {"width": grid_w, "height": 0.0, "ts": ts}, rows)
            + "</g>"
        )
        foot_y += band_h

    drawn = sum(counts)
    total = drawn + sum(withheld.values())
    lines = [
        f"{panel_count} panel{'s' if panel_count != 1 else ''}, one per {by}, "
        f"{windows[0][2]} to {windows[-1][2]}; {drawn:,} of {total:,} mark"
        f"{'s' if total != 1 else ''} drawn.",
        "Every panel is built from one config, so the extent, the projection and "
        "the symbol scale are shared; a window with nothing in it is still a panel.",
    ]
    if withheld:
        why = "; ".join(f"{n:,} {reason}" for reason, n in sorted(withheld.items()) if n)
        lines.append(f"Not placed: {why}.")
    if str(cfg.get("caption", "none")) == "full":
        for key in ("method", "source", "as_of"):
            if cfg.get(key):
                lines.append(f"{key.replace('_', ' ').title()}: {cfg[key]}")
    for line in lines:
        foot_y += 13 * ts
        chrome.append(
            f'<text x="{margin:.1f}" y="{foot_y:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{9.5 * ts:.1f}" fill="{pal["chrome_sub"]}">{_esc(line)}</text>'
        )

    height = foot_y + margin
    chrome.append(
        _attribution_layer(sheet, {"width": width, "height": height, "ts": ts}, bbox)
    )

    a11y_title = str(title or f"Situation map, {windows[0][2]} to {windows[-1][2]}")
    a11y_desc = " ".join(lines)
    size = f'width="{width:.1f}" height="{height:.1f}"'
    if cfg.get("print_width"):
        mm_w = parse_length_mm(cfg["print_width"])
        size = f'width="{mm_w:.4g}mm" height="{mm_w * height / width:.4g}mm"'
    hatch = (cfg.get("areas_of_control") or {}).get("hatch_color", "#b03a3a")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'{size} role="graphics-document" aria-labelledby="sm-title sm-desc">'
        f'<title id="sm-title">{_esc(a11y_title)}</title>'
        f'<desc id="sm-desc">{_esc(a11y_desc)}</desc>'
        f"{svg_defs(hatch, _plate_patterns(sheet))}"
        f'<rect width="{width:.1f}" height="{height:.1f}" fill="{page_color}"/>'
        f"{''.join(cells)}{''.join(chrome)}"
        f"</svg>"
    )
    if cfg.get("print_width"):
        _warn_if_unprintable(svg, parse_length_mm(cfg["print_width"]), width)
    return svg


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


#: Every key ``build_map`` reads. A situation plate is configured by a YAML
#: file with two dozen optional keys, hand-edited, and an unrecognised key is
#: simply never read -- so a one-letter slip silently drops a whole layer and
#: the plate still looks like a finished intelligence product. That is the
#: worst possible response to a typo, and it is why this list exists.
CONFIG_KEYS: frozenset[str] = frozenset({
    "admin2_borders", "annotations", "inset", "interactivity",
    "areas_of_control", "arrows", "as_of", "attribution", "basemap", "canvas_width",
    "lakes",
    "caption", "events", "forces", "frame", "front", "frontiers",
    "infrastructure", "internal_borders", "labels", "legend_footer",
    "legend_position", "marker_legend", "method", "padding", "projection",
    "cities", "region", "rivers", "simplify", "source", "subtitle", "title",
    "legend_title", "print_width", "small_multiples",
})

#: Keys the loaders set themselves; a caller never writes these.
_INTERNAL_KEYS: frozenset[str] = frozenset(
    {"_config_dir", "_panel", "_plate", "_relief_cache", "_relief_tone"}
)


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


#: Every key each nested section reads, so a typo one level down is refused
#: the way a typo at the top level already was.
#:
#: ``CONFIG_KEYS`` has always caught ``regoin``. It never caught
#: ``areas_of_control: {palett: ...}``, which is the same mistake in the
#: same file and just as silent -- the section is a plain dict and an
#: unread key in it simply does nothing. Two options added in 0.10.0
#: (``over_water``, ``depth_rings``) also reached no document for exactly
#: this reason: nothing enumerated them, so nothing could check them.
#:
#: Keeping the list here rather than deriving it means one obligation: a new
#: option has to be added in two places. That is the point. The second place
#: is what makes it documented and refusable, and
#: ``tests/test_config_schema_is_documented.py`` fails if the two drift.
SECTION_KEYS: dict[str, frozenset[str]] = {
    "admin2_borders": frozenset({"show", "color", "label_names", "label_min_area_frac"}),
    "areas_of_control": frozenset({
        "source", "category_field", "confidence_field", "palette", "contested",
        "fill_opacity", "casing_width", "blend", "over_water", "hatch_color",
    }),
    "basemap": frozenset({
        "relief", "relief_strength", "hypsometric", "plate", "sea_color",
        "land_color", "coast_color", "bathymetry",
    }),
    "cities": frozenset({"show", "size", "limit", "max_rank", "hand_placed_clearance"}),
    "frame": frozenset({"margin", "page_color", "radius"}),
    "front": frozenset({
        "line", "color", "label", "label_at", "label_dx", "label_dy",
        "legend", "legend_label",
    }),
    "frontiers": frozenset({
        "show", "color", "focus", "label_neighbours", "label_min_area_frac",
        "source", "as_of", "fields",
    }),
    "infrastructure": frozenset({"roads", "airports"}),
    "inset": frozenset({"show", "bbox", "position", "width", "zoom"}),
    "internal_borders": frozenset({"show", "color", "label_names", "label_min_area_frac"}),
    "labels": frozenset({"places", "waters", "water", "territories"}),
    "lakes": frozenset({
        "show", "color", "edge_color", "skip", "former", "historic", "always_label",
        "label_color", "label_min_area_frac", "depth_rings",
    }),
    "small_multiples": frozenset({"by", "from", "to", "columns", "panel_width"}),
    "rivers": frozenset({
        "show", "width", "color", "skip", "always_label", "label_color",
        "label_min_length_frac", "label_max_scalerank",
    }),
}


def _check_section(name: str, value: Any) -> None:
    """Refuse a nested section carrying a key this generator never reads.

    Same rule and same wording as :func:`validate_config` one level down,
    because the failure is identical: the key is simply not read, whatever
    it configures does nothing, and the plate still looks finished.

    Raises
    ------
    ValueError
        Naming the closest known key, since the realistic cause is a typo.
    """
    known = SECTION_KEYS.get(name)
    if known is None or not isinstance(value, dict):
        return
    unknown = sorted(set(value) - known)
    if not unknown:
        return
    hints = []
    for key in unknown:
        near = get_close_matches(key, sorted(known), n=1, cutoff=0.7)
        hints.append(f"{key!r}" + (f" (did you mean {near[0]!r}?)" if near else ""))
    raise ValueError(
        f"{name} has key(s) this generator never reads, so whatever they "
        f"configure would be silently dropped: {', '.join(hints)}. "
        f"Known {name} keys: {', '.join(sorted(known))}"
    )


#: Config options that name real features in a vendored dataset, and the
#: loader whose names they must appear in. Every one of these is a list of
#: proper nouns typed by hand, which is the single most typo-prone thing a
#: config here contains.
_NAME_LISTS: tuple[tuple[str, str, str], ...] = (
    ("lakes", "always_label", "lakes"),
    ("lakes", "skip", "lakes"),
    ("lakes", "former", "lakes"),
    ("lakes", "historic", "lakes"),
    ("rivers", "always_label", "rivers"),
    ("rivers", "skip", "rivers"),
)


def _known_feature_names(dataset: str) -> set[str]:
    """Return every name the vendored ``dataset`` carries, lowercased."""
    source = load_lakes() if dataset == "lakes" else load_rivers()
    return {str(name).lower() for _geom, name, *_ in source if name}


def _check_named_features(cfg: dict[str, Any]) -> None:
    """Refuse a water name that exists in no vendored dataset.

    This repository's stated rule is that a mistyped config key is refused
    rather than ignored. That was only ever enforced on *keys*. The values
    in ``lakes.always_label``, ``rivers.skip`` and their four siblings are
    proper nouns matched by exact lowercase string equality against Natural
    Earth, and a name that matched nothing did nothing, quietly.

    It is not a hypothetical. The Ukraine plate draws the Kakhovka
    Reservoir as *former* -- dashed, unfilled, because it drained in 2023 --
    purely on the strength of ``lakes.former: ["Kakhovka Reservoir"]``
    matching Natural Earth's spelling. Had that spelling drifted, the plate
    would have gone back to painting 2 150 km2 of water that is not there
    and said nothing about it. Two of these names were wrong in a config
    written for this very release ("Lake Neuchatel", "Aare") and the only
    reason anyone noticed is that someone looked at the picture.

    The check is deliberately against the **whole dataset**, not the plate's
    own bbox: naming a river that exists but lies outside this region is a
    perfectly reasonable thing for a config shared between plates, while
    naming one that exists nowhere is a typo every time.
    """
    problems: list[str] = []
    for section, option, dataset in _NAME_LISTS:
        wanted = (cfg.get(section) or {}).get(option)
        if not wanted:
            continue
        known = _known_feature_names(dataset)
        for name in wanted:
            if str(name).lower() in known:
                continue
            near = get_close_matches(str(name), sorted(known), n=1, cutoff=0.6)
            problems.append(
                f"{section}.{option}: {name!r} matches no {dataset[:-1]} in the "
                f"vendored data" + (f" (did you mean {near[0]!r}?)" if near else "")
            )
    if problems:
        raise ValueError(
            "situation map config names water that does not exist, so the "
            "option would be silently ignored: " + "; ".join(problems)
        )


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

    for section in SECTION_KEYS:
        if section in cfg:
            _check_section(section, cfg[section])

    _check_named_features(cfg)

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
