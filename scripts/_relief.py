"""
_relief — shared raster-relief sampling for the geo generators.

Module summary
--------------
Both ``make_choropleth.py`` (Equal Earth, world scale) and, eventually,
``make_situation_map.py`` (Lambert Conformal Conic, regional scale) want the
same thing under their vector layers: a faint, desaturated hillshade texture
that reads as "this is a real planet with terrain" without competing with
the actual data on top of it. The vendored source
(``assets/geo/relief-lowres.png``, a 1440x720 greyscale PNG downsampled from
Natural Earth's public-domain 1:50m "Gray Earth" shaded relief) is a plain
equirectangular grid: pixel column/row map linearly to longitude/latitude.
Neither Equal Earth nor Lambert Conformal Conic is equirectangular, so the
raster has to be *reprojected* -- resampled at the (lon, lat) each output
pixel's projection actually corresponds to -- rather than just stretched
onto the canvas.

The projection-specific half of that (turning a canvas pixel into a
(lon, lat) pair, which requires inverting whichever projection a generator
uses) stays in that generator's own module. This module owns the
projection-*agnostic* half: given arrays of (lon, lat) already computed by
the caller, bilinearly sample the source raster and retint it through a
warm/cool duotone (shadow -> cool blue-slate, ridge highlight -> warm
sand-gold, interpolated in OKLCH via ``_geo_colors`` for the same
perceptual-uniformity reason that module's ramps use it) rather than
literal greyscale -- a classic relief-shading convention (Eduard Imhof's
"warm highlights, cool shadows") that reads as considerably more alive
than flat grey at the low opacity this composites at. Packed into an RGBA
array ready to embed as a base64 PNG ``<image>`` in the SVG.

Usage example
-------------
>>> import numpy as np
>>> lon = np.array([[0.0, 90.0]])
>>> lat = np.array([[0.0, 45.0]])
>>> valid = np.array([[True, True]])
>>> rgba = sample_relief(lon, lat, valid)
>>> rgba.shape
(1, 2, 4)

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _geo_colors import sequential_ramp_hex  # noqa: E402
from PIL import Image

#: Vendored Natural Earth "Gray Earth" shaded relief, downsampled to
#: 1440x720 (0.25 degree/pixel) from the original 1:50m 10800x5400 source --
#: see ``.private/todo.md`` for the exact acquisition command. Equirectangular:
#: column 0..1439 spans longitude -180..180, row 0..719 spans latitude 90..-90.
RELIEF_PNG: Path = Path(__file__).resolve().parent.parent / "assets" / "geo" / "relief-lowres.png"

#: Default opacity for the composited relief layer, as rendered directly
#: over the background (i.e. in ocean / no-data areas with no country fill
#: on top). Raised from an initial 0.30 after a Ralph Eyeball pass: at 0.30
#: combined with the ~10% peek-through choropleth country fills allow (see
#: make_choropleth.py's ``fill-opacity``), the mountain-ridge highlights
#: that give hillshade its whole visual point (up to ~66 grey levels above
#: the flat-terrain baseline in the vendored raster) came out under a
#: perceptible threshold once diluted twice -- the map "exported
#: successfully" but the relief did not actually read. 0.55 keeps the ocean
#: reading as a pale tint (never competing with the data on top) while
#: giving mountain highlights enough contrast to survive the country
#: fill's own peek-through dilution.
DEFAULT_RELIEF_OPACITY: float = 0.55

# Warm/cool duotone stops the raw 0-255 shade value maps through, instead of
# literal grey. Low values (shadowed valleys, low ground) tint cool
# blue-slate; high values (sunlit ridgelines, peaks) tint warm sand-gold; a
# muted warm-grey sits at the midpoint so mid-elevation terrain doesn't
# swing hard to either extreme. This is Eduard Imhof's "warm light, cool
# shadow" relief-shading convention, not an arbitrary palette choice.
#
# The endpoints need real *lightness* range, not just a hue shift -- a
# first attempt held both endpoints close to the same mid-lightness and the
# result read flatter than the plain-greyscale version it replaced (caught
# by comparing renders side by side): the greyscale highlight was near-white
# (~242/255), so a duotone highlight only as bright as a muted gold lost
# most of that contrast. The highlight below is a genuinely bright, pale
# cream; the shadow is a real dark slate, not just a desaturated mid-tone.
_DUOTONE_STOPS: tuple[tuple[float, str], ...] = (
    (0.00, "#4C6478"),
    (0.50, "#B3A98E"),
    (1.00, "#F2E7C8"),
)

# The raw source's actual data rarely uses its own full 0-255 range: flat
# open ocean sits at a fixed ~146 baseline and even dramatic terrain (the
# Himalaya, sampled directly from the vendored raster) only reaches
# roughly 90-245 -- most single-region crops (e.g. Western Europe) occupy
# an even narrower band inside that. Feeding raw shade values straight into
# the duotone LUT wastes most of the LUT's contrast on values the data
# never hits (caught by comparing a Western-Europe render against the
# pre-duotone plain-greyscale version: the duotone read visibly *flatter*,
# not richer, because 122..199 -- Western Europe's actual range -- only
# spans the LUT's muted middle third). Stretching the measured working
# range to the LUT's full domain first restores (and, via the OKLCH
# interpolation, improves on) the contrast the plain-greyscale version had.
_SHADE_STRETCH_LOW: float = 90.0
_SHADE_STRETCH_HIGH: float = 245.0

# Cached decoded source raster: the PNG is read once per process, not once
# per render call, since a caller (a batch export, or the test suite) may
# render many maps in one run.
_relief_array_cache: Optional[np.ndarray] = None

# Cached 256-entry duotone lookup table: (256, 3) uint8, index = the 0-255
# shade value, columns = (R, G, B). Built once via _geo_colors'
# OKLCH-interpolated sequential_ramp_hex (256 calls -- cheap, done at most
# once per process) rather than a naive per-channel lerp, for the same
# perceptual-uniformity reason every other ramp in this stack uses OKLCH:
# a straight RGB lerp between a saturated blue and a saturated gold would
# pass through a visibly muddy, desaturated grey-brown at the midpoint.
# Then applied to a whole image via one numpy fancy-index (lut[shade]) --
# no per-pixel Python loop.
_duotone_lut_cache: Optional[np.ndarray] = None


def _duotone_lut() -> np.ndarray:
    """Build (and cache) the 256-entry warm/cool duotone lookup table.

    Returns
    -------
    numpy.ndarray
        Shape ``(256, 3)``, dtype ``uint8``. Row ``i`` is the ``(R, G, B)``
        this LUT maps shade value ``i`` to.

    Examples
    --------
    >>> lut = _duotone_lut()
    >>> lut.shape
    (256, 3)
    >>> tuple(int(c) for c in lut[0])
    (76, 100, 120)
    """
    global _duotone_lut_cache
    if _duotone_lut_cache is None:
        lut = np.zeros((256, 3), dtype=np.uint8)
        for shade in range(256):
            hex_color = sequential_ramp_hex(shade / 255.0, _DUOTONE_STOPS)
            lut[shade] = (
                int(hex_color[1:3], 16),
                int(hex_color[3:5], 16),
                int(hex_color[5:7], 16),
            )
        _duotone_lut_cache = lut
    return _duotone_lut_cache


def load_relief_grayscale() -> np.ndarray:
    """Load (and cache) the vendored relief raster as a 2-D uint8 array.

    Returns
    -------
    numpy.ndarray
        Shape ``(720, 1440)``, dtype ``uint8``. Row 0 is the north edge
        (latitude +90), column 0 is the west edge (longitude -180) -- the
        same row/column convention every equirectangular raster in this
        module's docstrings assumes.

    Examples
    --------
    >>> arr = load_relief_grayscale()
    >>> arr.shape
    (720, 1440)
    >>> arr.dtype
    dtype('uint8')
    """
    global _relief_array_cache
    if _relief_array_cache is None:
        with Image.open(RELIEF_PNG) as img:
            # Force 8-bit greyscale ("L") even though the vendored file is
            # already that mode -- an explicit convert() means this function
            # keeps its documented dtype/shape contract even if the PNG were
            # ever swapped for a differently-encoded source.
            _relief_array_cache = np.array(img.convert("L"), dtype=np.uint8)
    return _relief_array_cache


def sample_relief(
    lon_deg: np.ndarray,
    lat_deg: np.ndarray,
    valid: np.ndarray,
    *,
    opacity: float = DEFAULT_RELIEF_OPACITY,
) -> np.ndarray:
    """Bilinearly sample the relief raster at arbitrary (lon, lat).

    Parameters
    ----------
    lon_deg, lat_deg : numpy.ndarray
        Longitude/latitude in degrees, same shape, for every output pixel.
        Values are expected in ``[-180, 180]`` / ``[-90, 90]`` but are
        clamped defensively -- a caller's inverse-projection math landing a
        hair outside that range by floating-point error should not raise.
    valid : numpy.ndarray of bool
        Same shape as ``lon_deg``. ``False`` marks a pixel with no real
        (lon, lat) -- e.g. outside a pseudocylindrical projection's curved
        outline, inside the canvas's rectangular bounding box but off the
        actual map -- which must come out fully transparent rather than
        showing a nonsense sample from wherever the un-clamped math landed.
    opacity : float, optional
        Alpha (as a fraction of 255) applied to every *valid* pixel
        (default :data:`DEFAULT_RELIEF_OPACITY`). Invalid pixels are always
        alpha 0 regardless of this value.

    Returns
    -------
    numpy.ndarray
        RGBA, ``uint8``, shape ``lon_deg.shape + (4,)``. R/G/B carry the
        shade value retinted through the warm/cool duotone (see
        :data:`_DUOTONE_STOPS`), not the source's raw greyscale; A carries
        ``opacity`` where ``valid`` else 0.

    Notes
    -----
    This was nearest-neighbour in an earlier version, on the reasoning that
    the 1440x720 source is "already coarse enough that bilinear would not
    be visibly different." That held for `make_choropleth.py`'s world-scale
    view (each source pixel maps to well under one screen pixel there) but
    was wrong for `make_situation_map.py` zoomed into a single country:
    there, one 0.25-degree source pixel can cover dozens of screen pixels,
    and nearest-neighbour made that visible as a flagrant grid of flat
    blocks (caught via the Ralph Eyeball Loop on a France-only render).
    Bilinear costs four lookups instead of one -- negligible next to the
    projection math already run over the same grid -- and removes the
    blockiness at any zoom level.

    Examples
    --------
    >>> import numpy as np
    >>> lon = np.array([[-180.0, 180.0]])
    >>> lat = np.array([[90.0, -90.0]])
    >>> valid = np.array([[True, False]])
    >>> rgba = sample_relief(lon, lat, valid)
    >>> rgba[0, 1, 3]
    np.uint8(0)
    """
    # Work in float32: bilinear weights need fractional pixel positions,
    # and averaging four uint8 source samples in floating point avoids
    # 8-bit integer overflow/rounding drift before the final cast back.
    relief = load_relief_grayscale().astype(np.float32)
    height, width = relief.shape
    # Continuous (fractional) pixel coordinates, pixel-CENTER convention
    # (the "-0.5"): column/row index k's centre sits at longitude/latitude
    # k+0.5 pixels from the west/north edge, matching the vendored PNG's
    # own georeferencing (its .tfw-equivalent origin is half a pixel in
    # from -180/+90, not exactly on it).
    col_f = np.clip((lon_deg + 180.0) / 360.0 * width - 0.5, 0.0, width - 1.0)
    row_f = np.clip((90.0 - lat_deg) / 180.0 * height - 0.5, 0.0, height - 1.0)
    col0 = np.floor(col_f).astype(np.int64)
    row0 = np.floor(row_f).astype(np.int64)
    # The "+1" neighbour, clamped rather than wrapped at the antimeridian --
    # both this repo's callers sample a bounded region (a world view whose
    # edge is mid-ocean, or a regional LCC plate), never a seam exactly at
    # +/-180 degrees, so edge-clamping is simpler than date-line wraparound
    # for a difference that would land on open ocean either way.
    col1 = np.clip(col0 + 1, 0, width - 1)
    row1 = np.clip(row0 + 1, 0, height - 1)
    frac_col = col_f - col0
    frac_row = row_f - row0
    top = relief[row0, col0] * (1.0 - frac_col) + relief[row0, col1] * frac_col
    bottom = relief[row1, col0] * (1.0 - frac_col) + relief[row1, col1] * frac_col
    shade = top * (1.0 - frac_row) + bottom * frac_row
    # Contrast-stretch the measured working range to the LUT's full 0-255
    # domain before lookup -- see _SHADE_STRETCH_LOW/_HIGH's comment for why
    # skipping this step made real renders look flatter, not richer.
    stretched = np.clip(
        (shade - _SHADE_STRETCH_LOW) / (_SHADE_STRETCH_HIGH - _SHADE_STRETCH_LOW) * 255.0,
        0.0, 255.0,
    ).astype(np.uint8)
    alpha = np.where(valid, round(opacity * 255), 0).astype(np.uint8)
    # One fancy-index lookup retints the whole grid through the warm/cool
    # duotone at once -- lut[stretched] has shape (..., 3), same leading
    # shape as `stretched` itself with an extra trailing RGB axis.
    rgb = _duotone_lut()[stretched]
    rgba = np.concatenate([rgb, alpha[..., np.newaxis]], axis=-1).astype(np.uint8)
    return rgba


def rgba_to_data_uri(rgba: np.ndarray) -> str:
    """Encode an RGBA array as a base64 ``data:image/png`` URI.

    Parameters
    ----------
    rgba : numpy.ndarray
        Shape ``(height, width, 4)``, dtype ``uint8``.

    Returns
    -------
    str
        A ``data:image/png;base64,...`` string usable directly as an SVG
        ``<image>`` element's ``href``, keeping the output self-contained
        (no external file reference, consistent with every other asset this
        stack embeds -- fonts included -- for a standalone SVG).

    Examples
    --------
    >>> import numpy as np
    >>> tiny = np.zeros((1, 1, 4), dtype=np.uint8)
    >>> rgba_to_data_uri(tiny).startswith("data:image/png;base64,")
    True
    """
    buffer = io.BytesIO()
    # Image.fromarray infers RGBA from the array's own (H, W, 4) uint8
    # shape/dtype -- no explicit mode= needed (and Pillow >=13 deprecates
    # passing one anyway).
    Image.fromarray(rgba).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


# ---------------------------------------------------------------------------
# Elevation-based terrain shading (regional generators only -- see
# terrain_shade_for_bbox's docstring for why this is a separate path from
# sample_relief above rather than a replacement for it).
#
# Source: GMTED2010 (USGS/NGA, public domain), the 30 arc-second "mean"
# statistic global grid (~925m/px at the equator), converted once at
# vendoring time with ``rasterio`` (a build-time-only tool, not a runtime
# dependency, same status as ``npx mapshaper`` for the TopoJSON borders) --
# full native resolution for the finest tier, not downsampled from
# anything coarser. Stored as 16-bit greyscale PNG (elevation in metres +
# 1000, so the Dead Sea's -412m still fits an unsigned range) -- plain
# Pillow reads these, no GDAL/rasterio needed at render time.
#
# Loading the full 237MB tier for every render -- including a whole-continent
# situation_map where individual river valleys are sub-pixel anyway -- wastes
# real time and memory for detail the output can't show. So this ships as a
# *pyramid*, mipmap-style: five more tiers, each a 2x2 block-average of the
# tier above it (not a fresh downsample from the 30 arc-second source each
# time, so the levels stay mutually consistent), down to 16 arc-minute
# (~0.4MB). :func:`select_elevation_tier` picks the coarsest tier that still
# comfortably covers the requested render's actual angular resolution --
# the same "why load 10m borders for a whole-continent view" reasoning
# ``make_situation_map.py``'s ``_land_topojson_for_bbox`` already applies to
# vector borders, now applied to the elevation raster too.
# ---------------------------------------------------------------------------

#: Elevation pyramid tiers, finest first: ``(resolution_arcsec, path)``.
#: Resolution in arc-seconds is what a tier's own pixel spacing represents,
#: not a claim about the underlying terrain's true accuracy (GMTED2010's
#: "mean" statistic already smooths within each 30 arc-second cell).
_ELEVATION_TIERS: tuple[tuple[float, Path], ...] = tuple(
    (arcsec, Path(__file__).resolve().parent.parent / "assets" / "geo" / f"elevation-{name}.png")
    for arcsec, name in (
        (30.0, "30arcsec"),
        (60.0, "1arcmin"),
        (120.0, "2arcmin"),
        (240.0, "4arcmin"),
        (480.0, "8arcmin"),
        (960.0, "16arcmin"),
    )
)

#: The finest tier -- kept as a standalone name for callers that always want
#: maximum detail regardless of render size (e.g. a future choropleth-style
#: consumer), and as the pyramid's implicit "top" for path resolution.
ELEVATION_PNG: Path = _ELEVATION_TIERS[0][1]

#: The vendored grid's actual bounds (GMTED2010 excludes the deepest Antarctic
#: interior rather than covering a full -90..90) and the +1000m offset baked
#: into its pixel values (undone on load). Identical across every pyramid
#: tier -- each level covers the same geographic extent, just coarser.
_ELEVATION_BOUNDS = {"west": -180.0, "east": 180.0, "south": -90.0, "north": 84.0}
_ELEVATION_OFFSET_M = 1000.0

#: Per-tier decoded array cache, keyed by path -- a render that needs the
#: coarse tier today and the fine tier tomorrow (different regions/sizes in
#: the same process) shouldn't evict and re-decode either one.
_elevation_array_cache: dict[Path, np.ndarray] = {}


def select_elevation_tier(
    west: float,
    south: float,
    east: float,
    north: float,
    plot_w_px: float,
    plot_h_px: float,
    *,
    oversample: float = 2.0,
) -> Path:
    """Pick the coarsest vendored elevation tier still fine enough for a render.

    Parameters
    ----------
    west, south, east, north : float
        The region being rendered, in degrees.
    plot_w_px, plot_h_px : float
        The output canvas's plot-area size in pixels (i.e. the region's
        actual rendered footprint, not the whole SVG including margins).
    oversample : float, optional
        How many source pixels per output pixel to require along the more
        demanding axis (default 2.0 -- calibrated against the Iberia/
        Switzerland/Western-Europe renders used to validate this whole
        relief system: at oversample=2, both Iberia and Switzerland's
        actual bboxes still resolve to the finest 30 arc-second tier
        (matching what visual comparison against the editorial reference
        cartography this project targets showed was needed), while
        Western Europe's much larger
        bbox comfortably drops to 1 arc-minute with no visible loss at
        that scale).

    Returns
    -------
    pathlib.Path
        The chosen tier's vendored PNG path.

    Notes
    -----
    This is a mipmap-style selection, same idea as texture mipmapping in
    graphics: compute the render's angular resolution (degrees of the
    region per output pixel, taking the *more demanding* of the two axes
    so neither is under-resolved), then pick the coarsest available tier
    whose own pixel spacing is still at least ``oversample`` times finer
    than that. Texture shading specifically benefits from oversampling
    beyond a literal 1:1 pixel match (unlike a simple hillshade) because
    it draws out fractal structure below the output's own pixel size that
    then anti-aliases into the final bilinear resample -- a tier that just
    barely matches output resolution measurably softens the result (this
    is exactly what went wrong with this system's first version, which
    shipped a single fixed 2.5 arc-minute tier).

    Examples
    --------
    >>> select_elevation_tier(-9.6, 35.9, 3.4, 43.9, 950, 730).name
    'elevation-30arcsec.png'
    >>> select_elevation_tier(-11.0, 35.0, 30.0, 60.0, 948, 577).name
    'elevation-1arcmin.png'
    """
    lon_deg_per_px = (east - west) / max(plot_w_px, 1.0)
    lat_deg_per_px = (north - south) / max(plot_h_px, 1.0)
    # The more demanding axis is the one with *fewer* degrees per pixel
    # (more angular detail packed into each pixel) -- that is the binding
    # constraint neither axis may be under-resolved against.
    output_deg_per_px = min(lon_deg_per_px, lat_deg_per_px)
    budget_deg_per_px = output_deg_per_px / oversample

    # Tiers are ordered finest-first; walk coarsening and keep the last one
    # that still fits the budget. Falls back to the finest tier (index 0)
    # when even that isn't fine enough for tiny regions -- the correct
    # behaviour is "give me the best available", not "give up".
    chosen = _ELEVATION_TIERS[0][1]
    for tier_arcsec, tier_path in _ELEVATION_TIERS:
        tier_deg_per_px = tier_arcsec / 3600.0
        if tier_deg_per_px <= budget_deg_per_px:
            chosen = tier_path
        else:
            break
    return chosen


def load_elevation(path: Path = ELEVATION_PNG) -> np.ndarray:
    """Load (and cache) one vendored elevation tier as a float32 array, in metres.

    Parameters
    ----------
    path : pathlib.Path, optional
        Which pyramid tier to load (default: the finest, :data:`ELEVATION_PNG`).
        Pass the result of :func:`select_elevation_tier` to load whichever
        tier actually matches a given render.

    Returns
    -------
    numpy.ndarray
        2-D float32, one row per tier-pixel of latitude (north edge first)
        by one column per tier-pixel of longitude (west edge first) across
        :data:`_ELEVATION_BOUNDS`. Real elevation in metres (the vendored
        file's +1000m storage offset is undone here, so callers never see
        it).

    Examples
    --------
    >>> arr = load_elevation()
    >>> arr.dtype
    dtype('float32')
    """
    if path not in _elevation_array_cache:
        # The finest tier is 902M pixels, well past Pillow's default
        # "decompression bomb" ceiling (~179M) -- a sane default against
        # untrusted uploads, but this is our own vendored, version-controlled
        # asset, not user input, so raising the ceiling for this one
        # open() is the correct call rather than disabling the check
        # globally for the whole process.
        previous_limit = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = None
        try:
            with Image.open(path) as img:
                raw = np.array(img, dtype=np.float32)
        finally:
            Image.MAX_IMAGE_PIXELS = previous_limit
        _elevation_array_cache[path] = raw - _ELEVATION_OFFSET_M
    return _elevation_array_cache[path]


def _elevation_window(
    west: float, south: float, east: float, north: float, *, path: Path = ELEVATION_PNG
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Crop one vendored elevation tier to a padded bbox.

    Parameters
    ----------
    west, south, east, north : float
        The region of interest, in degrees.
    path : pathlib.Path, optional
        Which pyramid tier to crop from (default: the finest). Pass
        :func:`select_elevation_tier`'s result to use whichever tier
        actually matches a render.

    Returns
    -------
    elevation : numpy.ndarray
        Float32 elevation crop in metres, padded by 15% of the bbox's own
        span on each side (clamped to the grid's real extent). The padding
        matters for :func:`terrain_shade_for_bbox`'s FFT step: without it,
        the Hann window (needed to avoid ringing at the tile edge) would
        also darken/fade real terrain right at the region's actual
        boundary -- padding pushes that fade-out into a margin that gets
        cropped away before reprojection, not into the region itself.
    padded_bounds : tuple of float
        ``(west, south, east, north)`` of the returned crop (after padding
        and clamping) -- callers need this to map the crop's pixels back to
        real lon/lat.

    Examples
    --------
    >>> elev, bounds = _elevation_window(-9.6, 35.9, 3.4, 43.9)
    >>> elev.ndim
    2
    >>> bounds[0] < -9.6  # padded west of the requested bbox
    True
    """
    grid = load_elevation(path)
    h, w = grid.shape
    gb = _ELEVATION_BOUNDS
    res_lon = (gb["east"] - gb["west"]) / w
    res_lat = (gb["north"] - gb["south"]) / h

    pad_lon = (east - west) * 0.15
    pad_lat = (north - south) * 0.15
    pw = max(gb["west"], west - pad_lon)
    pe = min(gb["east"], east + pad_lon)
    ps = max(gb["south"], south - pad_lat)
    pn = min(gb["north"], north + pad_lat)

    col0 = max(0, int((pw - gb["west"]) / res_lon))
    col1 = min(w, int(np.ceil((pe - gb["west"]) / res_lon)))
    row0 = max(0, int((gb["north"] - pn) / res_lat))
    row1 = min(h, int(np.ceil((gb["north"] - ps) / res_lat)))

    crop = grid[row0:row1, col0:col1]
    actual_bounds = (
        gb["west"] + col0 * res_lon,
        gb["north"] - row1 * res_lat,
        gb["west"] + col1 * res_lon,
        gb["north"] - row0 * res_lat,
    )
    return crop, actual_bounds


#: Shipped defaults for the three exaggeration knobs :func:`_compute_terrain_shade`
#: exposes -- vertical exaggeration on the hillshade gradient, the fractional
#: Laplacian's order in texture shading, and the hillshade/texture blend weight.
#: Named here (not just inline literals) so :doc:`doc/CARTOGRAPHY.tex`'s illustrative
#: comparison figures can render the *same* production code path at other
#: values without duplicating the algorithm in a throwaway script.
DEFAULT_VERTICAL_EXAGGERATION: float = 2.0
DEFAULT_TEXTURE_ALPHA: float = 0.5
DEFAULT_HILLSHADE_WEIGHT: float = 0.35


def _compute_terrain_shade(
    elevation: np.ndarray,
    res_lon_deg: float,
    res_lat_deg: float,
    lat_top: float,
    *,
    vertical_exaggeration: float = DEFAULT_VERTICAL_EXAGGERATION,
    texture_alpha: float = DEFAULT_TEXTURE_ALPHA,
    hillshade_weight: float = DEFAULT_HILLSHADE_WEIGHT,
) -> np.ndarray:
    """Blend a directional hillshade with fractional-Laplacian texture shading.

    Parameters
    ----------
    elevation : numpy.ndarray
        Float32 elevation crop, metres, north row first.
    res_lon_deg, res_lat_deg : float
        The crop's pixel size in degrees (longitude, latitude).
    lat_top : float
        Latitude of the crop's north edge -- needed to convert the
        longitude pixel spacing to metres (it shrinks with
        ``cos(latitude)``; the latitude spacing does not).
    vertical_exaggeration : float, optional
        Multiplier on the elevation gradient before it becomes a hillshade
        slope/aspect (default :data:`DEFAULT_VERTICAL_EXAGGERATION`). See
        Notes.
    texture_alpha : float, optional
        Fractional order of the frequency-domain Laplacian texture shading
        applies (default :data:`DEFAULT_TEXTURE_ALPHA`). See Notes.
    hillshade_weight : float, optional
        Weight given to the hillshade term in the final blend (default
        :data:`DEFAULT_HILLSHADE_WEIGHT`); texture shading gets
        ``1 - hillshade_weight``, so the two always sum to a full-strength
        blend rather than needing two independent weights kept in sync by
        the caller.

    Returns
    -------
    numpy.ndarray
        uint8, same shape as ``elevation``, ready for
        :data:`_duotone_lut`.

    Notes
    -----
    Two techniques, combined because each covers what the other misses --
    and each carries its own *exaggeration* knob, a deliberate departure
    from a physically literal render, not a bug to eventually remove. See
    ``doc/CARTOGRAPHY.tex``'s "Relief exaggeration strategies" section for the
    illustrated version of this argument.

    - **Hillshade** (Lambertian, single light source, NW at 45 degrees
      altitude): gives the overall light/dark balance a reader expects
      from "a lit 3-D surface" -- but is scale-blind to structure much
      smaller than the light/shadow transition itself. Its exaggeration
      knob is ``vertical_exaggeration``: real terrain slopes read as
      nearly flat at true scale even on this 30 arc-second grid, so the
      elevation gradient is multiplied up before it becomes a slope
      angle, a deliberate graphic choice, not a physically "correct"
      light simulation.
    - **Texture shading** (Brown 2010 -- a fractional-order Laplacian
      applied in the frequency domain: FFT the elevation, multiply by
      ``|frequency|^alpha``, inverse FFT): scale-invariant, so it draws out
      ridgelines and drainage networks at *every* scale at once. This is
      the piece that makes the result read as "engraved"/painterly rather
      than "a photo of a lit ball" -- verified against editorial,
      New-York-Times-style relief cartography during development, not
      chosen on theory alone; see ``.private/todo.md`` for the comparison.
      Its exaggeration knob is ``texture_alpha``: a *frequency-domain*
      exaggeration rather than a spatial one, since it boosts every scale
      of ridge/valley structure by the same power law instead of
      stretching one direction's gradient.

    A Hann window is applied before the FFT to avoid ringing at the crop's
    hard rectangular edge (a raw rectangular window's sharp cut is itself a
    high-frequency signal, which a high-pass filter would amplify into
    visible edge artefacts).

    Examples
    --------
    >>> import numpy as np
    >>> flat = np.zeros((64, 64), dtype=np.float32)
    >>> shade = _compute_terrain_shade(flat, 0.01, 0.01, 40.0)
    >>> shade.shape
    (64, 64)
    >>> shade.dtype
    dtype('uint8')
    """
    h, w = elevation.shape
    # Longitude spacing shrinks toward the poles; latitude spacing doesn't.
    # Both need converting from degrees to metres before a gradient is a
    # real physical slope rather than a degree-per-degree ratio.
    lats = lat_top - (np.arange(h) + 0.5) * res_lat_deg
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lats))
    dx_m = (res_lon_deg * m_per_deg_lon)[:, None]
    dy_m = res_lat_deg * 111_320.0

    dzdx = np.gradient(elevation, axis=1) / dx_m * vertical_exaggeration
    dzdy = np.gradient(elevation, axis=0) / dy_m * vertical_exaggeration
    slope = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    aspect = np.arctan2(dzdy, -dzdx)
    azimuth_deg, altitude_deg = 315.0, 45.0
    az = np.radians(360.0 - azimuth_deg + 90.0)
    alt = np.radians(altitude_deg)
    hillshade = np.clip(
        np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0.0, 1.0
    )

    window = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    elevation_windowed = (elevation - elevation.mean()) * window
    spectrum = np.fft.fft2(elevation_windowed)
    freq_y = np.fft.fftfreq(h)[:, None]
    freq_x = np.fft.fftfreq(w)[None, :]
    freq_radius = np.sqrt(freq_y**2 + freq_x**2)
    freq_radius[0, 0] = 1e-9  # avoid 0**alpha at the DC term
    texture = np.fft.ifft2(spectrum * (freq_radius**texture_alpha)).real
    # Texture shading's output is unbounded and scale-free (unlike
    # hillshade's physical [0, 1] cosine) -- recentre on its own standard
    # deviation rather than a fixed constant, so this normalises sensibly
    # regardless of the crop's absolute relief amplitude.
    texture_std = texture.std() or 1.0
    texture_norm = np.clip(texture / (4.0 * texture_std) + 0.5, 0.0, 1.0)

    # Weighted toward texture at the shipped default: hillshade alone
    # supplies believable overall lighting, texture shading alone supplies
    # the fine multi-scale detail that reads as "alive" -- a 0.35/0.65
    # hillshade/texture split was the blend that matched the reference
    # during manual comparison (see Notes).
    blended = np.clip(hillshade_weight * hillshade + (1.0 - hillshade_weight) * texture_norm, 0.0, 1.0)
    return (blended * 255).astype(np.uint8)


def terrain_shade_for_bbox(
    west: float,
    south: float,
    east: float,
    north: float,
    plot_w_px: float,
    plot_h_px: float,
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Compute blended terrain shading for one region, from real elevation.

    Parameters
    ----------
    west, south, east, north : float
        The region of interest, in degrees.
    plot_w_px, plot_h_px : float
        The output canvas's plot-area size in pixels -- forwarded to
        :func:`select_elevation_tier` so this loads whichever pyramid tier
        actually matches the render, not always the heaviest one.

    Returns
    -------
    shade : numpy.ndarray
        uint8 shade grid (not yet retinted -- pass through
        :data:`_duotone_lut` for that), covering ``bounds`` below.
    bounds : tuple of float
        ``(west, south, east, north)`` the returned ``shade`` array actually
        covers (the padded, clamped window -- see :func:`_elevation_window`),
        needed by the caller to map canvas pixels back into this array.

    Notes
    -----
    This is the regional (``make_situation_map.py``) relief path, separate
    from :func:`sample_relief`'s pre-rendered-raster path
    (``make_choropleth.py``, world scale). The two are architecturally
    different on purpose: texture shading needs a *regular equirectangular
    grid* to run its FFT on, computed *before* reprojection -- it cannot be
    evaluated pixel-by-pixel the way ``sample_relief`` samples the
    already-shaded world raster per output pixel. World-scale choropleth
    keeps the older, cheaper pre-rendered-raster path because a world crop
    is too large to FFT cheaply and the fine texture this technique adds
    would be invisible at that zoom anyway.

    Examples
    --------
    >>> shade, bounds = terrain_shade_for_bbox(-9.6, 35.9, 3.4, 43.9, 950, 730)
    >>> shade.dtype
    dtype('uint8')
    >>> len(bounds)
    4
    """
    tier_path = select_elevation_tier(west, south, east, north, plot_w_px, plot_h_px)
    elevation, padded_bounds = _elevation_window(west, south, east, north, path=tier_path)
    h, w = elevation.shape
    pw, ps, pe, pn = padded_bounds
    res_lon_deg = (pe - pw) / w
    res_lat_deg = (pn - ps) / h
    shade = _compute_terrain_shade(elevation, res_lon_deg, res_lat_deg, pn)
    return shade, padded_bounds


def sample_terrain_shade(
    lon_deg: np.ndarray,
    lat_deg: np.ndarray,
    valid: np.ndarray,
    shade: np.ndarray,
    bounds: tuple[float, float, float, float],
    *,
    opacity: float = DEFAULT_RELIEF_OPACITY,
) -> np.ndarray:
    """Bilinearly sample a precomputed terrain-shade array and apply the duotone.

    Parameters
    ----------
    lon_deg, lat_deg : numpy.ndarray
        Longitude/latitude in degrees, same shape, one entry per output
        (canvas) pixel.
    valid : numpy.ndarray of bool
        Same shape as ``lon_deg``; ``False`` -> fully transparent (see
        :func:`sample_relief`'s parameter docs for the general rationale).
    shade : numpy.ndarray
        uint8 shade grid from :func:`terrain_shade_for_bbox`.
    bounds : tuple of float
        ``(west, south, east, north)`` that ``shade`` covers, from the same
        call.
    opacity : float, optional
        As in :func:`sample_relief`.

    Returns
    -------
    numpy.ndarray
        RGBA uint8, shape ``lon_deg.shape + (4,)``.

    Examples
    --------
    >>> import numpy as np
    >>> shade = np.full((4, 4), 128, dtype=np.uint8)
    >>> bounds = (0.0, 0.0, 1.0, 1.0)
    >>> lon = np.array([[0.5]]); lat = np.array([[0.5]]); valid = np.array([[True]])
    >>> rgba = sample_terrain_shade(lon, lat, valid, shade, bounds)
    >>> rgba.shape
    (1, 1, 4)
    """
    west, south, east, north = bounds
    h, w = shade.shape
    col_f = np.clip((lon_deg - west) / (east - west) * w - 0.5, 0.0, w - 1.0)
    row_f = np.clip((north - lat_deg) / (north - south) * h - 0.5, 0.0, h - 1.0)
    col0 = np.floor(col_f).astype(np.int64)
    row0 = np.floor(row_f).astype(np.int64)
    col1 = np.clip(col0 + 1, 0, w - 1)
    row1 = np.clip(row0 + 1, 0, h - 1)
    frac_col = col_f - col0
    frac_row = row_f - row0
    shade_f = shade.astype(np.float32)
    top = shade_f[row0, col0] * (1.0 - frac_col) + shade_f[row0, col1] * frac_col
    bottom = shade_f[row1, col0] * (1.0 - frac_col) + shade_f[row1, col1] * frac_col
    interpolated = (top * (1.0 - frac_row) + bottom * frac_row).astype(np.uint8)
    alpha = np.where(valid, round(opacity * 255), 0).astype(np.uint8)
    rgb = _duotone_lut()[interpolated]
    return np.concatenate([rgb, alpha[..., np.newaxis]], axis=-1).astype(np.uint8)
