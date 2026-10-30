"""Drawing a named disputed boundary without its sentence is a position taken.

The UNHCR Mapping Guidelines attach a *standard sentence* to three
boundaries -- Jammu and Kashmir, Sudan and South Sudan, Abyei. A plate
that draws one of those lines and says nothing has made a statement by
omission, and a package that leaves the sentence to the caller's memory
will make that statement on every plate of the region anybody renders.
The Himalaya plate shipped for weeks drawing the Line of Control in
dashes, with Srinagar labelled, and no sentence anywhere on it.

So the obligation moved into the generator, on the pattern already set by
``_attribution_layer``: the ODbL credit appears whenever an OpenStreetMap
layer would actually draw for the plate's bounding box, rather than
whenever the caller remembers it. Same rule, heavier duty.

Keyed on the extent and not on the labels, deliberately: a plate can draw
the Line of Control without printing the word Kashmir, and the obligation
is about the line.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

_KASHMIR = {"region": {"bbox": [70.0, 25.0, 100.0, 40.0]}}
_IBERIA = {"region": {"bbox": [-9.6, 35.9, 3.4, 43.9]}}
_SUDAN = {"region": {"bbox": [21.5, 8.0, 39.0, 23.0]}}


def test_a_plate_over_jammu_and_kashmir_carries_the_sentence() -> None:
    owed = msm._required_disclaimers(_KASHMIR)
    assert owed, "the plate draws the Line of Control and owes a sentence"
    assert "Jammu and Kashmir" in owed[0]


def test_a_plate_nowhere_near_one_carries_none() -> None:
    """The measure has to land on the right side for the plates known good.

    Iberia draws international boundaries and owes nothing. A rule that
    fired here would be noise, and noise is how a guard gets switched off.
    """
    assert msm._required_disclaimers(_IBERIA) == []


def test_sudan_owes_two_and_gets_both() -> None:
    """The south boundary and Abyei are separate obligations in the guidelines."""
    owed = msm._required_disclaimers(_SUDAN)
    assert len(owed) == 2, owed
    assert any("South Sudan" in line for line in owed)
    assert any("Abyei" in line for line in owed)


def test_a_plate_that_draws_no_boundaries_owes_nothing() -> None:
    """A relief plate makes no claim about where a line runs."""
    relief_only = {**_KASHMIR, "frontiers": {"show": False}}
    assert msm._required_disclaimers(relief_only) == []


def test_turning_the_caption_off_does_not_turn_the_disclaimer_off() -> None:
    """The one way a caller could have declined it by accident.

    The sentence rides in the provenance footer, and the footer is
    opt-in. A plate that said ``caption: none`` would therefore have
    dropped a required disclaimer while looking perfectly finished -- the
    quietest way to lose it. An owed sentence turns the footer on.
    """
    assert msm._caption_mode({**_KASHMIR, "caption": "none"}) == "full"
    assert msm._caption_mode({**_IBERIA, "caption": "none"}) == "none"
    assert msm._caption_lines({**_KASHMIR, "caption": "none"}), (
        "the footer came back empty on a plate that owes a sentence"
    )


def test_the_footer_counts_the_lines_it_will_print() -> None:
    """Height and content are computed in two places; they must agree.

    They each held their own copy of the list before the disclaimers
    existed. A footer reserving room for three lines and printing four
    writes the fourth over the map.
    """
    cfg = {
        **_KASHMIR,
        "caption": "full",
        "method": "schematic",
        "source": "Natural Earth",
    }
    lines = msm._caption_lines(cfg)
    assert len(lines) == 3, lines
    height = msm._caption_height(cfg, 1.0)
    assert height == len(lines) * 11.5 + 17.0
