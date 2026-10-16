"""
A plate is a snapshot. Almost everything a researcher wants to say is a change.

The two usual answers are both worse than they look. An animation asks the
reader to compare a frame against one they can no longer see. One plate
exported per window lets the extent, the projection and the symbol scale drift
apart between frames, and nothing on the page admits that the panels have
stopped being comparable.

``small_multiples`` cuts one config into one panel per window of time. Because
every panel is built from that single config, the drift is not prevented, it is
impossible -- and because the marker radii were sized by the loader over the
whole file before the split, a disc in the first panel means what the same disc
means in the last.

The tests below are about the two things that are easy to get wrong and
invisible once wrong: an empty window silently dropped, which compresses the
time axis and makes the remaining panels read as consecutive; and a mark whose
own ``time_precision`` is coarser than the window, quietly binned anyway, which
invents the one fact the sheet exists to show.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _plates import plate  # noqa: E402


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


msm = _load("make_situation_map")


def _event(lon: float, lat: float, when: str, precision: int = 1) -> dict[str, Any]:
    """One dated mark, positioned exactly, so only its *date* is under test."""
    return {
        "lon": lon,
        "lat": lat,
        "color": "#c0392b",
        "r": 5,
        "label": f"event {when}",
        "precision": 1,
        "date": when,
        "time_precision": precision,
    }


def _cfg(events: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "title": "Sheet under test",
        "region": {"bbox": [30.0, 45.0, 36.0, 49.0]},
        "canvas_width": 1000,
        # Terrain is tested on its own below; off here so the rest of these
        # run in seconds rather than minutes.
        "basemap": {"relief": False},
        "cities": {"show": False},
        "marker_legend": [{"color": "#c0392b", "label": "Recorded event", "precision": 1}],
        "events": events,
        "small_multiples": {"by": "year"},
    }
    cfg.update(over)
    return cfg


# --------------------------------------------------------------------------- #
# The time axis is not allowed to compress                                     #
# --------------------------------------------------------------------------- #


def test_a_window_with_nothing_in_it_is_still_a_panel() -> None:
    """2017 had no events; dropping its panel would make 2016 and 2018 adjacent."""
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2018-06-01")]))
    labels = re.findall(r'aria-label="(20\d\d): ([^"]+)"', svg)
    assert [lab for lab, _ in labels] == ["2016", "2017", "2018"]
    assert dict(labels)["2017"] == "nothing drawn"


def test_the_span_can_be_widened_past_the_data() -> None:
    """`from`/`to` state the period under study; the data does not get to shrink it."""
    svg = plate(
        _cfg(
            [_event(33.0, 47.0, "2016-05-02")],
            small_multiples={"by": "year", "from": "2014-01-01", "to": "2017-12-31"},
        )
    )
    assert [lab for lab, _ in re.findall(r'aria-label="(20\d\d): ([^"]+)"', svg)] == [
        "2014",
        "2015",
        "2016",
        "2017",
    ]


# --------------------------------------------------------------------------- #
# A mark goes only where its own date precision lets it go                     #
# --------------------------------------------------------------------------- #


def test_a_date_known_to_the_month_lands_in_that_month() -> None:
    svg = plate(
        _cfg(
            [_event(33.0, 47.0, "2016-03-01", precision=3)],
            small_multiples={"by": "month", "from": "2016-03-01", "to": "2016-04-30"},
        )
    )
    tally = dict(re.findall(r'aria-label="(\w+ 2016): ([^"]+)"', svg))
    assert tally["Mar 2016"] == "1 mark"
    assert tally["Apr 2016"] == "nothing drawn"


def test_a_date_known_only_to_the_year_lands_in_no_month_panel() -> None:
    """The row says 2016. It does not say March, and the sheet will not say it for it."""
    svg = plate(
        _cfg(
            [_event(33.0, 47.0, "2016-03-01", precision=4)],
            small_multiples={"by": "month", "from": "2016-01-01", "to": "2016-03-31"},
        )
    )
    assert all(
        v == "nothing drawn"
        for v in dict(re.findall(r'aria-label="(\w+ 2016): ([^"]+)"', svg)).values()
    )
    assert "1 dated only to a year, which no single month panel contains" in svg


def test_the_same_year_date_is_placed_once_the_window_is_a_year() -> None:
    svg = plate(_cfg([_event(33.0, 47.0, "2016-03-01", precision=4)]))
    assert dict(re.findall(r'aria-label="(20\d\d): ([^"]+)"', svg))["2016"] == "1 mark"


def test_a_week_that_straddles_two_months_is_not_placed_in_either() -> None:
    """ "Week of 2016-03-28" reaches into April. Neither month contains all of it."""
    svg = plate(
        _cfg(
            [_event(33.0, 47.0, "2016-03-28", precision=2)],
            small_multiples={"by": "month", "from": "2016-03-01", "to": "2016-04-30"},
        )
    )
    assert "which no single month panel contains" in svg


def test_a_mark_with_no_date_is_withheld_and_counted() -> None:
    cfg = _cfg([_event(33.0, 47.0, "2016-05-02")])
    cfg["events"].append({"lon": 34.0, "lat": 47.0, "color": "#c0392b", "r": 5, "label": "undated"})
    svg = plate(cfg)
    assert "1 with no date" in svg


def test_a_date_written_in_prose_is_refused_by_name() -> None:
    cfg = _cfg([_event(33.0, 47.0, "2016-05-02")])
    cfg["events"][0]["date"] = "early 2016"
    with pytest.raises(ValueError, match=r"events\[0\]\.date"):
        plate(cfg)


def test_a_sheet_nobody_could_read_is_refused() -> None:
    with pytest.raises(ValueError, match="more than 60 panels"):
        plate(
            _cfg(
                [_event(33.0, 47.0, "2016-01-01")],
                small_multiples={"by": "month", "from": "2000-01-01", "to": "2016-12-31"},
            )
        )


# --------------------------------------------------------------------------- #
# The panels really are comparable                                             #
# --------------------------------------------------------------------------- #


def test_every_panel_draws_the_same_ground() -> None:
    """The coastline is the one thing that must be identical in all of them."""
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2017-06-01")]))
    lands = re.findall(r'<g id="basemap-land-p\d+"><path d="([^"]+)"', svg)
    assert len(lands) == 2
    assert lands[0] == lands[1]


def test_the_chrome_is_drawn_once_for_the_sheet() -> None:
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2017-06-01")]))
    assert svg.count('id="scale-bar"') == 1
    assert svg.count('id="legend"') == 1
    assert svg.count('id="annotation-furniture-p') == 2  # present, and empty
    assert re.search(r'<g id="annotation-furniture-p0"></g>', svg)


def test_no_identifier_is_defined_twice() -> None:
    """Nine panels from one config define the same clip path nine times unless renamed."""
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2017-06-01")]))
    ids = re.findall(r'(?<![\w-])id="([^"]+)"', svg)
    duplicated = {i for i in ids if ids.count(i) > 1}
    assert not duplicated, f"defined more than once: {sorted(duplicated)}"


def test_the_terrain_raster_is_embedded_once() -> None:
    """Nine copies of a 2 MB raster is an 18 MB file nobody can open."""
    svg = plate(
        _cfg(
            [_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2017-06-01")],
            basemap={"relief": True},
            small_multiples={"by": "year", "panel_width": 300},
        )
    )
    assert svg.count("data:image/") == 1
    assert svg.count('<use href="#sm-relief"/>') == 1


# --------------------------------------------------------------------------- #
# The sheet says what it did                                                   #
# --------------------------------------------------------------------------- #


def test_the_sheet_states_its_own_arithmetic() -> None:
    svg = plate(
        _cfg(
            [
                _event(33.0, 47.0, "2016-05-02"),
                _event(33.5, 47.5, "2017-06-01"),
                _event(34.0, 46.5, "2017-01-01", precision=4),
            ],
            small_multiples={"by": "month", "from": "2016-05-01", "to": "2016-06-30"},
        )
    )
    assert "2 panels, one per month" in svg
    assert "1 of 3 marks drawn" in svg
    assert "Not placed:" in svg


def test_nothing_on_the_sheet_is_a_silent_tab_stop() -> None:
    """The a11y rule the plates already keep, kept across the join."""
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02"), _event(33.5, 47.5, "2017-06-01")]))
    for tag in re.findall(r"<[^>]*\btabindex=\"0\"[^>]*>", svg):
        assert "aria-label=" in tag, tag


def test_the_sheet_is_one_graphics_document_with_a_name() -> None:
    svg = plate(_cfg([_event(33.0, 47.0, "2016-05-02")]))
    assert svg.count('role="graphics-document"') == 1
    assert '<title id="sm-title">Sheet under test</title>' in svg
