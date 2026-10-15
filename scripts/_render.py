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
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import inspect
import os
import re
from collections.abc import Callable
from pathlib import Path

#: The root ``width``/``height`` of a plate sized for a printed page.
#:
#: ``print_width`` puts a physical size on the root (``width="90mm"``), which
#: is the whole point of it: the file then lands at exactly that size in
#: InDesign or ``\includegraphics``. The rasteriser will not read it.
_PHYSICAL_SIZE_RE = re.compile(
    r'\s(width|height)="\s*[\d.]+\s*(?:mm|cm|in|pt|pc|q)"', re.I
)

#: The root ``viewBox``, which carries the drawing's own coordinate system.
_VIEWBOX_RE = re.compile(r'viewBox="\s*[\d.+-]+\s+[\d.+-]+\s+([\d.]+)\s+([\d.]+)\s*"')

#: One root dimension with its unit, for reading a plate's intended print size.
_ROOT_DIM_RE = re.compile(r'\s(width|height)="\s*([\d.]+)\s*(mm|cm|in|pt|pc)"', re.I)

#: Millimetres per unit, for the units ``print_width`` accepts.
_MM_PER_UNIT: dict[str, float] = {
    "mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.0, "pc": 25.4 / 6.0,
}


def _render_scale() -> float:
    """Read the raster/PDF scale factor from ``SPREZZATURE_RENDER_SCALE``.

    Threading a ``--scale`` argument through every ``make_<id>.py`` generator
    would mean editing ~90 hand-authored signatures; instead the render CLIs
    set this one environment variable just before they call the generator, and
    the single rasterisation choke point below reads it. Absent or unparseable,
    the scale is ``1.0`` (native pixel size), so the default output is unchanged.
    A non-positive value is ignored the same way: ``resvg_py`` would reject it.
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
    the skill's ``assets/svg-examples`` folder, a sibling of the ``scripts``
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


def write_svg(
    out: Path,
    svg: str,
    *,
    embed_fonts: bool = True,
    faces: tuple[str, ...] | None = None,
) -> Path:
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
        Destination file path: typically the return of
        :func:`svg_example_path`, or a caller-supplied ``--out`` override.
    svg : str
        The complete SVG document to write.
    embed_fonts : bool, optional
        Splice in the embedded font block if the document doesn't already
        have one (default ``True``). Pass ``False`` to skip (e.g. a caller
        writing a non-SVG file that happens to reuse this helper).
    faces : tuple of str, optional
        Which font faces to embed, from ``sprezzature_figures.fonts``'s
        ``available_faces()``. Defaults to that module's ``DEFAULT_SVG_FACES``
        (``sans`` + ``mono``). Pass the full set when the plate draws serif
        text, so the family it names is the family it carries.

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

        # The default pair is sans + mono. A plate that sets a *serif* in its
        # text has to say so, or it embeds two families it never names and
        # draws in a third one it never shipped -- which is exactly what the
        # density plate did: 427 KB of Roboto and Roboto Mono base64 in a
        # 525 KB file, while every `<text>` asked for Georgia.
        wanted = faces if faces is not None else DEFAULT_SVG_FACES
        if wanted:
            insert_at = svg.index(">") + 1
            svg = svg[:insert_at] + svg_font_defs(tuple(wanted)) + svg[insert_at:]
    # ``parents=True`` mirrors the inline ``mkdir(parents=True, exist_ok=True)``
    # so a fresh checkout (no assets/ yet) still succeeds.
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_in_format(out, svg)
    # User-facing confirmation, byte-identical to the generators' own line.
    print(f"wrote {out}")
    return out


def _size_in_pixels(svg: str) -> str:
    """Return ``svg`` with any physical root size replaced by its viewBox size.

    ``resvg_py`` refuses a document whose root is measured in millimetres --
    *"SVG has an invalid size"*, on a one-rectangle document as readily as on
    a plate -- so a plate built for a journal column could be written as
    ``.svg`` and not as ``.png`` or ``.pdf``. Two shipped features that did
    not compose, and nothing caught it because the print-width tests read the
    SVG string and never rasterise it.

    Substituted here and nowhere else: the ``.svg`` a user asks for still
    carries the physical size, because that is what it is for. Nothing about
    the drawing changes either way -- the viewBox is the coordinate system
    every path is already written in, and the root size only ever said how
    large to present it.

    Examples
    --------
    >>> doc = '<svg viewBox="0 0 100 50" width="90mm" height="45mm"><rect/></svg>'
    >>> _size_in_pixels(doc)
    '<svg width="100" height="50" viewBox="0 0 100 50"><rect/></svg>'

    A plate already measured in user units is handed back untouched:

    >>> plain = '<svg viewBox="0 0 100 50" width="100" height="50"><rect/></svg>'
    >>> _size_in_pixels(plain) == plain
    True
    """
    if not _PHYSICAL_SIZE_RE.search(svg[: svg.find(">") + 1] or svg):
        return svg
    box = _VIEWBOX_RE.search(svg)
    if not box:
        # No coordinate system to fall back on. Handing it over unchanged
        # gets resvg's own refusal, which names the real problem better than
        # a guessed size would hide it.
        return svg
    head_end = svg.find(">") + 1
    head = _PHYSICAL_SIZE_RE.sub("", svg[:head_end])
    sized = head.replace(
        "<svg", f'<svg width="{box.group(1)}" height="{box.group(2)}"', 1
    )
    return sized + svg[head_end:]


def _print_width_mm(svg: str) -> float | None:
    """Return the width in millimetres a plate was built to print at, if it says.

    ``print_width`` is the only thing that puts a physical unit on the root,
    and it exists because journals specify figures in millimetres. A PDF has
    a page size, so it is the one output format that can carry that intent
    rather than merely record it.

    Examples
    --------
    >>> _print_width_mm('<svg width="90mm" height="45mm" viewBox="0 0 2 1"/>')
    90.0
    >>> _print_width_mm('<svg width="3.5in" height="2in" viewBox="0 0 2 1"/>')
    88.9
    >>> _print_width_mm('<svg width="900" height="450" viewBox="0 0 2 1"/>') is None
    True
    """
    found = _ROOT_DIM_RE.search(svg[: svg.find(">") + 1] or svg)
    if not found or found.group(1).lower() != "width":
        return None
    return round(float(found.group(2)) * _MM_PER_UNIT[found.group(3).lower()], 4)


#: The external renderer that turns an SVG into a real vector page.
#:
#: ``rsvg-convert`` ships with librsvg, which is the one converter measured
#: against this project's own plates that got all three of page size,
#: typography and layer fidelity right. The two alternatives each failed
#: visibly: ``cairosvg`` -- on the same cairo build -- drew the white halo
#: behind every place name and not the name, so a map came out with its
#: toponyms erased; headless Chromium printed the plate's interactive layer
#: panel into the figure and fell back to Times for part of the type.
_VECTOR_RENDERER = "rsvg-convert"

#: Extensions a vector page can be written in, and the ``-f`` rsvg takes.
_VECTOR_FORMATS: dict[str, str] = {".pdf": "pdf", ".eps": "eps"}


def _vector_bytes(svg: str, fmt: str) -> bytes | None:
    """Return ``svg`` rendered to ``fmt`` as a vector page, or ``None``.

    ``None`` means the renderer is not installed, which is a normal state and
    not an error: it is an optional system package, and the caller falls back
    to a raster page and says so rather than failing a render over it.

    The SVG goes in on stdin, so nothing is written to a temporary file --
    the document carries its own fonts and rasters inline and has no relative
    references for a working directory to resolve.
    """
    import shutil
    import subprocess

    exe = shutil.which(_VECTOR_RENDERER)
    if not exe:
        return None
    try:
        done = subprocess.run(
            [exe, "-f", fmt],
            input=svg.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # Installed and unhappy with this document. Falling back keeps a
        # render from dying on an optional dependency, and the caller's
        # warning says which page the user ended up with.
        return None
    return done.stdout or None


def _svg_to_png_bytes(svg: str) -> bytes:
    """Rasterise a complete SVG document to PNG bytes at :func:`_render_scale`.

    ``resvg_py`` (a thin wrapper around the Rust ``resvg`` crate) is the
    house rasteriser: it needs no browser and no Node, and
    it renders exactly the static markup the hand-authored generators emit
    (embedded ``@font-face`` fonts, gradients, filters) rather than
    re-interpreting a chart grammar.
    """
    import resvg_py

    zoom = _render_scale()
    return resvg_py.svg_to_bytes(
        svg_string=_size_in_pixels(svg), zoom=zoom if zoom != 1.0 else None
    )


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
    elif suffix in _VECTOR_FORMATS:
        import warnings

        page = _vector_bytes(svg, _VECTOR_FORMATS[suffix])
        if page is not None:
            out.write_bytes(page)
            return
        warnings.warn(
            f"{out.name} is a raster page: every journal that asks for "
            f"{suffix[1:].upper()} asks for vector, and this one is a picture of "
            f"the plate. Install {_VECTOR_RENDERER} (librsvg) and render again "
            "for a vector page, or hand over the .svg, which is vector already.",
            RuntimeWarning,
            stacklevel=2,
        )
        _raster_page(out, svg, suffix)
    elif suffix in (".jpg", ".jpeg"):
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(_svg_to_png_bytes(svg)))
        # JPEG has no alpha channel; flatten onto white first.
        flat = Image.new("RGB", image.size, "#FFFFFF")
        flat.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
        flat.save(out, format="JPEG", quality=92)
    else:
        # Unknown extension (e.g. .json): the generator only has an SVG string,
        # so write that rather than silently producing a mislabelled binary.
        out.write_text(svg, encoding="utf-8")


def _raster_page(out: Path, svg: str, suffix: str) -> None:
    """Write a page with the rasterised plate inside it.

    The fallback when :func:`_vector_bytes` finds no renderer. It is a
    picture of the plate rather than the plate, and the caller has already
    said so -- but it is at least a picture at the right physical size, which
    the version before this was not.
    """
    import io

    from PIL import Image

    image = Image.open(io.BytesIO(_svg_to_png_bytes(svg))).convert("RGB")
    # Pillow lays the page out at the pixel count over the resolution it is
    # given, and its default of 72 turned a plate built for a 90 mm journal
    # column into a 333 mm page -- the exact opposite of what asking for a
    # print width means. Told the real resolution, the page comes out at the
    # size the plate asked to print at.
    wide_mm = _print_width_mm(svg)
    extra = {"resolution": image.width / (wide_mm / 25.4)} if wide_mm else {}
    image.save(out, format="PDF" if suffix == ".pdf" else "EPS", **extra)


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
