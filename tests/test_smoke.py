"""Smoke tests: both generators render valid, non-trivial SVG from their demo data."""

from __future__ import annotations

from pathlib import Path

from sprezzature_maps import make_choropleth, make_situation_map


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
