"""A country cut at the antimeridian must not be re-closed across the map.

The defect this guards, found by looking at the plate rather than at the
code. Four rings in the vendored atlas run past +-180: Russia's mainland
and a companion, Fiji, and both of Antarctica's. The generator already cut
them at the seam, correctly, and then closed each resulting piece on
itself -- which is wrong, because a ring is a *cycle* and the vertex it
happens to be stored from sits in the middle of one of the pieces. That
piece therefore arrives in two halves, one at each end of the list, and
closing each half separately draws a chord from its own last vertex back
to its own first.

For Russia that chord ran from the Bering coast diagonally across the Sea
of Okhotsk to Japan, filled in the same confident blue as a real value.
Nobody saw it for as long as the relief layer painted the sea khaki; the
moment the sea became the page, it was the first thing on the plate.

The invariant is cheap to state and leaves no room to argue: **a drawn
sub-polygon closes along the seam or it closes on itself, never across the
map.** Measured as the longitude distance between a piece's two ends --
0.1 degrees for Russia once the halves are rejoined, 152 degrees before.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from make_choropleth import _load_countries, seam_segments  # noqa: E402

#: How far apart, in degrees of longitude, a piece's two ends may be
#: before the line closing them stops being an edge of the map and starts
#: being a shoreline the atlas does not have. Two degrees is roughly four
#: pixels on a 745-unit world plate -- comfortably above the rounding in
#: the vendored coordinates, and two orders of magnitude below the 152 the
#: defect produced.
_MAX_CLOSING_SPAN_DEG = 2.0


def _identity(lon: float, lat: float) -> tuple[float, float]:
    """Stand in for the map's projection, so pieces come back in degrees."""
    return lon, lat


def _wrapping_rings() -> list[tuple[str, int, list[tuple[float, float]]]]:
    """Every ring in the vendored atlas that crosses the antimeridian."""
    found = []
    for country in _load_countries():
        for index, ring in enumerate(country["rings"]):
            if len(ring) < 3:
                continue
            if any(
                abs(nxt[0] - here[0]) > 180.0
                for here, nxt in zip(ring, ring[1:], strict=False)
            ):
                found.append((str(country["name"]), index, ring))
    return found


def test_the_atlas_still_has_rings_that_cross_the_seam():
    """Without these, every assertion below would pass by having nothing to check.

    A vendored atlas can be re-cut, and an atlas whose rings were split at
    the seam upstream would leave this whole file green and asleep.
    """
    names = {name for name, _i, _r in _wrapping_rings()}
    assert names, "no ring crosses the antimeridian: the guard below tests nothing"
    assert {"Russia", "Antarctica"} <= names, (
        f"the atlas changed shape: expected Russia and Antarctica to wrap, got {names}"
    )


@pytest.mark.parametrize("name,index,ring", _wrapping_rings(), ids=lambda v: str(v)[:18])
def test_no_piece_closes_itself_across_the_map(name, index, ring):
    """Each piece's two ends are near enough to join without crossing the plate."""
    for piece_no, piece in enumerate(seam_segments(ring, _identity)):
        first_lon, last_lon = piece[0][0], piece[-1][0]
        span = abs(last_lon - first_lon)
        assert span <= _MAX_CLOSING_SPAN_DEG, (
            f"{name} ring {index} piece {piece_no} would be closed by a chord "
            f"spanning {span:.1f} degrees of longitude, from {first_lon:.1f} to "
            f"{last_lon:.1f}. That line is not a coastline; it is a hole in the "
            "seam handling being filled in as if it were land."
        )


def test_a_pole_encircling_ring_is_closed_over_the_pole():
    """Antarctica's coast crosses the seam once, so it has to close over the pole.

    An odd number of crossings is a ring that went round the world and did
    not come back, which it can only do by going round a pole. Joining its
    two ends directly would run a chord across the plate at about 84
    degrees south *and* leave the six degrees below it unfilled -- a
    shoreline invented and a shoreline lost in one stroke.
    """
    coast = max(
        (ring for nm, _i, ring in _wrapping_rings() if nm == "Antarctica"),
        key=len,
    )
    pieces = seam_segments(coast, _identity)
    assert len(pieces) == 1, "one crossing should leave one piece"
    reached = min(lat for _lon, lat in pieces[0])
    assert reached == pytest.approx(-90.0), (
        f"the closed coastline reaches only {reached:.1f} degrees south; "
        "a ring that encircles the pole has to be taken to it"
    )
