"""
_render: the finishing steps shared by every ``make_<id>.py`` generator.

Each ``make_<id>.py`` in this folder builds a figure as one long SVG text
string, then runs the exact same three-step ending: work out where the
file should go by default (under ``<skill>/assets/svg-examples/<id>.svg``,
one path per figure kind), create that folder if it doesn't exist yet,
write the text to disk as UTF-8, and print ``wrote <path>`` so a person
running the script by hand from a terminal can see where the file landed.
That ending used to be copied, word for word, into roughly sixty
generators. This module is the one place it lives now, so a fix or a
change to it only has to happen once.

Only the parts that really were identical, byte for byte, across every
generator are pulled out here: the path calculation, the
create-folder/write-file/print sequence, and, for the handful of
generators that expose a command-line ``--out`` flag, the small amount of
argparse (Python's standard command-line-argument parser) wiring needed
for that flag. Each generator's own ``build_svg`` function, the part that
actually draws the figure, stays in its own file; this module never
touches the SVG text itself, so adopting it changes nothing about what
gets rendered. A few generators have a non-standard ending of their own
(an animated variant that renders twice, or a map that also writes out a
matching PNG image); those still call :func:`write_svg` and
:func:`svg_example_path` for the parts they do share, and keep their
extra step written out inline.

This module imports only from Python's standard library (``argparse`` and
``pathlib``, nothing that needs installing), so it works wherever a
generator already runs, without needing the heavier data-visualization
dependencies some other parts of the project use. The ``wrote <path>``
line is a deliberate message meant for the person running the command
(these scripts are meant to be run by hand from a terminal), not an
internal diagnostic log, which is why it stays a plain ``print`` rather
than going through a logging system.

Consumers
---------
The ``make_<id>.py`` generators in this same ``scripts/`` directory, via
``from _render import svg_example_path, write_svg, render_cli``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import inspect
import os
from collections.abc import Callable
from pathlib import Path


def _render_scale() -> float:
    """Read the raster/PDF scale factor from ``SPREZZATURE_RENDER_SCALE``.

    Threading a ``--scale`` argument through every ``make_<id>.py`` generator
    would mean editing ~90 hand-authored signatures; instead the render CLIs
    set this one environment variable just before they call the generator, and
    the single rasterisation choke point below reads it. Absent or unparseable,
    the scale is ``1.0`` (native pixel size), so the default output is unchanged.
    A non-positive value is ignored the same way — ``resvg_py`` would reject it.
    """
    raw = os.environ.get("SPREZZATURE_RENDER_SCALE")
    if not raw:
        return 1.0
    try:
        scale = float(raw)
    except ValueError:
        return 1.0
    return scale if scale > 0 else 1.0


def svg_example_path(script_file: str, figure_id: str) -> Path:
    """Return the canonical ``assets/svg-examples/<figure_id>.svg`` for a generator.

    Every generator writes, by default, to a file named after its figure inside
    the skill's ``assets/svg-examples`` folder — a sibling of the ``scripts``
    directory the generator lives in. Passing ``__file__`` lets this helper
    locate that folder relative to the *calling* script, exactly as the inline
    ``Path(__file__).resolve().parent.parent / "assets" / "svg-examples" /
    f"{figure_id}.svg"`` expression did, so the resolved path is identical.

    Parameters
    ----------
    script_file : str
        The calling generator's ``__file__``. Resolved to an absolute path so
        the result does not depend on the current working directory.
    figure_id : str
        The figure's short identifier (e.g. ``"dumbbell"``, ``"hexbin-map"``).
        Becomes the output file's stem; ``.svg`` is appended here.

    Returns
    -------
    pathlib.Path
        The absolute path ``<skill>/assets/svg-examples/<figure_id>.svg``.

    Examples
    --------
    >>> p = svg_example_path("/repo/sprezzature-figures/scripts/make_venn.py", "venn")
    >>> p.as_posix().endswith("sprezzature-figures/assets/svg-examples/venn.svg")
    True
    """
    # ``.parent`` is the scripts/ dir; ``.parent.parent`` is the skill root that
    # holds assets/. Resolve first so a relative ``__file__`` still works.
    return (
        Path(script_file).resolve().parent.parent / "assets" / "svg-examples" / f"{figure_id}.svg"
    )


def write_svg(out: Path, svg: str, *, embed_fonts: bool = True) -> Path:
    """Write ``svg`` to ``out`` (creating parents) and echo ``wrote <out>``.

    This is the identical three-line tail every generator carried: ensure the
    destination directory exists, write the string as UTF-8, and print a
    one-line confirmation of where the file went. The confirmation is a
    user-facing CLI message (the generators are run by hand), not diagnostic
    logging, so it stays a plain ``print``.

    Also the shared choke point for font embedding: every generator hand-writes
    its SVG via ``_svg.svg_open(embed_fonts=True)``, which already carries an
    embedded ``@font-face`` block. When ``embed_fonts`` is true (the default)
    and the string does not already carry one, this splices the bundled
    Roboto/Roboto Mono ``@font-face`` block in right after the opening
    ``<svg ...>`` tag, so the raster/PDF export stays font-independent even
    for a caller that built its own SVG string by hand.

    Parameters
    ----------
    out : pathlib.Path
        Destination file path — typically the return of
        :func:`svg_example_path`, or a caller-supplied ``--out`` override.
    svg : str
        The complete SVG document to write.
    embed_fonts : bool, optional
        Splice in the embedded font block if the document doesn't already
        have one (default ``True``). Pass ``False`` to skip (e.g. a caller
        writing a non-SVG file that happens to reuse this helper).

    Returns
    -------
    pathlib.Path
        ``out`` unchanged, so callers can chain or log it if they wish.

    Examples
    --------
    >>> write_svg(Path("/tmp/venn.svg"), "<svg .../>")  # doctest: +SKIP
    PosixPath('/tmp/venn.svg')
    """
    if embed_fonts and "@font-face" not in svg and svg.lstrip().startswith("<svg"):
        from sprezzature_figures.fonts import DEFAULT_SVG_FACES, svg_font_defs

        if DEFAULT_SVG_FACES:
            insert_at = svg.index(">") + 1
            svg = svg[:insert_at] + svg_font_defs(DEFAULT_SVG_FACES) + svg[insert_at:]
    # ``parents=True`` mirrors the inline ``mkdir(parents=True, exist_ok=True)``
    # so a fresh checkout (no assets/ yet) still succeeds.
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_in_format(out, svg)
    # User-facing confirmation, byte-identical to the generators' own line.
    print(f"wrote {out}")
    return out


def _svg_to_png_bytes(svg: str) -> bytes:
    """Rasterise a complete SVG document to PNG bytes at :func:`_render_scale`.

    ``resvg_py`` (a thin wrapper around the Rust ``resvg`` crate) is the
    house rasteriser: it needs no browser, no Node, and no Vega runtime, and
    it renders exactly the static markup the hand-authored generators emit
    (embedded ``@font-face`` fonts, gradients, filters) rather than
    re-interpreting a chart grammar.
    """
    import resvg_py

    zoom = _render_scale()
    return resvg_py.svg_to_bytes(svg_string=svg, zoom=zoom if zoom != 1.0 else None)


def _write_in_format(out: Path, svg: str) -> None:
    """Write ``svg`` to ``out`` honouring the destination extension.

    The generators all build an SVG string; a user who asks for ``--out
    chart.png`` expects a PNG, not SVG bytes in a ``.png`` file. This converts
    the (font-embedded, self-contained) SVG to the requested raster/vector
    format: PNG comes straight from :func:`_svg_to_png_bytes`; PDF and JPEG go
    through that same PNG by way of Pillow (already a house dependency),
    since PNG is the only raster format the rasteriser itself emits.
    ``.svg`` stays a plain UTF-8 write, byte-for-byte what every generator
    produced before, so nothing about the SVG path changes. Unknown
    extensions fall back to writing the SVG text rather than guessing.
    """
    suffix = out.suffix.lower()
    if suffix in ("", ".svg", ".txt"):
        out.write_text(svg, encoding="utf-8")
    elif suffix in (".html", ".htm"):
        out.write_text(_svg_to_html(svg), encoding="utf-8")
    elif suffix == ".png":
        out.write_bytes(_svg_to_png_bytes(svg))
    elif suffix in (".pdf", ".jpg", ".jpeg"):
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(_svg_to_png_bytes(svg)))
        if suffix == ".pdf":
            image.convert("RGB").save(out, format="PDF")
        else:
            # JPEG has no alpha channel; flatten onto white first.
            flat = Image.new("RGB", image.size, "#FFFFFF")
            flat.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
            flat.save(out, format="JPEG", quality=92)
    else:
        # Unknown extension (e.g. .json): the generator only has an SVG string,
        # so write that rather than silently producing a mislabelled binary.
        out.write_text(svg, encoding="utf-8")


def _svg_to_html(svg: str) -> str:
    """Wrap a standalone SVG in a minimal, responsive HTML document."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<style>html,body{margin:0;height:100%}"
        "body{display:grid;place-items:center;background:#fff}"
        "svg{max-width:100%;height:auto}</style>\n"
        "</head>\n<body>\n" + svg + "\n</body>\n</html>\n"
    )


def render_cli(
    script_file: str,
    figure_id: str,
    build_svg: Callable[[], str],
    *,
    description: str,
) -> None:
    """Run the standard ``--out`` command line for an SVG generator.

    Wraps the argparse boilerplate the ``--out``-exposing generators shared:
    a single optional ``--out`` argument that defaults to the canonical
    :func:`svg_example_path`, followed by a :func:`write_svg` of
    ``build_svg()``'s result. The default path and the ``wrote <path>`` output
    are unchanged from the inline version, so behaviour is preserved.

    Parameters
    ----------
    script_file : str
        The calling generator's ``__file__`` (used to resolve the default
        output path).
    figure_id : str
        The figure's short identifier; sets both the default file name and the
        wording of the ``--out`` help text.
    build_svg : callable
        Zero-argument function returning the complete SVG document string. It is
        called only after arguments parse, so ``--help`` stays cheap.
    description : str
        One-line description shown at the top of ``--help``.

    Returns
    -------
    None
        The SVG is written as a side effect; nothing is returned.
    """
    default_out = svg_example_path(script_file, figure_id)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help=f"output SVG path (default: the skill's svg-examples/{figure_id}.svg)",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained)",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    parser.add_argument(
        "--language",
        choices=("en", "fr"),
        default="en",
        help="chrome-text language for title/subtitle/legend (default: en).",
    )
    args = parser.parse_args()
    # Build lazily (after parsing) so ``--help`` never runs the figure code.
    # Pass ``mode`` / ``accessibility`` / ``language`` only to generators
    # whose ``build_svg`` accepts them, so this helper keeps working for
    # figures that have not adopted these arguments yet.
    params = inspect.signature(build_svg).parameters
    kwargs = {}
    if "mode" in params:
        kwargs["mode"] = args.mode
    if "accessibility" in params:
        kwargs["accessibility"] = args.accessibility
    if "language" in params:
        kwargs["language"] = args.language
    write_svg(args.out, build_svg(**kwargs))


if __name__ == "__main__":  # pragma: no cover - smoke check, not a generator
    # This module is a library for the generators, not a generator itself.
    # Running it directly just proves the path helper resolves sensibly.
    print(svg_example_path(__file__, "example"))
