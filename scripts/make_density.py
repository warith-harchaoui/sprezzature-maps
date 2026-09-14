"""
make_density — an accumulation map: where a thing happened, and how often.

What this draws
---------------
Millions of point events — lightning strikes, sightings, calls, quakes —
binned to a grid and drawn as a luminous field. The point of the form is
that **the data is the geography**: no coastline is drawn, no border, no
graticule. The land appears because events fell on it, and the sea is dark
because none did. A reader recognises the shape without being shown it,
which is a different and stronger kind of recognition than reading a label.

Why cells and not a raster
--------------------------
A million points cannot be a million SVG elements, so the field is binned.
The house rule for how far to bin is measurable rather than a matter of
taste: *once an SVG is larger than the PNG you could export from it, that
is the signal to approximate*, with a practical budget of a few hundred
kilobytes — a megabyte is too much.

Measured on 381 406 synthetic points at 1000 × 414:

===========  ==========  ==========  ==========  ==========
encoding     40 bins     120 bins    260 bins    400 bins
===========  ==========  ==========  ==========  ==========
one rect     109 KB      972 KB      4.3 MB      8.6 MB
per level    16 KB       123 KB      573 KB      1.3 MB
the PNG      5 KB        15 KB       44 KB       114 KB
===========  ==========  ==========  ==========  ==========

Quantising the ramp and merging every cell of one level into a single path
cuts the weight sevenfold: 120 bins is eight paths. Past roughly 260 bins
the field stops being a field and becomes grain — the *visual* limit arrives
before the size limit, which is the more useful of the two.

So: no embedded raster. Vector, binned, one path per level.

Usage
-----
::

    python3 make_density.py --out lightning.svg
    python3 make_density.py --bins 80 --out coarse.svg

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _render import render_cli, svg_example_path, write_svg  # noqa: E402

#: Bin count along the long axis. 120 is the measured sweet spot: the field
#: still reads as a field, and the plate lands near 150 KB.
DEFAULT_BINS: int = 120

#: Ten steps from the plate to near-white. Sequential and luminance-ordered,
#: so the ramp survives greyscale and colour blindness: the reading is
#: carried by lightness, and hue only makes it pleasant.
RAMP: tuple[str, ...] = (
    "#0b1b3a", "#12306b", "#1a4a9c", "#2168c8", "#3b8ae0",
    "#63a9ee", "#8fc4f5", "#b6dcfa", "#d8eefd", "#f2f9ff",
)

#: The ground. Not pure black: a hair of blue keeps the plate from reading
#: as a hole punched in the page.
PLATE: str = "#050a16"
INK: str = "#eef2f7"
SUBTLE: str = "#8f9bab"

#: Cells are drawn a fraction wider than their slot. Adjacent rectangles
#: that merely touch leave a seam of background showing through where the
#: renderer antialiases both edges, and a grid of hairlines appears over the
#: whole field.
_OVERLAP: float = 0.6


def demo_points(n: int = 400_000, seed: int = 20260912) -> list[tuple[float, float]]:
    """
    A synthetic strike field over the continental United States.

    Storm corridors over a diffuse background, which is roughly how
    convective lightning distributes: not uniform, not a single blob.
    Synthetic and labelled as such — a demo that passed itself off as
    observation would be the one dishonest thing in the file.

    Parameters
    ----------
    n : int, optional
        Point count before clipping to the window.
    seed : int, optional
        Generator seed, so the figure is reproducible.

    Returns
    -------
    list of tuple
        ``(lon, lat)`` pairs.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    corridors = ((-95, 35, 9, 5), (-88, 41, 7, 4), (-99, 31, 6, 4), (-82, 28, 5, 3))
    parts = [
        np.column_stack([rng.normal(cx, sx, n // 6), rng.normal(cy, sy, n // 6)])
        for cx, cy, sx, sy in corridors
    ]
    parts.append(
        np.column_stack([rng.uniform(-125, -67, n // 3), rng.uniform(25, 49, n // 3)])
    )
    pts = np.vstack(parts)
    keep = (pts[:, 0] > -125) & (pts[:, 0] < -67) & (pts[:, 1] > 25) & (pts[:, 1] < 49)
    pts = pts[keep]

    # Clip to land. Without this the diffuse background paints the whole
    # rectangle and the plate loses the one thing the form is for: on a real
    # accumulation map the coastline is never drawn, it *emerges* from where
    # events fell, and a reader recognises the shape without being shown it.
    return [(lon, lat) for lon, lat in pts if _on_land(lon, lat)]


#: Resolution of the land mask, in cells along the longitude span. The mask
#: only decides whether a *demo* point is kept, so a cell here is far finer
#: than a bin in the plate and the coastline still lands where it should.
_MASK_NX: int = 480

#: ``(west, south, east, north, nx, ny, bits)`` for the cached mask.
_MASK: tuple[float, float, float, float, int, int, list[bool]] | None = None


def _on_land(lon: float, lat: float) -> bool:
    """
    True when the point falls on the United States landmass.

    Looks the answer up in a precomputed grid rather than running
    point-in-polygon per point. The direct version was correct and took
    seven and a half minutes on the demo's 380 000 points, which is not a
    generator anybody runs twice; the mask is built once, in about a second,
    and every lookup after that is an index.
    """
    mask = _land_mask()
    west, south, east, north, nx, ny, bits = mask
    if not (west <= lon <= east and south <= lat <= north):
        return False
    i = min(nx - 1, int((lon - west) / (east - west) * nx))
    j = min(ny - 1, int((lat - south) / (north - south) * ny))
    return bits[j * nx + i]


def _land_mask() -> tuple[float, float, float, float, int, int, list[bool]]:
    """Build (once) a boolean grid of land over the demo window."""
    global _MASK
    if _MASK is not None:
        return _MASK
    west, south, east, north = -125.0, 25.0, -67.0, 49.0
    nx = _MASK_NX
    ny = max(1, round(nx * (north - south) / (east - west)))
    rings = _us_rings()
    # Per-ring bounding boxes: most rings are nowhere near most cells, and
    # skipping them early is what turns this from slow into instant.
    boxes = [
        (min(p[0] for p in r), min(p[1] for p in r),
         max(p[0] for p in r), max(p[1] for p in r), r)
        for r in rings
    ]
    bits: list[bool] = [False] * (nx * ny)
    for j in range(ny):
        lat = south + (j + 0.5) / ny * (north - south)
        row = j * nx
        for i in range(nx):
            lon = west + (i + 0.5) / nx * (east - west)
            for x0, y0, x1, y1, ring in boxes:
                if x0 <= lon <= x1 and y0 <= lat <= y1 and _point_in_ring(lon, lat, ring):
                    bits[row + i] = True
                    break
    _MASK = (west, south, east, north, nx, ny, bits)
    return _MASK


def _us_rings() -> list[list[tuple[float, float]]]:
    """The US outline, loaded once and kept."""
    global _US_RINGS
    if _US_RINGS is None:
        from make_choropleth import _load_countries

        us = next(c for c in _load_countries() if str(c["id"]) == "840")
        # Only rings that touch the window: Alaska and Hawaii are in the file
        # and would cost a point-in-polygon test each, for nothing.
        _US_RINGS = [
            r for r in us["rings"]
            if len(r) > 3 and min(p[0] for p in r) > -130 and max(p[0] for p in r) < -60
        ]
    return _US_RINGS


#: Cache for :func:`_us_rings`; the demo runs point-in-polygon a few hundred
#: thousand times and reloading the atlas each call would dominate.
_US_RINGS: list[list[tuple[float, float]]] | None = None


def _point_in_ring(x: float, y: float, ring: Sequence[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon, the textbook one."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def bin_points(
    points: Sequence[tuple[float, float]],
    bbox: tuple[float, float, float, float],
    bins: int,
) -> tuple[list[list[int]], int, int, int]:
    """
    Count points into a grid.

    Pure Python rather than numpy: the caller may have millions of points
    and numpy, or a few thousand and no numpy, and a generator that refuses
    to run without a scientific stack is a generator nobody reaches for.

    Parameters
    ----------
    points : sequence of tuple
        ``(lon, lat)`` pairs.
    bbox : tuple
        ``(west, south, east, north)``.
    bins : int
        Cells along the long axis.

    Returns
    -------
    tuple
        ``(grid, nx, ny, peak)``; ``grid[i][j]`` is the count in column
        ``i``, row ``j``.
    """
    west, south, east, north = bbox
    span_x, span_y = east - west, north - south
    if span_x <= 0 or span_y <= 0:
        raise ValueError(f"bbox has no area: {bbox}")

    nx = bins if span_x >= span_y else max(1, round(bins * span_x / span_y))
    ny = bins if span_y > span_x else max(1, round(bins * span_y / span_x))
    grid = [[0] * ny for _ in range(nx)]
    peak = 0
    for lon, lat in points:
        if not (west <= lon <= east and south <= lat <= north):
            continue
        i = min(nx - 1, int((lon - west) / span_x * nx))
        j = min(ny - 1, int((lat - south) / span_y * ny))
        grid[i][j] += 1
        if grid[i][j] > peak:
            peak = grid[i][j]
    return grid, nx, ny, peak


def build_svg(
    points: Sequence[tuple[float, float]] | None = None,
    *,
    bbox: tuple[float, float, float, float] = (-125.0, 25.0, -67.0, 49.0),
    bins: int = DEFAULT_BINS,
    width: int = 1000,
    title: str = "Where the lightning fell",
    subtitle: str = "Every flash of a synthetic year, accumulated one day at a time",
    caption: str = "SYNTHETIC DEMONSTRATION DATA · NOT AN OBSERVATIONAL RECORD",
) -> str:
    """
    Render the accumulation plate.

    Parameters
    ----------
    points : sequence of tuple, optional
        ``(lon, lat)`` pairs. ``None`` uses :func:`demo_points`.
    bbox : tuple, optional
        ``(west, south, east, north)`` window.
    bins : int, optional
        Cells along the long axis.
    width : int, optional
        Canvas width in pixels; height follows the window's aspect.
    title, subtitle, caption : str, optional
        Chrome. The caption states the provenance, and stays on the plate so
        the figure keeps saying what it is once it travels alone.

    Returns
    -------
    str
        A complete SVG document.

    Raises
    ------
    ValueError
        If `bins` is not positive, or no point falls inside `bbox`.
    """
    if bins < 1:
        raise ValueError(f"bins must be positive, got {bins}")
    pts = list(points) if points is not None else demo_points()
    grid, nx, ny, peak = bin_points(pts, bbox, bins)
    if peak == 0:
        raise ValueError("no point fell inside the bbox; nothing to draw")

    west, south, east, north = bbox
    height = round(width * (north - south) / (east - west))
    top = 92          # room for the title block
    foot = 46         # room for the caption
    plate_h = height + top + foot
    cw = width / nx
    ch = height / ny

    # One bucket per level; every cell of a level becomes one subpath, so the
    # whole field is as many <path> elements as there are levels.
    buckets: dict[int, list[str]] = {}
    for i in range(nx):
        column = grid[i]
        for j in range(ny):
            count = column[j]
            if count <= 0:
                continue      # no data is not zero data: leave the plate bare
            # sqrt keeps the long tail visible: a linear ramp on a field with
            # one bright core paints everything else the darkest step.
            level = min(len(RAMP) - 1, int(math.sqrt(count / peak) * len(RAMP)))
            x = i * cw
            y = top + height - (j + 1) * ch
            buckets.setdefault(level, []).append(
                f"M{x:.1f} {y:.1f}h{cw + _OVERLAP:.1f}v{ch + _OVERLAP:.1f}h-{cw + _OVERLAP:.1f}z"
            )

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{plate_h}" '
        f'viewBox="0 0 {width} {plate_h}" role="img" aria-labelledby="dens-title dens-desc" '
        f'shape-rendering="crispEdges">',
        f'<title id="dens-title">{_esc(title)}</title>',
        f'<desc id="dens-desc">{_esc(subtitle)} — {len(pts):,} points binned to '
        f'{nx} by {ny} cells.</desc>',
        f'<rect width="{width}" height="{plate_h}" fill="{PLATE}"/>',
    ]
    for level in sorted(buckets):
        out.append(f'<path fill="{RAMP[level]}" d="{"".join(buckets[level])}"/>')

    out.append(
        f'<text x="26" y="44" font-family="Georgia, \'Times New Roman\', serif" '
        f'font-size="30" fill="{INK}">{_esc(title)}</text>'
    )
    out.append(
        f'<text x="26" y="70" font-family="Georgia, \'Times New Roman\', serif" '
        f'font-size="14" font-style="italic" fill="{SUBTLE}">{_esc(subtitle)}</text>'
    )
    out.extend(_ramp_legend(width - 300, plate_h - 26, peak))
    out.append(
        f'<text x="26" y="{plate_h - 22:.0f}" font-family="ui-monospace, monospace" '
        f'font-size="9" fill="{SUBTLE}" letter-spacing="0.6">{_esc(caption)}</text>'
    )
    out.append("</svg>")
    return "\n".join(out)


def _ramp_legend(x: float, y: float, peak: int) -> list[str]:
    """
    A bare gradient bar with two words under it.

    No ticks and no numbers on the bar itself: the reading a density field
    supports is "more here than there", and printing counts invites a
    precision the binning does not have.
    """
    parts: list[str] = []
    step = 16
    for k, colour in enumerate(RAMP):
        parts.append(
            f'<rect x="{x + k * step:.0f}" y="{y - 14:.0f}" width="{step}" height="7" '
            f'fill="{colour}"/>'
        )
    parts.append(
        f'<text x="{x:.0f}" y="{y + 2:.0f}" font-family="ui-monospace, monospace" '
        f'font-size="9" fill="{SUBTLE}">fewer → more (peak {peak:,} per cell)</text>'
    )
    return parts


def _esc(text: str) -> str:
    """Escape the five XML characters."""
    return (
        str(text)
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&apos;")
    )


def make_density(
    points: Sequence[tuple[float, float]] | None = None,
    *,
    out: Path | str | None = None,
    bbox: tuple[float, float, float, float] = (-125.0, 25.0, -67.0, 49.0),
    bins: int = DEFAULT_BINS,
    width: int = 1000,
    title: str = "Where the lightning fell",
    subtitle: str = "Every flash of a synthetic year, accumulated one day at a time",
    caption: str = "SYNTHETIC DEMONSTRATION DATA · NOT AN OBSERVATIONAL RECORD",
) -> Path:
    """Render an accumulation map and write the SVG to *out*.

    The third kind this package draws, and the one that inverts the other two:
    no coastline, no border, no graticule. Point events are binned to a
    luminous field, and the land appears because events fell on it while the
    sea stays dark because none did. A reader recognises the shape without
    being shown it, which is a stronger recognition than reading a label.

    Until 0.4.0 this existed only as a script somebody had to run by hand: no
    library function, no CLI kind, no route. A map nobody can reach is a map
    this package does not have.

    Parameters
    ----------
    points : sequence of (lon, lat), optional
        Event positions in degrees. Defaults to the synthetic demo set.
    out : Path, str, or None
        Output path (.svg). Defaults to the bundled example location.
    bbox : (west, south, east, north)
        Geographic extent to bin over, in degrees.
    bins : int
        Cells across the image. Past roughly 260 the field stops being a field
        and becomes grain, so the visual limit arrives before the size limit.
    width : int
        Canvas width in pixels.
    title, subtitle, caption : str
        Chart chrome. The caption is where provenance goes, and the demo's
        says its data is synthetic *on the plate* — this form is persuasive
        enough to be believed otherwise.

    Returns
    -------
    Path
        Absolute path to the written SVG file.
    """
    svg = build_svg(
        points,
        bbox=bbox,
        bins=bins,
        width=width,
        title=title,
        subtitle=subtitle,
        caption=caption,
    )
    dest = Path(out) if out else svg_example_path(__file__, "density")
    return write_svg(dest, svg)


def main() -> None:
    """Command-line entry point."""
    render_cli(
        figure_id="density",
        build=lambda **kw: build_svg(
            bins=int(kw.pop("bins", DEFAULT_BINS)),
            **{k: v for k, v in kw.items() if k in ("width", "title", "subtitle", "caption")},
        ),
        description="Render an accumulation map: point events binned to a luminous field.",
    )


if __name__ == "__main__":
    main()
