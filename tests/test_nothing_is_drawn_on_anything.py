"""
Where the ink lands: no name over another name, and nothing off the plate.

Every placement defect this repository has fixed was found the same way --
somebody rendered a plate and looked at it. That worked, in the sense that
the defects were found; it failed in the sense that it only ever found the
plate that was looked at, and only the defect that was looked for. The
control panel on the legend took a reader with a browser. The subtitle
printed across the map survived every plate the generator ever drew. The
suite counted elements and never once asked where they were.

So this file asks where. It re-reads the finished SVG -- not the generator's
intentions, the actual markup -- walks it, composes the ancestor transforms
by hand, measures every visible run of text against real font metrics, and
asserts the two properties a page has to have:

* **no two names share paper**, and
* **every name is on the plate**.

Three things make the measurement honest rather than decorative:

``getBBox()`` would have lied.
    A teammate's note on the panel-over-legend defect is explicit about it:
    the DOM's ``getBBox`` ignores the transforms of an element's ancestors,
    so it reports where a label would be if nothing had moved it. Only
    ``getBoundingClientRect`` tells the truth in a browser. There is no
    browser here, so :func:`_text_boxes` composes the transform chain
    itself, which is the same arithmetic done where it can be checked.

The tooltips are not on the page.
    Each marker carries a ``<g class="tip">`` sibling that the plate's own
    stylesheet holds at ``opacity: 0`` until hover or focus. Measured
    naively they are the overwhelming majority of every "collision" on
    every plate -- 42 of the 43 found on the Ukraine plate -- and all of
    them are false. A measurement that is wrong 98% of the time is not a
    gate, it is noise with a threshold.

A flat glyph width would have missed the defects it was meant to catch.
    See :mod:`_textbox`: the generators' old ``0.55`` em per character
    under-measures an upper-case name by about a fifth, which is most of
    the reason the overlaps existed in the first place.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps import _load_script

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from _textbox import boxes_overlap, text_box  # noqa: E402

msm = _load_script("make_situation_map")

SVG = "{http://www.w3.org/2000/svg}"

#: Elements whose content is never painted on the page.
_UNPAINTED = frozenset(
    f"{SVG}{tag}"
    for tag in ("defs", "clipPath", "mask", "symbol", "title", "desc", "style", "script")
)

#: How much two text boxes may share before it counts as a collision, as a
#: fraction of the smaller box's area. Not zero: two names can touch by a
#: corner of their boxes while their ink is nowhere near, because a box is a
#: rectangle and a word is not. One twentieth is well under the smallest
#: real defect this found (``Seine`` over ``PARIS``, at a fourteenth) and
#: well over the largest touch that turned out to be nothing.
_TOLERATED_OVERLAP = 0.05


def _builders() -> dict[str, Any]:
    """The bundled plate builders, by name."""
    return _load_script("build_situation_examples").BUILDERS


#: The identity, in SVG's ``(a, b, c, d, e, f)`` order: ``x' = a x + c y +
#: e``, ``y' = b x + d y + f``.
_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose(m: tuple[float, ...], n: tuple[float, ...]) -> tuple[float, ...]:
    """Return ``m`` with ``n`` applied inside it, the way SVG nests them."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2, b * a2 + d * b2,
        a * c2 + c * d2, b * c2 + d * d2,
        a * e2 + c * f2 + e, b * e2 + d * f2 + f,
    )


def _transform(value: str) -> tuple[float, ...]:
    """Return the matrix for one ``transform`` attribute.

    Translate, scale, rotate and matrix, in the order they are written.
    Anything else raises rather than being skipped: a transform this cannot
    read is a label it cannot place, and a gate that quietly stops
    measuring reads exactly like a gate that found nothing.
    """
    out = _IDENTITY
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", value):
        nums = [float(n) for n in re.findall(r"[-+]?[\d.]+(?:[eE][-+]?\d+)?", args)]
        if name == "translate":
            out = _compose(out, (1, 0, 0, 1, nums[0], nums[1] if len(nums) > 1 else 0.0))
        elif name == "scale":
            out = _compose(out, (nums[0], 0, 0, nums[1] if len(nums) > 1 else nums[0], 0, 0))
        elif name == "rotate":
            rad = math.radians(nums[0])
            cos, sin = math.cos(rad), math.sin(rad)
            cx, cy = (nums[1], nums[2]) if len(nums) > 2 else (0.0, 0.0)
            out = _compose(out, (1, 0, 0, 1, cx, cy))
            out = _compose(out, (cos, sin, -sin, cos, 0, 0))
            out = _compose(out, (1, 0, 0, 1, -cx, -cy))
        elif name == "matrix":
            out = _compose(out, tuple(nums))
        else:
            raise AssertionError(f"unhandled transform in the plate: {value!r}")
    return out


def _number(raw: str | None, default: float = 0.0) -> float:
    """Read a leading number off an SVG attribute, units and all."""
    if raw is None:
        return default
    hit = re.match(r"\s*(-?[\d.]+)", raw)
    return float(hit.group(1)) if hit else default


def _text_boxes(svg: str) -> list[dict[str, Any]]:
    """Return one record per visible run of text in ``svg``.

    Each record carries the owning layer's ``id``, the string, and the box
    the run inks in the root coordinate system.
    """
    out: list[dict[str, Any]] = []

    def walk(el: ET.Element, ctm: tuple[float, ...], layer: str) -> None:
        if el.tag in _UNPAINTED or _is_hidden(el):
            return
        if el.get("transform"):
            ctm = _compose(ctm, _transform(el.get("transform", "")))
        if el.tag == f"{SVG}g" and el.get("id"):
            layer = el.get("id", layer)
        if el.tag == f"{SVG}text":
            body = "".join(el.itertext()).strip()
            if body:
                out.append(_measure(el, ctm, layer, body))
            return
        for child in el:
            walk(child, ctm, layer)

    walk(ET.fromstring(svg), _IDENTITY, "root")
    return out


def _is_hidden(el: ET.Element) -> bool:
    """Whether this element is kept off the page for a reader who has it open.

    Note what is *not* here: ``style="display:none"``. The plate's control
    panel ships that way and the plate's own script turns it on, so a
    rasteriser never draws it and a reader with scripting on always sees
    it. Treating it as absent is exactly the blind spot that let "Blue
    Nile" come to rest under the word "Terrain" on the Sudan plate, which
    is how this measurement found it.
    """
    if el.get("display") == "none" or el.get("visibility") == "hidden":
        return True
    # The hover tooltips. They are the plate's accessibility and interaction
    # story, and they are invisible until a pointer or a focus ring reaches
    # them; measuring them would make every marker a collision.
    return "tip" in (el.get("class") or "").split()


def _measure(
    el: ET.Element, ctm: tuple[float, ...], layer: str, body: str
) -> dict[str, Any]:
    """Measure one ``<text>`` element into a record.

    A rotated run becomes the upright box that contains it -- the same
    answer the generator's own ``_rotated_box`` gives, arrived at from the
    markup rather than from the config.
    """
    a, b, c, d, e, f = ctm
    box = text_box(
        _number(el.get("x")),
        _number(el.get("y")),
        body,
        size=_number(el.get("font-size"), 16.0),
        tracking=_number(el.get("letter-spacing")),
        anchor=el.get("text-anchor", "start"),
    )
    corners = [
        (a * px + c * py + e, b * px + d * py + f)
        for px, py in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))
    ]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return {"layer": layer, "text": body, "box": (min(xs), min(ys), max(xs), max(ys))}


def _shared_area(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Return the overlap of two boxes as a fraction of the smaller one."""
    if not boxes_overlap(a, b):
        return 0.0
    shared = (min(a[2], b[2]) - max(a[0], b[0])) * (min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return shared / smaller if smaller > 0 else 1.0


@pytest.mark.parametrize("name", sorted(_builders()))
def test_no_two_names_share_the_same_paper(name: str) -> None:
    """
    Two labels in the same place are not two labels. They are a smudge.

    Every layer used to dodge only the labels it had drawn itself, so a
    river name and a town name -- written by two different layers that had
    never been introduced -- landed on each other freely. Measured on the
    nine plates as shipped, that happened eight times: ``Sutlej`` inside
    ``Jullundur`` and ``Yamuna`` inside ``Agra`` on the Himalaya plate,
    ``Blue Nile`` inside ``AD-DAMAZIN`` on the Sudan one, ``Zuwara``
    inside ``TRIPOLI`` on Libya, and so on. Not one of them was visible to
    a test that counted elements.
    """
    svg = msm.build_map(_builders()[name]())
    runs = _text_boxes(svg)
    assert len(runs) > 10, f"{name}: only {len(runs)} labels — is the plate drawing at all?"

    clashes = [
        (a, b, frac)
        for i, a in enumerate(runs)
        for b in runs[i + 1 :]
        if (frac := _shared_area(a["box"], b["box"])) > _TOLERATED_OVERLAP
    ]
    assert not clashes, "\n".join(
        f"{name}: [{a['layer']}] {a['text']!r} and [{b['layer']}] {b['text']!r} "
        f"share {frac * 100:.0f}% of the smaller one's box"
        for a, b, frac in clashes
    )


@pytest.mark.parametrize("name", sorted(_builders()))
def test_every_name_is_on_the_plate(name: str) -> None:
    """
    A label drawn past the edge is not a label, and nothing used to say so.

    ``Kalemie`` sat 1.2 degrees south of the eastern-DRC region, ``Kolkata``
    1.9 degrees south of the Himalaya one, and ``Black Sea`` -- 19 units of
    tracked capitals, the Ukraine plate's largest orientation cue -- 0.9
    degrees south of its region. All three were written by hand into a
    config, accepted by the validator, and drawn into the margin where no
    reader could ever find them. The generator now refuses the config; this
    checks the other direction, that nothing else walks off the page.
    """
    svg = msm.build_map(_builders()[name]())
    root = ET.fromstring(svg)
    width, height = _number(root.get("width")), _number(root.get("height"))
    strays = [
        r
        for r in _text_boxes(svg)
        if r["box"][0] < -0.5
        or r["box"][1] < -0.5
        or r["box"][2] > width + 0.5
        or r["box"][3] > height + 0.5
    ]
    assert not strays, "\n".join(
        f"{name}: [{r['layer']}] {r['text']!r} inks "
        f"({r['box'][0]:.0f}, {r['box'][1]:.0f})-({r['box'][2]:.0f}, {r['box'][3]:.0f}) "
        f"on a {width:.0f} by {height:.0f} plate"
        for r in strays
    )


def test_a_hand_placed_label_outside_the_region_is_refused() -> None:
    """
    The author gets an error, not a silent deletion.

    This is the same rule the water names already follow -- a name that
    matches nothing in the dataset is refused rather than ignored -- applied
    to a name that matches nothing on the *page*. The alternative is what
    shipped for months: four invisible labels and a reader wondering why
    the generator had ignored them.
    """
    cfg = {
        "title": "Off the edge",
        "region": {"bbox": [5.0, 45.0, 11.0, 48.0]},
        "canvas_width": 600,
        "basemap": {"relief": False},
        "labels": {"places": [{"lon": 8.0, "lat": 40.0, "text": "Far South"}]},
    }
    msm.validate_config(cfg)
    with pytest.raises(ValueError, match="outside the"):
        msm.build_map(cfg)


def test_the_measurement_can_see_a_collision_it_is_given() -> None:
    """
    The gate above is only worth having if it fails on a real overlap.

    Two names at the same point, in markup shaped exactly like the
    generator's own. Verified in the negative, the way the panel-over-
    legend guard was: a property test that has never been watched to fail
    is a property test that might be measuring nothing.
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
        '<g id="rivers"><text x="40" y="50" font-size="12">Sutlej</text></g>'
        '<g id="cities"><text x="40" y="50" font-size="12">Jullundur</text></g>'
        "</svg>"
    )
    runs = _text_boxes(svg)
    assert len(runs) == 2
    assert _shared_area(runs[0]["box"], runs[1]["box"]) > _TOLERATED_OVERLAP


def test_an_ancestor_transform_moves_the_box() -> None:
    """
    The composed transform is the whole reason this file measures by hand.

    ``getBBox()`` would report the same box for both of these; they are 120
    units apart on the page.
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">'
        '<g id="a"><text x="10" y="50" font-size="12">Here</text></g>'
        '<g id="b" transform="translate(120,0)">'
        '<text x="10" y="50" font-size="12">Here</text></g>'
        "</svg>"
    )
    a, b = _text_boxes(svg)
    assert b["box"][0] - a["box"][0] == pytest.approx(120.0)
    assert _shared_area(a["box"], b["box"]) == 0.0
