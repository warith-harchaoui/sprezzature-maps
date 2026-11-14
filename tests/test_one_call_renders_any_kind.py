"""
One call renders any kind through a table lookup, and frames what it was given.

Why this file exists
--------------------
``sprezzature_maps.render`` is the improve loop's whole rendering path, and it
has no ``if kind ==`` in it: the keyword each generator takes its data under
lives in the registry. These tests are what makes that worth relying on — that
one call reaches all three kinds, that a payload of ``None`` still gets the
built-in demo (what a caller shows before a file is chosen), and that
an explicit option wins over an inferred one.

The bounding box, and the dead end that put it here
---------------------------------------------------
``make_density``'s own default box is the continental United States, which is
right for a generator with a demo dataset and no way to ask. The first thing
tried while writing the module was Paris, London and Berlin, and the answer
was ``ValueError: no point fell inside the bbox; nothing to draw`` — accurate,
and a dead end: the data was fine and the frame was somewhere else. So the
call frames what it was given. The command line keeps its documented
default, because that is a different promise to a different reader.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sprezzature_maps.kinds import KINDS
from sprezzature_maps.render import (
    BBOX_MARGIN,
    BBOX_MINIMUM_SPAN,
    infer_bbox,
    render,
)

#: Points inside ``make_density``'s own default box, so the "explicit wins"
#: case can be checked without the inference quietly rescuing it.
INSIDE_THE_DEFAULT_BOX = [[-74.0, 40.7], [-87.6, 41.9], [-118.2, 34.1]]

#: Paris, London, Berlin. Outside that box, which is the whole point.
EUROPEAN_EVENTS = [[2.35, 48.86], [-0.13, 51.51], [13.4, 52.5]]


# ── the bounding box ──────────────────────────────────────────────────────


def test_a_box_is_widened_by_the_margin() -> None:
    """A one-degree span gains the margin on each side, not inside it.

    Widening inward would crop the outermost events, which are usually the
    ones a reader is looking for.
    """
    west, south, east, north = infer_bbox([[2.0, 48.0], [3.0, 49.0]])
    assert west == pytest.approx(2.0 - BBOX_MARGIN)
    assert east == pytest.approx(3.0 + BBOX_MARGIN)
    assert south == pytest.approx(48.0 - BBOX_MARGIN)
    assert north == pytest.approx(49.0 + BBOX_MARGIN)


def test_the_box_contains_every_point() -> None:
    """The property the margin exists to guarantee, asserted directly."""
    west, south, east, north = infer_bbox(EUROPEAN_EVENTS)
    for longitude, latitude in EUROPEAN_EVENTS:
        assert west < longitude < east, f"{longitude} is not inside {west}..{east}"
        assert south < latitude < north, f"{latitude} is not inside {south}..{north}"


def test_one_point_is_widened_to_the_minimum_span() -> None:
    """Several events at one address give a zero-extent box.

    No projection can scale a box of no size, so it becomes the smallest
    frame in which a single luminous cell reads as a place.
    """
    west, south, east, north = infer_bbox([[2.0, 48.0]])
    assert east - west == pytest.approx(BBOX_MINIMUM_SPAN)
    assert north - south == pytest.approx(BBOX_MINIMUM_SPAN)
    assert (west + east) / 2 == pytest.approx(2.0), "the point is not centred in its frame"


def test_a_span_narrow_in_one_direction_only_is_widened_there() -> None:
    """A line of events along a coast road is narrow in one axis and not the other."""
    west, south, east, north = infer_bbox([[2.0, 48.0], [9.0, 48.0]])
    assert east - west > 1.0, "the wide axis was collapsed to the minimum"
    assert north - south == pytest.approx(BBOX_MINIMUM_SPAN)


def test_no_points_is_refused_rather_than_framed() -> None:
    """A box around nothing is a frame with no contents.

    Told apart from a frame in the wrong place, because the caller fixes the
    two differently.
    """
    with pytest.raises(ValueError, match=r"no points"):
        infer_bbox([])


# ── the dispatch ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_renders_its_demo_through_one_call(entry, tmp_path: Path) -> None:
    """A payload of ``None`` gets the kind's built-in demo.

    This is a caller's first screen: something on the canvas before a file
    has been chosen. It is also the cheapest possible check that the registry's
    renderer name and payload keyword agree with the real function — a wrong
    keyword raises ``TypeError`` here.
    """
    out = tmp_path / f"{entry.name}.svg"
    written = render(entry.name, None, out=out)
    assert Path(written).is_file(), f"{entry.name} reported {written} and wrote nothing"
    assert Path(written).stat().st_size > 1000, f"{entry.name} wrote a suspiciously small file"
    assert "<svg" in Path(written).read_text(encoding="utf-8")[:400]


def test_european_events_render_instead_of_refusing(tmp_path: Path) -> None:
    """The regression this module's bounding box exists for.

    Before the inference this raised ``no point fell inside the bbox``, on
    three capitals and a generator that was working perfectly.
    """
    out = tmp_path / "europe.svg"
    written = render("density", EUROPEAN_EVENTS, out=out, title="european events")
    assert Path(written).stat().st_size > 1000


def test_an_explicit_box_wins_over_the_inferred_one(tmp_path: Path) -> None:
    """Because a reader who names a frame means it.

    Checked with points that *are* inside the default box, so a pass cannot be
    the inference rescuing a wrong box. The explicit one is deliberately
    elsewhere: if it were ignored, the render would succeed on the inferred box
    and this test would pass for the wrong reason — so the assertion is that it
    fails, with the generator's own message about an empty frame.
    """
    out = tmp_path / "explicit.svg"
    with pytest.raises(ValueError, match=r"no point fell inside"):
        render(
            "density",
            INSIDE_THE_DEFAULT_BOX,
            out=out,
            bbox=(100.0, 10.0, 110.0, 20.0),
        )


def test_a_choropleth_renders_the_rows_it_is_handed(tmp_path: Path) -> None:
    """The ``rows`` shape, through the same single call."""
    out = tmp_path / "rows.svg"
    written = render(
        "choropleth",
        [{"id": "840", "value": 12.5}, {"id": "124", "value": -3.2}],
        out=out,
        title="two countries",
    )
    assert "two countries" in Path(written).read_text(encoding="utf-8")


def test_an_unknown_kind_names_the_known_ones(tmp_path: Path) -> None:
    """A typed kind name is a likely mistake in a URL or a config."""
    with pytest.raises(KeyError, match=r"choropleth"):
        render("hexmap", None, out=tmp_path / "x.svg")


def test_a_hyphenated_kind_name_is_accepted(tmp_path: Path) -> None:
    """``situation-map`` and ``situation_map`` are the same kind.

    The command line spells it both ways, so a route or a config file
    should not have to know which.
    """
    out = tmp_path / "hyphen.svg"
    assert Path(render("situation-map", None, out=out)).is_file()
