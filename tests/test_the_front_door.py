"""Tests that the Click command line keeps its contract: ``sprezzature-maps``
renders both map kinds and reads CSV data with column mapping correctly.

One scenario-style file covering many small cases together, mirroring
what was checked by hand while building ``sprezzature_maps/cli.py``,
following CODING.md's "prefer functional tests over one test per
function" guidance, since these commands are thin adapters over
generators that already have their own unit tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_MANIFEST_ROOT = Path(__file__).resolve().parent.parent


def _console_scripts() -> dict[str, str]:
    """
    ``[project.scripts]``, read with a regex rather than ``tomllib``.

    ``tomllib`` is standard library only from 3.11 and this package supports
    3.10, where the import alone fails -- in CI, while passing on every
    developer machine. sprezzature-cli-gui's own test says exactly this in a
    comment, and it was written there because it had already happened once.
    """
    text = (_MANIFEST_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if block is None:
        return {}
    return dict(re.findall(r'^([\w.-]+)\s*=\s*"([^"]+)"', block.group(1), re.M))


def _base_dependencies() -> str:
    """The ``dependencies = [...]`` block as text, comments stripped."""
    text = (_MANIFEST_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S)
    return re.sub(r"#[^\n]*", "", block.group(1)) if block else ""


def _extras() -> set[str]:
    """The extras this package declares."""
    text = (_MANIFEST_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    return set(re.findall(r"^([\w.-]+)\s*=\s*\[", block.group(1), re.M)) if block else set()


click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

from sprezzature_maps.cli import main  # noqa: E402

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
            "--data",
            str(csv_path),
            "--map",
            "id=Code",
            "--map",
            "value=Score",
            "--out",
            str(out),
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
    """No --config renders the bundled Europe demo."""
    out = tmp_path / "region.svg"
    result = runner.invoke(main, ["situation-map", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_the_two_spellings_are_one_callable() -> None:
    """
    ``make-map`` and ``sprezzature-maps`` must resolve to the same target.

    There were two parsers until 2026-10-25, and the click one was missing a
    command the argparse one had — ``density`` — which is exactly how a second
    front door fails: not loudly, but by quietly offering less.
    """
    scripts = _console_scripts()
    assert scripts["make-map"] == scripts["sprezzature-maps"]
    assert scripts["make-map"] == "sprezzature_maps.cli:main"


def test_every_generator_has_a_command() -> None:
    """
    The three generators this package ships must each be reachable.

    ``density`` was in the argparse front door and not the click one. Removing
    argparse without porting it would have dropped a documented generator from
    the command line with nothing to notice.
    """
    from sprezzature_maps.cli import main

    assert {"choropleth", "density", "situation-map"} <= set(main.commands)


def test_no_second_parser_grows_back() -> None:
    """A second front door is how `density` went missing in the first place."""
    from pathlib import Path

    pkg = Path(__file__).resolve().parent.parent / "sprezzature_maps"
    assert not (pkg / "cli_click.py").exists()
    assert "import argparse" not in (pkg / "cli.py").read_text(encoding="utf-8")
