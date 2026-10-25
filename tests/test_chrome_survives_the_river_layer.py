"""
Drawing rivers must not move the legend or the fullscreen control.

``build_svg`` takes ``width`` as the canvas width — 745 by default — and the
river layer bound the same name to its stroke width, 1.6 px for a trunk down
to 0.8 px for a tributary. Everything the function read out of ``width``
afterwards got the stroke instead of the canvas: the classed legend places
its "No data" swatch at ``width - side_margin - 92``, which came out at
x=-111.2, off the left edge of a 745 px plate, and ``fullscreen_control``
was positioned against 0.8 as well.

Rivers are drawn by default, so this was the default classed output, not a
corner. It survived because nothing downstream crashes: the SVG is valid,
the swatch is simply somewhere nobody looks. The type gate found it — the
rebinding changed ``width`` from int to float, which is what mypy reported —
and this test is the part of that catch the suite can hold on its own.

The two assertions pin the shape of the bug rather than the pixel: the
chrome a river layer must not touch is the chrome the plate draws from its
own width, and it has to land in the same place either way.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re

from sprezzature_maps import _load_script

mc = _load_script("make_choropleth")

#: The classed legend is the branch that reads ``width`` after the river
#: layer has run; the unclassed one lays its legend out from the left.
_CLASSED = {"classes": 5, "method": "quantile"}


def _no_data_swatch_x(svg: str) -> list[str]:
    """Return the x of every legend swatch filled with the no-data grey."""
    return re.findall(
        rf'<rect x="(-?[\d.]+)"[^>]*fill="{re.escape(mc.NO_DATA)}"', svg
    )


def test_the_no_data_swatch_lands_in_the_same_place_with_and_without_rivers() -> None:
    """
    The legend is laid out from the canvas width, which rivers must not touch.

    Measured rather than asserted against a constant: the point is that the
    two renders agree, not that the swatch sits at any particular x.
    """
    without = _no_data_swatch_x(mc.build_svg(rivers=False, **_CLASSED))
    with_rivers = _no_data_swatch_x(mc.build_svg(rivers=True, **_CLASSED))

    assert without, "the classed legend should draw a no-data swatch"
    assert with_rivers == without, (
        f"the river layer moved the no-data swatch from {without} to "
        f"{with_rivers}: something downstream is reading a stroke width as "
        f"the canvas width."
    )


def test_the_swatch_stays_on_the_plate() -> None:
    """
    A negative x is the signature of the bug, and is worth naming directly.

    If the swatch is ever laid out from a stroke width again it lands far
    left of zero, so the sign alone catches it even if the comparison above
    is weakened by both renders breaking the same way.
    """
    (x,) = _no_data_swatch_x(mc.build_svg(rivers=True, **_CLASSED))
    assert float(x) > 0, f"the no-data swatch is off the left edge at x={x}"
