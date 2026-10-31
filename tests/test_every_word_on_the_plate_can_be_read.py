"""No label collides, runs off the plate, or is set too small to read.

A map is mostly type, and this repository already measures type carefully:
``_textbox`` carries per-character advances taken from the real faces, and
``_places`` drops a town name rather than nudge it somewhere it would lie.
That machinery governs the layers that go through it. Everything else on a
plate is positioned by arithmetic somebody did once — the scale bar at a
corner, the legend card at another, the break values under a colour strip,
the provenance footer at the foot — and each of those was correct on the
plate it was tuned on.

Found by looking, in one session:

* the scale bar printing through a graded key's colour strip and its break
  values, on the first regional choropleth drawn here;
* the break values overprinting into ``11.4 636.1 901.2 1263``, one word;
* ``Los Angeles`` and ``Washington, D.C.`` placed 1.2 units apart, their
  white halos fused into a grey smear across the United States — and the
  collision test passed, because it measured the *ink* and the halo is
  1.2 units wider than the ink on every side;
* the provenance footer running 38 units off the eastern-DRC plate, the
  last eleven words simply absent;
* ``Constanța``, ``Jerusalem``, ``Bouaké`` and ``CENTRAL AFRICAN REP.``
  each buried under the opaque band that footer paints.

Looking does not scale: twenty-six plates, and a label moves whenever a
bbox does. So the eyeball became a measurement, and this is where it runs.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sprezzature_maps import _load_script
from sprezzature_maps.audit import audit

legibility = _load_script("_legibility")

ROOT = Path(__file__).resolve().parents[1]


def _plate(*texts: str) -> str:
    """A bare SVG carrying the given ``<text>`` elements verbatim."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" '
        'role="img" aria-labelledby="t"><title id="t">t</title>'
        + "".join(texts)
        + "</svg>"
    )


# ── the measurement itself ───────────────────────────────────────────────


def test_two_labels_on_top_of_each_other_are_reported() -> None:
    found = legibility.unreadable(
        _plate(
            '<text x="20" y="40" font-size="12">Los Angeles</text>',
            '<text x="40" y="44" font-size="12">Washington</text>',
        )
    )
    assert any("collides" in line for line in found), found


def test_two_labels_with_room_between_them_are_not() -> None:
    """The measure has to land on the right side for the case known good."""
    assert (
        legibility.unreadable(
            _plate(
                '<text x="20" y="40" font-size="12">Los Angeles</text>',
                '<text x="20" y="90" font-size="12">Washington</text>',
            )
        )
        == []
    )


def test_consecutive_lines_of_one_block_are_not_a_collision() -> None:
    """A paragraph's leading is a typographic decision, not a defect.

    Without this the rule reports every wrapped sentence on every plate:
    the how-it-works figure sets its body with 0.73 units of clear air
    between one line's ink and the next, which is tight, deliberate, and
    perfectly readable — the eye reads *down* a block and *across* a map.
    """
    assert (
        legibility.unreadable(
            _plate(
                '<text x="20" y="40" font-size="13.5">first line of the note</text>',
                '<text x="20" y="54" font-size="13.5">second line of the note</text>',
            )
        )
        == []
    )


def test_a_label_running_off_the_plate_is_reported() -> None:
    """A name half outside the frame is a different name: "Ista"."""
    found = legibility.unreadable(
        _plate('<text x="330" y="40" font-size="14">Constantinople</text>')
    )
    assert any("runs off the plate" in line for line in found), found


def test_a_label_too_small_to_read_is_reported() -> None:
    found = legibility.unreadable(_plate('<text x="20" y="40" font-size="4">tiny</text>'))
    assert any("under the" in line for line in found), found


def test_a_hover_only_bubble_is_not_measured() -> None:
    """The choropleth's tooltips are real text at real coordinates.

    All 173 of them, held at ``opacity:0`` until a pointer arrives and
    revealed one at a time. Measured as drawn, they overlap each other
    and everything else: the first run of this check reported 25 723
    collisions, of which about forty were real. A measurement that buries
    its own signal is not one.
    """
    assert (
        legibility.unreadable(
            _plate(
                '<text x="20" y="40" font-size="12">Kyiv</text>',
                '<g class="tip"><text x="20" y="42" font-size="12">Kyiv: 4.6</text></g>',
            )
        )
        == []
    )


def test_a_rotated_label_is_left_alone() -> None:
    """Its upright bounding box is wider than its ink by its own length.

    Every rotated label on these plates is a river name, placed by the
    collision-aware layer. Measuring the box would report collisions that
    are not on the page.
    """
    assert (
        legibility.unreadable(
            _plate(
                '<text x="20" y="40" font-size="12">Kyiv</text>',
                '<g transform="rotate(31 20 40)">'
                '<text x="20" y="40" font-size="12">Dnieper</text></g>',
            )
        )
        == []
    )


# ── the plates ───────────────────────────────────────────────────────────


def _shipped() -> list[Path]:
    return sorted((ROOT / "assets").rglob("*.svg"))


@pytest.mark.parametrize("plate", _shipped(), ids=lambda p: p.stem)
def test_every_shipped_plate_reads(plate: Path) -> None:
    """The guard, over everything this repository draws."""
    problems = legibility.unreadable(plate.read_text(errors="replace"))
    assert not problems, f"{plate.name}:\n  " + "\n  ".join(problems)


def test_the_auditor_carries_the_rule() -> None:
    """Folded into ``audit`` rather than given a command of its own.

    The loop is render, audit, fix, render; a second command is a second
    thing to remember, and the defects this catches are exactly the ones
    nobody remembers to look for.
    """
    rules = {
        f.rule
        for f in audit(
            _plate(
                '<text x="20" y="40" font-size="12">Los Angeles</text>',
                '<text x="40" y="44" font-size="12">Washington</text>',
                "<text>Synthetic demo data</text>",
            )
        )
    }
    assert "text-unreadable" in rules
