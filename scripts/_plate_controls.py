"""
_plate_controls: the situation plate, made interrogable without a map runtime.

A situation map is an argument about who holds what, and a reader's first
honest question is *which part of this am I being shown*. On paper the
answer is "all of it, at once". On a page it does not have to be.

This adds, to the plate itself and to nothing else:

* **layer switches** -- terrain, water, boundaries, control, marks, notes --
  so a reader can take the claim off the ground and look at the ground, or
  the other way round;
* **a confidence filter**, which is the one that matters for this genre: show
  only what is assessed, or admit reported movement, or admit a belligerent's
  unverified claim. The ladder is already drawn (see ``_CONFIDENCE_TIERS``);
  this makes it a control rather than a legend entry;
* **isolate a class** by clicking it in the legend;
* **a shareable state**, encoded in the URL fragment, so "assessed control
  only, no terrain" is a link rather than an instruction.

The house position is unchanged and is the reason this is built the way it
is. There is no map library, no tile server, no runtime to load: the SVG
file carries its own controls and its own script, so opening the .svg in a
browser, inlining it in a page, or serving it through an ``<object>`` all
give the same working thing, and the file remains the whole deliverable.

**It degrades to today's plate.** The controls are drawn with
``display:none`` and revealed by the script, so an ``<img>`` embed, a
rasteriser, a PDF, or a browser with scripting off all show exactly the map
that shipped before any of this -- which is also what makes the change
checkable against the existing renders.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
from collections.abc import Collection

#: Which drawn group belongs to which switch. A reader does not think in
#: ``admin2-borders``; they think "borders". Grouping is therefore by what
#: the thing *is* to a reader, not by how the generator happens to layer it.
LAYER_GROUPS: dict[str, tuple[str, ...]] = {
    "terrain": ("relief",),
    "water": ("basemap-bathymetry", "lakes", "rivers"),
    "boundaries": ("frontiers", "internal-borders", "admin2-borders"),
    "control": ("areas-of-control", "front-line", "arrows"),
    "marks": ("forces", "events", "cities", "infrastructure"),
    "notes": ("annotation-labels", "annotations"),
}

#: The switch labels, in the order they are drawn.
_SWITCH_ORDER: tuple[tuple[str, str], ...] = (
    ("terrain", "Terrain"),
    ("water", "Water"),
    ("boundaries", "Borders"),
    ("control", "Control"),
    ("marks", "Places"),
    ("notes", "Notes"),
)

#: The confidence ladder as a filter: each step admits everything at or
#: above it in certainty. Mirrors ``_CONFIDENCE_TIERS`` in the generator.
_CONFIDENCE_STEPS: tuple[tuple[str, str], ...] = (
    ("assessed", "Assessed only"),
    ("reported", "+ reported"),
    ("claimed", "+ claimed"),
)


def layer_key_for(group_id: str) -> str | None:
    """Return the switch a drawn group belongs to, or ``None`` if it is chrome.

    Examples
    --------
    >>> layer_key_for("rivers"), layer_key_for("areas-of-control")
    ('water', 'control')
    >>> layer_key_for("legend") is None
    True
    """
    for key, members in LAYER_GROUPS.items():
        if group_id in members:
            return key
    return None



def _steps_for(tiers: Collection[str] | None) -> list[tuple[str, str]]:
    """Return the confidence ladder to offer, or nothing if it would not be one.

    A plate whose zones are all assessed has a single rung. Offering it draws
    a radio that is already on and cannot be turned off -- the same "a control
    that cannot change anything is noise" rule that keeps the whole panel off
    a locator plate. The eastern DRC is that plate, and it wore the useless
    rung until someone opened it.

    Both the markup and the sizing ask this, because a panel sized for a row
    it does not draw is a panel with a hole in it.
    """
    steps = [step for step in _CONFIDENCE_STEPS if step[0] in tiers] if tiers else []
    return steps if len(steps) > 1 else []


def controls_size(ts: float, *, tiers: tuple[str, ...] = ()) -> tuple[float, float]:
    """Return the ``(width, height)`` the panel will occupy, before drawing it.

    So a caller can place the panel against what is already on the plate
    rather than discover the collision afterwards.
    """
    pad = 12 * ts
    row = 22 * ts
    steps = _steps_for(tiers)
    rows = len(_SWITCH_ORDER) + (len(steps) + 1 if steps else 0)
    return 132 * ts, pad * 2 + 16 * ts + rows * row


# The palette is one of make_situation_map's _PLATES entries: colour strings
# with one opacity number among them, which is why the value type is a union.
def controls_markup(width: float, height: float, ts: float,
                    palette: dict[str, str | float],
                    *, tiers: tuple[str, ...] = (),
                    origin: tuple[float, float] | None = None) -> str:
    """Return the control panel, hidden until the script reveals it.

    Parameters
    ----------
    width, height : float
        Plate size in SVG units.
    ts : float
        Type scale, so the panel tracks the plate's own sizing.
    palette : dict
        The resolved plate palette.
    origin : tuple of (float, float), optional
        Top-left corner of the panel in plate units. The caller picks it,
        because only the caller knows where the legend, the scale bar and
        the north arrow already are -- the panel used to sit in a fixed
        bottom-left corner and landed on top of the legend on the one
        bundled plate whose legend is also bottom-left.
    tiers : tuple of str, optional
        The confidence tiers this plate actually draws. The filter is only
        offered when there is something to filter: a plate with no
        ``reported`` or ``claimed`` zone gets layer switches and no ladder,
        because a control that cannot change anything is noise.

    Returns
    -------
    str
        An SVG group. ``display:none`` until the script turns it on.
    """
    pad = 12 * ts
    row = 22 * ts
    panel_w = 132 * ts
    switches = list(_SWITCH_ORDER)
    steps = _steps_for(tiers)
    rows = len(switches) + (len(steps) + 1 if steps else 0)
    panel_h = pad * 2 + 16 * ts + rows * row
    x, y = origin if origin is not None else (16 * ts, height - panel_h - 16 * ts)

    out: list[str] = [
        f'<g id="plate-controls" style="display:none" transform="translate({x:.1f},{y:.1f})" '
        f'role="group" aria-label="Map layers and confidence filter">',
        f'<rect width="{panel_w:.1f}" height="{panel_h:.1f}" rx="{8 * ts:.1f}" '
        f'fill="{palette["panel"]}" fill-opacity="0.97" stroke="{palette["panel_edge"]}"/>',
        f'<text x="{pad:.1f}" y="{pad + 10 * ts:.1f}" font-size="{9.5 * ts:.1f}" '
        f'font-weight="700" letter-spacing="1.1" fill="{palette["chrome_ink"]}">SHOW</text>',
    ]
    top = pad + 20 * ts
    for index, (key, label) in enumerate(switches):
        cy = top + index * row + row / 2
        out.append(
            f'<g class="pc-switch" data-switch="{key}" role="switch" aria-checked="true" '
            f'tabindex="0" aria-label="{label}" transform="translate(0,{cy - row / 2:.1f})">'
            f'<rect x="{pad / 2:.1f}" y="0" width="{panel_w - pad:.1f}" height="{row:.1f}" '
            f'fill="transparent"/>'
            f'<rect class="pc-box" x="{pad:.1f}" y="{row / 2 - 5 * ts:.1f}" '
            f'width="{10 * ts:.1f}" height="{10 * ts:.1f}" rx="{2 * ts:.1f}" '
            f'fill="{palette["chrome_ink"]}" stroke="{palette["chrome_ink"]}"/>'
            f'<text x="{pad + 16 * ts:.1f}" y="{row / 2 + 3.5 * ts:.1f}" '
            f'font-size="{10.5 * ts:.1f}" fill="{palette["legend_ink"]}">{label}</text>'
            f"</g>"
        )
    if steps:
        base = top + len(switches) * row
        out.append(
            f'<text x="{pad:.1f}" y="{base + 12 * ts:.1f}" font-size="{9.5 * ts:.1f}" '
            f'font-weight="700" letter-spacing="1.1" fill="{palette["chrome_ink"]}">CONFIDENCE</text>'
        )
        for index, (key, label) in enumerate(steps):
            cy = base + 18 * ts + index * row
            out.append(
                f'<g class="pc-step" data-step="{key}" role="radio" aria-checked="false" '
                f'tabindex="0" aria-label="{label}" transform="translate(0,{cy:.1f})">'
                f'<rect x="{pad / 2:.1f}" y="0" width="{panel_w - pad:.1f}" height="{row:.1f}" '
                f'fill="transparent"/>'
                f'<circle class="pc-dot" cx="{pad + 5 * ts:.1f}" cy="{row / 2:.1f}" '
                f'r="{4.5 * ts:.1f}" fill="none" stroke="{palette["chrome_ink"]}"/>'
                f'<text x="{pad + 16 * ts:.1f}" y="{row / 2 + 3.5 * ts:.1f}" '
                f'font-size="{10.5 * ts:.1f}" fill="{palette["legend_ink"]}">{label}</text>'
                f"</g>"
            )
    out.append("</g>")
    return "".join(out)


#: The behaviour, as one dependency-free script. Kept readable rather than
#: minified: it ships inside a file a reader can open, and a script nobody
#: can read is a runtime by another name.
_SCRIPT = r"""
(function () {
  var svg = document.currentScript && document.currentScript.ownerSVGElement;
  if (!svg) { svg = document.documentElement; }
  var panel = svg.querySelector('#plate-controls');
  if (!panel) { return; }

  var GROUPS = __GROUPS__;
  var ORDER = ['assessed', 'reported', 'claimed'];

  // Revealed only once the script runs, so an <img> embed, a rasteriser or
  // a browser with scripting off all keep the plate exactly as it shipped.
  panel.style.display = '';

  var state = { off: {}, upto: 'claimed', only: null };

  function parseHash() {
    var raw = (svg.ownerDocument.defaultView || window).location.hash.slice(1);
    if (!raw) { return; }
    raw.split('&').forEach(function (pair) {
      var bits = pair.split('=');
      if (bits[0] === 'off' && bits[1]) {
        bits[1].split(',').forEach(function (k) { state.off[k] = true; });
      } else if (bits[0] === 'upto' && ORDER.indexOf(bits[1]) >= 0) {
        state.upto = bits[1];
      } else if (bits[0] === 'only' && bits[1]) {
        state.only = decodeURIComponent(bits[1]);
      }
    });
  }

  function writeHash() {
    var parts = [];
    var off = Object.keys(state.off).filter(function (k) { return state.off[k]; });
    if (off.length) { parts.push('off=' + off.join(',')); }
    if (state.upto !== 'claimed') { parts.push('upto=' + state.upto); }
    if (state.only) { parts.push('only=' + encodeURIComponent(state.only)); }
    var view = svg.ownerDocument.defaultView || window;
    if (view.history && view.history.replaceState) {
      view.history.replaceState(null, '', parts.length ? '#' + parts.join('&') : '#');
    }
  }

  function apply() {
    Object.keys(GROUPS).forEach(function (key) {
      var hidden = !!state.off[key];
      GROUPS[key].forEach(function (id) {
        var node = svg.querySelector('[data-layer-id="' + id + '"]');
        if (node) { node.style.display = hidden ? 'none' : ''; }
      });
    });
    var limit = ORDER.indexOf(state.upto);
    var zones = svg.querySelectorAll('[data-confidence]');
    for (var i = 0; i < zones.length; i++) {
      var z = zones[i];
      var tier = ORDER.indexOf(z.getAttribute('data-confidence'));
      var category = z.getAttribute('data-category');
      var show = tier >= 0 && tier <= limit && (!state.only || category === state.only);
      z.style.display = show ? '' : 'none';
    }
    var switches = svg.querySelectorAll('.pc-switch');
    for (var s = 0; s < switches.length; s++) {
      var on = !state.off[switches[s].getAttribute('data-switch')];
      switches[s].setAttribute('aria-checked', on ? 'true' : 'false');
      var box = switches[s].querySelector('.pc-box');
      if (box) { box.setAttribute('fill-opacity', on ? '1' : '0'); }
    }
    var steps = svg.querySelectorAll('.pc-step');
    for (var t = 0; t < steps.length; t++) {
      var picked = steps[t].getAttribute('data-step') === state.upto;
      steps[t].setAttribute('aria-checked', picked ? 'true' : 'false');
      var dot = steps[t].querySelector('.pc-dot');
      if (dot) { dot.setAttribute('fill-opacity', picked ? '1' : '0'); }
    }
    writeHash();
  }

  function bind(nodes, handler) {
    for (var i = 0; i < nodes.length; i++) {
      (function (node) {
        node.addEventListener('click', function () { handler(node); apply(); });
        node.addEventListener('keydown', function (event) {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handler(node);
            apply();
          }
        });
      })(nodes[i]);
    }
  }

  bind(svg.querySelectorAll('.pc-switch'), function (node) {
    var key = node.getAttribute('data-switch');
    state.off[key] = !state.off[key];
  });
  bind(svg.querySelectorAll('.pc-step'), function (node) {
    state.upto = node.getAttribute('data-step');
  });
  // Clicking a class in the legend isolates it; clicking it again restores.
  bind(svg.querySelectorAll('[data-legend-category]'), function (node) {
    var name = node.getAttribute('data-legend-category');
    state.only = state.only === name ? null : name;
  });

  parseHash();
  apply();
})();
"""


def controls_script(mode: str = "self-contained") -> str:
    """Return the behaviour script, or nothing outside self-contained mode.

    Mirrors :func:`_interactive.fullscreen_control`'s contract: ``external``
    means a page-level script owns the interaction, ``static`` means there is
    none.

    Examples
    --------
    >>> controls_script("static")
    ''
    >>> controls_script().startswith("<script")
    True
    """
    if mode != "self-contained":
        return ""
    groups = json.dumps({k: list(v) for k, v in LAYER_GROUPS.items()})
    return "<script><![CDATA[" + _SCRIPT.replace("__GROUPS__", groups) + "]]></script>"


def tag_layer(group_svg: str) -> str:
    """Return ``group_svg`` with a ``data-layer-id`` the script can find.

    The generator's groups already carry ``id`` attributes, but an ``id`` is
    document-unique and these plates get inlined several to a page: two maps
    in one article would collide, and the script would drive the wrong one.
    A data attribute scoped to the element, queried from the owning ``<svg>``
    rather than the document, is the version that survives being embedded
    twice.

    Examples
    --------
    >>> tag_layer('<g id="rivers"><path/></g>')
    '<g id="rivers" data-layer-id="rivers"><path/></g>'

    A group that is chrome rather than map content is left alone:

    >>> tag_layer('<g id="legend"><rect/></g>')
    '<g id="legend"><rect/></g>'
    """
    marker = '<g id="'
    if not group_svg.startswith(marker):
        return group_svg
    end = group_svg.index('"', len(marker))
    group_id = group_svg[len(marker) : end]
    if layer_key_for(group_id) is None:
        return group_svg
    return (
        group_svg[: end + 1] + f' data-layer-id="{group_id}"' + group_svg[end + 1 :]
    )
