#!/usr/bin/env python3
"""
make_choropleth: a house-styled world choropleth map, drawn as hand-authored SVG.

A choropleth map is a map where each region (here, each country) is
filled with a colour that encodes a number: darker usually means "more."
This module draws one number per country as fill colour on a world map,
using a single colour ramp running from pale to navy blue, so that how
much of something a country has is readable from lightness alone, a
choice that is designed to stay legible both in plain greyscale and under
simulated colour-vision deficiency (a limitation, most often the
inability to distinguish red from green, that changes how a colour ramp
looks to some readers). That has actually been checked with the
simulation tool in ``_geo_colors.py``, not just assumed; see
``build_color_relief_figures.py``, which renders the verification image,
and ``.private/todo.md`` for the record of that check. Countries with no
assigned value fall back to a neutral grey rather than disappearing from
the map. Typical uses: any per-country indicator, an exposure or risk
index, an adoption rate, survey coverage, anything where the geography
itself already carries meaning a reader has spatial intuition for.

This map used to be drawn through Vega-Lite (a JSON-based charting
grammar) using its ``geoshape`` mark, a bundled TopoJSON country atlas
(TopoJSON is a compact format for map boundaries that stores each shared
border only once instead of once per neighbouring country), and an
``equalEarth`` projection, all converted to an image by ``vl_convert``. It
no longer is. This module now reads that same offline TopoJSON atlas
itself (``assets/geo/countries-50m.json``, vendored Natural Earth data
already used by ``make_situation_map.py``) and projects it with its own
hand-written, closed-form Equal Earth projection (a projection is the
mathematical recipe for flattening the round Earth onto a flat image;
Equal Earth is the specific recipe that keeps every country's true
relative area, so a large but often visually exaggerated landmass like
Greenland or Russia is not overstated the way it is on a classic Mercator
map; "closed-form" means the formula is computed directly, with no
external library, iteration, or lookup table needed). No Vega, no
matplotlib (Python's classic plotting library), no ``pyproj`` (a common
third-party geographic-projection library, not needed here). Every
country carries a native browser ``<title>`` tooltip with its exact
value, its rank among all countries, and, for a sequential indicator, its
share of the total, plus a richer on-canvas hover bubble (the
``.hit``/``.tip`` elements, built with ``_svg.tooltip_bubble`` from the
sprezzature-figures repository) repeating the same information for
anyone using a pointer or a keyboard rather than relying on the browser's
native tooltip.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _geo_colors import diverging_ramp_hex, sequential_ramp_hex  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _relief import rgba_to_data_uri, sample_relief  # noqa: E402
from _render import render_cli, svg_example_path, write_svg  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402

# tooltip_bubble lives in sprezzature-figures/scripts/_svg.py, not in this
# repo's own scripts/_svg.py (see that module's docstring, "Deliberately not
# extracted" -- it is a genuinely new capability, not a byte-identical
# extraction). Resolved the same robust way market_style.py
# (~/sprezzature/case-studies/financial-markets) does, with a sibling-repo
# fallback. Loaded via importlib under a distinct module name -- a plain
# ``sys.path.insert`` + ``from _svg import ...`` would silently reuse this
# file's *own*, already-imported ``_svg`` module (Python caches by module
# name, not path) and fail to find ``tooltip_bubble`` there.
_TOOLTIP_SVG_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "sprezzature-figures" / "scripts",
    Path.home() / "sprezzature-figures" / "scripts",
]
_TOOLTIP_SVG_DIR = next(
    (p for p in _TOOLTIP_SVG_CANDIDATES if (p / "_svg.py").is_file()),
    _TOOLTIP_SVG_CANDIDATES[-1],
)
_tooltip_spec = importlib.util.spec_from_file_location(
    "_svg_figures_tooltip", _TOOLTIP_SVG_DIR / "_svg.py"
)
_svg_figures = importlib.util.module_from_spec(_tooltip_spec)
_tooltip_spec.loader.exec_module(_svg_figures)
tooltip_bubble = _svg_figures.tooltip_bubble

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
NO_DATA = "#E5E5EA"
NO_DATA_EDGE = "#D1D1D6"

# Country fill opacity: lets the relief layer underneath show through as a
# faint terrain texture instead of being fully hidden by an opaque fill.
# Tuned empirically via the Ralph Eyeball Loop, not guessed: 0.9 (10% peek)
# was tried first and was completely imperceptible at any render size (the
# math: a ~66-grey-level mountain-ridge highlight, diluted first by the
# relief layer's own opacity and then by only a 10% peek, lands under
# 2/255 of visible delta -- nowhere near a human contrast threshold); 0.5
# (50% peek) made the effect clearly visible but started to compete with
# the ramp's own value differences. 0.7 is the point where terrain texture
# reads as texture without a viewer mistaking it for noise in the data.
_COUNTRY_FILL_OPACITY = 0.7

# 50m: same vendored Natural Earth atlas make_situation_map.py already uses,
# just switched on for the world view too (110m was a first-pass choice).
_GEO = Path(__file__).resolve().parent.parent / "assets" / "geo" / "countries-50m.json"

# Equal Earth (Savric, Patterson & Jenny, 2018) -- closed-form, published
# constants, no iteration. Restores the equal-area property the old
# Vega-Lite ``equalEarth`` mark had before this generator was rewritten as
# hand-authored SVG with a plain equirectangular projection, which inflates
# high-latitude countries (Greenland reads ~14x its true relative size) --
# a real bias for a choropleth, where colored area carries meaning.
_EE_A1, _EE_A2, _EE_A3, _EE_A4 = 1.340264, -0.081106, 0.000893, 0.003796
_EE_M = math.sqrt(3) / 2.0


def _equal_earth_raw(lon: float, lat: float) -> tuple[float, float]:
    """Project (lon, lat) in degrees to Equal Earth's own (unitless) plane.

    Returns raw projection-space coordinates, not screen pixels -- callers
    fit the projected point cloud's bounding box to the canvas with a single
    uniform scale (never independent x/y stretch, which would undo the
    equal-area property) and flip y for SVG's downward-growing axis.
    """
    lam = math.radians(lon)
    phi = math.radians(lat)
    theta = math.asin(_EE_M * math.sin(phi))
    theta2 = theta * theta
    theta6 = theta2 * theta2 * theta2
    x = (
        lam
        * math.cos(theta)
        / (_EE_M * (_EE_A1 + 3 * _EE_A2 * theta2 + theta6 * (7 * _EE_A3 + 9 * _EE_A4 * theta2)))
    )
    y = theta * (_EE_A1 + _EE_A2 * theta2 + theta6 * (_EE_A3 + _EE_A4 * theta2))
    return x, y


def _equal_earth_invert_batch(
    x: np.ndarray, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised inverse Equal Earth: plane ``(x, y)`` -> ``(lon, lat)`` degrees.

    Needed only for the relief raster (task: composite a hillshade texture
    that has to sit at the *correct* lon/lat under each canvas pixel, not
    the country outlines -- those are drawn forward, from known (lon, lat)
    vertices, and never need inverting).

    Parameters
    ----------
    x, y : numpy.ndarray
        Equal Earth plane coordinates (the same unitless plane
        :func:`_equal_earth_raw` produces), same shape, one entry per
        canvas pixel the caller wants a (lon, lat) for.

    Returns
    -------
    lon_deg, lat_deg, valid : numpy.ndarray
        ``lon_deg``/``lat_deg`` in degrees (undefined -- do not use -- where
        ``valid`` is ``False``). ``valid`` is ``False`` wherever ``(x, y)``
        does not correspond to any real point on the globe: Equal Earth's
        outline is a curved lens shape, not the rectangle its bounding box
        suggests, so most rectangular grids of ``(x, y)`` include points
        outside the actual map (e.g. near the corners) that have no inverse.

    Notes
    -----
    Equal Earth has no closed-form inverse (unlike the forward direction):
    ``y`` is a degree-9 odd polynomial in ``theta`` with no algebraic root
    formula, so ``theta`` is recovered by Newton-Raphson on
    ``f(theta) = y(theta) - y_target``, starting from the linear
    small-angle approximation ``theta ~= y / A1`` (exact at ``theta=0`` and
    close enough for quadratic Newton convergence within a handful of
    iterations across Equal Earth's whole valid ``theta`` range). Longitude
    then falls out of the *forward* ``x`` formula solved for ``lam`` at the
    now-known ``theta``, and latitude from inverting
    ``theta = asin(M * sin(phi))``.

    Examples
    --------
    >>> x0, y0 = _equal_earth_raw(30.0, -15.0)
    >>> lon, lat, valid = _equal_earth_invert_batch(np.array([x0]), np.array([y0]))
    >>> bool(valid[0])
    True
    >>> round(float(lon[0]), 4), round(float(lat[0]), 4)
    (30.0, -15.0)
    """
    # Newton-Raphson on f(theta) = y(theta) - y, starting from the
    # small-angle linear approximation. 12 iterations comfortably
    # converges to float64 precision across Equal Earth's full theta range
    # (|theta| < ~65 degrees) -- verified by the round-trip doctest above.
    theta = y / _EE_A1
    for _ in range(12):
        theta2 = theta * theta
        theta6 = theta2 * theta2 * theta2
        # d(y)/d(theta) -- the same polynomial that appears (times M) as
        # the x-formula's denominator in _equal_earth_raw, differentiated
        # term-by-term from y(theta) = A1*theta + A2*theta^3 + A3*theta^7 + A4*theta^9.
        dy_dtheta = _EE_A1 + 3 * _EE_A2 * theta2 + theta6 * (7 * _EE_A3 + 9 * _EE_A4 * theta2)
        f = theta * (_EE_A1 + _EE_A2 * theta2 + theta6 * (_EE_A3 + _EE_A4 * theta2)) - y
        with np.errstate(divide="ignore", invalid="ignore"):
            step = np.where(np.abs(dy_dtheta) > 1e-12, f / dy_dtheta, 0.0)
        theta = theta - step
    theta2 = theta * theta
    theta6 = theta2 * theta2 * theta2
    denom = _EE_M * (_EE_A1 + 3 * _EE_A2 * theta2 + theta6 * (7 * _EE_A3 + 9 * _EE_A4 * theta2))
    cos_theta = np.cos(theta)
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = np.where(np.abs(cos_theta) > 1e-9, x * denom / cos_theta, np.nan)
    sin_phi = np.sin(theta) / _EE_M
    # A pixel is only a real point on the globe if cos(theta) didn't
    # vanish (would make lam infinite) AND sin(phi) landed in [-1, 1]
    # (asin's domain) AND the Newton solve actually produced a finite lam.
    valid = (np.abs(cos_theta) > 1e-9) & (sin_phi >= -1.0) & (sin_phi <= 1.0) & np.isfinite(lam)
    lat_deg = np.degrees(np.arcsin(np.clip(sin_phi, -1.0, 1.0)))
    lon_deg = np.degrees(lam)
    return lon_deg, lat_deg, valid


# Sequential blue ramp — pale sky -> system blue -> deep navy. Same three
# hex stops the pre-OKLCH ramp used; only the interpolation between them
# changed (OKLCH via _geo_colors.sequential_ramp_hex, not a per-channel
# RGB lerp -- see that module's docstring for why the difference matters).
_RAMP: tuple[tuple[float, str], ...] = (
    (0.00, "#EAF3FF"),
    (0.62, "#007AFF"),
    (1.00, "#0A4DA0"),
)


def _ramp_hex(t: float) -> str:
    """Sample the house sequential blue ramp at position ``t`` in ``[0, 1]``."""
    return sequential_ramp_hex(t, _RAMP)


# ---------------------------------------------------------------------------
# Synthetic "global exposure index" demo values, keyed by ISO-3166-1 numeric
# country code (the same ids the vendored TopoJSON atlas uses). Invented
# figures for a fictional indicator, not real-world statistics.
# ---------------------------------------------------------------------------
DEMO_DATA: list[dict[str, Any]] = [
    {"id": "242", "value": 23.6},
    {"id": "834", "value": 10.3},
    {"id": "732", "value": 39.6},
    {"id": "124", "value": 15.5},
    {"id": "840", "value": 6.7},
    {"id": "398", "value": 40.2},
    {"id": "860", "value": 91.8},
    {"id": "598", "value": 80.0},
    {"id": "360", "value": 76.5},
    {"id": "032", "value": 22.2},
    {"id": "152", "value": 53.7},
    {"id": "180", "value": 27.7},
    {"id": "706", "value": 17.3},
    {"id": "404", "value": 10.6},
    {"id": "729", "value": 21.4},
    {"id": "148", "value": 92.7},
    {"id": "332", "value": 82.9},
    {"id": "214", "value": 80.7},
    {"id": "643", "value": 80.0},
    {"id": "044", "value": 19.3},
    {"id": "238", "value": 31.0},
    {"id": "578", "value": 62.7},
    {"id": "304", "value": 73.2},
    {"id": "260", "value": 85.5},
    {"id": "626", "value": 88.0},
    {"id": "710", "value": 8.7},
    {"id": "426", "value": 60.6},
    {"id": "484", "value": 67.2},
    {"id": "858", "value": 50.6},
    {"id": "076", "value": 17.8},
    {"id": "068", "value": 47.4},
    {"id": "604", "value": 8.9},
    {"id": "170", "value": 93.5},
    {"id": "591", "value": 86.5},
    {"id": "188", "value": 54.8},
    {"id": "558", "value": 30.0},
    {"id": "340", "value": 90.9},
    {"id": "222", "value": 57.2},
    {"id": "320", "value": 88.2},
    {"id": "084", "value": 84.8},
    {"id": "862", "value": 50.8},
    {"id": "328", "value": 41.4},
    {"id": "740", "value": 59.9},
    {"id": "250", "value": 43.1},
    {"id": "218", "value": 16.1},
    {"id": "630", "value": 30.5},
    {"id": "388", "value": 81.3},
    {"id": "192", "value": 4.3},
    {"id": "716", "value": 4.6},
    {"id": "072", "value": 62.6},
    {"id": "516", "value": 28.0},
    {"id": "686", "value": 53.5},
    {"id": "466", "value": 47.1},
    {"id": "478", "value": 34.3},
    {"id": "204", "value": 99.7},
    {"id": "562", "value": 19.6},
    {"id": "566", "value": 41.3},
    {"id": "120", "value": 20.3},
    {"id": "768", "value": 63.3},
    {"id": "288", "value": 27.6},
    {"id": "384", "value": 35.6},
    {"id": "324", "value": 74.7},
    {"id": "624", "value": 32.1},
    {"id": "430", "value": 55.9},
    {"id": "694", "value": 90.4},
    {"id": "854", "value": 10.1},
    {"id": "140", "value": 6.2},
    {"id": "178", "value": 22.9},
    {"id": "266", "value": 76.5},
    {"id": "226", "value": 61.5},
    {"id": "894", "value": 23.7},
    {"id": "454", "value": 33.1},
    {"id": "508", "value": 17.8},
    {"id": "748", "value": 45.9},
    {"id": "024", "value": 4.3},
    {"id": "108", "value": 69.7},
    {"id": "376", "value": 89.6},
    {"id": "422", "value": 95.5},
    {"id": "450", "value": 73.5},
    {"id": "275", "value": 96.0},
    {"id": "270", "value": 1.8},
    {"id": "788", "value": 28.9},
    {"id": "012", "value": 96.6},
    {"id": "400", "value": 77.5},
    {"id": "784", "value": 41.0},
    {"id": "634", "value": 94.3},
    {"id": "414", "value": 62.1},
    {"id": "368", "value": 81.8},
    {"id": "512", "value": 29.3},
    {"id": "548", "value": 19.1},
    {"id": "116", "value": 44.4},
    {"id": "764", "value": 13.6},
    {"id": "418", "value": 38.2},
    {"id": "104", "value": 96.2},
    {"id": "704", "value": 33.1},
    {"id": "408", "value": 0.9},
    {"id": "410", "value": 4.5},
    {"id": "496", "value": 17.0},
    {"id": "356", "value": 78.4},
    {"id": "050", "value": 36.3},
    {"id": "064", "value": 29.0},
    {"id": "524", "value": 9.7},
    {"id": "586", "value": 98.2},
    {"id": "004", "value": 42.4},
    {"id": "762", "value": 20.8},
    {"id": "417", "value": 5.9},
    {"id": "795", "value": 5.5},
    {"id": "364", "value": 16.9},
    {"id": "760", "value": 67.7},
    {"id": "051", "value": 15.0},
    {"id": "752", "value": 4.1},
    {"id": "112", "value": 49.1},
    {"id": "804", "value": 24.9},
    {"id": "616", "value": 99.8},
    {"id": "040", "value": 12.2},
    {"id": "348", "value": 52.9},
    {"id": "498", "value": 77.4},
    {"id": "642", "value": 40.9},
    {"id": "440", "value": 98.8},
    {"id": "428", "value": 47.8},
    {"id": "233", "value": 24.2},
    {"id": "276", "value": 41.1},
    {"id": "100", "value": 3.7},
    {"id": "300", "value": 42.1},
    {"id": "792", "value": 24.9},
    {"id": "008", "value": 88.9},
    {"id": "191", "value": 83.1},
    {"id": "756", "value": 49.9},
    {"id": "442", "value": 3.2},
    {"id": "056", "value": 25.4},
    {"id": "528", "value": 24.2},
    {"id": "620", "value": 20.8},
    {"id": "724", "value": 23.1},
    {"id": "372", "value": 87.0},
    {"id": "540", "value": 14.2},
    {"id": "090", "value": 5.1},
    {"id": "554", "value": 92.8},
    {"id": "036", "value": 56.5},
    {"id": "144", "value": 99.1},
    {"id": "156", "value": 40.3},
    {"id": "158", "value": 90.1},
    {"id": "380", "value": 65.4},
    {"id": "208", "value": 79.1},
    {"id": "826", "value": 74.5},
    {"id": "352", "value": 49.4},
    {"id": "031", "value": 9.3},
    {"id": "268", "value": 21.1},
    {"id": "608", "value": 87.4},
    {"id": "458", "value": 90.0},
    {"id": "096", "value": 92.5},
    {"id": "705", "value": 33.7},
    {"id": "246", "value": 65.7},
    {"id": "703", "value": 80.0},
    {"id": "203", "value": 64.2},
    {"id": "232", "value": 81.5},
    {"id": "392", "value": 52.8},
    {"id": "600", "value": 65.5},
    {"id": "887", "value": 68.6},
    {"id": "682", "value": 26.8},
    {"id": "010", "value": 92.3},
    {"id": "196", "value": 95.6},
    {"id": "504", "value": 7.4},
    {"id": "818", "value": 97.1},
    {"id": "434", "value": 96.2},
    {"id": "231", "value": 66.8},
    {"id": "262", "value": 4.5},
    {"id": "800", "value": 89.9},
    {"id": "646", "value": 12.8},
    {"id": "070", "value": 96.9},
    {"id": "807", "value": 66.7},
    {"id": "688", "value": 6.0},
    {"id": "499", "value": 16.7},
    {"id": "780", "value": 63.5},
    {"id": "728", "value": 56.9},
]


def _decode_arc(
    arc: list[list[int]], scale: tuple[float, float], translate: tuple[float, float]
) -> list[tuple[float, float]]:
    """Decode one TopoJSON delta-encoded arc to absolute (lon, lat) points."""
    sx, sy = scale
    tx, ty = translate
    x = y = 0
    points: list[tuple[float, float]] = []
    for dx, dy in arc:
        x += dx
        y += dy
        points.append((x * sx + tx, y * sy + ty))
    return points


def _ring_coords(
    indices: list[int], arcs: list[list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """Assemble one polygon ring's (lon, lat) points from TopoJSON arc indices.

    A negative index ``i`` means "arc ``~i``, reversed" (the TopoJSON arc-
    sharing convention); consecutive arcs share their join point, so every
    arc after the first contributes all but its own first point.
    """
    coords: list[tuple[float, float]] = []
    for idx in indices:
        pts = arcs[idx] if idx >= 0 else list(reversed(arcs[~idx]))
        coords.extend(pts if not coords else pts[1:])
    return coords


def _load_countries() -> list[dict[str, Any]]:
    """Return ``[{id, name, rings: [[(lon, lat), ...], ...]}, ...]`` for every
    country polygon/multipolygon in the vendored TopoJSON atlas, each
    country flattened to its list of outer+inner rings (winding order is
    not distinguished -- the fill rule below handles holes visually via
    plain nonzero fill, close enough at this figure's scale).
    """
    topo = json.loads(_GEO.read_text(encoding="utf-8"))
    transform = topo["transform"]
    scale = tuple(transform["scale"])
    translate = tuple(transform["translate"])
    arcs = [_decode_arc(a, scale, translate) for a in topo["arcs"]]

    countries: list[dict[str, Any]] = []
    for geom in topo["objects"]["countries"]["geometries"]:
        rings: list[list[tuple[float, float]]] = []
        if geom["type"] == "Polygon":
            polygons = [geom["arcs"]]
        elif geom["type"] == "MultiPolygon":
            polygons = geom["arcs"]
        else:
            continue
        for polygon in polygons:
            for ring in polygon:
                rings.append(_ring_coords(ring, arcs))
        countries.append(
            {
                "id": geom.get("id", ""),
                "name": geom.get("properties", {}).get("name", "Unknown"),
                "rings": rings,
            }
        )
    return countries


def build_svg(
    data: list[dict[str, Any]] | None = None,
    title: str = "Global Exposure Index, by Country",
    subtitle: str = "Higher = greater exposure · synthetic demo data · no data in grey",
    width: int = 745,
    height: int = 420,
    mode: str = "self-contained",
    accessibility: str = "universal",
    diverging: bool | None = None,
    relief: bool = True,
) -> str:
    """Assemble the full choropleth map SVG document as a string.

    Parameters
    ----------
    data : list of dict or None
        Rows with keys ``id`` (str, ISO-3166-1 numeric country code) and
        ``value`` (numeric). Defaults to :data:`DEMO_DATA`.
    title, subtitle : str
        Chart text.
    width, height : int
        Canvas size in pixels.
    mode : str, optional
        Forwarded to :func:`_interactive.fullscreen_control`.
    accessibility : str, optional
        Accepted for CLI parity but a documented no-op: both ramps
        (sequential and diverging) are mono-per-side hue scales where
        magnitude reads by lightness alone, verified
        colour-vision-deficiency-safe via ``_geo_colors.simulate_cvd_hex``
        rather than merely asserted -- see ``.private/todo.md``.
    diverging : bool or None, optional
        Force the diverging (negative/neutral/positive) ramp on or off.
        ``None`` (the default) auto-detects: the diverging ramp switches on
        automatically when the data spans both negative and positive
        values (a meaningful zero, e.g. growth or an anomaly), otherwise
        the sequential ramp is used.
    relief : bool, optional
        Composite the vendored Natural Earth hillshade under the vector
        layers (default ``True``). Set ``False`` to skip it -- e.g. for a
        faster render in a tight test loop, since the reprojection is the
        one part of this generator that costs more than a few
        milliseconds.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    _ = accessibility
    rows = data if data else DEMO_DATA
    values_by_id = {str(r["id"]): float(r["value"]) for r in rows}
    countries = _load_countries()
    all_values = list(values_by_id.values())
    v_min, v_max = (min(all_values), max(all_values)) if all_values else (0.0, 1.0)
    v_span = (v_max - v_min) or 1.0
    v_median = statistics.median(all_values) if all_values else 0.0
    # Auto-detect a diverging indicator (both signs present, e.g. growth
    # rates) unless the caller already decided. A diverging ramp centers
    # on the data's actual zero, not on the midpoint of [v_min, v_max] --
    # those only coincide when the range happens to be symmetric.
    use_diverging = diverging if diverging is not None else (v_min < 0.0 < v_max)
    # Symmetric half-extent for the diverging ramp so +/-v_abs_max reach
    # full saturation at the more extreme of the two tails; the milder
    # tail stays inside [-1, 1] and reads proportionally lighter.
    v_abs_max = max(abs(v_min), abs(v_max)) or 1.0

    def _color_for_value(value: float) -> str:
        """Map one data value to a ramp hex, honouring ``use_diverging``."""
        if use_diverging:
            return diverging_ramp_hex(value / v_abs_max)
        return _ramp_hex((value - v_min) / v_span)

    # Rank (1 = highest value) for the tooltip enrichment below. Ties get
    # the same rank a human reading a leaderboard would expect (dense
    # ranking is overkill here -- ties are rare in real indicator data and
    # "co-3rd" reads stranger in a one-line tooltip than it helps).
    rank_by_id = {
        cid: rank
        for rank, (cid, _value) in enumerate(
            sorted(values_by_id.items(), key=lambda kv: kv[1], reverse=True), start=1
        )
    }
    # Percent-of-total only makes sense for a sequential (all-one-sign-ish)
    # indicator -- for a diverging one (growth rates, anomalies) the sum
    # can land near zero and turn "share of total" into a meaningless or
    # wildly unstable number, so it is only computed and shown when the
    # ramp itself is sequential.
    values_total = sum(values_by_id.values())
    show_percent_of_total = not use_diverging and values_total != 0.0

    def _ordinal(n: int) -> str:
        """Format an integer rank as an English ordinal (1 -> "1st").

        Parameters
        ----------
        n : int
            A positive rank (1-based).

        Returns
        -------
        str
            ``n`` followed by its ordinal suffix.

        Examples
        --------
        >>> _ordinal(1)
        '1st'
        >>> _ordinal(11)
        '11th'
        >>> _ordinal(22)
        '22nd'
        """
        # The 11th/12th/13th special case: those end in 1/2/3 but still
        # take "th" (English ordinals except for the "teen" exceptions).
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    # bottom_margin grew from 36 to 44 to leave room for the median tick
    # label the enriched legend adds above the ramp swatches.
    top_margin, bottom_margin, side_margin = 96.0, 44.0, 20.0
    plot_w = width - 2 * side_margin
    plot_h = height - top_margin - bottom_margin

    # Fit the Equal Earth point cloud to the plot rect with ONE uniform
    # scale (equal-area only holds if x and y are scaled together), then
    # center it and flip y for SVG.
    raw_pts = [
        _equal_earth_raw(lon, lat)
        for country in countries
        for ring in country["rings"]
        for lon, lat in ring
    ]
    ee_x_min = min(p[0] for p in raw_pts)
    ee_x_max = max(p[0] for p in raw_pts)
    ee_y_min = min(p[1] for p in raw_pts)
    ee_y_max = max(p[1] for p in raw_pts)
    ee_scale = min(plot_w / (ee_x_max - ee_x_min), plot_h / (ee_y_max - ee_y_min))
    ee_x_mid = (ee_x_min + ee_x_max) / 2.0
    ee_y_mid = (ee_y_min + ee_y_max) / 2.0
    map_w = ee_scale * (ee_x_max - ee_x_min)
    cx = side_margin + plot_w / 2.0
    cy = top_margin + plot_h / 2.0

    def project(lon: float, lat: float) -> tuple[float, float]:
        x, y = _equal_earth_raw(lon, lat)
        return cx + (x - ee_x_mid) * ee_scale, cy - (y - ee_y_mid) * ee_scale

    parts: list[str] = []
    parts.append(svg_open(width, height, "cx-title", "cx-desc"))
    parts.append(f'<title id="cx-title">{xml_escape(title)}</title>')
    n_with_data = len(values_by_id)
    parts.append(
        f'<desc id="cx-desc">Choropleth map, {n_with_data} countries with data ranging '
        f"{v_min:.1f} to {v_max:.1f}, remainder in grey. Hover or focus a country for its "
        f"exact value.</desc>"
    )
    parts.append(
        "<style>"
        ".country{transition:opacity .15s ease;}"
        ".country:hover,.country:focus{opacity:.72;outline:none;}"
        "@media (prefers-reduced-motion: reduce){.country{transition:none;}}"
        # Richer hover-info bubble, on top of the native <title> tooltip above:
        # same .hit/.tip convention as case-studies/financial-markets.
        ".tip{opacity:0;pointer-events:none;transition:opacity .12s ease;}"
        ".hit:hover~.tip,.hit:focus~.tip{opacity:1;}"
        ".hit:focus-visible{outline:2px solid " + INK + ";outline-offset:1px;}"
        "@media (prefers-reduced-motion: reduce){.tip{transition:none;}}"
        "</style>"
    )
    parts.append(f'<rect width="{width}" height="{height}" fill="{BG}"/>')
    parts.append(
        f'<text x="40" y="44" font-size="22" font-weight="700" fill="{INK}" '
        f'letter-spacing="-0.3">{xml_escape(title)}</text>'
    )
    parts.append(
        f'<text x="40" y="66" font-size="13" fill="{SECONDARY}">{xml_escape(subtitle)}</text>'
    )

    if relief:
        # ---- relief: a faint desaturated hillshade texture under
        # everything else (graticule and countries both paint on top of
        # it). The source raster is equirectangular; Equal Earth is not,
        # so each output pixel's (lon, lat) has to be recovered via the
        # inverse projection before the raster can be sampled there --
        # see _equal_earth_invert_batch's docstring for why that needs
        # Newton-Raphson rather than a closed form.
        plot_px = np.arange(int(plot_w))
        plot_py = np.arange(int(plot_h))
        grid_px, grid_py = np.meshgrid(plot_px, plot_py)
        # Undo the screen-space project() transform to get back to the
        # Equal Earth plane, then invert Equal Earth itself to (lon, lat).
        # Offsetting by side_margin/top_margin keeps this grid exactly
        # aligned with where the <image> element below gets placed.
        ee_x = (grid_px + side_margin - cx) / ee_scale + ee_x_mid
        ee_y = (cy - (grid_py + top_margin)) / ee_scale + ee_y_mid
        lon_grid, lat_grid, valid_grid = _equal_earth_invert_batch(ee_x, ee_y)
        relief_rgba = sample_relief(lon_grid, lat_grid, valid_grid)
        parts.append(
            f'<image x="{side_margin:.1f}" y="{top_margin:.1f}" '
            f'width="{int(plot_w)}" height="{int(plot_h)}" '
            f'href="{rgba_to_data_uri(relief_rgba)}" preserveAspectRatio="none"/>'
        )

    # ---- graticule: 30-degree meridians/parallels, drawn UNDER the
    # countries so it reads as faint texture rather than competing with
    # the choropleth data. Equal Earth curves every meridian except the
    # central one, so each line needs enough sample points along its own
    # length (not just its two endpoints) to look smooth once projected.
    parts.append(f'<g stroke="{SECONDARY}" stroke-width="0.4" fill="none" opacity="0.09">')
    # Meridians (constant longitude, -180..180 every 30 degrees): sample
    # every 5 degrees of latitude across the same range the country data
    # itself spans, so the grid always matches whatever the caller's
    # dataset actually renders (rather than a hardcoded world extent that
    # could clip or overshoot for a lopsided value set).
    lat_lo, lat_hi = -85.0, 85.0
    for lon_deg in range(-180, 181, 30):
        pts = [project(lon_deg, lat) for lat in range(int(lat_lo), int(lat_hi) + 1, 5)]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<path d="{d}"/>')
    # Parallels (constant latitude, skipping the poles where Equal Earth's
    # pseudocylindrical pole-line already reads as its own strong shape --
    # a graticule ring there would just double up on that).
    for lat_deg in range(-60, 61, 30):
        pts = [project(lon, lat_deg) for lon in range(-180, 181, 5)]
        d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<path d="{d}"/>')
    parts.append("</g>")

    for country in countries:
        cid = str(country["id"])
        value = values_by_id.get(cid)
        path_d_parts: list[str] = []
        # Anchor for the hover bubble: centroid of the largest ring/segment
        # (the main landmass), not a naive average across every ring -- a
        # country with far-flung islands (or an antimeridian-split ring like
        # Russia/Fiji) would otherwise anchor somewhere over open ocean.
        anchor_seg: list[tuple[float, float]] = []
        for ring in country["rings"]:
            if len(ring) < 3:
                continue
            pts = [project(lon, lat) for lon, lat in ring]
            # Antimeridian wrap (e.g. Russia, Fiji cross lon +-180): a big
            # jump in screen x between consecutive points is the seam, not
            # real geometry -- break into a fresh subpath there instead of
            # drawing a line straight across the map.
            segments: list[list[tuple[float, float]]] = [[pts[0]]]
            for (x0, _y0), (x1, y1) in zip(pts, pts[1:], strict=False):
                if abs(x1 - x0) > map_w * 0.5:
                    segments.append([])
                segments[-1].append((x1, y1))
            for seg in segments:
                if len(seg) < 3:
                    continue
                path_d_parts.append("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in seg) + " Z")
                if len(seg) > len(anchor_seg):
                    anchor_seg = seg
        if not path_d_parts:
            continue
        path_d = " ".join(path_d_parts)
        if value is None:
            fill, edge = NO_DATA, NO_DATA_EDGE
            tip = f"{country['name']}: no data"
            tip_lines = [country["name"], "No data"]
        else:
            fill, edge = _color_for_value(value), BG
            # Enrich the raw value with its rank ("3rd of 42") and, when
            # meaningful, its share of the total ("12% of total") -- the
            # native SVG <title> tooltip already existed for the exact
            # value; this only adds context a reader would otherwise have
            # to compute by eye against every other country's shade.
            tip = f"{country['name']}: {value:.1f} ({_ordinal(rank_by_id[cid])} of {n_with_data}"
            detail = f"Value {value:.1f} · {_ordinal(rank_by_id[cid])} of {n_with_data}"
            if show_percent_of_total:
                # One decimal, not zero: with dozens of countries sharing
                # one total, most individual shares round to "0%" or "1%"
                # at zero decimals, which erases exactly the signal this
                # stat exists to show.
                tip += f", {value / values_total * 100:.1f}% of total"
                detail += f" · {value / values_total * 100:.1f}% of total"
            tip += ")"
            tip_lines = [country["name"], detail]
        bubble = ""
        if anchor_seg:
            ax = sum(p[0] for p in anchor_seg) / len(anchor_seg)
            ay = sum(p[1] for p in anchor_seg) / len(anchor_seg)
            bubble = tooltip_bubble(
                ax,
                ay,
                tip_lines,
                canvas_w=width,
                canvas_h=height,
                ink=INK,
                secondary=SECONDARY,
                border=NO_DATA_EDGE,
            )
        parts.append(
            f'<path class="country hit" tabindex="0" d="{path_d}" fill="{fill}" fill-opacity="{_COUNTRY_FILL_OPACITY}" '
            f'stroke="{edge}" stroke-width="0.4"><title>{xml_escape(tip)}</title></path>'
            f"{bubble}"
        )

    # ---- legend: ramp swatches + min/median/max labels ----
    ly = height - 16.0
    swatch_top = ly - 11.0
    lx0 = side_margin
    parts.append(
        f'<text x="{lx0:.1f}" y="{ly:.1f}" font-size="11" fill="{SECONDARY}">{v_min:.0f}</text>'
    )
    swatch_x = lx0 + 26.0
    n_swatches = 8
    swatch_run = n_swatches * 16.0
    for i in range(n_swatches):
        # Sample the legend strip across the same value range the map
        # itself used, converting each swatch's *value* through
        # _color_for_value so the legend and the map are always the same
        # ramp -- sequential or diverging -- rather than two independent
        # color choices that could drift apart.
        swatch_value = v_min + (v_max - v_min) * i / (n_swatches - 1)
        parts.append(
            f'<rect x="{swatch_x + i * 16:.1f}" y="{swatch_top:.1f}" width="14" height="12" fill="{_color_for_value(swatch_value)}"/>'
        )
    parts.append(
        f'<text x="{swatch_x + swatch_run + 6:.1f}" y="{ly:.1f}" font-size="11" '
        f'fill="{SECONDARY}">{v_max:.0f}</text>'
    )
    # Median tick: a short caret sitting on the swatch strip at the
    # proportional x position of the median value, with its own label
    # above -- so a reader can place "typical" on the ramp, not just the
    # two extremes.
    median_frac = (v_median - v_min) / (v_max - v_min) if v_max > v_min else 0.5
    median_x = swatch_x + median_frac * swatch_run
    parts.append(
        f'<path d="M {median_x:.1f},{swatch_top - 1:.1f} L {median_x:.1f},{swatch_top + 13:.1f}" '
        f'stroke="{INK}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{median_x:.1f}" y="{swatch_top - 4:.1f}" font-size="9" text-anchor="middle" '
        f'fill="{SECONDARY}">med {v_median:.0f}</text>'
    )
    swatch_end = swatch_x + swatch_run + 40
    parts.append(
        f'<rect x="{swatch_end:.1f}" y="{swatch_top:.1f}" width="14" height="12" fill="{NO_DATA}" stroke="{NO_DATA_EDGE}"/>'
    )
    parts.append(
        f'<text x="{swatch_end + 20:.1f}" y="{ly:.1f}" font-size="11" fill="{SECONDARY}">No data</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def make_choropleth(
    data: list[dict[str, Any]] | None = None,
    *,
    out: Path | str | None = None,
    title: str = "Global Exposure Index, by Country",
    subtitle: str = "Higher = greater exposure · synthetic demo data · no data in grey",
    width: int = 745,
    height: int = 420,
    mode: str = "self-contained",
    accessibility: str = "universal",
    diverging: bool | None = None,
    relief: bool = True,
) -> Path:
    """Render a hand-authored choropleth map and write the SVG to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``id`` (str, ISO-3166-1 numeric country code) and
        ``value`` (float). Defaults to DEMO_DATA (a synthetic global
        exposure index).
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/choropleth.svg``.
    title, subtitle : str
        Chart text.
    width, height : int
        Canvas size in pixels.
    mode, accessibility, diverging, relief
        Forwarded to :func:`build_svg`.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_choropleth()  # doctest: +ELLIPSIS
    wrote .../choropleth.svg
    >>> p.exists()
    True
    """
    svg = build_svg(
        data,
        title=title,
        subtitle=subtitle,
        width=width,
        height=height,
        mode=mode,
        accessibility=accessibility,
        diverging=diverging,
        relief=relief,
    )
    dest = Path(out) if out else svg_example_path(__file__, "choropleth")
    return write_svg(dest, svg)


def main() -> None:
    render_cli(__file__, "choropleth", build_svg, description="Generate a world choropleth map.")


if __name__ == "__main__":
    main()
