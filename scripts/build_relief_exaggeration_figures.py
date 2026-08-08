"""
build_relief_exaggeration_figures — regenerate CARTOGRAPHY.md's exaggeration-strategy figures.

Module summary
--------------
``CARTOGRAPHY.md``'s "Relief exaggeration strategies" section illustrates
the three knobs :func:`_relief._compute_terrain_shade` exposes (vertical
exaggeration, texture shading's fractional order, the hillshade/texture
blend weight) with real comparison renders, not a diagram. This script
regenerates those renders from the *actual* production shading function
(imported from ``_relief.py``, not reimplemented here) at a small set of
illustrative parameter values, on the same real elevation data every other
figure in this repository uses -- no synthetic terrain, no matplotlib.

Two composite PNGs are written to ``web/img/``:

- ``relief-exaggeration-vertical.png``: hillshade-only (texture weight 0),
  at true-scale (``vertical_exaggeration=1.0``) vs. the shipped default
  (``2.0``), two panels.
- ``relief-exaggeration-blend.png``: hillshade-only, texture-only, and the
  shipped 0.35/0.65 blend, three panels.

Panels are composited with plain Pillow drawing (paste + a captioned
bottom bar), not matplotlib, consistent with this whole stack's
"no matplotlib, ever" constraint. Captions use a system serif face
(Georgia, matching this document's editorial print register) when
available, falling back to Pillow's bitmap default otherwise, so the
script degrades rather than fails on a machine without it.

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
from _relief import (  # noqa: E402
    DEFAULT_HILLSHADE_WEIGHT,
    DEFAULT_TEXTURE_ALPHA,
    DEFAULT_VERTICAL_EXAGGERATION,
    _compute_terrain_shade,
    _duotone_lut,
    _elevation_window,
    select_elevation_tier,
)

#: Everest massif, a compact bbox with the most dramatic real relief this
#: repo has vendored data for -- the small span keeps the FFT and the
#: whole-script runtime cheap while still making an exaggeration
#: difference obvious at figure scale (west, south, east, north, degrees).
_BBOX = (86.2, 27.5, 88.4, 28.7)

#: Deliberately larger than any real render would need for this tiny bbox
#: (see :func:`select_elevation_tier`'s docstring) -- forces the finest 30
#: arc-second tier regardless of oversample, which is what a dramatic
#: illustrative figure wants.
_PLOT_W_PX, _PLOT_H_PX = 1800.0, 1000.0

_CAPTION_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
)
_PANEL_BG = (250, 247, 240)
_CAPTION_TEXT = (43, 41, 38)
_GUTTER_PX = 10


def _caption_font(size: int) -> ImageFont.ImageFont:
    """Load the editorial-serif caption face, falling back to Pillow's default.

    Parameters
    ----------
    size : int
        Point size to load the face at.

    Returns
    -------
    PIL.ImageFont.ImageFont
        A loaded TrueType font from :data:`_CAPTION_FONT_CANDIDATES`, or
        Pillow's built-in bitmap font if none of those paths exist on this
        machine -- this script is a documentation-figure build tool, not
        part of the render pipeline, so degrading gracefully here matters
        more than failing loudly.

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


def _render_panel(
    elevation: np.ndarray,
    res_lon_deg: float,
    res_lat_deg: float,
    lat_top: float,
    trim: tuple[int, int, int, int],
    **shade_kwargs: float,
) -> np.ndarray:
    """Compute one duotone-shaded, padding-trimmed panel via the real shading function.

    Parameters
    ----------
    elevation, res_lon_deg, res_lat_deg, lat_top : see :func:`_compute_terrain_shade`
        Forwarded as-is.
    trim : tuple of int
        ``(row0, row1, col0, col1)`` slicing the padded crop back down to
        the figure's actual bbox (the padding exists only so the FFT's Hann
        window doesn't fade real terrain at the bbox edge -- see
        :func:`_elevation_window`'s docstring -- and would otherwise show
        up as a soft, uninformative border in a small illustrative figure).
    **shade_kwargs
        Forwarded to :func:`_compute_terrain_shade` (``vertical_exaggeration``,
        ``texture_alpha``, ``hillshade_weight``).

    Returns
    -------
    numpy.ndarray
        RGB uint8, the trimmed, duotone-retinted panel.

    Examples
    --------
    >>> import numpy as np
    >>> flat = np.zeros((40, 40), dtype=np.float32)
    >>> panel = _render_panel(flat, 0.01, 0.01, 30.0, (5, 35, 5, 35))
    >>> panel.shape
    (30, 30, 3)
    """
    shade = _compute_terrain_shade(elevation, res_lon_deg, res_lat_deg, lat_top, **shade_kwargs)
    row0, row1, col0, col1 = trim
    return _duotone_lut()[shade[row0:row1, col0:col1]]


def _compose_row(
    panels: list[tuple[str, np.ndarray]], out_path: Path, *, panel_width: int = 620
) -> None:
    """Lay out labeled panels in a single row with a captioned bar under each.

    Parameters
    ----------
    panels : list of (str, numpy.ndarray)
        Each entry is a caption and an RGB uint8 array.
    out_path : pathlib.Path
        Where to write the composite PNG.
    panel_width : int, optional
        Every panel is resized to this width (nearest-neighbour would be
        cheaper but visibly blockier at this size jump; Pillow's default
        bicubic resample reads cleanly instead), preserving its own aspect
        ratio, so panels of a slightly different trimmed shape still line
        up in one tidy row (default 620).

    Examples
    --------
    >>> import numpy as np
    >>> from pathlib import Path
    >>> import tempfile
    >>> panel = np.zeros((10, 10, 3), dtype=np.uint8)
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     out = Path(tmp) / "row.png"
    ...     _compose_row([("a", panel), ("b", panel)], out, panel_width=40)
    ...     out.exists()
    True
    """
    caption_h = 56
    resized = []
    for _, arr in panels:
        img = Image.fromarray(arr)
        h = round(panel_width * arr.shape[0] / arr.shape[1])
        resized.append(img.resize((panel_width, h), Image.Resampling.BICUBIC))
    row_h = max(im.height for im in resized)
    total_w = panel_width * len(resized) + _GUTTER_PX * (len(resized) - 1)
    canvas = Image.new("RGB", (total_w, row_h + caption_h), _PANEL_BG)
    draw = ImageDraw.Draw(canvas)
    font = _caption_font(20)
    x = 0
    for (caption, _), img in zip(panels, resized):
        canvas.paste(img, (x, 0))
        bbox = draw.textbbox((0, 0), caption, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (panel_width - text_w) / 2, row_h + 14),
            caption,
            fill=_CAPTION_TEXT,
            font=font,
        )
        x += panel_width + _GUTTER_PX
    canvas.save(out_path, format="PNG")


def main() -> None:
    """Render both exaggeration-strategy comparison figures and write them to ``web/img/``.

    Examples
    --------
    >>> callable(main)
    True
    """
    out_dir = Path(__file__).resolve().parent.parent / "web" / "img"
    west, south, east, north = _BBOX
    tier_path = select_elevation_tier(west, south, east, north, _PLOT_W_PX, _PLOT_H_PX)
    elevation, (pw, ps, pe, pn) = _elevation_window(west, south, east, north, path=tier_path)
    h, w = elevation.shape
    res_lon_deg = (pe - pw) / w
    res_lat_deg = (pn - ps) / h
    # Trim the FFT-safety padding back down to the real bbox for display --
    # see _render_panel's docstring for why the padding itself must stay in
    # the shading computation but not in what a reader sees.
    col0 = round((west - pw) / res_lon_deg)
    col1 = round((east - pw) / res_lon_deg)
    row0 = round((pn - north) / res_lat_deg)
    row1 = round((pn - south) / res_lat_deg)
    trim = (row0, row1, col0, col1)

    def panel(**kwargs: float) -> np.ndarray:
        return _render_panel(elevation, res_lon_deg, res_lat_deg, pn, trim, **kwargs)

    vertical_true = panel(vertical_exaggeration=1.0, hillshade_weight=1.0)
    vertical_default = panel(vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION, hillshade_weight=1.0)
    _compose_row(
        [
            ("Vertical exaggeration ×1 (true to scale)", vertical_true),
            (f"Vertical exaggeration ×{DEFAULT_VERTICAL_EXAGGERATION:g} (shipped)", vertical_default),
        ],
        out_dir / "relief-exaggeration-vertical.png",
    )
    print(f"wrote {out_dir / 'relief-exaggeration-vertical.png'}")

    hillshade_only = panel(hillshade_weight=1.0)
    texture_only = panel(hillshade_weight=0.0)
    blended = panel(
        vertical_exaggeration=DEFAULT_VERTICAL_EXAGGERATION,
        texture_alpha=DEFAULT_TEXTURE_ALPHA,
        hillshade_weight=DEFAULT_HILLSHADE_WEIGHT,
    )
    _compose_row(
        [
            ("Hillshade only", hillshade_only),
            ("Texture shading only", texture_only),
            ("Blended (shipped)", blended),
        ],
        out_dir / "relief-exaggeration-blend.png",
        panel_width=420,
    )
    print(f"wrote {out_dir / 'relief-exaggeration-blend.png'}")


if __name__ == "__main__":
    main()
