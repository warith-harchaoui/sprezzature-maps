"""Smoke tests: both generators render valid, non-trivial SVG from their demo data.

A smoke test is the most basic check there is: does the thing work at
all, without checking every detail. The name comes from electronics,
where the first test after building a circuit is powering it on and
checking that nothing literally starts smoking.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sprezzature_maps import _load_script, make_choropleth, make_situation_map


def test_choropleth_renders(tmp_path: Path) -> None:
    out = tmp_path / "choropleth.svg"
    path = make_choropleth(out=out)
    assert path == out
    svg = out.read_text()
    assert svg.startswith("<svg") or "<svg" in svg[:200]
    assert "<path" in svg


def test_situation_map_renders(tmp_path: Path) -> None:
    out = tmp_path / "situation_map.svg"
    path = make_situation_map(out=out)
    assert path == out
    svg = out.read_text()
    assert svg.startswith("<svg") or "<svg" in svg[:200]
    assert "<path" in svg


def test_figures_scripts_dir_resolves_via_installed_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """tooltip_bubble's home must not depend on a sibling checkout existing.

    Regression test: ``make_choropleth.py`` and ``make_situation_map.py``
    used to locate ``sprezzature-figures/scripts/_svg.py`` by guessing two
    hardcoded filesystem paths -- a sibling ``../sprezzature-figures``
    checkout, or ``~/sprezzature-figures`` -- even though ``pyproject.toml``
    already declares ``sprezzature-figures`` as a real dependency that pip
    installs as the sibling package ``sprezzature_figures_scripts``. Any
    real install without that specific sibling-checkout layout (a fresh
    venv, a different user's machine, a Docker image) crashed the moment
    either generator ran, with ``FileNotFoundError`` -- confirmed with a
    real ``pip install`` into a fresh venv with ``HOME`` pointed at an
    empty directory. CI's own green run never caught this because it
    manually clones ``sprezzature-figures`` into the exact sibling
    location the hardcoded guess expects.

    This test proves the fix does not depend on ``Path.home()`` either:
    it points ``HOME`` at a directory with no ``sprezzature-figures`` in
    it and confirms resolution still succeeds via the installed package.
    """
    figures_scripts_dir = _load_script("_assets").figures_scripts_dir

    with tempfile.TemporaryDirectory() as empty_home:
        monkeypatch.setenv("HOME", empty_home)
        resolved = figures_scripts_dir()
        assert (resolved / "_svg.py").is_file()


def test_situation_map_config_dir_default_is_cwd_not_install_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller-supplied config dict must anchor relative paths at cwd.

    Regression test: ``make_situation_map()``'s ``config`` path used to
    default ``_config_dir`` to ``Path(__file__).parent.parent / "assets"``
    -- the source tree's ``assets/`` directory, which does not exist at all
    under an installed wheel (that data ships as the sibling package
    ``sprezzature_maps_geo/``) and was never a sensible anchor for a
    caller-supplied dict regardless of install layout. It is now ``"."``,
    matching the same default the feature-loading helpers
    (``_areas_of_control_layer``/``_infrastructure_layer``) already fall
    back to when the key is absent entirely.
    """
    m = _load_script("make_situation_map")

    captured: dict[str, object] = {}

    def _fake_build_map(cfg: dict[str, object]) -> str:
        captured.update(cfg)
        return "<svg></svg>"

    monkeypatch.setattr(m, "build_map", _fake_build_map)
    # `region` is not incidental: the generator has always required it, and
    # this config only got away without one because build_map is faked here.
    # Config validation (0.6.0) now says so before the fake is reached.
    m.make_situation_map(
        config={"title": "test", "region": "western-europe"},
        out=tmp_path / "out.svg",
    )
    assert captured["_config_dir"] == "."
