"""An accumulation map of real events does not describe itself as the demo.

The lightning title and the line ``SYNTHETIC DEMONSTRATION DATA`` are true of
the bundled demo set and of nothing else. They used to be the defaults of every
call, so a caller's own events came out captioned as invented, and the audit's
provenance rule, which rightly accepts "synthetic", passed on that false
sentence. And ``make-map density --points`` has no ``--bbox``, so it binned over
the demo's window: events outside the contiguous United States ended in an
error from the drawing code.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sprezzature_maps import _load_script, make_density
from sprezzature_maps.audit import audit
from sprezzature_maps.cli import main

EUROPE = [[2.35, 48.86], [2.29, 48.85], [5.37, 43.30], [13.40, 52.52], [12.50, 41.90]]
FRAME = (-5.0, 40.0, 16.0, 55.0)


def test_the_demo_still_says_it_is_synthetic() -> None:
    svg = _load_script("make_density").build_svg(bins=20, width=300)
    assert "SYNTHETIC DEMONSTRATION DATA" in svg
    assert "Where the lightning fell" in svg


def test_your_own_points_are_not_labelled_as_the_demo(tmp_path: Path) -> None:
    out = make_density(points=[tuple(p) for p in EUROPE], bbox=FRAME, out=tmp_path / "e.svg")
    svg = Path(out).read_text(encoding="utf-8")
    for word in ("SYNTHETIC", "synthetic", "lightning", "flash"):
        assert word not in svg


def test_real_points_with_no_source_are_reported_by_the_audit(tmp_path: Path) -> None:
    out = make_density(
        points=[tuple(p) for p in EUROPE], bbox=FRAME, title="Strikes", out=tmp_path / "e.svg"
    )
    rules = {finding.rule for finding in audit(Path(out).read_text(encoding="utf-8"))}
    assert "no-provenance" in rules


def test_a_caption_you_pass_is_the_caption_drawn(tmp_path: Path) -> None:
    out = make_density(
        points=[tuple(p) for p in EUROPE],
        bbox=FRAME,
        caption="SOURCE: ACLED",
        out=tmp_path / "e.svg",
    )
    assert "SOURCE: ACLED" in Path(out).read_text(encoding="utf-8")


def test_the_command_line_frames_points_outside_the_demo_window(tmp_path: Path) -> None:
    points = tmp_path / "events.json"
    points.write_text(json.dumps(EUROPE), encoding="utf-8")
    out = tmp_path / "where.svg"
    result = CliRunner().invoke(
        main, ["density", "--points", str(points), "--bins", "20", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_an_empty_list_of_points_is_an_error_not_a_traceback(tmp_path: Path) -> None:
    points = tmp_path / "events.json"
    points.write_text("[]", encoding="utf-8")
    result = CliRunner().invoke(main, ["density", "--points", str(points)])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "no points" in result.output


def test_a_bad_config_is_an_error_not_a_traceback(tmp_path: Path) -> None:
    config = tmp_path / "region.yaml"
    config.write_text("region: {bbox: [2, 42, 8, 48]}\nareas_of_contrl: {}\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["situation-map", "--config", str(config), "--out", str(tmp_path / "r.svg")]
    )
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "areas_of_control" in result.output
