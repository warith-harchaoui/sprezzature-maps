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
asserts the three properties a page has to have:

* **no two names share paper**,
* **every name is on the plate**, and
* **every name that points at ground is on the drawn map**.

The third is the second done properly. The plate is a rectangle; under a
conic the map drawn on it is a trapezoid, narrower at top and bottom, and
the paper between the two belongs to the margin. A name out there has not
fallen off the page -- it passes the plate test -- it has merely stopped
being on the map, which is the only thing a place name is for. Nine names
on five plates shipped like that: ``EL GENEINA`` and ``MEDITERRANEAN SEA``
opened out on the margin, ``LISBON`` and ``ATLANTIC OCEAN`` each lost
letters to it on two plates apiece, ``LUHANSK`` ran off the eastern edge,
``BLACK SEA`` laid its baseline along the neat line, and ``Danube`` -- in
a layer the region clip actually cuts -- had its last letter sliced off.

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

from _plates import plate  # noqa: E402
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


#: Layers whose text is *about* the plate rather than on the map: the title
#: band, the caption, the legend, the scale bar, the north arrow, the source
#: line, the reader's control panel. The generator draws these outside the
#: region clip on purpose -- they are annotations entitled to the margin.
#:
#: Named as a denylist, not an allowlist of map layers, and the direction
#: matters: the recurring failure in this repository is a rule that covered
#: everything except the one thing nobody thought of -- a config key no
#: layer read, a label layer no collision test compared. A new layer that
#: puts a name on the ground is covered here by saying nothing at all.
_FURNITURE = frozenset(
    {
        "annotation-furniture",
        "attribution",
        "caption",
        "legend",
        "north-arrow",
        "plate-controls",
        "scale-bar",
    }
)


def _drawn_map(svg: str) -> Any:
    """Return the region clip -- the ground the plate actually draws -- in root coordinates.

    Read back out of the markup rather than recomputed from the config, for
    the reason the rest of this file exists: what the generator meant to
    clip to and what it wrote into ``<defs>`` are two different claims, and
    only the second one reaches a reader. The path is in the user space of
    whatever references it, so it is carried through that element's own
    transform chain to meet the text boxes in the same coordinates.
    """
    from shapely.affinity import affine_transform
    from shapely.geometry import Polygon

    root = ET.fromstring(svg)
    path = None
    for clip in root.iter(f"{SVG}clipPath"):
        if clip.get("id") == "region-clip":
            path = list(clip)[0].get("d")
    if path is None:
        return None
    nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", path)]
    poly = Polygon(list(zip(nums[0::2], nums[1::2], strict=True)))

    users: list[tuple[float, ...]] = []

    def walk(el: ET.Element, ctm: tuple[float, ...]) -> None:
        if el.get("transform"):
            ctm = _compose(ctm, _transform(el.get("transform", "")))
        if "region-clip" in (el.get("clip-path") or ""):
            users.append(ctm)
        for child in el:
            walk(child, ctm)

    walk(root, _IDENTITY)
    if not users:
        return None
    a, b, c, d, e, f = users[0]
    # shapely wants (a, b, d, e, xoff, yoff) for [x' = a x + b y + xoff],
    # which is SVG's (a, c, b, d, e, f) read in a different order.
    return affine_transform(poly, [a, c, b, d, e, f])


#: The identity, in SVG's ``(a, b, c, d, e, f)`` order: ``x' = a x + c y +
#: e``, ``y' = b x + d y + f``.
_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose(m: tuple[float, ...], n: tuple[float, ...]) -> tuple[float, ...]:
    """Return ``m`` with ``n`` applied inside it, the way SVG nests them."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
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


def _measure(el: ET.Element, ctm: tuple[float, ...], layer: str, body: str) -> dict[str, Any]:
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


def _as_poly(b: tuple[float, ...]) -> Any:
    """The ink rectangle as a polygon, for the containment tests."""
    from shapely.geometry import box as _box

    return _box(*b)


def _area(b: tuple[float, ...]) -> float:
    """The ink rectangle's area."""
    return (b[2] - b[0]) * (b[3] - b[1])


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
    svg = plate(_builders()[name]())
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
    svg = plate(_builders()[name]())
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


@pytest.mark.parametrize("name", sorted(_builders()))
def test_every_name_that_points_at_ground_is_on_the_drawn_map(name: str) -> None:
    """
    A name in the margin names nothing, whether or not the clip cuts it.

    The test above asks whether a label is on the plate. That is the wrong
    rectangle and it said yes to nine names on five plates that a reader
    sees broken: under a conic the drawn map is a trapezoid, so there is
    paper inside the plate the map does not cover. What happens out there
    depends only on which layer wrote the name -- the geographic stack is
    clipped, so ``Danube`` simply lost its last letter; the hand-placed
    layer is not, so ``EL GENEINA`` opened on the margin instead. Both are
    the same defect and neither was visible to a rectangle.

    Furniture is exempt by name, not by position: the title, caption,
    legend, scale bar, north arrow, source line and control panel are drawn
    outside the clip deliberately.
    """
    svg = plate(_builders()[name]())
    drawn = _drawn_map(svg)
    assert drawn is not None, f"{name}: no region clip in the markup"
    strays = [
        (r, drawn.intersection(_as_poly(r["box"])).area / max(_area(r["box"]), 1e-9))
        for r in _text_boxes(svg)
        if r["layer"] not in _FURNITURE and not drawn.contains(_as_poly(r["box"]))
    ]
    assert not strays, "\n".join(
        f"{name}: [{r['layer']}] {r['text']!r} is {frac:.0%} on the drawn map, "
        f"inking ({r['box'][0]:.0f}, {r['box'][1]:.0f})-({r['box'][2]:.0f}, {r['box'][3]:.0f})"
        for r, frac in strays
    )


def test_the_drawn_map_is_read_back_from_the_markup() -> None:
    """
    The clip the test measures is the clip the file carries, transforms and all.

    Without this, a plate whose region clip went missing -- or whose whole
    map group stopped being translated -- would make the test above pass by
    having nothing to fail against.
    """
    svg = plate(_builders()["ukraine"]())
    drawn = _drawn_map(svg)
    root = ET.fromstring(svg)
    width, height = _number(root.get("width")), _number(root.get("height"))
    assert drawn.area > 0.3 * width * height, "the drawn map is implausibly small"
    # The plate's own frame margin moves it off the origin: a clip read
    # without the ancestor transform would start at (0, 0).
    assert drawn.bounds[0] > 0.5 and drawn.bounds[1] > 0.5


def test_a_name_in_the_margin_is_caught() -> None:
    """The measurement fails on a label it is handed in the margin, not just in principle."""
    cfg = _builders()["ukraine"]()
    drawn = _drawn_map(plate(cfg))
    west, south, east, north = drawn.bounds
    assert not drawn.contains(_as_poly((west - 40.0, south + 10.0, west - 5.0, south + 24.0)))
    mid_x, mid_y = (west + east) / 2, (south + north) / 2
    assert drawn.contains(_as_poly((mid_x - 20, mid_y, mid_x + 20, mid_y + 12)))


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
        plate(cfg)


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
