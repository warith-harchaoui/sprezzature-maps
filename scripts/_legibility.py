"""
_legibility: can every word on this plate actually be read?

A map is mostly type. The generator places labels with real font metrics
and a collision policy, and that machinery works -- but it only governs
the layers that go through it. Everything else on a plate is positioned by
arithmetic somebody did once: the scale bar at ``26 * ts`` from the left,
the legend card at a corner, the break values under a colour strip, the
provenance footer at the foot. Each of those is correct on the plate it
was tuned on, and each has collided with something on a plate it was not.

Found by looking, three times in one session:

* the scale bar printing straight through the graded key's colour strip
  and its break values, on the first regional choropleth drawn here;
* the break values overprinting each other into ``11.4 636.1 901.2 1263``,
  one word, because six classes at a fixed swatch width leave a label
  forty units of room and need sixty;
* ``Washington, D.C.`` landing on ``Los Angeles`` on a world choropleth,
  and ``Rio de Janeiro`` on ``São Paulo``.

Looking is how all three were found and looking does not scale: there are
twenty-six shipped plates and a label moves whenever a bbox does. So the
eyeball becomes a measurement. This module reads a rendered SVG, rebuilds
each ``<text>`` element's ink rectangle from the same font metrics the
placer uses, and reports the pairs that touch, the ones that fall off the
plate, and the ones set below a legible size.

What it deliberately does not do
--------------------------------
Judge contrast against what is *behind* the text. That needs the raster,
not the markup, and the two labels on these plates that sit on a busy
ground -- a place name over a hillshade, a water name over the sea -- both
carry a halo already. A rule for it would fire on every one of them.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _textbox import boxes_overlap, text_box  # noqa: E402

_SVG_NS = "{http://www.w3.org/2000/svg}"

#: Pull the two numbers out of ``translate(12.5,-3)``. Only translate and
#: scale are followed: a rotated label's upright bounding box is wider
#: than its ink by up to its own length, so measuring one would report
#: collisions that are not there -- and every rotated label on these
#: plates is a river name, which is placed by the collision-aware layer
#: and is not what this module exists to catch.
_TRANSLATE_RE = re.compile(r"translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)")
_ROTATE_RE = re.compile(r"\brotate\(")

#: Classes whose subtree is not on the plate until a pointer puts it
#: there. The hover bubbles a choropleth carries are real ``<text>``
#: elements at real coordinates, held at ``opacity:0`` by the document's
#: own stylesheet and revealed one at a time on ``:hover``. Measured as
#: drawn, 173 of them overlap each other and everything else, and the
#: first run of this module reported 25 723 collisions, of which about
#: forty were real. A measurement that buries its own signal is not one.
_INTERACTIVE_CLASSES = frozenset({"tip", "hit", "controls", "plate-controls"})

#: Below this, in SVG user units at the plate's own scale, a label stops
#: being type and becomes texture. Eight is the smallest size any shipped
#: plate sets deliberately (the provenance footer, at ``8.2 * ts``), so
#: the floor is set just under it: a rule that fired on the house's own
#: smallest intentional size would be a rule about taste.
_MIN_READABLE = 7.0

#: How close two labels may come before they are touching. Zero would
#: report two words a hair apart as a collision; a point and a half is
#: the gap below which a reader has to work out where one word ends.
_TOUCH_PAD = 1.5


@dataclass(frozen=True)
class Label:
    """One drawn ``<text>``, resolved to the plate's own coordinates."""

    text: str
    box: tuple[float, float, float, float]
    size: float
    layer: str

    @property
    def where(self) -> str:
        return f"{self.text!r} ({self.layer}, {self.size:.1f}u)"


def _float(value: str | None, fallback: float) -> float:
    try:
        return float(str(value).strip().replace("px", ""))
    except (TypeError, ValueError):
        return fallback


def _flat_text(node: ET.Element) -> str:
    """Everything a ``<text>`` actually prints, tspans included."""
    return "".join(node.itertext()).strip()


def labels(svg: str) -> list[Label]:
    """Return every visible label on the plate, with its ink rectangle.

    Parameters
    ----------
    svg : str
        A rendered SVG document.

    Returns
    -------
    list of Label
        Hidden subtrees are skipped, and so is anything inside a rotated
        group -- see :data:`_ROTATE_RE` for why.

    Examples
    --------
    >>> found = labels(
    ...     '<svg xmlns="http://www.w3.org/2000/svg">'
    ...     '<g id="legend"><text x="10" y="20" font-size="12">Kyiv</text></g>'
    ...     "</svg>"
    ... )
    >>> [(lab.text, lab.layer, round(lab.size)) for lab in found]
    [('Kyiv', 'legend', 12)]
    """
    root = ET.fromstring(svg)
    out: list[Label] = []

    def walk(node: ET.Element, dx: float, dy: float, size: float, layer: str) -> None:
        style = (node.get("style") or "").replace(" ", "")
        if "display:none" in style or "opacity:0;" in f"{style};":
            return
        classes = set((node.get("class") or "").split())
        if classes & _INTERACTIVE_CLASSES:
            return
        transform = node.get("transform") or ""
        if _ROTATE_RE.search(transform):
            return
        shift = _TRANSLATE_RE.search(transform)
        if shift:
            dx += float(shift.group(1))
            dy += float(shift.group(2))
        size = _float(node.get("font-size"), size)
        layer = node.get("id") or layer
        if node.tag == f"{_SVG_NS}text":
            content = _flat_text(node)
            if content:
                x = _float(node.get("x"), 0.0) + dx
                y = _float(node.get("y"), 0.0) + dy
                out.append(
                    Label(
                        text=content,
                        box=text_box(
                            x,
                            y,
                            content,
                            size=size,
                            tracking=_float(node.get("letter-spacing"), 0.0),
                            anchor=node.get("text-anchor") or "start",
                        ),
                        size=size,
                        layer=layer,
                    )
                )
            return
        for child in node:
            walk(child, dx, dy, size, layer)

    walk(root, 0.0, 0.0, 16.0, "root")
    return out


def _canvas(svg: str) -> tuple[float, float]:
    """The plate's own width and height, from the root element."""
    root = ET.fromstring(svg)
    box = (root.get("viewBox") or "").split()
    if len(box) == 4:
        return float(box[2]), float(box[3])
    return _float(root.get("width"), 0.0), _float(root.get("height"), 0.0)


def unreadable(svg: str, *, pad: float = _TOUCH_PAD) -> list[str]:
    """Report every label a reader could not read, and why.

    Three questions, in the order they cost a reader:

    **Does it collide with another label?** Two words in the same paper
    are not two words. This is measured on the ink rectangles, with a
    point and a half of slack, and deliberately ignores a label wholly
    inside another's box in one axis only -- the strip-and-break layout
    is meant to interleave.

    **Does it fall off the plate?** A name half outside the frame is a
    different name: "Istanbul" clipped at the edge reads as "Ista".

    **Is it set below a readable size?**

    Parameters
    ----------
    svg : str
        A rendered SVG document.
    pad : float, optional
        How close two labels may come before they count as touching.

    Returns
    -------
    list of str
        One sentence per problem, empty when the plate reads.
    """
    found = labels(svg)
    width, height = _canvas(svg)
    problems: list[str] = []

    for label in found:
        if label.size < _MIN_READABLE:
            problems.append(
                f"{label.where} is set at {label.size:.1f} units, under the "
                f"{_MIN_READABLE:g} a reader can take"
            )
        x0, y0, x1, y1 = label.box
        if width and height and (x0 < -1.0 or y0 < -1.0 or x1 > width + 1.0 or y1 > height + 1.0):
            problems.append(
                f"{label.where} runs off the plate: its ink reaches "
                f"({x0:.0f}, {y0:.0f})-({x1:.0f}, {y1:.0f}) on a "
                f"{width:.0f}x{height:.0f} canvas"
            )

    for i, a in enumerate(found):
        for b in found[i + 1 :]:
            if a.box == b.box or _same_block(a, b):
                continue
            if boxes_overlap(a.box, b.box, pad=pad):
                problems.append(f"{a.where} collides with {b.where}")
    return problems


def _same_block(a: Label, b: Label) -> bool:
    """Whether two labels are consecutive lines of one set block.

    A paragraph's leading is a typographic decision, not a collision, and
    a rule that could not tell the two apart would report every wrapped
    sentence on every plate. The how-it-works figure sets its body at 13.5
    units with 0.73 of clear air between the ink of one line and the next
    -- tight, deliberate, and perfectly readable, because the eye reads
    *down* a block and *across* a map.

    The test is the one a typesetter would use: same left edge, same size,
    and no horizontal question to settle because neither line is beside
    the other. Two town names never satisfy it -- their left edges are
    their own dots' -- which is why "Mumbai" against "Kolkata" survives
    this and is still reported.

    Examples
    --------
    >>> line = lambda y, x=10.0: Label("x", (x, y, x + 50, y + 10), 12.0, "root")
    >>> _same_block(line(0.0), line(11.0))
    True
    >>> _same_block(line(0.0), line(11.0, x=40.0))
    False
    """
    if abs(a.size - b.size) > 0.01 or abs(a.box[0] - b.box[0]) > 0.5:
        return False
    # Stacked, not side by side: the boxes must not actually intersect in y.
    return min(a.box[3], b.box[3]) <= max(a.box[1], b.box[1])


def report(path: Path) -> list[str]:
    """Run :func:`unreadable` over one file, prefixed with its name."""
    return [f"{path.name}: {line}" for line in unreadable(path.read_text())]


def main(argv: list[str] | None = None) -> int:
    """Walk the paths given and print every label that cannot be read."""
    args = argv if argv is not None else sys.argv[1:]
    targets: list[Path] = []
    for raw in args or ["assets"]:
        here = Path(raw)
        targets.extend(sorted(here.rglob("*.svg")) if here.is_dir() else [here])
    lines: list[str] = []
    for target in targets:
        lines.extend(report(target))
    for line in lines:
        print(line)
    print(f"\n{len(lines)} unreadable label(s) over {len(targets)} plate(s)")
    return 1 if lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
