"""
_places: which cities to name on a map, and where their labels fit.

Module summary
--------------
A map of the Earth with no cities on it is a map of an empty planet. Both
generators drew coastlines, borders and terrain and then stopped, so a reader
could see where the Andes are and not where Lima is — and had no anchor at all
for the scale of what they were looking at.

Two problems have to be solved together, and the second is the hard one.

**Which cities.** Not "the capitals": that is a political list, not a
geographic one, and it leaves out New York, Mumbai, São Paulo, Shanghai, Los
Angeles and Karachi, all of which are in the world's twelve largest. The
vendored list carries 1 251 places with a population and Natural Earth's
``scalerank`` — a cartographic prominence rank where 0 is the handful of
places that belong on a world map and 10 is a town that belongs only on a
regional one. Selection here is by that rank, widened as the map zooms in,
because prominence is exactly the question "does this belong at this scale".

**Where the labels go.** 1 251 labels on one canvas is a black rectangle. Even
forty, placed naively, overlap into illegibility. Labels are placed greedily in
prominence order — the most important city gets its preferred position, and any
later label whose box would collide with one already placed is dropped rather
than moved somewhere misleading. Dropping is the honest failure: a label nudged
far from its dot points at the wrong place, and a reader cannot tell.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from _assets import geo_dir

#: Average glyph advance as a fraction of the font size, for the house sans.
#: Labels only need a box wide enough to reject overlaps, so a flat ratio is
#: adequate here in a way it is not for fitting text to a fixed width.
_GLYPH_WIDTH_RATIO = 0.55

#: How prominent a city must be to appear, by how much of the world is in
#: frame. Keyed by the larger of the view's longitude and latitude span in
#: degrees; the value is the highest ``scalerank`` still drawn. A world view
#: gets the couple of dozen places that belong on a world map; a single
#: country gets its regional centres too.
_RANK_BY_SPAN: tuple[tuple[float, int], ...] = (
    (0.0, 8),      # a city and its surroundings
    (5.0, 6),      # a province
    (15.0, 4),     # a country
    (40.0, 2),     # a continent
    (120.0, 1),    # a hemisphere
    (240.0, 0),    # the world
)


@dataclass(frozen=True)
class City:
    """One place, with what is needed to decide whether to draw it."""

    name: str
    lon: float
    lat: float
    population: int
    rank: int
    capital: bool
    country: str


@lru_cache(maxsize=1)
def load_cities() -> tuple[City, ...]:
    """Every vendored place, most prominent first."""
    path = geo_dir() / "cities-50m.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        City(
            name=c["n"],
            lon=float(c["o"]),
            lat=float(c["a"]),
            population=int(c["p"]),
            rank=int(c["r"]),
            capital=bool(c["c"]),
            country=c["y"],
        )
        for c in raw["cities"]
    )


def rank_ceiling_for_span(span_deg: float) -> int:
    """The highest ``scalerank`` worth drawing for a view this wide."""
    ceiling = _RANK_BY_SPAN[0][1]
    for threshold, rank in _RANK_BY_SPAN:
        if span_deg >= threshold:
            ceiling = rank
    return ceiling


def cities_in_view(
    west: float,
    south: float,
    east: float,
    north: float,
    *,
    limit: int = 60,
    rank_ceiling: int | None = None,
) -> list[City]:
    """
    The places worth naming inside a bounding box, most prominent first.

    `limit` is a hard cap on how many come back, because a canvas has a fixed
    amount of room for words regardless of how many cities the box contains.
    It is applied after the prominence sort, so raising or lowering it changes
    how deep the list goes, never which end of it you get.
    """
    span = max(east - west, north - south)
    ceiling = rank_ceiling_for_span(span) if rank_ceiling is None else rank_ceiling
    inside = [
        c
        for c in load_cities()
        if c.rank <= ceiling and west <= c.lon <= east and south <= c.lat <= north
    ]
    return inside[:limit]


def place_labels(
    cities: Sequence[City],
    project: Callable[[float, float], tuple[float, float]],
    *,
    font_size: float = 9.0,
    dot_radius: float = 1.8,
    bounds_px: tuple[float, float, float, float] | None = None,
) -> list[tuple[City, float, float, float, float]]:
    """
    Place a label per city, dropping any that would collide.

    Returns one entry per *kept* city: ``(city, dot_x, dot_y, label_x,
    label_y)``. The label sits to the right of its dot when there is room and
    to the left otherwise, so a city near the right edge does not push its name
    off the canvas.

    A dropped city is not moved elsewhere. A name nudged away from its dot
    points at the wrong place and a reader has no way to know, which is worse
    than a name that simply is not there.
    """
    placed: list[tuple[float, float, float, float]] = []
    kept: list[tuple[City, float, float, float, float]] = []
    gap = dot_radius + 3.0
    half_height = font_size * 0.62

    for city in cities:
        dot_x, dot_y = project(city.lon, city.lat)
        width = len(city.name) * font_size * _GLYPH_WIDTH_RATIO

        for label_x, box_left in (
            (dot_x + gap, dot_x + gap),
            (dot_x - gap - width, dot_x - gap - width),
        ):
            box = (box_left, dot_y - half_height, box_left + width, dot_y + half_height)
            if bounds_px is not None:
                x0, y0, x1, y1 = bounds_px
                if box[0] < x0 or box[2] > x1 or box[1] < y0 or box[3] > y1:
                    continue
            if any(_overlaps(box, other) for other in placed):
                continue
            placed.append(box)
            kept.append((city, dot_x, dot_y, label_x, dot_y + half_height * 0.5))
            break

    return kept


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Whether two label boxes intersect, with a pixel of breathing room."""
    pad = 1.0
    return not (
        a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1]
    )
