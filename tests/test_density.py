"""
Tests for the accumulation map.

What matters here is not that it draws, but that it keeps the two promises
the form rests on: the data defines the geography, and the plate stays
within the size budget that made a vector answer defensible at all.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _density():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "_density_mod", ROOT / "scripts" / "make_density.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_one_path_per_level_not_one_per_cell() -> None:
    """
    The whole field is as many paths as there are levels.

    One rect per cell put the same plate at 972 KB against its PNG's 15 KB.
    Merging every cell of a level into one path is what makes a vector
    answer defensible, and a regression here would be invisible except in
    the file size.
    """
    module = _density()
    svg = module.build_svg(bins=60)
    assert svg.count("<path") <= len(module.RAMP), svg.count("<path")


def test_the_plate_stays_inside_the_budget() -> None:
    """
    A megabyte is too much; a few hundred kilobytes is fine.

    The default bin count was chosen against this, and a change that pushed
    it past the budget would be a change that should have binned coarser.
    """
    module = _density()
    svg = module.build_svg()
    assert len(svg.encode("utf-8")) < 300_000, len(svg.encode("utf-8"))


def test_empty_cells_are_left_bare() -> None:
    """
    No data is not zero data.

    The sea is dark because nothing fell there, not because something drew
    it dark. Painting empty cells the lowest level would fill the whole
    rectangle and lose the only thing this form is for.
    """
    module = _density()
    grid, nx, ny, peak = module.bin_points(
        [(-100.0, 40.0)] * 50, (-125.0, 25.0, -67.0, 49.0), 20
    )
    filled = sum(1 for col in grid for cell in col if cell)
    assert filled == 1, filled
    assert peak == 50


def test_cells_overlap_so_no_seam_shows() -> None:
    """
    Adjacent rectangles that merely touch leave an antialiased seam.

    A grid of hairlines appeared over the whole field the first time. The
    overlap is small enough to be invisible and large enough to close it.
    """
    module = _density()
    assert 0 < module._OVERLAP < 1


def test_an_empty_window_is_refused() -> None:
    """Silently drawing a blank plate would look like a region with no events."""
    module = _density()
    with pytest.raises(ValueError, match="no point fell"):
        module.build_svg(points=[(0.0, 0.0)], bbox=(-125.0, 25.0, -67.0, 49.0))


def test_bins_must_be_positive() -> None:
    """A typo must not produce a division by zero three frames down."""
    module = _density()
    with pytest.raises(ValueError, match="bins must be positive"):
        module.build_svg(bins=0)


def test_the_demo_says_it_is_synthetic() -> None:
    """
    A demo that passed itself off as observation would be the one dishonest
    thing in the file, and this plate is persuasive enough to be believed.
    """
    module = _density()
    svg = module.build_svg(bins=40)
    assert "SYNTHETIC" in svg.upper()
