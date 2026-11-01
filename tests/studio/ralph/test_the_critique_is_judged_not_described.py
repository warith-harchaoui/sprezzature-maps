"""
The loop asks for a judgement, and the judgement is what lets it stop well.

The first engine asked what the picture *showed* — kind, title, legend — and
acted on the issues. That repairs a map; it cannot tell whether the repair
helped. A reading with no numbers in it cannot be compared with the one before
it, so a loop built on one cannot tell progress from change: it will trade a
legible legend for a cluttered coastline and call that a round.

So the critique carries five scores and a verdict, and these tests pin the
three things that buys: a verdict can stop the loop, a falling total stops it,
and last round's issues reach the next round's prompt.

Author
------
Project maintainers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps.studio.assistant import (
    FakeLLMClient,
    MapIssue,
    MapReading,
    profile_rows,
)
from sprezzature_maps.studio.ralph import improve
from sprezzature_maps.studio.ralph.critic import issues_as_text, request_critique

POINTS = [[2.35, 48.85], [13.4, 52.52], [-0.12, 51.5]]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
SECRETS = [{"country": "FRA", "patients": "4117"}, {"country": "DEU", "patients": "2903"}]


class Spy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, kind_name: str, payload: Any = None, **kwargs: Any) -> Path:
        out = Path(kwargs["out"])
        self.calls.append({"kind": kind_name, **kwargs})
        out.write_bytes(PNG)
        return out


def _reading(**over: Any) -> MapReading:
    base: dict[str, Any] = {
        "kind_seen": "density", "legend_present": True, "legend_readable": True,
        "verdict": "needs_changes", "readability": 60, "colour_separation": 60,
        "geographic_honesty": 60, "clarity": 60, "answers_the_question": 60,
        "issues": [MapIssue(severity="blocking", what="the surface looks blocky")],
    }
    base.update(over)
    return MapReading(**base)


def test_a_satisfied_verdict_stops_the_loop(tmp_path: Path) -> None:
    """Even with a blocking issue still listed: the reader has said ship it."""
    result = improve(
        FakeLLMClient([_reading(verdict="satisfied")]), "density", POINTS,
        out=tmp_path / "m.png", renderer=Spy(),
    )
    assert result.reason == "satisfied"
    assert len(result.rounds) == 1


def test_a_blocked_verdict_stops_before_anything_else(tmp_path: Path) -> None:
    """No option moves a map that cannot be read at all, so the loop says so
    rather than spending its rounds."""
    spy = Spy()
    result = improve(
        FakeLLMClient([_reading(verdict="blocked", kind_seen="")]), "density", POINTS,
        out=tmp_path / "m.png", renderer=spy,
    )
    assert result.reason == "blocked"
    assert len(spy.calls) == 1


def test_a_falling_total_stops_the_loop(tmp_path: Path) -> None:
    """The rule the first version could not have had.

    Round 1 scores 300 and is repaired; round 2 scores 250 — the repair made
    the map worse on balance. Without the comparison the loop would keep
    going, and the fourth round would be further from the first.
    """
    worse = _reading(readability=30, colour_separation=30, geographic_honesty=30,
                     clarity=30, answers_the_question=30,
                     issues=[MapIssue(severity="blocking", what="the surface looks blocky and coarse")])
    result = improve(
        FakeLLMClient([_reading(), worse, _reading()]), "density", POINTS,
        out=tmp_path / "m.png", renderer=Spy(),
    )
    assert result.reason == "render_regressed", [r.reading.score_total for r in result.rounds]
    assert [r.reading.score_total for r in result.rounds] == [300, 150]


def test_a_rising_total_does_not(tmp_path: Path) -> None:
    """Non-vacuity: the comparison must not stop a loop that is improving."""
    better = _reading(readability=90, colour_separation=90, geographic_honesty=90,
                      clarity=90, answers_the_question=90,
                      issues=[MapIssue(severity="blocking", what="the surface looks blocky, differently")])
    result = improve(
        FakeLLMClient([_reading(), better, better]), "density", POINTS,
        out=tmp_path / "m.png", renderer=Spy(),
    )
    assert result.reason != "render_regressed"
    assert len(result.rounds) >= 2


def test_last_rounds_issues_reach_the_next_prompt(tmp_path: Path) -> None:
    """A critique that cannot see what was already said repeats it — and a
    loop reads a repeated issue as "no progress" and stops on it."""
    client = FakeLLMClient([
        _reading(
            legend_readable=False,
            issues=[MapIssue(severity="blocking", what="the legend is 4px tall")],
        ),
        _reading(verdict="satisfied"),
    ])
    improve(client, "density", POINTS, out=tmp_path / "m.png", renderer=Spy())
    assert len(client.calls) == 2
    assert "the legend is 4px tall" not in client.calls[0]["prompt"]
    assert "the legend is 4px tall" in client.calls[1]["prompt"], (
        "the second critique was asked blind"
    )


def test_the_critique_prompt_carries_no_cell_value() -> None:
    """Judging whether a map is honest about its data needs to know what the
    data is shaped like, not what is in it."""
    client = FakeLLMClient([_reading()])
    request_critique(
        client, PNG, "choropleth",
        options={"width": 1400},
        title="Patients by country",
        profile=profile_rows(SECRETS, source="/Users/someone/trial/patients.csv"),
    )
    prompt = client.calls[0]["prompt"]
    for row in SECRETS:
        for value in row.values():
            assert value not in prompt, f"{value!r} would have been sent to a model"
    assert "country" in prompt and "patients" in prompt, "the headers are the useful part"
    assert "someone" not in prompt and "trial" not in prompt


def test_the_options_are_named_so_a_default_is_not_a_decision() -> None:
    client = FakeLLMClient([_reading()])
    request_critique(client, PNG, "density", options={"bins": 320})
    assert "bins=320" in client.calls[0]["prompt"]
    client2 = FakeLLMClient([_reading()])
    request_critique(client2, PNG, "density")
    assert "(defaults)" in client2.calls[0]["prompt"]


def test_an_empty_previous_round_says_nothing() -> None:
    assert issues_as_text(None) == ""
    assert issues_as_text(MapReading()) == ""
    text = issues_as_text(_reading())
    assert text.startswith("- [blocking]")


@pytest.mark.parametrize("payload", [b"", b'<?xml version="1.0"?><svg/>'])
def test_the_critic_refuses_what_is_not_a_raster(payload: bytes) -> None:
    """Shares its rules with read_map, deliberately: the two are the only
    paths to a vision model here and a reader shown SVG source is the failure
    both exist to avoid."""
    from sprezzature_maps.studio.assistant import MapReadingError

    client = FakeLLMClient([_reading()])
    with pytest.raises(MapReadingError):
        request_critique(client, payload, "density")
    assert not client.calls, "the model was called anyway"
