"""
The loop must be reachable, which is the part this suite keeps getting wrong.

The dominant failure here is not a broken tool: it is a working tool nothing
calls. ``list`` answered two kinds of three for exactly that reason, and the
``--map`` role was silently ignored for the same shape of reason. So the loop
gets a sub-command, and this file drives it through Click's runner — against
``main.commands``, which is running code, not source text.

No model is involved: ``default_client`` is replaced with a scripted fake, so
what is tested is the wiring, the refusals and the report.

Author
------
Project maintainers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sprezzature_maps.assistant import FakeLLMClient, MapIssue, MapReading
from sprezzature_maps.cli import main

POINTS = [[2.35, 48.85], [13.4, 52.52], [-0.12, 51.5]]


@pytest.fixture
def points_file(tmp_path: Path) -> Path:
    path = tmp_path / "events.json"
    path.write_text(json.dumps(POINTS), encoding="utf-8")
    return path


def _fake(readings: list[MapReading]):
    client = FakeLLMClient(list(readings))
    return lambda: client


def test_the_command_exists_and_is_not_only_a_function() -> None:
    """Asked of the group's running registry, not of the file."""
    assert "improve" in main.commands


def test_it_renders_and_reports(points_file: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sprezzature_maps.assistant.default_client",
        _fake([MapReading(kind_seen="density", legend_present=True, legend_readable=True)]),
    )
    out = tmp_path / "m.png"
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "density", "--points", str(points_file), "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file() and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "round 1: read as density" in result.output
    assert "stopped: readable" in result.output
    assert "nothing was changed" in result.output


def test_a_safe_repair_is_reported_as_applied(points_file: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sprezzature_maps.assistant.default_client",
        _fake([
            MapReading(kind_seen="density", legend_present=True, legend_readable=False),
            MapReading(kind_seen="density", legend_present=True, legend_readable=True),
        ]),
    )
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "density", "--points", str(points_file),
         "--out", str(tmp_path / "m.png")],
    )
    assert result.exit_code == 0, result.output
    assert "applied width=1400" in result.output
    assert "nothing was changed" not in result.output


def test_an_unsafe_repair_is_printed_for_a_person(tmp_path: Path, monkeypatch) -> None:
    rows = tmp_path / "rows.csv"
    rows.write_text("id,value\nFRA,68\nDEU,83\n", encoding="utf-8")
    stuck = MapReading(
        kind_seen="choropleth",
        legend_present=True,
        legend_readable=True,
        issues=[MapIssue(severity="blocking", what="two bands are the same colour")],
    )
    monkeypatch.setattr(
        "sprezzature_maps.assistant.default_client", _fake([stuck, stuck]),
    )
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "choropleth", "--data", str(rows),
         "--out", str(tmp_path / "m.png")],
    )
    assert result.exit_code == 0, result.output
    assert "for you to decide: method=" in result.output
    assert "can change what the map says about the data" in result.output


def test_the_wrong_flag_for_the_kind_names_the_right_one(points_file: Path, tmp_path: Path) -> None:
    """The registry answers this, so a fourth kind needs no new branch."""
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "choropleth", "--points", str(points_file),
         "--out", str(tmp_path / "m.png")],
    )
    assert result.exit_code != 0
    assert "--data" in result.output and "--points" in result.output


def test_no_data_at_all_says_which_flag(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["improve", "--kind", "density", "--out", str(tmp_path / "m.png")]
    )
    assert result.exit_code != 0
    assert "--points" in result.output


def test_a_non_png_destination_is_refused_with_a_reason(points_file: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sprezzature_maps.assistant.default_client",
        _fake([MapReading(legend_present=True, legend_readable=True)]),
    )
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "density", "--points", str(points_file),
         "--out", str(tmp_path / "m.svg")],
    )
    assert result.exit_code != 0
    assert "raster" in result.output or "png" in result.output


def test_an_unknown_kind_is_refused_by_the_registry(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["improve", "--kind", "heatmap", "--out", str(tmp_path / "m.png")]
    )
    assert result.exit_code != 0
    assert "heatmap" in result.output


def test_a_bad_role_is_refused_before_a_model_is_called(tmp_path: Path) -> None:
    """The reader's own refusal, inherited rather than reimplemented."""
    rows = tmp_path / "rows.csv"
    rows.write_text("id,value\nFRA,68\n", encoding="utf-8")
    result = CliRunner().invoke(
        main,
        ["improve", "--kind", "choropleth", "--data", str(rows),
         "--map", "colour=value", "--out", str(tmp_path / "m.png")],
    )
    assert result.exit_code != 0
    assert "colour" in result.output
