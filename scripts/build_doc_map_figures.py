"""
build_doc_map_figures: rasterize the bundled SVG maps at print resolution, for doc/CARTOGRAPHY.tex.

Module summary
--------------
Rasterizing means converting a vector image (one described as shapes and
coordinates, like the SVGs, Scalable Vector Graphics, this repo's
generators write) into a plain grid of coloured pixels, the format a
printed page or a photo actually needs. ``web/img/`` already holds the
six real map renders that CARTOGRAPHY's choropleth and situation-map
figures embed (three choropleth colour ramps at 1440 by 812 pixels, two
of them generated but only two ultimately used; four situation maps),
each kept alongside the SVG file it was rasterized from. That means the
web gallery's PNG thumbnails and this print document's own image copies
are both just one rasterization step away from the same underlying
source, so they can never quietly drift apart. Those web thumbnails are
sized for a browser window (900 pixels wide) and look soft once placed
at full page width in a printed PDF (Portable Document Format) file.
This script re-rasterizes the same SVGs at a much higher pixel width,
through the same rasterizer the generators themselves already use
(``resvg_py``, a Python binding to ``resvg``, a rasterizing engine
written in the Rust programming language, called from
:func:`_render._svg_to_png_bytes`), and writes the sharper results to
``doc/img/``, a folder dedicated to this printed document's own figure
copies, kept separate from the web gallery's.

Usage example
-------------
>>> True  # this module runs as a script; import-time side effects only
True

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import resvg_py

#: Print target width, in pixels, for a figure placed at full text width in
#: the LaTeX document (roughly 6.3 inches at the document's margins) at a
#: sharp 300-plus pixels-per-inch print resolution.
_PRINT_WIDTH_PX = 2400

#: Every SVG this document embeds, vendored already in ``web/img/``.
_SOURCE_NAMES = (
    "choropleth-sequential",
    "choropleth-diverging",
    "situation-switzerland",
    "situation-iberia",
    "situation-western-europe",
    "situation-himalaya",
)


def rasterize(svg_path: Path, out_path: Path, *, width: int = _PRINT_WIDTH_PX) -> None:
    """Rasterize one SVG file to a PNG file at a fixed pixel width.

    Parameters
    ----------
    svg_path : pathlib.Path
        Source SVG file.
    out_path : pathlib.Path
        Destination PNG file.
    width : int, optional
        Output width in pixels (default :data:`_PRINT_WIDTH_PX`); height
        follows the source SVG's own aspect ratio automatically since only
        ``width`` is passed to the rasterizer, not ``height``.

    Examples
    --------
    >>> import tempfile
    >>> tiny_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">' \\
    ...     '<rect width="10" height="10" fill="red"/></svg>'
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     src = Path(tmp) / "tiny.svg"
    ...     dst = Path(tmp) / "tiny.png"
    ...     _ = src.write_text(tiny_svg)
    ...     rasterize(src, dst, width=20)
    ...     dst.exists()
    True
    """
    png_bytes = resvg_py.svg_to_bytes(svg_path=str(svg_path), width=width)
    out_path.write_bytes(bytes(png_bytes))


def main() -> None:
    """Rasterize every vendored map SVG at print resolution into ``doc/img/``.

    Examples
    --------
    >>> callable(main)
    True
    """
    repo_root = Path(__file__).resolve().parent.parent
    web_img = repo_root / "web" / "img"
    doc_img = repo_root / "doc" / "img"
    doc_img.mkdir(parents=True, exist_ok=True)
    for name in _SOURCE_NAMES:
        svg_path = web_img / f"{name}.svg"
        out_path = doc_img / f"{name}.png"
        rasterize(svg_path, out_path)
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
