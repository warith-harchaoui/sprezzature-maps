"""A country's wrap seam is not a frontier, and must never be drawn as one.

The defect this guards, found by looking at the plate rather than the code.
Six countries in the vendored atlas cross the antimeridian. Five are stored
split into real halves. Fiji is not: among its twenty-six parts sits a
six-vertex rectangle **358.89 degrees wide and 0.05 degrees tall**, lying at
16.5 degrees south. It is not an island. It is the seam a ring leaves when it
runs off one edge of the world and has to get home along a parallel.

Nothing about it shows until a plate happens to sit on that parallel. Shapely
normalises Fiji's bounding box to the whole planet, so every plate on Earth
loads it and asks whether it is in frame -- and the Andes plate, the equator
to Cape Horn and nowhere near the Pacific, answered yes. It drew Fiji's seam
as a dashed international frontier straight across the South Atlantic, through
La Paz, and out over the Pacific the other side: eleven hundred pixels of open
ocean in the house border style, on a plate whose whole subject is a mountain
range.

Two assertions, because the defect has two faces and either could come back
alone:

* **the atlas hands out no seam.** The repair lives in the two TopoJSON
  decoders, so this asks the loaders directly and names the country if one
  reappears -- a new atlas vintage is the realistic way that happens.
* **no plate draws one.** The loaders are not the only way geometry reaches
  the frontier layer; a historical boundary file supplied by a config takes a
  different road. So the drawn plate is measured too, which is the property a
  reader actually has.

This is the sibling of ``test_no_polygon_closes_itself_across_the_map``, which
guards the same hazard on the choropleth's own atlas. Both exist because the
antimeridian is where a round world meets a rectangular file, and the join
leaks differently into every consumer.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from make_situation_map import (  # noqa: E402
    _WRAP_SEAM_HEIGHT_DEGREES,
    _WRAP_SEAM_SPAN_DEGREES,
    load_admin2,
    load_countries,
    load_fr_regions,
    load_osm_admin1,
    load_us_states,
)

#: Every decoder that turns vendored TopoJSON into named polygons. Each is
#: asked for the whole world, because a seam's whole problem is that it is
#: nowhere in particular and therefore everywhere.
_WORLD = (-180.0, -90.0, 180.0, 90.0)


def _atlases() -> list[tuple[str, list[tuple[str, object]]]]:
    """Return ``(loader name, rows)`` for every vendored polygon source."""
    out: list[tuple[str, list[tuple[str, object]]]] = []
    for name, loader in (
        ("countries", load_countries),
        ("us_states", load_us_states),
        ("osm_admin1", load_osm_admin1),
        ("fr_regions", load_fr_regions),
        ("admin2", load_admin2),
    ):
        try:
            out.append((name, loader(bbox=_WORLD)))
        except (FileNotFoundError, TypeError):
            # A loader the vendored tree does not carry, or one with a
            # different signature, is not this test's business.
            continue
    return out


def _seam_parts(geom: object) -> list[tuple[float, float]]:
    """Return ``(width, height)`` for every part of ``geom`` shaped like a seam."""
    if geom is None:
        return []
    parts = list(getattr(geom, "geoms", [])) or [geom]
    found = []
    for part in parts:
        try:
            west, south, east, north = part.bounds
        except Exception:
            continue
        width, height = east - west, north - south
        if width > _WRAP_SEAM_SPAN_DEGREES and height < _WRAP_SEAM_HEIGHT_DEGREES:
            found.append((width, height))
    return found


def test_no_vendored_atlas_hands_out_a_wrap_seam() -> None:
    """No loader returns a part three hundred degrees wide and flat.

    Stated on the part and not on the country, because the country is
    legitimately enormous and the part never is. Russia, the widest real
    landmass inside one hemisphere, spans about 170 degrees.
    """
    offenders: list[str] = []
    for atlas, rows in _atlases():
        for name, geom in rows:
            for width, height in _seam_parts(geom):
                offenders.append(
                    f"{atlas}: {name or '<unnamed>'} has a part "
                    f"{width:.2f} deg wide and {height:.2f} deg tall"
                )
    assert not offenders, (
        "a vendored atlas is handing out the seam of an antimeridian wrap as "
        "though it were ground. Drawn, it is a frontier straight across the "
        "map. Offenders:\n  " + "\n  ".join(offenders)
    )


def test_the_guard_would_notice_a_seam_coming_back() -> None:
    """Sabotage check: the measurement above actually fires on a real seam.

    A guard whose precondition can never hold passes forever and says
    nothing. This builds the exact shape the atlas used to carry -- Fiji's
    358.89 by 0.05 rectangle at 16.5 south -- and asserts the measurement
    catches it. Without this, removing the repair and leaving the test would
    look like a green suite.
    """
    from shapely.geometry import box

    fiji_seam = box(-180.0, -16.54, 178.89, -16.49)
    assert _seam_parts(fiji_seam), (
        "the seam measurement no longer recognises the shape it was written "
        "for, so the test above is asserting nothing"
    )


@pytest.mark.parametrize("plate_name", ["andes", "south-china-sea", "caribbean"])
def test_no_plate_draws_a_frontier_across_open_water(plate_name: str) -> None:
    """The drawn plate carries no frontier run spanning it at a fixed latitude.

    Measured on the markup rather than on the atlas, because the loaders are
    not the only road into the frontier layer: ``frontiers.source`` takes a
    historical boundary file instead, and a seam in one of those would reach
    the plate past the repair. The three plates named are the wide, ocean-
    heavy ones -- the shape of plate where a seam has room to be obvious and
    where the defect was actually seen.
    """
    import importlib
    import re

    sys.path.insert(0, str(REPO / "tests"))
    from _plates import plate  # noqa: E402

    # The builder, not the shipped YAML beside the plate. Both describe the
    # same plate, and only one of them is in the repository: everything
    # under ``assets/situation-maps/`` is gitignored -- it is one command
    # away from these builders, which are the source. Reading the file made
    # this test pass on a machine that had run that command and fail with
    # ``FileNotFoundError`` on a fresh clone, which is what CI is.
    cfg = importlib.import_module("build_situation_examples").BUILDERS[plate_name]()
    svg = plate(cfg)

    start = svg.index('<g id="frontiers"')
    end = svg.index("<g id=", start + 1)
    layer = svg[start:end]

    width = float(re.search(r'viewBox="0 0 ([\d.]+)', svg).group(1))
    strays: list[str] = []
    for path in re.finditer(r'd="([^"]+)"', layer):
        for run in path.group(1).split("M")[1:]:
            points = re.findall(r"(-?[\d.]+),(-?[\d.]+)", run)
            if len(points) < 2:
                continue
            xs = [float(x) for x, _ in points]
            ys = [float(y) for _, y in points]
            span, rise = max(xs) - min(xs), max(ys) - min(ys)
            # A frontier crossing three-quarters of the plate while staying
            # within a few units of one height is not a border: no coastline
            # or watershed on Earth is that straight for that long.
            if span > 0.75 * width and rise < 0.02 * width:
                strays.append(f"{span:.0f} units wide, {rise:.0f} tall")

    assert not strays, (
        f"{plate_name}: the frontier layer draws a run straight across the "
        f"plate at a fixed height, which is the signature of an antimeridian "
        f"wrap seam rather than a border: {strays}"
    )
