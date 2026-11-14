"""
The loop, driven end to end with no model and no network.

``FakeLLMClient`` is scripted with readings a vision model would plausibly
return, and the renderer is injected, so these run in milliseconds and still
exercise the real stopping rules, the real repair table and the real ladder.
One test at the end drives the *actual* renderer once, because a loop that only
ever ran against a stub would not have proved that a map comes out of it.

Author
------
Project maintainers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps.assistant import FakeLLMClient, MapIssue, MapReading
from sprezzature_maps.ralph import MAX_ROUNDS, improve

POINTS = [[2.35, 48.85], [13.4, 52.52], [-0.12, 51.5], [4.9, 52.37], [12.5, 41.9]]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class Spy:
    """A renderer that records its calls and writes a plausible PNG."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, kind_name: str, payload: Any = None, **kwargs: Any) -> Path:
        out = Path(kwargs["out"])
        self.calls.append({"kind": kind_name, **kwargs})
        out.write_bytes(PNG)
        return out


def _clean() -> MapReading:
    return MapReading(legend_present=True, legend_readable=True)


def _illegible() -> MapReading:
    return MapReading(legend_present=True, legend_readable=False)


def test_a_clean_reading_stops_after_one_round(tmp_path: Path) -> None:
    spy = Spy()
    result = improve(
        FakeLLMClient([_clean()]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy,
    )
    assert result.reason == "readable"
    assert len(result.rounds) == 1
    assert not result.improved, "nothing was changed, and the result must not imply otherwise"
    assert len(spy.calls) == 1


def test_a_safe_repair_is_applied_and_the_next_round_uses_it(tmp_path: Path) -> None:
    """The illegible legend is a structural finding, so the loop acts on it
    without needing the reader to have written a sentence about it."""
    spy = Spy()
    result = improve(
        FakeLLMClient([_illegible(), _clean()]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy,
    )
    assert [r.index for r in result.rounds] == [1, 2]
    assert result.improved
    applied = result.rounds[0].applied
    assert [(r.option, r.value) for r in applied] == [("width", 1400)], (
        "density's width defaults to 1000, so one rung up is 1400 -- 745 would "
        "mean the choropleth default leaked across kinds"
    )
    assert "width" not in spy.calls[0], "the first round must use the renderer's own default"
    assert spy.calls[1]["width"] == 1400
    assert result.reason == "readable"


def test_an_unsafe_repair_is_offered_and_never_applied(tmp_path: Path) -> None:
    """Re-cutting the classes changes what the map says about the data."""
    spy = Spy()
    reading = MapReading(
        legend_present=True,
        legend_readable=True,
        issues=[
            MapIssue(severity="blocking", what="two bands are indistinguishable, the same colour"),
        ],
    )
    result = improve(
        FakeLLMClient([reading, reading]), "choropleth", [{"id": "FRA", "value": 1}],
        out=tmp_path / "m.png", renderer=spy,
    )
    assert all("method" not in call for call in spy.calls), "the method was changed unattended"
    assert [(r.option, r.value) for r in result.for_a_person] == [("method", "equal")]
    assert not result.improved


def test_the_same_complaint_twice_stops_it(tmp_path: Path) -> None:
    """Without this the loop trades one wording for another until the ceiling."""
    spy = Spy()
    stuck = MapReading(
        legend_present=True,
        legend_readable=True,
        issues=[MapIssue(severity="blocking", what="the map is cluttered with labels")],
    )
    result = improve(
        FakeLLMClient([stuck, stuck, stuck, stuck]), "choropleth", [{"id": "FRA", "value": 1}],
        out=tmp_path / "m.png", renderer=spy,
    )
    assert result.reason == "repeated_issue_signature"
    assert len(result.rounds) == 2, f"ran {len(result.rounds)} rounds"


def test_the_wrong_kind_drawn_is_not_an_option_problem(tmp_path: Path) -> None:
    """No keyword fixes it, so the loop says so instead of spending its rounds."""
    spy = Spy()
    reading = MapReading(kind_seen="choropleth", legend_present=True, legend_readable=False)
    result = improve(
        FakeLLMClient([reading]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy,
    )
    assert result.reason == "wrong_kind_rendered"
    assert len(spy.calls) == 1


def test_a_complaint_no_rule_matches_produces_no_repair(tmp_path: Path) -> None:
    """An honest dead end: the loop stops rather than guessing a keyword."""
    spy = Spy()
    reading = MapReading(
        legend_present=True,
        legend_readable=True,
        issues=[MapIssue(severity="blocking", what="the subject of the map is uninteresting")],
    )
    result = improve(
        FakeLLMClient([reading]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy,
    )
    assert result.reason == "no_repair_available"
    assert not result.improved


def test_the_ceiling_cannot_be_raised_by_a_caller(tmp_path: Path) -> None:
    """`max_rounds` lowers the bill; it does not raise it. Every round renders
    and reads a map, so the ceiling is a cost control as much as a rule."""
    spy = Spy()
    varying = [
        MapReading(
            legend_present=True,
            legend_readable=True,
            issues=[MapIssue(severity="blocking", what=f"the map is cluttered, round {n}")],
        )
        for n in range(20)
    ]
    result = improve(
        FakeLLMClient(varying), "choropleth", [{"id": "FRA", "value": 1}],
        out=tmp_path / "m.png", renderer=spy, max_rounds=99,
    )
    assert len(result.rounds) <= MAX_ROUNDS, f"{len(result.rounds)} rounds against a ceiling of {MAX_ROUNDS}"


def test_a_non_png_destination_is_refused(tmp_path: Path) -> None:
    """A vision model shown SVG source reads the markup, never the picture."""
    with pytest.raises(ValueError, match="raster|png"):
        improve(FakeLLMClient([_clean()]), "density", POINTS,
                out=tmp_path / "m.svg", renderer=Spy())


def test_the_reader_is_shown_the_bytes_that_were_rendered(tmp_path: Path) -> None:
    client = FakeLLMClient([_clean()])
    improve(client, "density", POINTS, out=tmp_path / "m.png", renderer=Spy())
    assert client.calls[0]["image"] == PNG


def test_the_users_own_title_is_never_rewritten(tmp_path: Path) -> None:
    spy = Spy()
    improve(
        FakeLLMClient([_illegible(), _clean()]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy, title="Où la foudre est tombée",
    )
    assert {call["title"] for call in spy.calls} == {"Où la foudre est tombée"}


def test_one_round_against_the_real_renderer(tmp_path: Path) -> None:
    """The loop must actually produce a map, not only drive a stub.

    Everything above injects a renderer and would pass against one that never
    drew anything, so this one does not. It carried a ``slow`` marker until the
    cost was measured: 0.08 s and an 11 KB PNG, for three points. A marker is
    an invitation to deselect, and a guard nobody runs is worse than none.
    """
    client = FakeLLMClient([_clean()])
    out = tmp_path / "real.png"
    result = improve(client, "density", POINTS, out=out, title="Essai")
    assert result.image.is_file()
    assert result.image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.calls[0]["image"][:8] == b"\x89PNG\r\n\x1a\n", (
        "the reader was shown something that is not a PNG"
    )
    assert result.image.stat().st_size > 2000
