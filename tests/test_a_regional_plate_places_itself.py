"""A regional plate carries a locator inset unless it says otherwise.

The defect this guards is not a bug, it is worse than one. The locator
inset was written, documented, tested and *opt-in*, and across every plate
this package ships it was used exactly zero times. The code existed; the
capability did not.

The UNHCR Mapping Guidelines make a locator a required element of a
regional plate, with a size in millimetres attached, and the reason is not
house style: a reader who does not already know where North Kivu is learns
nothing from a map of North Kivu. "Zoom out for perspective, zoom in for
detail" is the locator map's one rule, and a plate that only ever zooms in
is answering half of it.

So the default inverted. This file holds the invariant in place from both
sides -- that a plain regional config gets one, and that a caller who
declines still gets none.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

import re

import pytest
from _plates import plate  # noqa: E402

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

#: A region the size this generator is for: eleven degrees of Ukraine.
_REGIONAL = {"region": {"bbox": [29.0, 45.0, 41.0, 53.0]}}


def _inset_group(svg: str) -> str:
    """The locator's markup, or the empty string when it drew nothing."""
    match = re.search(r'<g id="inset"[^>]*>(.*?)</g>\s*(?:<g|<defs|$)', svg, re.S)
    return match.group(1) if match else ""


def test_a_plain_regional_config_gets_a_locator() -> None:
    """The default, and the whole point of the change."""
    assert msm._inset_settings(_REGIONAL) is not None


def test_declining_a_locator_still_works() -> None:
    """A default has to be refusable or it is a mandate."""
    declined = {**_REGIONAL, "inset": {"show": False}}
    assert msm._inset_settings(declined) is None


def test_a_plate_wide_enough_to_place_itself_gets_none() -> None:
    """A continent needs no small picture of the same continent.

    The cut-off is in longitude because that is the axis a conic plate
    actually grows along here, and because the widest shipped plate --
    western Europe, 41 degrees -- has to stay on the keeping side of it.
    """
    hemisphere = {"region": {"bbox": [-20.0, 10.0, 110.0, 60.0]}}
    assert msm._inset_settings(hemisphere) is None
    western_europe = {"region": {"bbox": [-11.0, 35.0, 30.0, 60.0]}}
    assert msm._inset_settings(western_europe) is not None


def test_a_panel_of_a_sheet_gets_none() -> None:
    """Nine identical locators tell a reader one thing nine times."""
    assert msm._inset_settings({**_REGIONAL, "_panel": True}) is None


@pytest.mark.parametrize(
    "legend_position,forbidden",
    [("top-right", "top-right"), ("bottom-right", "bottom-right")],
)
def test_the_locator_does_not_take_the_legend_s_corner(
    legend_position: str, forbidden: str
) -> None:
    """Two cards in one corner is one card and a mistake.

    The legend's position is resolved before the locator's, so the locator
    takes a corner the legend does not want -- and never the top-left,
    which is the title block's on every plate this generator draws.
    """
    cfg = {
        **_REGIONAL,
        "legend_position": legend_position,
        "areas_of_control": {"palette": {"A": "#888888"}},
    }
    corner = msm._inset_corner(cfg, 1.0, 1000.0)
    assert corner != forbidden
    assert corner != "top-left"


def test_the_locator_reaches_the_rendered_plate() -> None:
    """The settings being right is not the same as the ink being there.

    Everything above tests the decision. This tests the drawing, because a
    resolved option that no layer reads is the exact failure mode this file
    exists about.
    """
    svg = plate(
        {
            "title": "Locator smoke plate",
            "region": {"bbox": [29.0, 45.0, 41.0, 53.0]},
            "canvas_width": 700,
            "basemap": {"relief": False},
        }
    )
    drawn = _inset_group(svg)
    assert drawn, "the plate drew an empty inset group"
    assert "inset-clip" in drawn, "the locator has no clip, so it is not a card"
    assert msm._INSET_REGION_INK in drawn, (
        "the mapped area is not marked in the locator's accent, so the "
        "locator does not say which part of the context it is about"
    )
