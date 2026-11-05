"""
A render with no ``out`` lands in the working directory, nowhere else.

Every generator used to fall back to ``assets/svg-examples/<kind>.svg`` one
level above ``scripts/``. Reached through ``make_choropleth()`` or
``make-map choropleth``, that fallback overwrote the committed example in a
checkout and wrote under ``site-packages/`` in an installed package: a bare
``make-map density`` edited the shop window, or the interpreter. Both doors
now default to ``<kind>.svg`` in the current directory, and these tests hold
them to it without touching the committed examples.

The same fix landed in sprezzature-figures 2.9.0, for the same reason.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

import sprezzature_maps
from sprezzature_maps.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "assets" / "svg-examples"

#: Library function, CLI sub-command and the file stem each one writes.
#: ``situation_map`` keeps the underscore the committed example and the
#: registry already use, whichever CLI spelling was typed.
_KINDS = [
    ("make_choropleth", "choropleth", "choropleth"),
    ("make_density", "density", "density"),
    ("make_situation_map", "situation-map", "situation_map"),
]

#: Cheap arguments: the default density is 400 000 points binned at 120.
_FAST_LIB: dict[str, dict[str, object]] = {
    "make_choropleth": {"relief": False, "cities": False, "rivers": False},
    "make_density": {"points": [(-100.0, 40.0), (-90.0, 35.0)], "bins": 20},
    "make_situation_map": {},
}


@pytest.fixture
def examples_untouched() -> Iterator[None]:
    """Fail if any committed example is rewritten during the test."""
    before = {p.name: p.stat().st_mtime_ns for p in EXAMPLES.glob("*.svg")}
    assert before, "no committed example to guard"
    yield
    after = {p.name: p.stat().st_mtime_ns for p in EXAMPLES.glob("*.svg")}
    assert after == before, "a committed example was rewritten"


@pytest.mark.parametrize(("function", "_command", "stem"), _KINDS)
def test_library_without_out_writes_kind_svg_in_cwd(
    function: str,
    _command: str,
    stem: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    examples_untouched: None,
) -> None:
    monkeypatch.chdir(tmp_path)
    path = getattr(sprezzature_maps, function)(**_FAST_LIB[function])
    assert Path(path).resolve() == (tmp_path / f"{stem}.svg").resolve()
    assert Path(path).read_text(encoding="utf-8").lstrip().startswith(("<svg", "<?xml"))


@pytest.mark.parametrize(("_function", "command", "stem"), _KINDS)
def test_cli_without_out_writes_kind_svg_in_cwd(
    _function: str,
    command: str,
    stem: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    examples_untouched: None,
) -> None:
    monkeypatch.chdir(tmp_path)
    args = [command]
    if command == "choropleth":
        args += ["--no-relief"]
    elif command == "density":
        points = tmp_path / "points.json"
        points.write_text("[[-100, 40], [-90, 35]]", encoding="utf-8")
        args += ["--points", str(points), "--bins", "20"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    written = tmp_path / f"{stem}.svg"
    assert written.exists()
    assert str(written.resolve()) in result.output or str(written) in result.output


def test_the_committed_examples_are_reached_only_by_naming_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, examples_untouched: None
) -> None:
    """A bare demo call from the repository root leaves ``assets/`` alone.

    The old fallback did not depend on the working directory at all, so the
    sharpest version of the check runs from a directory that is not the
    examples' own and then asserts both halves: the file appeared here, and
    the committed one kept its timestamp (the fixture).
    """
    monkeypatch.chdir(tmp_path)
    path = sprezzature_maps.make_situation_map()
    assert Path(path).parent.resolve() == tmp_path.resolve()
    assert not Path(path).resolve().is_relative_to(EXAMPLES.resolve())
