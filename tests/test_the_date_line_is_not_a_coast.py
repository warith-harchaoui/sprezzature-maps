"""
A ring that crosses the date line is not a coast across the world.

Read as written, a lon/lat ring jumps from +179.9 to -179.9 where it crosses
the antimeridian, and that jump is a straight edge back across the planet.
Russia's outline in the vendored 1:50m atlas does it; so does Fiji's. The
damage showed in three places at once: bands of "land" 200 degrees wide at
65 to 71.5 N in every Arctic context, Fiji's seam drawn as two straight lines
of coast through Lake Titicaca on the Andes plate, and the Andes locator
striped with land that wrapped round from the far side of its projection.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import box

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

_ANDES = [-88.0, -56.0, -32.0, 3.0]


def _thin_wide_parts(geom, min_span: float = 20.0, max_height: float = 6.0) -> list:
    return [
        p.bounds
        for p in getattr(geom, "geoms", [geom])
        if p.bounds[2] - p.bounds[0] > min_span and p.bounds[3] - p.bounds[1] < max_height
    ]


@pytest.mark.parametrize("tier", [None, (30.0, 40.0, 40.0, 50.0)], ids=["50m", "10m"])
def test_russia_has_no_band_across_the_arctic(tier) -> None:
    russia = dict(msm.load_countries(tier))["Russia"]
    assert not _thin_wide_parts(russia), "Russia carries a wrap band"


def test_the_two_tiers_agree_on_how_big_russia_is() -> None:
    """The 50m Russia was 365 square degrees larger: the bands."""
    coarse = dict(msm.load_countries(None))["Russia"].area
    fine = dict(msm.load_countries((30.0, 40.0, 40.0, 50.0)))["Russia"].area
    assert coarse == pytest.approx(fine, rel=0.02)


def test_no_straight_coast_crosses_the_andes_plate() -> None:
    """Fiji's seam ran through La Paz at 16.5 S, edge to edge."""
    land = msm.load_land(bbox=_ANDES).intersection(box(*_ANDES))
    long_parallels = [
        (a, b)
        for poly in getattr(land, "geoms", [land])
        for ring in [poly.exterior, *poly.interiors]
        for a, b in zip(list(ring.coords), list(ring.coords)[1:], strict=False)
        if abs(b[1] - a[1]) < 0.05 and abs(b[0] - a[0]) > 8
        and min(abs(a[1] - _ANDES[1]), abs(a[1] - _ANDES[3])) > 0.01
    ]
    assert not long_parallels, f"a straight parallel of coast: {long_parallels[:2]}"


def test_a_ring_is_unwrapped_rather_than_closed_across_the_world() -> None:
    ring = [(179.0, 0.0), (-179.0, 0.0), (-179.0, 1.0), (179.0, 1.0), (179.0, 0.0)]
    poly = msm._polygon_across_the_date_line([ring])
    assert poly.area == pytest.approx(2.0), "the polygon is the 2-degree box, not the world"
    assert all(-180.0 <= v <= 180.0 for v in (poly.bounds[0], poly.bounds[2]))


def test_the_locator_loads_no_more_than_half_a_world_either_side() -> None:
    """Land past 180 degrees from the centre wrapped round as bands."""
    import inspect

    source = inspect.getsource(msm._inset_layer)
    assert "centre - 179.9" in source and "centre + 179.9" in source
    assert math.isfinite(msm._INSET_ZOOM)
