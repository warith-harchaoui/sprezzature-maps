"""
_interactive: the interactivity-mode layer shared by every make_*.py generator.

An SVG figure can ship in one of three interactivity modes. The choice is
a plain argument on the generator, defaulting to ``"self-contained"``:

* ``"self-contained"``: the SVG carries its own fullscreen button, plus the
  small script that makes the button work. Opened directly in a browser,
  served through an HTML ``<object>`` tag, or pasted straight into a page,
  the figure works entirely on its own, with no page-level JavaScript
  needed. This is the default because the SVG file itself is the whole
  deliverable; nothing else has to ship alongside it.
* ``"external"``: the SVG ships without its own button. A page-level
  script (``figure-fullscreen.js``) supplies the button and a richer
  tooltip, and drives fullscreen for every figure on a dashboard at once.
  The internal layer stays off in this mode precisely so the two never
  both try to draw a button.
* ``"static"``: no interactivity at all, just the responsive sizing
  (``viewBox``, the SVG attribute that lets an image scale cleanly to any
  container) that :func:`_svg.svg_open` already provides. For print, or
  for embedding as a plain ``<img>``.

This module owns the one piece that is genuinely identical across every
figure: the fullscreen wiring, a small generic script with no visible
appearance of its own. Each generator still owns its own figure-specific
clickable regions and tooltips.

There is no visible on-canvas button; the whole figure is the clickable
target. An SVG embedded through an ``<img>`` tag never runs the
``<script>`` at all (browsers do not execute scripts inside SVGs
referenced that way), so nothing changes for a thumbnail: the script only
ever runs once the SVG is loaded as a real, live document rather than
just displayed as a picture.

The module imports nothing, not even from the standard library, so it
loads wherever a generator does. It composes with :func:`_svg.svg_open`
(the responsive, accessible root tag every figure opens with) and mirrors
the same contract as ``sprezzature-ui/assets/components/figure-fullscreen.html``,
the equivalent piece on the web-UI side.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

#: The three supported interactivity modes (see the module docstring).
MODES = ("self-contained", "external", "static")

#: Generic fullscreen script, identical for every figure. No on-canvas icon —
#: the whole figure is the hit target, so it stays clean at thumbnail size.
#: Stands down inside a page-module-managed card (``[data-fs-target]``) and
#: never runs at all inside an ``<img>``-embedded SVG (browsers don't execute
#: scripts there).
#:
#: Three contexts, told apart by ``window.frameElement``:
#:
#: * **Gallery card** (embedded as a live ``<object>``, ``window.parent`` is
#:   the host page, not the lightbox's own object): a click anywhere on the
#:   figure can never bubble to the host page — ``<object>`` is a real,
#:   isolated document. So a click posts a message instead; ``lightbox.js`` in
#:   the web repo opens the modal on receipt. This keeps the card's own
#:   ``pointer-events:auto`` (native hover/``<title>`` tooltips stay live).
#: * **Lightbox's own enlarged object** (``data-lb-obj``): the figure is
#:   already shown at modal size, so a click on it does nothing extra.
#: * **Standalone** (opened as its own file/tab, or inlined outside the
#:   gallery — no ``frameElement`` at all): there is no host page to hand off
#:   to, so a click (or Enter/Space once focused) toggles the browser's own
#:   Fullscreen API directly on the SVG.
_FS_SCRIPT = (
    "(function(){"
    "var me=document.currentScript,svg=me.ownerSVGElement||me.parentNode;"
    # A page module owns this figure (dashboard): let it drive; do nothing here.
    "if(svg.closest&&svg.closest('[data-fs-target]'))return;"
    "var fe=null;try{fe=window.frameElement}catch(err){}"
    "if(fe&&fe.hasAttribute('data-lb-obj'))return;"  # already full-size in the lightbox
    "if(fe&&window.parent!==window){"
    "svg.addEventListener('click',function(){"
    "window.parent.postMessage({szFig:1,type:'open-fullscreen'},'*');"
    "});"
    "return;"
    "}"
    "var req=svg.requestFullscreen||svg.webkitRequestFullscreen;"
    "if(!req)return;"
    "var t=function(){var f=document.fullscreenElement||document.webkitFullscreenElement;"
    "if(f===svg)(document.exitFullscreen||document.webkitExitFullscreen).call(document);"
    "else req.call(svg);};"
    "svg.style.cursor='pointer';"
    "svg.setAttribute('tabindex','0');"
    "svg.addEventListener('click',t);"
    "svg.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();t();}});"
    "})();"
)


def fullscreen_control(
    width: float,
    height: float,
    mode: str = "self-contained",
    *,
    inset: float = 14.0,
) -> str:
    """Return the fullscreen wiring script for a figure, per interactivity mode.

    Append the result just before the closing ``</svg>`` of a generator's
    document. In ``"self-contained"`` mode it is the generic wiring script
    (see :data:`_FS_SCRIPT`) — no on-canvas button, the whole figure is the
    hit target. In ``"external"`` and ``"static"`` modes it is the empty
    string, so nothing ships.

    Parameters
    ----------
    width, height : float
        The SVG canvas size. Unused now that there is no button to place, but
        kept in the signature so the ~90 existing call sites (and any future
        placement need) stay source-compatible.
    mode : str, optional
        One of :data:`MODES`. Defaults to ``"self-contained"``.
    inset : float, optional
        Unused now that there is no button to place; kept for the same
        call-site-compatibility reason as ``width``/``height``.

    Returns
    -------
    str
        The ``<script>`` fragment, or ``""`` for the non-self-contained modes.

    Raises
    ------
    ValueError
        If ``mode`` is not one of :data:`MODES`.

    Examples
    --------
    >>> fullscreen_control(800, 600, "static")
    ''
    >>> fullscreen_control(800, 600, "external")
    ''
    >>> "<script>" in fullscreen_control(800, 600)
    True
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    # External mode defers to the page module; static ships no interactivity.
    if mode != "self-contained":
        return ""
    _ = width, height, inset  # kept for call-site compatibility; see docstring.
    return f"<script><![CDATA[{_FS_SCRIPT}]]></script>"


def hover_isolate_css(class_name: str, count: int, *, dim: float = 0.35) -> str:
    """Return the "hover one mark, dim the rest" CSS block shared by figures
    with N repeated marks (bars, bands, arcs, nodes, edges, ...).

    Every hand-authored generator with a small multiple of marks (one per
    category/series/node) wants the same interaction: hovering or focusing
    *any* mark dims all the others so the hovered one reads clearly. Rather
    than every generator hand-writing this CSS block (it was drifting
    slightly differently across files), this is the one shared source.

    Expects each mark to carry both a shared class (``class_name``) and an
    index-suffixed class (``f"{class_name}-{i}"`` for ``i`` in
    ``range(count)``) — e.g. ``class="band band-2"`` for the third band. The
    figure-specific parts (the marks themselves, tooltips, colors) stay in
    the generator; only this interaction pattern is shared.

    Parameters
    ----------
    class_name : str
        The shared class every mark carries (e.g. ``"band"``, ``"node"``).
    count : int
        How many marks there are (indices ``0..count-1``).
    dim : float, optional
        Opacity applied to non-hovered marks while any mark is hovered/focused
        (default ``0.35``).

    Returns
    -------
    str
        A ``<style>``-ready CSS string (no surrounding ``<style>`` tags).

    Examples
    --------
    >>> css = hover_isolate_css("band", 3)
    >>> ".band{transition:opacity .15s ease;}" in css
    True
    >>> "svg:has(.band-2:hover,.band-2:focus) .band-2{opacity:1;}" in css
    True
    """
    per_mark = "".join(
        f"svg:has(.{class_name}-{i}:hover,.{class_name}-{i}:focus) .{class_name}-{i}{{opacity:1;}}"
        for i in range(count)
    )
    return (
        f".{class_name}{{transition:opacity .15s ease;}}"
        f"svg:hover .{class_name},svg:focus-within .{class_name}{{opacity:{dim};}}"
        f"{per_mark}"
        "@media (prefers-reduced-motion: reduce){"
        f".{class_name}{{transition:none;}}"
        "}"
    )
