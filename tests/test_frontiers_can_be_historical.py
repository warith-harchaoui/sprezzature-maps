"""
A map of 1995 drawn over 2026 borders is not an approximation. It is a different claim.

The vendored basemap is present-day, which is what "international frontiers"
means for most plates and is exactly wrong for a plate of a past year. A map
of the Bosnian war with today's borders on it shows a Bosnia that did not
exist in the form it draws, beside a Serbia that did not have those edges,
and nothing on the page says so.

``frontiers.source`` takes a historical boundary file and ``frontiers.as_of``
the day to read it at. The rest of the frontier layer -- the de-duplicated
inner lines, the neighbour labels, the area threshold -- does not know which
source it was handed.

Nothing is vendored, and that is a licensing fact rather than a technical one.
CShapes 2.0, the only GIS dataset mapping state borders worldwide from 1886,
is CC BY-NC-SA 4.0: bundling it into a BSD package would attach a
non-commercial clause to the package and a share-alike obligation to anything
built on it. It is free for the academic use this is for, so the user
downloads it and the licence stays with them. These tests therefore run
against a small fixture written in CShapes' own property names.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
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


def _box(w: float, s: float, e: float, n: float) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def _feature(
    name: str,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    bounds: tuple[float, float, float, float],
) -> dict[str, Any]:
    """One CShapes-shaped feature: a name, a validity window, a shape."""
    return {
        "type": "Feature",
        "properties": {
            "cntry_name": name,
            "gwsyear": start[0],
            "gwsmonth": start[1],
            "gwsday": start[2],
            "gweyear": end[0],
            "gwemonth": end[1],
            "gweday": end[2],
        },
        "geometry": _box(*bounds),
    }


#: The case the feature exists for: one state becoming two, on a known day.
ERAS: list[dict[str, Any]] = [
    _feature("Yugoslavia", (1918, 12, 1), (1991, 6, 25), (13.4, 40.8, 23.0, 46.9)),
    _feature("Croatia", (1991, 6, 25), (2019, 12, 31), (13.4, 42.3, 19.5, 46.6)),
    _feature("Serbia", (1991, 6, 25), (2019, 12, 31), (18.8, 41.8, 23.0, 46.2)),
]


# ── the date ────────────────────────────────────────────────────────────


def test_a_full_date_is_read() -> None:
    assert msm.parse_as_of("1995-07-01") == date(1995, 7, 1)
    assert msm.parse_as_of(date(1995, 7, 1)) == date(1995, 7, 1)


@pytest.mark.parametrize("year", ["1991", "1990", 1991])
def test_a_bare_year_is_refused(year: Any) -> None:
    """
    A year is ambiguous for exactly the borders this draws.

    The Soviet Union existed on 1991-01-01 and did not on 1991-12-31;
    Yugoslavia was whole at the start of 1991 and dissolving by its middle.
    A loader that silently picked one end of the year would draw a map of a
    world that is defensible and unstated.
    """
    with pytest.raises(ValueError, match="is a year, not a date"):
        msm.parse_as_of(year)


def test_the_refusal_shows_what_to_write_instead() -> None:
    with pytest.raises(ValueError, match="1991-06-30"):
        msm.parse_as_of("1991")


@pytest.mark.parametrize("bad", ["yesterday", "1991-13-01", "", "01/06/1991"])
def test_an_unreadable_date_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="use YYYY-MM-DD"):
        msm.parse_as_of(bad)


# ── the window ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        ("1990-06-30", {"Yugoslavia"}),
        ("1991-06-24", {"Yugoslavia"}),  # the day before
        ("1991-06-25", {"Yugoslavia", "Croatia", "Serbia"}),  # both ends inclusive
        ("1991-06-26", {"Croatia", "Serbia"}),
        ("1995-06-30", {"Croatia", "Serbia"}),
    ],
)
def test_the_world_as_it_was_on_that_day(when: str, expected: set[str]) -> None:
    """
    One day either side of the split, because that is the whole point.

    A validity window that was off by a day would draw the right map almost
    always and the wrong one exactly when a reader is looking closely.
    """
    got = {name for name, _ in msm.countries_as_of(ERAS, msm.parse_as_of(when))}
    assert got == expected


def test_a_date_nothing_is_valid_on_is_an_error() -> None:
    """
    An empty frontier layer looks exactly like a region with no neighbours.

    Which is to say: like a finished map. Silence here is the failure mode
    this repository keeps closing.
    """
    with pytest.raises(ValueError, match="no feature in the frontiers source is valid"):
        msm.countries_as_of(ERAS, date(1850, 1, 1))


def test_the_error_says_which_properties_it_looked_for() -> None:
    with pytest.raises(ValueError, match="gwsyear/gweyear"):
        msm.countries_as_of(ERAS, date(1850, 1, 1))


def test_a_feature_with_no_window_is_always_valid() -> None:
    """A source that does not date its polygons is a present-day source."""
    undated = [
        {"type": "Feature", "properties": {"cntry_name": "Ruritania"}, "geometry": _box(0, 0, 1, 1)}
    ]
    assert msm.countries_as_of(undated, date(1850, 1, 1))[0][0] == "Ruritania"


def test_another_source_can_name_its_fields() -> None:
    """CShapes' names are a default, not a requirement."""
    other = [
        {
            "type": "Feature",
            "properties": {"label": "Ruritania", "from_y": 1900, "to_y": 1950},
            "geometry": _box(0, 0, 1, 1),
        }
    ]
    fields = {"name": ("label",), "start": ("from_y", "x", "x"), "end": ("to_y", "x", "x")}
    assert msm.countries_as_of(other, date(1920, 1, 1), fields)[0][0] == "Ruritania"
    with pytest.raises(ValueError):
        msm.countries_as_of(other, date(1960, 1, 1), fields)


# ── end to end, on a drawn plate ────────────────────────────────────────


def _cfg(tmp_path: Path, when: str) -> dict[str, Any]:
    src = tmp_path / "eras.geojson"
    src.write_text(json.dumps({"type": "FeatureCollection", "features": ERAS}))
    return {
        "title": f"Frontiers at {when}",
        "region": {"bbox": [12.0, 39.5, 24.5, 47.5]},
        "canvas_width": 700,
        "basemap": {"relief": False},
        "frontiers": {
            "source": str(src),
            "as_of": when,
            "label_neighbours": True,
            "label_min_area_frac": 0.001,
        },
    }


def test_the_plate_names_the_states_of_its_own_year(tmp_path: Path) -> None:
    before = msm.build_map(_cfg(tmp_path, "1990-06-30"))
    after = msm.build_map(_cfg(tmp_path, "1995-06-30"))
    assert "YUGOSLAVIA" in before.upper()
    assert "CROATIA" not in before.upper()
    assert "CROATIA" in after.upper() and "SERBIA" in after.upper()
    assert "YUGOSLAVIA" not in after.upper()


def test_the_same_plate_without_a_source_is_present_day(tmp_path: Path) -> None:
    """The default is untouched: every config written before this keeps its map."""
    cfg = _cfg(tmp_path, "1990-06-30")
    cfg["frontiers"].pop("source")
    cfg["frontiers"].pop("as_of")
    svg = plate(cfg)
    assert "YUGOSLAVIA" not in svg.upper()
    assert "CROATIA" in svg.upper()  # the basemap's own, present-day


def test_a_source_without_a_date_is_refused(tmp_path: Path) -> None:
    """
    A historical file holds every border the world has had.

    Reading one without a date would mean drawing all of them at once, or
    picking one silently. Neither is a map.
    """
    cfg = _cfg(tmp_path, "1990-06-30")
    cfg["frontiers"].pop("as_of")
    with pytest.raises(ValueError, match="frontiers.source needs frontiers.as_of"):
        plate(cfg)


def test_the_new_keys_are_accepted_by_the_validator(tmp_path: Path) -> None:
    msm.validate_config(_cfg(tmp_path, "1990-06-30"))
    assert {"source", "as_of", "fields"} <= msm.SECTION_KEYS["frontiers"]
