"""
A situation plate that starts finished, so the work is the subject.

The gap this closes. Until now there were two ways to begin a situation
map: a four-line demo config that draws a bare coastline, or the
thousand-line builder script behind the shipped gallery. Nothing in
between — no starting point that already carried the things a plate owes
a reader. So every new plate began by *not* having them, and the shipped
gallery is the evidence: fourteen plates, no locator inset on any of
them, two with no provenance footer at all, four drawing every control
zone at one confidence.

A default that has to be remembered is not a default. This writes a
config that is already furnished:

* a locator inset, now that a regional plate draws one unless it declines
* ``as of <date>`` in the provenance footer, and the footer switched on
* ``method`` and ``source`` lines phrased so that leaving them as they
  are would be an obviously unfinished sentence rather than a quiet lie
* the thematic layer as a **commented** block carrying ``confidence`` on
  every zone, because the shape of the thing is the part that is hard to
  remember and the polygons are the part only the author can supply

and that renders, as written, into a correct reference plate of the
region. The subject gets added to something that already works.

The bounding box is the other half. ``[west, south, east, north]`` in
degrees is a small thing to get wrong and a hard thing to look up, so
``--country`` reads it off the vendored atlas instead, with enough margin
that the neighbours are in the picture — which is where a front usually
is.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from datetime import date
from typing import Any

#: How much room to leave around a country when its box is read off the
#: atlas, as a fraction of the country's own span. A front line sits on a
#: border by definition, and a plate cropped to the national outline puts
#: the subject against the frame; a fifth is enough to show who is on the
#: other side without the country becoming a detail.
_COUNTRY_MARGIN = 0.18

#: Minimum margin in degrees, for a country small enough that a fraction
#: of its span rounds to nothing. Luxembourg spans half a degree.
_MIN_MARGIN_DEG = 0.6


def country_bbox(name: str, margin: float = _COUNTRY_MARGIN) -> list[float]:
    """Return ``[west, south, east, north]`` around a named country.

    Parameters
    ----------
    name : str
        Country name as the vendored Natural Earth atlas spells it.
    margin : float, optional
        Room to leave on each side, as a fraction of the country's own
        span.

    Returns
    -------
    list of float
        Rounded to two decimals, which is about a kilometre and is as
        precise as a hand-chosen frame ever needs to be.

    Raises
    ------
    KeyError
        If the atlas has no country of that name.
    """
    from sprezzature_maps import _load_script

    outline = _load_script("make_situation_map").load_country(name)
    west, south, east, north = outline.bounds
    pad_x = max((east - west) * margin, _MIN_MARGIN_DEG)
    pad_y = max((north - south) * margin, _MIN_MARGIN_DEG)
    return [
        round(max(-180.0, west - pad_x), 2),
        round(max(-90.0, south - pad_y), 2),
        round(min(180.0, east + pad_x), 2),
        round(min(90.0, north + pad_y), 2),
    ]


def _as_of_phrase(when: date) -> str:
    """Format a date the way the guidelines ask a plate to stamp one.

    "as of DD Month YYYY", spelled out. A numeric date is read differently
    on either side of the Atlantic and a plate travels.

    Examples
    --------
    >>> _as_of_phrase(date(2026, 9, 5))
    'As of 5 September 2026'
    """
    return f"As of {when.day} {when:%B} {when.year}"


def situation_starter(
    *,
    title: str,
    bbox: list[float] | tuple[float, float, float, float],
    subtitle: str = "",
    as_of: date | None = None,
    focus: str | None = None,
    actors: tuple[str, ...] = ("Government", "Opposition"),
) -> str:
    """Return a complete, commented YAML config for a new situation plate.

    Parameters
    ----------
    title : str
        The plate's own title.
    bbox : sequence of float
        ``[west, south, east, north]`` in degrees.
    subtitle : str, optional
        The editorial line under the title.
    as_of : datetime.date, optional
        The vintage stamped into the provenance footer. Defaults to today,
        which is right for a plate being drawn today and wrong for one
        reconstructing a past moment — so it is stated, not hidden.
    focus : str, optional
        A country name to emphasise in the frontier layer.
    actors : tuple of str, optional
        The forces the commented control block is written for.

    Returns
    -------
    str
        YAML, with the reasoning for each block beside it.

    Examples
    --------
    >>> text = situation_starter(title="Donbas", bbox=[36.0, 46.5, 40.5, 49.5],
    ...                          as_of=date(2026, 9, 5))
    >>> "As of 5 September 2026" in text
    True
    >>> "confidence: assessed" in text
    True
    """
    stamp = _as_of_phrase(as_of or date.today())
    west, south, east, north = (float(v) for v in bbox)
    focus_block = (
        f'  focus: "{focus}"          # thicker outline, neighbours greyed\n'
        if focus
        else '  # focus: "Country"   # thicker outline on one country,\n'
        "  #                     # neighbours greyed and letterspaced\n"
    )
    first, second = (list(actors) + ["Opposition"])[:2]
    return f"""# {title}
#
# Written by `make-map situation-new`. Everything here already renders:
# run it as it stands and you get a correct reference plate of the region,
# then add your subject to something that works.
#
#   make-map situation-map --config this-file.yaml --out plate.svg
#   make-map audit plate.svg
#
# The audit is the second half of the loop. It asks the questions a reader
# of a control map asks — as of when, on what evidence, where on Earth is
# this — and a plate that answers them is the whole of what this scaffold
# is for.

title: "{title}"
subtitle: "{subtitle or "Schematic, from open-source reporting"}"

region:
  # [west, south, east, north] in degrees. Read off the vendored atlas when
  # this file was written with --country, so the neighbours are in frame:
  # a front line sits on a border, and a plate cropped to the national
  # outline puts its own subject against the edge.
  bbox: [{west}, {south}, {east}, {north}]

projection: auto      # Lambert conformal conic, centred on the region
canvas_width: 1320
padding: 30

basemap:
  relief: true        # texture-shaded from real elevation, not a baked raster
  sea_color: "#a8bccb"
  land_color: "#f6f1df"
  coast_color: "#7993a6"

frontiers:
{focus_block}  label_neighbours: true

rivers: {{}}            # drawn and labelled from Natural Earth
lakes: {{}}
cities:
  show: true
  max_rank: 7         # lower means fewer, larger towns

# ── provenance ───────────────────────────────────────────────────────────
# A plate gets screenshotted, pasted into a deck, forwarded. By the time
# somebody asks what it is and when it was true, the page that carried the
# caption is gone. These three lines travel with the picture.
caption: full
as_of: "{stamp} · illustrative, not an operational assessment"
method: "REPLACE ME: how the zones were drawn — hand-traced from reporting, a geocoded dataset, or both"
source: "REPLACE ME: the sources, named"

# A locator inset is drawn automatically: the mapped area in red on a wider
# view, in a corner the legend and the scale bar have not taken. Say
# `inset: {{show: false}}` to decline it, or `position:` to place it.
#
# If this region reaches Jammu and Kashmir, the Sudan–South Sudan boundary
# or Abyei, the standard disclaimer joins the footer on its own. You do not
# have to remember it, and you cannot decline it by turning the footer off.

# ── the subject ──────────────────────────────────────────────────────────
# Uncomment and replace the geometry. The shape of the block is the part
# that is hard to remember; the polygons are the part only you can supply.
#
# `confidence` is the field that matters most and the one most often left
# out. Three tiers, visually ordered so a reader ranks them without the
# legend: `assessed` is a solid fill, `reported` is hatched, `claimed` is
# dotted and dashed. Omit it and a zone is drawn as assessed — the
# strongest claim on the plate, made by default, which is exactly the
# failure the tiers exist to prevent.
#
# areas_of_control:
#   palette:
#     "{first}": "#7f9a86"
#     "{second}": "#c0705f"
#   contested: "Contested"
#   source:
#     type: FeatureCollection
#     features:
#       - type: Feature
#         properties:
#           actor: "{first}"
#           confidence: assessed      # geolocated evidence
#         geometry: {{type: Polygon, coordinates: [[[{west}, {south}], [{east}, {south}], [{east}, {north}], [{west}, {south}]]]}}
#       - type: Feature
#         properties:
#           actor: "{second}"
#           confidence: claimed       # a belligerent says so, nobody checked
#         geometry: {{type: Polygon, coordinates: [[[{west}, {south}], [{east}, {north}], [{west}, {north}], [{west}, {south}]]]}}
#
# events:          # flashpoints, with ACLED/UCDP precision kept as a code
#   - lon: {round((west + east) / 2, 2)}
#     lat: {round((south + north) / 2, 2)}
#     label: "Town"
#     precision: 2    # 1 exact, 2 a ring, 3 draw it as the area it really is
#
# labels:
#   places:
#     - {{lon: {round((west + east) / 2, 2)}, lat: {round((south + north) / 2, 2)}, text: "Capital", capital: true}}
"""


def starter_config(**kwargs: Any) -> str:
    """Alias kept for symmetry with the other generators' entry points."""
    return situation_starter(**kwargs)
