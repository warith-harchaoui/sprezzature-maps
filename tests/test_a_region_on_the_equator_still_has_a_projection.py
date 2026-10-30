"""A conic balanced on the equator has no apex, and PROJ says so.

``build_projection`` puts the two standard parallels at the region's
one-sixth and five-sixth latitudes -- the classic two-thirds rule, and the
right rule. For a region balanced on the equator those two parallels are
mirror images, their sum is zero, the cone opens into a cylinder, and PROJ
refuses the whole thing: *"lcc: Invalid value for lat_1 and lat_2:
|lat_1 + lat_2| should be > 0"*.

This was latent for as long as the generator existed. Every shipped plate
sat clear of it, so nothing met it. It surfaced the day the locator inset
became a default: the inset builds a context six times the region's own
size, clamped to the latitudes the basemap covers, and for a plate centred
near the equator that clamp lands on a symmetric box. The Andes plate went
from rendering to raising, and took the three plates after it in the build
down with it.

The countries this would hit are not exotic -- Gabon, Kenya, Ecuador,
Sumatra, any plate of the Congo basin drawn symmetrically.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

import pytest

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")


@pytest.mark.parametrize(
    "bbox,what",
    [
        ([8.0, -4.0, 15.0, 4.0], "Gabon, balanced on the equator"),
        ([-82.0, -6.0, -74.0, 6.0], "Ecuador, the same"),
        ([-180.0, -84.0, 108.0, 84.0], "a locator context clamped to the world"),
        ([33.0, -5.0, 42.0, 5.0], "Kenya"),
    ],
)
def test_a_symmetric_region_projects(bbox, what) -> None:
    """It has to return a transformer, not an exception."""
    proj = msm.build_projection(bbox, "auto")
    x, y = proj.transform((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    assert all(abs(v) < 1e9 for v in (x, y)), f"{what} projected to {x}, {y}"


def test_an_ordinary_region_still_gets_its_conic() -> None:
    """The fallback must not quietly take over the normal case.

    A conic is the right projection for a regional plate and the reason
    the shapes on these maps are true. Swapping it for a cylindrical one
    everywhere would fix four countries and spoil the rest.
    """
    proj = msm.build_projection([22.0, 44.0, 41.0, 53.0], "auto")
    # Read off the WKT rather than round-tripping through a PROJ string,
    # which pyproj warns is lossy and is right to.
    assert "Lambert Conic Conformal" in proj.target_crs.to_wkt()


def test_the_locator_of_an_equatorial_plate_renders() -> None:
    """The path that actually broke, end to end.

    ``build_projection`` returning a transformer is necessary and not
    sufficient: the failure was reached through ``_inset_box``, which runs
    before any geometry is drawn and took the whole plate down with it.
    """
    cfg = {"region": {"bbox": [11.0, -5.0, 31.0, 5.0]}, "canvas_width": 700}
    vp = {"ts": 0.7, "width": 700.0, "height": 420.0}
    placed = msm._inset_box(cfg, vp)
    assert placed is not None, "an equatorial plate should still get a locator"
    x0, y0, x1, y1 = placed
    assert x1 > x0 and y1 > y0, f"the locator has no area: {placed}"
