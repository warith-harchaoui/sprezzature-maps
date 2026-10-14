"""
A plate is designed in user units and printed in millimetres, and nothing joins them.

Journals do not ask for pixels. Nature wants 90 mm for a single column and
180 for a double; Elsevier publishes 90, 140 and 190; Science 57, 121 and 184.
All three also state a floor for the type inside the figure -- 5 to 7 pt at
Nature and Science, 6 as Elsevier's minimum with 8 the safer choice -- and all
three say the same thing about method: build the figure at the width it will
print at, rather than scaling it afterwards.

That advice is unfollowable here without a number, because a plate's type is
measured in the same arbitrary user units as its coastline. Measured: the
bundled Ukraine plate is 1,768 units wide and its smallest label is 10.8 of
them. Dropped into a 90 mm column that label sets at **1.6 pt** -- a third of
the floor any major publisher accepts -- and it renders without complaint,
because a vector file always does.

So ``print_width`` does two things. The root carries the physical width, so
the file lands at that size in a layout instead of at whatever a consumer
infers from its pixel dimensions. And the plate measures its own smallest
label against that width and says what it will actually be.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


msm = _load("make_situation_map")


def _builders() -> dict[str, Any]:
    return _load("build_situation_examples").BUILDERS


#: The column widths the three publishers this project's users submit to
#: actually specify, in millimetres.
COLUMNS_MM: dict[str, tuple[float, ...]] = {
    "Nature": (90.0, 180.0),
    "Elsevier": (90.0, 140.0, 190.0),
    "Science": (57.0, 121.0, 184.0),
}


def _plain_cfg(**extra: Any) -> dict[str, Any]:
    """A cheap plate: no relief, no thematic layers, nothing to measure twice."""
    return {
        "title": "Print size",
        "region": {"bbox": [5.7, 45.6, 10.7, 48.0]},
        "canvas_width": 600,
        "basemap": {"relief": False},
        **extra,
    }


# ── reading a physical length ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "mm"),
    [("90mm", 90.0), ("9cm", 90.0), ("18.4 cm", 184.0), ("1in", 25.4), ("72pt", 25.4),
     ("90MM", 90.0), (90, 90.0), (90.0, 90.0)],
)
def test_a_length_is_read_in_the_unit_it_is_written_in(raw: Any, mm: float) -> None:
    assert msm.parse_length_mm(raw) == pytest.approx(mm)


@pytest.mark.parametrize("raw", ["90px", "90", "wide", "", "90 metres"])
def test_a_length_with_no_unit_this_knows_is_refused(raw: str) -> None:
    """
    Guessing would be the wrong kind of helpful.

    ``"90"`` could be millimetres or pixels and the two differ by a factor of
    three; a figure that silently comes out at a third of its intended width
    is worse than one that refuses to build.
    """
    with pytest.raises(ValueError, match="use mm, cm, in or pt"):
        msm.parse_length_mm(raw)


# ── what the root says ──────────────────────────────────────────────────


def test_the_root_carries_the_physical_width() -> None:
    """A layout program reads this; a pixel count it would only guess from."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        root = ET.fromstring(msm.build_map(_plain_cfg(print_width="90mm")))
    assert root.get("width") == "90mm"
    assert root.get("height", "").endswith("mm")


def test_the_drawing_is_untouched_by_the_print_width() -> None:
    """
    Physical width is a statement about the paper, not about the map.

    If setting it moved a coastline or resized a label, "build at the printed
    size" would mean rebuilding the plate, which is the opposite of the point.
    """
    plain = msm.build_map(_plain_cfg())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        printed = msm.build_map(_plain_cfg(print_width="90mm"))
    assert ET.fromstring(plain).get("viewBox") == ET.fromstring(printed).get("viewBox")
    # Same drawing, byte for byte, once the root tag is set aside.
    assert plain[plain.index(">") :] == printed[printed.index(">") :]


def test_the_aspect_ratio_survives_the_conversion() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        root = ET.fromstring(msm.build_map(_plain_cfg(print_width="120mm")))
    vb = [float(v) for v in (root.get("viewBox") or "").split()]
    w = float((root.get("width") or "").removesuffix("mm"))
    h = float((root.get("height") or "").removesuffix("mm"))
    assert w / h == pytest.approx(vb[2] / vb[3], rel=1e-3)


def test_without_the_key_nothing_changes() -> None:
    """Every config written before this existed keeps its pixel dimensions."""
    root = ET.fromstring(msm.build_map(_plain_cfg()))
    assert not (root.get("width") or "").endswith("mm")
    assert re.fullmatch(r"[\d.]+", root.get("width") or "")


# ── the measurement ─────────────────────────────────────────────────────


def test_the_smallest_label_is_measured_not_estimated() -> None:
    """Read off the finished markup, like everything else that must be true."""
    svg = '<svg viewBox="0 0 1767.9 1000"><text font-size="22"/><text font-size="10.8"/></svg>'
    units, pt = msm.smallest_type_pt(svg, 90.0)
    assert units == 10.8
    assert pt == pytest.approx(10.8 / 1767.9 * 90.0 / 25.4 * 72.0)


@pytest.mark.parametrize("publisher", sorted(COLUMNS_MM))
def test_a_screen_plate_is_told_it_cannot_be_printed(publisher: str) -> None:
    """
    The defect this exists for, at every column width that matters.

    The bundled plates are designed for a screen. At a journal column their
    labels are between one and four points -- legible nowhere -- and the only
    thing that ever said so was arithmetic nobody did.
    """
    narrowest = min(COLUMNS_MM[publisher])
    cfg = _builders()["ukraine"]()
    cfg["print_width"] = f"{narrowest}mm"
    with pytest.warns(RuntimeWarning, match=r"smallest label is [\d.]+ pt"):
        msm.build_map(cfg)


def test_the_warning_names_the_canvas_width_that_would_fix_it() -> None:
    """
    A measurement nobody can act on is a measurement that changes nothing.

    "Your type is 1.6 pt" is a complaint. "Design this at canvas_width 551 and
    it prints at 5 pt" is the same fact with the next step attached.
    """
    cfg = _builders()["ukraine"]()
    cfg["print_width"] = "90mm"
    with pytest.warns(RuntimeWarning) as caught:
        msm.build_map(cfg)
    message = str(caught[0].message)
    assert "canvas_width around" in message
    wanted = float(re.search(r"canvas_width around (\d+)", message).group(1))
    # Re-derive it: at that canvas the same label really does reach the floor.
    units = float(re.search(r"label is\s+([\d.]+) units", message).group(1))
    assert units / wanted * 90.0 / 25.4 * 72.0 == pytest.approx(5.0, abs=0.05)


def test_a_plate_built_for_the_page_says_nothing() -> None:
    """
    The quiet case has to be quiet, or the warning is noise and gets ignored.

    600 units at 190 mm puts the smallest label comfortably over six points.
    """
    cfg = _plain_cfg(print_width="190mm")
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        msm.build_map(cfg)


def test_the_floors_are_the_published_ones() -> None:
    """
    Pinned, because they are facts about other people's house styles.

    Nature and Science: 5 pt minimum, 7 recommended. Elsevier: 6 minimum, 8
    safer. The absolute floor is therefore 5 and the common one 6.
    """
    assert msm._TYPE_FLOOR_PT == 5.0
    assert msm._TYPE_SAFE_PT == 6.0


def test_the_warning_is_a_warning_and_not_a_refusal() -> None:
    """A poster is not a journal page, and the caller may know that."""
    cfg = _builders()["ukraine"]()
    cfg["print_width"] = "90mm"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        svg = msm.build_map(cfg)
    assert svg.startswith("<svg")
    assert 'width="90mm"' in svg[: svg.index(">")]


def test_the_key_is_accepted_by_the_validator() -> None:
    """A key the validator rejects is a key no config can carry."""
    msm.validate_config(_plain_cfg(print_width="90mm"))
    assert "print_width" in msm.CONFIG_KEYS
