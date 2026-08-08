"""
build_doc_map_figures — rasterize the vendored SVG maps at print resolution for doc/CARTOGRAPHY.tex.

Module summary
--------------
``web/img/`` already carries the six real map renders CARTOGRAPHY's
choropleth and situation-map figures embed (three choropleth ramps at
1440x812, two shared but only two used; four situation maps), each kept
alongside its own source Scalable Vector Graphics (SVG) file, a
resolution-independent vector image format, so the web gallery's PNG
thumbnails and this print document's own copies are both one rasterisation
away from the same source of truth. Those web thumbnails are sized for a
browser (900 pixels wide) and read soft once placed at full page width in
a printed Portable Document Format (PDF) file. This script re-rasterizes
the same SVGs at a much higher pixel width, via the same rasterizer
(``resvg_py``, a Python binding to the Rust ``resvg`` engine already used
by :func:`_render._svg_to_png_bytes`) the generators themselves use, and
writes the results to ``doc/img/``, a folder dedicated to this printed
document's own figure copies, kept separate from the web gallery's.

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
