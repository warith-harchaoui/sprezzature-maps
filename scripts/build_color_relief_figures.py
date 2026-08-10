"""
build_color_relief_figures — regenerate doc/CARTOGRAPHY.tex's color/relief verification figures.

Module summary
--------------
Two claims in ``doc/CARTOGRAPHY.tex`` are currently asserted in prose without a
supporting image: that shipped color ramps are verified (not just designed
by eye) against color-vision deficiency, and that the world-scale relief
path's Imhof-style duotone genuinely beats the plain contrast-stretched
greyscale it replaced. This script renders both, from the real production
functions (`_geo_colors.py`, `_relief.py`), not a re-implementation of
either -- no synthetic swatches, no matplotlib.

Two composite PNGs are written to ``doc/img/`` at print resolution:

- ``cvd-simulation-diverging.png``: the shipped diverging ramp as a smooth
  gradient bar, four rows (normal vision, then each of the three CVD types
  :func:`_geo_colors.simulate_cvd_hex` supports), so a reader can see
  directly that the negative/positive extremes stay visually distinct
  under every simulated condition, not just under normal vision.
- ``relief-duotone-comparison.png``: the same real Alps crop from the
  vendored Natural Earth hillshade raster, contrast-stretched plain
  greyscale next to the shipped Imhof-style OKLCH duotone.

Usage example
-------------
>>> True  # this module runs as a script; import-time side effects only
True

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _geo_colors import diverging_ramp_hex, simulate_cvd_hex  # noqa: E402
from _relief import (  # noqa: E402
    _SHADE_STRETCH_HIGH,
    _SHADE_STRETCH_LOW,
    _duotone_lut,
    load_relief_grayscale,
)

_CAPTION_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
)
_PANEL_BG = (250, 247, 240)
_CAPTION_TEXT = (43, 41, 38)

#: Alps arc, the most dramatic terrain the low-resolution world raster
#: resolves at all (west, south, east, north, degrees) -- picked so the
#: greyscale-vs-duotone comparison has real relief to show a difference
#: on, the same reasoning :data:`build_relief_exaggeration_figures._BBOX`
#: used for the elevation-based figures.
_ALPS_BBOX = (5.5, 43.5, 16.5, 48.0)


def _caption_font(size: int) -> ImageFont.ImageFont:
    """Load the editorial-serif caption face, falling back to Pillow's default.

    Parameters
    ----------
    size : int
        Point size to load the face at.

    Returns
    -------
    PIL.ImageFont.ImageFont
        A loaded TrueType font, or Pillow's built-in bitmap font if none of
        the candidate system paths exist on this machine.

    Examples
    --------
    >>> font = _caption_font(18)
    >>> font is not None
    True
    """
    for path in _CAPTION_FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _ramp_row(width: int, height: int, cvd_type: str | None) -> np.ndarray:
    """Render one horizontal gradient bar of the shipped diverging ramp.

    Parameters
    ----------
    width, height : int
        Bar size in pixels.
    cvd_type : str or None
        One of :data:`_geo_colors.CVD_MATRICES`'s keys to simulate that
        color-vision deficiency on every sampled color, or ``None`` for
        unsimulated (normal-vision) color.

    Returns
    -------
    numpy.ndarray
        RGB uint8, shape ``(height, width, 3)``.

    Examples
    --------
    >>> row = _ramp_row(20, 4, None)
    >>> row.shape
    (4, 20, 3)
    >>> row = _ramp_row(20, 4, "deuteranopia")
    >>> row.shape
    (4, 20, 3)
    """
    colors = np.zeros((width, 3), dtype=np.uint8)
    for i in range(width):
        t = (i / (width - 1)) * 2.0 - 1.0  # sweep -1..1 across the bar
        hex_color = diverging_ramp_hex(t)
        if cvd_type is not None:
            hex_color = simulate_cvd_hex(hex_color, cvd_type)
        colors[i] = (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))
    return np.tile(colors[None, :, :], (height, 1, 1))


def build_cvd_figure(out_path: Path, *, bar_width: int = 2200, bar_height: int = 170) -> None:
    """Render the four-row CVD-simulation comparison and write it to ``out_path``.

    Parameters
    ----------
    out_path : pathlib.Path
        Destination PNG.
    bar_width, bar_height : int, optional
        Size of each gradient bar (default 2200x170, print resolution).

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     out = Path(tmp) / "cvd.png"
    ...     build_cvd_figure(out, bar_width=40, bar_height=8)
    ...     out.exists()
    True
    """
    rows = [
        ("Normal vision", _ramp_row(bar_width, bar_height, None)),
        ("Protanopia (simulated)", _ramp_row(bar_width, bar_height, "protanopia")),
        ("Deuteranopia (simulated)", _ramp_row(bar_width, bar_height, "deuteranopia")),
        ("Tritanopia (simulated)", _ramp_row(bar_width, bar_height, "tritanopia")),
    ]
    label_w = 520
    gap = 20
    font = _caption_font(48)
    canvas = Image.new(
        "RGB", (label_w + bar_width, (bar_height + gap) * len(rows) - gap), _PANEL_BG
    )
    draw = ImageDraw.Draw(canvas)
    y = 0
    for label, arr in rows:
        canvas.paste(Image.fromarray(arr), (label_w, y))
        bbox = draw.textbbox((0, 0), label, font=font)
        text_h = bbox[3] - bbox[1]
        draw.text(
            (32, y + (bar_height - text_h) / 2 - bbox[1]), label, fill=_CAPTION_TEXT, font=font
        )
        y += bar_height + gap
    canvas.save(out_path, format="PNG")


def build_relief_duotone_figure(out_path: Path, *, panel_width: int = 1600) -> None:
    """Render the plain-greyscale-vs-Imhof-duotone comparison and write it to ``out_path``.

    Parameters
    ----------
    out_path : pathlib.Path
        Destination PNG.
    panel_width : int, optional
        Each panel's displayed width in pixels (default 1600, print
        resolution); the source crop is far smaller (the world raster
        is only 1440x720 pixels in total, covering the whole planet),
        so this upsamples for figure legibility, matching the
        convention :func:`build_relief_exaggeration_figures._compose_row`
        already uses for the elevation-based figures.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     out = Path(tmp) / "relief.png"
    ...     build_relief_duotone_figure(out, panel_width=40)
    ...     out.exists()
    True
    """
    grid = load_relief_grayscale()
    height, width = grid.shape
    west, south, east, north = _ALPS_BBOX
    col0 = round((west + 180.0) / 360.0 * width)
    col1 = round((east + 180.0) / 360.0 * width)
    row0 = round((90.0 - north) / 180.0 * height)
    row1 = round((90.0 - south) / 180.0 * height)
    crop = grid[row0:row1, col0:col1]

    stretched = np.clip(
        (crop.astype(np.float32) - _SHADE_STRETCH_LOW)
        / (_SHADE_STRETCH_HIGH - _SHADE_STRETCH_LOW)
        * 255.0,
        0.0,
        255.0,
    ).astype(np.uint8)
    plain_grey = np.stack([stretched, stretched, stretched], axis=-1)
    duotone = _duotone_lut()[stretched]

    panels = [
        ("Plain contrast-stretched greyscale", plain_grey),
        ("Imhof-style OKLCH duotone (shipped)", duotone),
    ]
    caption_h = 145
    gutter = 26
    resized = []
    for _, arr in panels:
        img = Image.fromarray(arr)
        h = round(panel_width * arr.shape[0] / arr.shape[1])
        # Bicubic, not nearest: the shipped generator itself bilinearly
        # resamples this same raster at render time (see sample_relief's
        # own docstring for why nearest-neighbour was replaced -- it made
        # a flagrant grid of flat blocks once zoomed past world scale).
        # A figure meant to represent what a real render looks like should
        # not reintroduce that artefact just because it upsamples a small
        # crop for legibility.
        resized.append(img.resize((panel_width, h), Image.Resampling.BICUBIC))
    row_h = max(im.height for im in resized)
    total_w = panel_width * len(resized) + gutter * (len(resized) - 1)
    canvas = Image.new("RGB", (total_w, row_h + caption_h), _PANEL_BG)
    draw = ImageDraw.Draw(canvas)
    font = _caption_font(52)
    x = 0
    for (caption, _), img in zip(panels, resized, strict=True):
        canvas.paste(img, (x, 0))
        bbox = draw.textbbox((0, 0), caption, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (panel_width - text_w) / 2, row_h + 36), caption, fill=_CAPTION_TEXT, font=font
        )
        x += panel_width + gutter
    canvas.save(out_path, format="PNG")


def main() -> None:
    """Render both color/relief verification figures and write them to ``doc/img/``.

    Examples
    --------
    >>> callable(main)
    True
    """
    out_dir = Path(__file__).resolve().parent.parent / "doc" / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    build_cvd_figure(out_dir / "cvd-simulation-diverging.png")
    print(f"wrote {out_dir / 'cvd-simulation-diverging.png'}")
    build_relief_duotone_figure(out_dir / "relief-duotone-comparison.png")
    print(f"wrote {out_dir / 'relief-duotone-comparison.png'}")


if __name__ == "__main__":
    main()
