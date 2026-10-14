"""
Every focusable thing on a plate says what it is, and the root does not hide it.

A situation plate puts ``tabindex="0"`` on its claim polygons, its marks and
its legend controls, which is right: the claim is the content, and a keyboard
user should be able to walk it. The version of this that shipped did half of
that. Measured across the five bundled thematic plates: **85 focusable
elements, 55 of them with no accessible name**. A screen-reader user tabbing
through the Sudan plate met fourteen stops that announced nothing.

The root made it worse rather than better. It carried ``role="img"``, which is
correct for a plate that is one picture and is what the other two generators
emit -- but ``img`` is a role whose children are *presentational*: the whole
subtree is dropped from the accessibility tree. Focusable descendants of a
presentational subtree can be navigated to and are not voiced, which is a
named defect with its own checkpoint in accessibility tooling. The two
mistakes compounded: unnamed stops, inside a container that had told the
screen reader there was nothing in there to name.

This file is the gate on both halves. It is written against the rendered
markup rather than the generator's intentions, for the same reason
``test_nothing_is_drawn_on_anything.py`` is: what a function meant to emit and
what reached the file are two different claims.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SVG = "{http://www.w3.org/2000/svg}"


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


#: Roles whose children ARIA treats as presentational, so a focusable
#: descendant of one is reachable and silent.
#:
#: ``img`` is the one this generator used to emit on every plate. The rest are
#: here so that "fixing" this by swapping in another leaf role fails loudly
#: rather than reintroducing the same defect under a different name.
PRESENTATIONAL_PARENTS = frozenset({"img", "button", "checkbox", "math", "progressbar",
                                    "scrollbar", "separator", "slider", "switch", "tab"})


def _focusables(svg: str) -> list[dict[str, str]]:
    """Return one record per element the keyboard can reach."""
    out: list[dict[str, str]] = []
    for el in ET.fromstring(svg).iter():
        if el.get("tabindex") is None:
            continue
        out.append(
            {
                "tag": el.tag.replace(SVG, ""),
                "role": el.get("role") or "",
                "label": (el.get("aria-label") or "").strip(),
                "labelledby": el.get("aria-labelledby") or "",
                "category": el.get("data-category") or el.get("data-legend-category") or "",
            }
        )
    return out


def _root_role(svg: str) -> str:
    return ET.fromstring(svg).get("role") or ""


THEMATIC = sorted(n for n in _builders() if n in
                  {"ukraine", "syria", "libya", "sudan", "drc"})
REFERENCE = sorted(n for n in _builders() if n not in set(THEMATIC))


@pytest.mark.parametrize("name", sorted(_builders()))
def test_no_focusable_element_is_silent(name: str) -> None:
    """
    The defect itself: a tab stop that announces nothing.

    Not a style point. A keyboard user has no way to skip a stop they cannot
    identify, so an unnamed one is worse than an unreachable one -- it costs
    them a keystroke and gives them nothing back.
    """
    svg = msm.build_map(_builders()[name]())
    silent = [f for f in _focusables(svg) if not (f["label"] or f["labelledby"])]
    assert not silent, (
        f"{name}: {len(silent)} focusable element(s) with no accessible name: "
        + ", ".join(f"<{f['tag']} role={f['role'] or 'none'}>" for f in silent[:6])
    )


@pytest.mark.parametrize("name", THEMATIC)
def test_a_plate_with_reachable_content_does_not_hide_it(name: str) -> None:
    """
    ``role="img"`` makes every descendant presentational, focusable ones included.

    So the root role has to follow what the plate holds. This is the half that
    no amount of labelling fixes: a perfectly named polygon inside a
    ``role="img"`` is still a polygon the screen reader has been told to
    ignore.
    """
    svg = msm.build_map(_builders()[name]())
    assert _focusables(svg), f"{name} is in the thematic list but has nothing to reach"
    role = _root_role(svg)
    assert role not in PRESENTATIONAL_PARENTS, (
        f"{name}: the root is role={role!r}, which drops its children from the "
        f"accessibility tree, and the plate has {len(_focusables(svg))} focusable ones"
    )
    assert role == "graphics-document", f"{name}: unexpected root role {role!r}"


@pytest.mark.parametrize("name", REFERENCE)
def test_a_plate_that_is_only_a_picture_says_so(name: str) -> None:
    """
    The other direction, which matters just as much.

    A basemap with no claims on it *is* one image, and announcing it as a
    document invites a reader to go looking through it for content that is not
    there.
    """
    svg = msm.build_map(_builders()[name]())
    assert not _focusables(svg), f"{name} has focusable content and should be a document"
    assert _root_role(svg) == "img"


@pytest.mark.parametrize("name", THEMATIC)
def test_the_root_is_still_labelled(name: str) -> None:
    """Changing the role must not have cost the title and description."""
    root = ET.fromstring(msm.build_map(_builders()[name]()))
    assert root.get("aria-labelledby") == "sm-title sm-desc"
    ids = {el.get("id") for el in root.iter() if el.tag in (f"{SVG}title", f"{SVG}desc")}
    assert {"sm-title", "sm-desc"} <= ids


@pytest.mark.parametrize("name", THEMATIC)
def test_a_claim_names_the_claim(name: str) -> None:
    """
    A zone's name carries what its own ``data-*`` attributes carry.

    The point of naming the zone is not that it has *a* name: it is that a
    reader who cannot see the fill learns whose ground it is and how much of
    the plate it covers, which is the entire content of the layer.
    """
    svg = msm.build_map(_builders()[name]())
    zones = [f for f in _focusables(svg) if f["role"] == "graphics-symbol" and f["category"]]
    assert zones, f"{name}: no named control zone found"
    for z in zones:
        assert z["category"] in z["label"], (
            f"{name}: a zone of category {z['category']!r} is announced as {z['label']!r}"
        )
        assert re.search(r"(\d+%|under 1%) of the mapped area", z["label"]), (
            f"{name}: {z['label']!r} does not say how much ground it is"
        )


@pytest.mark.parametrize("name", THEMATIC)
def test_a_mark_announces_its_precision(name: str) -> None:
    """
    The precision code is the one thing the non-visual reader cannot infer.

    A sighted reader sees a solid disc or a broken ring. Without it in the
    label, a screen-reader user is handed the confident reading of every
    approximate mark on the plate -- the exact failure the marker symbology
    exists to prevent, reintroduced for the readers least able to catch it.
    """
    svg = msm.build_map(_builders()[name]())
    marks = [
        f
        for f in _focusables(svg)
        if f["role"] == "graphics-symbol" and not f["category"]
    ]
    assert marks, f"{name}: no named marker found"
    wordings = set(msm._GEO_PRECISION.values())
    for m in marks:
        assert any(w in m["label"] for w in wordings), (
            f"{name}: {m['label']!r} does not say how well its position is known"
        )


@pytest.mark.parametrize("name", THEMATIC)
def test_the_description_says_there_is_something_to_reach(name: str) -> None:
    """
    A reachable plate is no use to a reader who never learns it is reachable.

    The count is not decoration: it is the difference between tabbing on
    purpose and tabbing into a surprise.
    """
    _, desc = msm.accessible_text(_builders()[name]())
    assert "can be reached with the Tab key" in desc
    assert re.search(r"\d+ mapped features can be reached", desc)


def test_a_legend_control_names_what_pressing_it_does() -> None:
    """``role="button"`` on a <g> does not take its name from the text inside it."""
    svg = msm.build_map(_builders()["ukraine"]())
    buttons = [f for f in _focusables(svg) if f["role"] == "button"]
    assert buttons, "the Ukraine plate draws an interactive legend"
    for b in buttons:
        assert b["label"].startswith("Show only "), b["label"]
        assert b["category"] and b["category"] in b["label"]


def test_the_measurement_would_notice_a_regression() -> None:
    """
    Verified in the negative: a silent stop is detected, not assumed absent.

    Without this, a parse that quietly matched nothing would make every test
    above pass on a plate full of silent stops.
    """
    svg = msm.build_map(_builders()["ukraine"]())
    assert len(_focusables(svg)) > 10, "the parse found suspiciously little to check"
    broken = svg.replace(' aria-label="Ukrainian government control', ' data-x="', 1)
    silent = [f for f in _focusables(broken) if not (f["label"] or f["labelledby"])]
    assert silent, "removing a label did not produce a silent stop; the check is blind"
