"""A curved flow passes through its points and never invents a detour.

On 2026-11-13 a flow arrow from Amdjarass (Chad) to El Fasher via al-Tina was
drawn through three points, legs of about 120 km and 300 km. The uniform
Catmull-Rom spline the arrows used overshot past the turn and came back, and
the geopolitics researcher it was drawn for said: "in real life there is no
reason to go that low to climb back up." The arrows now use the centripetal
spline, and `bend` asks for a curve in one word instead of typed control
points.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("msm_flow", _SCRIPTS / "make_situation_map.py")
msm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(msm)


def _overshoot(points: list[tuple[float, float]]) -> float:
    """How far the curve leaves the box its own points span, on either axis.

    The old spline's detour was sideways: 22 units west of the turn it was
    meant to round, on a plate where west is into Chad.
    """
    curve = msm._catmull_rom(points, per_segment=40)
    worst = 0.0
    for axis in (0, 1):
        lo = min(p[axis] for p in points)
        hi = max(p[axis] for p in points)
        worst = max(worst, max(max(0.0, lo - c[axis], c[axis] - hi) for c in curve))
    return worst


def test_uneven_legs_do_not_overshoot() -> None:
    # A short leg straight down, then a long one across: the shape of
    # Amdjarass -> al-Tina -> El Fasher on the plate.
    points = [(0.0, 0.0), (0.0, 120.0), (300.0, 260.0)]
    assert _overshoot(points) < 1.0


def test_the_curve_still_passes_through_every_point() -> None:
    points = [(0.0, 0.0), (0.0, 120.0), (300.0, 260.0)]
    curve = msm._catmull_rom(points, per_segment=40)
    for p in points:
        assert min(abs(x - p[0]) + abs(y - p[1]) for x, y in curve) < 1e-6


def test_bend_curves_a_two_point_flow_to_the_requested_side() -> None:
    bent = msm._catmull_rom(msm._bend_path([(0.0, 0.0), (100.0, 0.0)], 0.15), per_segment=20)
    # Travelling +x with y growing downward, "left" is negative y.
    assert min(y for _, y in bent) < -10.0
    assert max(y for _, y in bent) <= 1e-9
