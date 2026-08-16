"""
_svg: small, output-identical SVG building blocks shared by the make_*.py generators.

Every ``make_<id>.py`` generator writes its own SVG (Scalable Vector
Graphics, an image format made of shapes and paths described as text,
rather than a grid of coloured dots) by hand, assembling it piece by
piece from Python f-strings. A handful of small building blocks turned
up, worded identically, in three or more of those generators. This
module is where such a piece gets pulled out, and only such a piece:
every function here can be swapped in for the inline code it replaces
while producing the exact same bytes of output, so factoring it out
changes nothing about what actually renders. (Some of the generators
named below, for historical reasons explained at the end of this
docstring, live in the sibling repository, sprezzature-figures, not in
this one.)

* :func:`xml_escape`: the standard three-step text escape that makes a
  string safe to place inside XML markup (turning the literal characters
  ``&``, ``<``, and ``>`` into ``&amp;``, ``&lt;``, and ``&gt;``, since
  those three characters have special meaning to an XML parser and would
  otherwise be read as markup instead of text). About eleven generators
  had each written their own private copy of this, usually named
  ``_xml`` or ``_esc``.
* :func:`point_on_circle`: converts a polar coordinate (an angle and a
  distance from a centre point) to the Cartesian, x/y coordinate an SVG
  actually needs to draw at: ``(cx + r*cos(theta), cy + r*sin(theta))``,
  with ``theta`` already expressed in radians. Several generators that
  lay elements out in a circle (chord, windrose, radviz, speaking-time)
  had this formula written out inline.
* :func:`fmt_compact`: formats a number to one decimal place, then trims
  any trailing zero and, if nothing is left after the decimal point, the
  decimal point itself, for use inside SVG path data (the string of
  coordinates that defines a curve or shape). Three generators
  (streamgraph, difference-chart, bollinger) each carried this as a
  private ``_fmt`` helper.
* :func:`catmull_rom_beziers`: converts a Catmull-Rom spline (a smooth
  curve defined by simply passing through a list of points, popular
  because you never have to hand-place control handles) into the cubic
  Bézier ``C`` commands SVG path data actually understands. The same
  three generators above each carried this as a private
  ``_catmull_rom``. The caller supplies its own number-formatting
  function, so the text this produces stays byte-identical to before;
  all three pass it :func:`fmt_compact`.
* :func:`hex_to_rgb`: converts a ``#RRGGBB`` hex colour string into its
  three separate red, green, and blue integers. The hexbin-map,
  binned-grid-map, and circle-packing generators each had their own
  private ``_hex_to_rgb`` doing the same thing.
* :func:`svg_open`: the responsive, accessible opening ``<svg ...>`` tag
  every figure starts with: an explicit pixel width and height, a
  matching ``viewBox`` (the SVG attribute that lets the image scale
  smoothly to fit any container instead of clipping or leaving blank
  space), the project's house font, and the ARIA (Accessible Rich
  Internet Applications, the standard that lets a screen reader announce
  what an image is) ``role``/``aria-labelledby`` attributes. About 46
  generators opened their document with this exact tag. Only the
  precise shared template is emitted here; a generator whose root tag
  orders its attributes differently (andrews, for instance, which leads
  with ``aria-label`` instead) kept its own inline version, so that
  every adoption still matches its generator's previous output byte for
  byte.

Deliberately left out of this module: the per-element hover and tooltip
wrappers (the small ``<g tabindex=...><title>...`` blocks and their
``:hover`` CSS rules) and the pill-shaped label backgrounds. Those
differ from generator to generator in class names, ARIA wiring, and
corner rounding, so no single shared version could reproduce every
generator's existing output exactly, and changing rendered bytes during
this kind of refactor (a change to how code is organized, never to what
it produces) is exactly what must not happen. Each caller keeps its own
number formatting; the functions here only ever return the same raw
string or numbers the inline code used to produce.

A few other candidates looked tempting but were rejected, either because
fewer than three generators actually shared the code (the usual bar for
factoring something out) or because making a shared version would have
changed at least one generator's output: the ring-sector arc path (only
rose and radial-bar use it); the clock-bearing helpers (their behaviour
splits by which arguments are passed, and all of them already call
:func:`point_on_circle` underneath); the Equal Earth map projection
(spike-map and hexbin-map compute it differently, and windbarb uses a
different, equirectangular projection instead); the flow-ribbon paths
(three generators, three unrelated implementations); the sequential
colour ramp (hexbin and binned-grid-map differ in their colour stops,
gamma correction, and light-end anchor); and the convex-hull scan (an
algorithm for finding the smallest polygon that encloses a set of
points, used by only one generator here).

This module imports nothing beyond Python's standard :mod:`math` module,
so it can be imported anywhere ``_style.py`` can, without needing the
heavier data-visualization dependencies some other parts of the project
use.

Historical note: the generator names above (chord, windrose, streamgraph,
and the rest of the roughly 120-kind catalogue) belong to
sprezzature-figures, the sibling repository this module's design
reasoning came from when ``choropleth`` and ``situation_map`` were split
out into their own product, this repo. This copy of the module has since
diverged from that repository's own version; the two are similar in
spirit, not kept byte-identical to each other.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import textwrap
from collections.abc import Callable, Sequence

# Function words that must never be left stranded at the end of a wrapped line
# (house rule: no line-end orphans, EN or FR). See references/corners.md's sibling
# typography note and the no-line-end-orphans memory.
_ORPHAN_WORDS = frozenset(
    [
        "of",
        "the",
        "a",
        "an",
        "to",
        "and",
        "or",
        "for",
        "in",
        "on",
        "by",
        "with",
        "from",
        "is",
        "as",
        "than",
        "per",
        "vs",
        "le",
        "la",
        "les",
        "des",
        "du",
        "de",
        "un",
        "une",
        "et",
        "a",
        "au",
        "aux",
        "dans",
        "sur",
        "pour",
        "par",
    ]
)


def wrap_no_orphan(text: str, width: int) -> list[str]:
    """Word-wrap ``text`` to ``width`` characters per line, then push any line
    that ends on a dangling function word (or an elided ``l'``) down to the next
    line, so no wrapped line ever ends on ``of the`` / ``the`` / ``l'`` ...
    """
    lines = textwrap.wrap(text, width=width) or [""]
    changed = True
    while changed:
        changed = False
        for i in range(len(lines) - 1):
            words = lines[i].split()
            if not words:
                continue
            last = words[-1].lower().rstrip(".,;:")
            if last in _ORPHAN_WORDS or words[-1].endswith(("l'", "l’")):
                moved = words.pop()
                lines[i] = " ".join(words)
                lines[i + 1] = f"{moved} {lines[i + 1]}"
                changed = True
    return [ln for ln in lines if ln] or [""]


try:
    from sprezzature_figures.fonts import DEFAULT_SVG_FACES, svg_font_defs
except ImportError:  # pragma: no cover - fonts.py is stdlib-only, always importable
    DEFAULT_SVG_FACES = ()

    def svg_font_defs(keys: tuple[str, ...] = ()) -> str:  # type: ignore[misc]
        return ""


def xml_escape(text: str) -> str:
    """Escape the three XML metacharacters for safe inclusion in an SVG.

    Replaces ``&``, ``<`` and ``>`` with their entity forms, in that
    order (ampersand first so the ``&`` introduced by ``&lt;`` / ``&gt;``
    is not double-escaped). This is byte-identical to the private
    ``_xml`` / ``_esc`` helpers the generators previously carried; it is
    intentionally minimal (no quote escaping) because generator text only
    ever lands in element content, never inside an attribute value.

    Parameters
    ----------
    text : str
        Raw text (a label, place name, category, …) to embed as SVG
        element content.

    Returns
    -------
    str
        ``text`` with ``&`` → ``&amp;``, ``<`` → ``&lt;``, ``>`` →
        ``&gt;``.

    Examples
    --------
    >>> xml_escape("Tom & Jerry <3")
    'Tom &amp; Jerry &lt;3'
    """
    # Order matters: escape "&" first, otherwise the "&" in "&lt;" / "&gt;"
    # produced by the later replacements would itself get re-escaped.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def point_on_circle(cx: float, cy: float, r: float, theta_rad: float) -> tuple[float, float]:
    """Cartesian point at radius ``r`` and angle ``theta_rad`` about a centre.

    Standard math convention: ``theta_rad = 0`` points along +x (3
    o'clock) and grows counter-clockwise in a conventional axis — but in
    SVG's y-down space it reads as clockwise. Callers that want "0 = up"
    pass a pre-rotated angle (e.g. ``math.radians(deg - 90.0)``); this
    helper does no rotation of its own, so it returns exactly the pair
    the inline ``cx + r*cos(theta), cy + r*sin(theta)`` produced.

    Parameters
    ----------
    cx : float
        Centre x-coordinate, in user-space pixels.
    cy : float
        Centre y-coordinate, in user-space pixels.
    r : float
        Radius (distance from the centre), in user-space pixels.
    theta_rad : float
        Angle **in radians** (already converted from degrees by the
        caller if needed).

    Returns
    -------
    tuple of float
        The ``(x, y)`` point. Unformatted floats — the caller keeps its
        own ``:.1f`` / ``:.2f`` formatting so output stays identical.

    Examples
    --------
    >>> x, y = point_on_circle(100.0, 100.0, 50.0, 0.0)
    >>> round(x, 6), round(y, 6)
    (150.0, 100.0)
    """
    return cx + r * math.cos(theta_rad), cy + r * math.sin(theta_rad)


def fmt_compact(v: float) -> str:
    """Format a float compactly for SVG path data: one decimal, no trailing zero.

    Rounds to a single decimal place, then strips a trailing ``0`` and a
    now-dangling ``.`` so ``12.0`` prints as ``12`` and ``12.30`` as
    ``12.3``. This is byte-identical to the private ``_fmt`` the
    streamgraph, difference-chart and bollinger generators each carried,
    and the callers pass it straight into :func:`catmull_rom_beziers`.

    Parameters
    ----------
    v : float
        A pixel coordinate (or any path-data number).

    Returns
    -------
    str
        The compact decimal string.

    Examples
    --------
    >>> fmt_compact(12.0)
    '12'
    >>> fmt_compact(12.34)
    '12.3'
    """
    # ``:.1f`` first (so 12.34 -> "12.3"), then drop a trailing zero and the
    # orphaned dot it leaves behind ("12.0" -> "12", "12" stays "12").
    return f"{v:.1f}".rstrip("0").rstrip(".")


def rounded_rect_path(
    x: float,
    y: float,
    w: float,
    h: float,
    r_tl: float = 0.0,
    r_tr: float = 0.0,
    r_br: float = 0.0,
    r_bl: float = 0.0,
) -> str:
    """SVG path ``d`` for a rectangle with per-corner radii (SVG house config
    for the Sprezzature Corner Policy, see references/corners.md).

    Each radius is clamped to half the smaller side so a corner never overshoots.
    Zero-radius corners stay square. Use this (not a plain ``<rect rx>``) whenever
    only *some* corners round — bars, stacked segments, arc-adjacent tiles — so
    baseline and adjacent corners can stay crisp.
    """
    m = min(w, h) / 2.0
    tl, tr, br, bl = (max(0.0, min(v, m)) for v in (r_tl, r_tr, r_br, r_bl))
    f = fmt_compact
    return (
        f"M{f(x + tl)},{f(y)} "
        f"H{f(x + w - tr)} "
        + (f"A{f(tr)},{f(tr)} 0 0 1 {f(x + w)},{f(y + tr)} " if tr else "")
        + f"V{f(y + h - br)} "
        + (f"A{f(br)},{f(br)} 0 0 1 {f(x + w - br)},{f(y + h)} " if br else "")
        + f"H{f(x + bl)} "
        + (f"A{f(bl)},{f(bl)} 0 0 1 {f(x)},{f(y + h - bl)} " if bl else "")
        + f"V{f(y + tl)} "
        + (f"A{f(tl)},{f(tl)} 0 0 1 {f(x + tl)},{f(y)} " if tl else "")
        + "Z"
    )


def bar_path(x: float, y: float, w: float, h: float, r: float, side: str = "top") -> str:
    """SVG path ``d`` for a bar rounded on its value-end only (policy: the
    baseline corners stay square so the bar sits flat on the axis). ``side`` is
    the value-end: ``top`` / ``bottom`` for columns, ``left`` / ``right`` for
    horizontal bars."""
    sides = {
        "top": (r, r, 0.0, 0.0),
        "bottom": (0.0, 0.0, r, r),
        "right": (0.0, r, r, 0.0),
        "left": (r, 0.0, 0.0, r),
    }
    tl, tr, br, bl = sides.get(side, sides["top"])
    return rounded_rect_path(x, y, w, h, tl, tr, br, bl)


def catmull_rom_beziers(
    pts: Sequence[tuple[float, float]],
    fmt: Callable[[float], str],
    tension: float = 6.0,
) -> str:
    """Return SVG ``C`` commands for a smooth Catmull-Rom spline through ``pts``.

    The caller has already emitted the ``M`` (or ``M``/``L``) to
    ``pts[0]``; this appends the cubic-Bézier segments that flow through
    every later point. End tangents are clamped to the terminal points so
    the curve neither drifts nor over-shoots off the ends. Below three
    points it degrades to plain ``L`` line-tos, exactly as the inline
    ``_catmull_rom`` did.

    The float formatter is injected (rather than hard-coded) so the
    emitted string is byte-for-byte identical to each caller's private
    copy: the streamgraph, difference-chart and bollinger generators all
    pass :func:`fmt_compact`, so the ``C``/``L`` numbers match what they
    produced before the extraction.

    Parameters
    ----------
    pts : sequence of (float, float)
        The sample points, in pixel coordinates. ``pts[0]`` is assumed to
        have already been emitted by the caller (as an ``M``/``L``).
    fmt : callable
        The float-to-string formatter to apply to every coordinate — the
        caller's own ``_fmt`` (typically :func:`fmt_compact`). Injecting
        it keeps the output identical to the inline code.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (a plain line-to run when fewer
        than three points are supplied).
    """
    n = len(pts)
    # Fewer than three points cannot form a spline — fall back to straight
    # line-tos through the tail (the caller already emitted pts[0]).
    if n < 3:
        return "".join(f" L{fmt(x)},{fmt(y)}" for x, y in pts[1:])
    seg = []
    for i in range(n - 1):
        # p0..p3 are the four points the uniform Catmull-Rom segment needs;
        # the ends are clamped (repeat the terminal point) so the curve does
        # not swing past the first/last sample.
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        # Catmull-Rom -> Bézier control points: the tangent at each anchor is
        # the neighbour-difference scaled by 1/tension.
        c1x, c1y = p1[0] + (p2[0] - p0[0]) / tension, p1[1] + (p2[1] - p0[1]) / tension
        c2x, c2y = p2[0] - (p3[0] - p1[0]) / tension, p2[1] - (p3[1] - p1[1]) / tension
        seg.append(f" C{fmt(c1x)},{fmt(c1y)} {fmt(c2x)},{fmt(c2y)} {fmt(p2[0])},{fmt(p2[1])}")
    return "".join(seg)


def svg_open(
    width: object,
    height: object,
    title_id: str,
    desc_id: str,
    *,
    font_family: str = "Roboto, system-ui, sans-serif",
    embed_fonts: bool = True,
) -> str:
    """Return the responsive, accessible ``<svg>`` opening tag the figures share.

    Nearly every ``make_<id>.py`` generator opens its document with the *same*
    root element: an explicit ``width``/``height`` for a sensible intrinsic
    size, a ``viewBox="0 0 width height"`` so the graphic scales fluidly to any
    container (this is what makes the SVG **responsive** — a viewer can set
    ``width:100%`` and the coordinates rescale), the house ``font-family``, and
    ``role="img"`` + ``aria-labelledby`` wiring the ``<title>``/``<desc>`` pair
    that follows into one accessible name for screen readers. The ``<title>``
    also surfaces as the browser's native hover tooltip.

    This returns exactly the string those generators assembled inline, so
    adopting it leaves the rendered bytes unchanged. The ``<title>`` and
    ``<desc>`` elements themselves stay in the caller (their text is
    figure-specific); this helper only emits the root tag that references them
    by the two ids passed here.

    Parameters
    ----------
    width : object
        Canvas width in user-space pixels. Stringified as-is (an ``int`` prints
        without a decimal point), matching the inline ``f"{width}"``.
    height : object
        Canvas height in user-space pixels. Stringified as-is.
    title_id : str
        The ``id`` of the ``<title>`` element the caller emits next (e.g.
        ``"vn-title"``); becomes the first token of ``aria-labelledby``.
    desc_id : str
        The ``id`` of the ``<desc>`` element (e.g. ``"vn-desc"``); the second
        ``aria-labelledby`` token.
    font_family : str, optional
        CSS font stack for the whole document. Defaults to the house stack
        ``"Roboto, system-ui, sans-serif"``; pass a different string for the
        (few) generators that inject their own.
    embed_fonts : bool, optional
        When true (the default), the returned string also carries a
        ``<defs><style>@font-face…</style></defs>`` block embedding the
        bundled Roboto + Roboto Mono WOFF2 faces as base64 data URIs (see
        ``sprezzature_figures.fonts``), so the SVG renders the house
        typography correctly wherever it is opened -- no dependency on the
        viewer having Roboto installed. Pass ``False`` for a lighter,
        font-independent tag (e.g. tests, or a caller that already emits
        its own ``<defs>``).

    Returns
    -------
    str
        The ``<svg ...>`` opening tag, optionally followed by an embedded
        ``<defs>`` font block.

    Examples
    --------
    >>> svg_open(800, 600, "vn-title", "vn-desc", embed_fonts=False)
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600" font-family="Roboto, system-ui, sans-serif" role="img" aria-labelledby="vn-title vn-desc">'
    """
    # One f-string so the emitted bytes match the generators' multi-fragment
    # concatenation exactly; the viewBox mirrors width/height so the graphic
    # scales to its container without distortion.
    tag = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{font_family}" role="img" '
        f'aria-labelledby="{title_id} {desc_id}">'
    )
    if embed_fonts and DEFAULT_SVG_FACES:
        tag += svg_font_defs(DEFAULT_SVG_FACES)
    return tag


def hex_to_rgb(hexv: str) -> tuple[int, int, int]:
    """Convert a ``#RRGGBB`` string to an ``(r, g, b)`` integer triple.

    Strips an optional leading ``#`` then reads the three hex byte pairs.
    Byte-identical to the private ``_hex_to_rgb`` the hexbin-map,
    binned-grid-map and circle-packing generators each carried (one used
    the parameter name ``h``, but the returned triple is the same).

    Parameters
    ----------
    hexv : str
        A colour as ``#RRGGBB`` (the leading ``#`` is optional).

    Returns
    -------
    tuple of int
        The ``(r, g, b)`` channels, each ``0..255``.

    Examples
    --------
    >>> hex_to_rgb("#FF9500")
    (255, 149, 0)
    """
    h = hexv.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
