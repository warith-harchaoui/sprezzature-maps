"""
Cities: a map of the Earth with nobody on it is a map of an empty planet.

Both generators drew coastlines, borders and terrain and then stopped, so a
reader could see where the Andes are and not where Lima is. These tests pin
the two decisions that make the layer worth having: which places are chosen,
and what happens when their names collide.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _places import (  # noqa: E402
    cities_in_view,
    load_cities,
    place_labels,
    rank_ceiling_for_span,
)


def test_the_list_is_not_just_capitals() -> None:
    """
    "Capitals" is a political list, and it is the wrong one.

    New York, Mumbai, São Paulo, Shanghai, Los Angeles and Karachi are six of
    the world's twelve largest cities and none of them is a capital. A map that
    names Wellington and not Shanghai is not showing where people are.
    """
    cities = load_cities()
    assert len(cities) > 1000
    assert sum(1 for c in cities if not c.capital) > 800

    biggest = sorted(cities, key=lambda c: -c.population)[:12]
    names = {c.name for c in biggest}
    assert {"New York", "Mumbai", "São Paulo", "Shanghai"} <= names, names
    assert any(not c.capital for c in biggest)


def test_prominence_widens_as_the_map_zooms_in() -> None:
    """A world view gets world cities; a province gets its own towns."""
    # Compared across bands, not within one: a country (11 degrees) and a
    # province (6) share a band on purpose, because the same places belong on
    # both. The claim is that the ceiling rises monotonically as the view
    # narrows, never that every pair of spans differs.
    spans = [360.0, 150.0, 60.0, 20.0, 8.0, 2.0]
    ceilings = [rank_ceiling_for_span(s) for s in spans]
    assert ceilings == sorted(ceilings), dict(zip(spans, ceilings, strict=True))
    assert ceilings[0] < ceilings[-1], ceilings


def test_a_country_view_names_capitals_and_major_cities_alike() -> None:
    """The point of the whole layer, on a view of France."""
    names = {c.name for c in cities_in_view(-5.0, 42.0, 8.0, 51.0, limit=14)}
    assert "Paris" in names
    assert {"Lyon", "Marseille"} & names, names


def test_no_two_kept_labels_overlap() -> None:
    """
    The invariant, stated as itself rather than as a count.

    Piling every city onto one point is the worst case a canvas can present.
    Two names can still survive it — one to the left of the dot and one to the
    right, which do not overlap and are both readable — so counting them
    proves nothing. What must hold is that no kept label overlaps another, and
    that the rest are dropped rather than nudged: a name moved clear of its own
    dot points at the wrong place and says nothing about it.
    """
    cities = [c for c in load_cities() if c.rank <= 2][:12]

    def everything_at_one_point(lon: float, lat: float) -> tuple[float, float]:
        return (300.0, 100.0)

    kept = place_labels(cities, everything_at_one_point, font_size=10.0)
    assert 0 < len(kept) < len(cities), [c.name for c, *_ in kept]

    boxes = [
        (label_x, label_y - 6.0, label_x + len(city.name) * 10.0 * 0.55, label_y + 6.0)
        for city, _dot_x, _dot_y, label_x, label_y in kept
    ]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)


def test_a_label_that_cannot_fit_the_canvas_is_dropped() -> None:
    """
    Half a name outside the frame is worse than no name — "Ista" for Istanbul.

    At the right edge the label flips to the left of its dot, which is the
    point of having two candidate positions; it is dropped only when neither
    side fits. A canvas narrower than the name itself is that case.
    """
    city = next(c for c in load_cities() if len(c.name) > 8)

    def at_the_right_edge(lon: float, lat: float) -> tuple[float, float]:
        return (398.0, 100.0)

    # Wide enough for the flipped label: kept.
    assert place_labels([city], at_the_right_edge, bounds_px=(0, 0, 400, 200))
    # Narrower than the name itself: neither side fits, so it goes.
    assert place_labels([city], at_the_right_edge, bounds_px=(390, 0, 400, 200)) == []


@pytest.mark.parametrize("limit", [5, 20, 60])
def test_the_limit_cuts_the_tail_not_the_head(limit: int) -> None:
    """Lowering the cap must drop the least prominent, never the most."""
    deep = cities_in_view(-180.0, -90.0, 180.0, 90.0, limit=60)
    shallow = cities_in_view(-180.0, -90.0, 180.0, 90.0, limit=limit)
    assert shallow == deep[: len(shallow)]
