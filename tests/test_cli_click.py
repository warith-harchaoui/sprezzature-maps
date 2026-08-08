"""Click CLI contract tests: ``sprezzature-maps`` renders both kinds and
ingests CSV data with column mapping.

One scenario-style file, mirroring what was verified by hand while
building ``sprezzature_maps/cli_click.py`` -- CODING.md's "prefer
functional tests over one test per function" guidance, since these
commands are thin adapters over the already-unit-tested generators.
"""

from __future__ import annotations

from pathlib import Path

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

from sprezzature_maps.cli_click import main  # noqa: E402

runner = CliRunner()


def test_list_prints_both_kinds() -> None:
    """`list` is a plain, scriptable one-kind-per-line output."""
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert result.output.splitlines() == ["choropleth", "situation_map"]


def test_choropleth_demo(tmp_path: Path) -> None:
    """No --data renders the built-in demo data."""
    out = tmp_path / "world.svg"
    result = runner.invoke(main, ["choropleth", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "<svg" in out.read_text()[:200]


def test_choropleth_csv_with_column_mapping(tmp_path: Path) -> None:
    """--data CSV with non-default column names, bound via --map."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("Code,Score\n840,12.5\n124,-3.2\n", encoding="utf-8")
    out = tmp_path / "custom.svg"
    result = runner.invoke(
        main,
        [
            "choropleth",
            "--data", str(csv_path),
            "--map", "id=Code",
            "--map", "value=Score",
            "--out", str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_choropleth_missing_column_is_a_clean_error(tmp_path: Path) -> None:
    """A CSV without id/value columns (and no --map) fails with a helpful
    message, not a traceback."""
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("foo,bar\n1,2\n", encoding="utf-8")
    result = runner.invoke(main, ["choropleth", "--data", str(csv_path)])
    assert result.exit_code != 0
    assert "missing column" in result.output


def test_situation_map_demo(tmp_path: Path) -> None:
    """No --config renders the bundled Western-Europe demo."""
    out = tmp_path / "region.svg"
    result = runner.invoke(main, ["situation-map", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
