"""The four rules that only apply to a regional situation plate.

``audit`` asks whether a plate says enough about itself for a reader to
question it. The six rules it started with were written for a thematic
chart that happens to be a map. A situation plate gets read against a
different standard -- the UNHCR Mapping Guidelines for the furniture, the
Institute for the Study of War for the evidence model -- and those
questions are the ones a control map most often gets wrong.

Each rule is checked from both sides. A rule that only ever fires is a
rule somebody will switch off; a rule that never fires is decoration.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

from sprezzature_maps.audit import audit

#: What makes a plate *regional*: the clip that bounds its geography to a
#: region rather than to the world. Without it none of these rules apply,
#: which is what keeps them off the world choropleth.
_REGION_CLIP = '<clipPath id="region-clip"><path d="M 0,0"/></clipPath>'
_LOCATOR = '<g id="inset"><rect x="0" y="0"/></g>'
_CONTROL = '<g id="areas-of-control"><path d="M 0,0"/></g>'


def plate(*labels: str, extra: str = "") -> str:
    """A minimal regional plate carrying the given visible text."""
    texts = "".join(f"<text>{label}</text>" for label in labels)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t">'
        f'<title id="t">A plate</title>{_REGION_CLIP}{texts}{extra}</svg>'
    )


def rules(svg: str) -> set[str]:
    return {f.rule for f in audit(svg)}


# ── the locator ──────────────────────────────────────────────────────────


def test_a_regional_plate_with_no_locator_is_reported() -> None:
    assert "no-locator" in rules(plate("Eastern DRC, schematic"))


def test_a_regional_plate_with_a_locator_is_not() -> None:
    assert "no-locator" not in rules(plate("Eastern DRC, schematic", extra=_LOCATOR))


def test_an_empty_locator_group_counts_as_none() -> None:
    """Every layer is emitted whether or not it drew.

    So presence is not the question, and a rule that only looked for the
    tag would have passed all thirteen plates that carried an empty one.
    """
    assert "no-locator" in rules(plate("Eastern DRC, schematic", extra='<g id="inset"></g>'))


def test_a_world_plate_is_not_asked_for_a_locator() -> None:
    """A map of the world has nowhere to zoom out to.

    The measure landing on the right side for the case known good: the
    three shipped choropleths audit clean, and must keep doing so.
    """
    world = (
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t">'
        '<title id="t">World</title><text>Synthetic demo data</text></svg>'
    )
    assert rules(world) == set()


# ── the date ─────────────────────────────────────────────────────────────


def test_a_control_plate_with_no_as_of_is_reported() -> None:
    """Stricter than ``no-provenance``, and deliberately so.

    "Schematic" satisfies the general rule, because a schematic has no
    vintage to state. A front does: it is a claim about a moment, and
    the plate goes on making it for as long as the file exists.
    """
    undated = plate("Syria: areas of control", "Schematic", extra=_LOCATOR + _CONTROL)
    assert "no-provenance" not in rules(undated)
    assert "undated-control" in rules(undated)


def test_a_control_plate_that_says_as_of_when_is_not() -> None:
    dated = plate(
        "Syria: areas of control",
        "As of 25 September 2026 · schematic",
        extra=_LOCATOR + _CONTROL,
    )
    assert "undated-control" not in rules(dated)


def test_a_year_printed_somewhere_else_does_not_count() -> None:
    """The loose date rule accepts any year; this one must not.

    A source citation carrying a publication year would otherwise date a
    front line, which is the mistake in its purest form.
    """
    sourced = plate(
        "Syria: areas of control",
        "Natural Earth 1:50m, 2024 edition",
        extra=_LOCATOR + _CONTROL,
    )
    assert "undated-control" in rules(sourced)


# ── the evidence model ───────────────────────────────────────────────────


def test_a_flat_control_plate_is_reported() -> None:
    flat = plate(
        "Areas of control",
        "As of 2026 · government, occupied, contested",
        extra=_LOCATOR + _CONTROL,
    )
    assert "evidence-unclassed" in rules(flat)


def test_a_plate_that_separates_claimed_from_assessed_is_not() -> None:
    graded = plate(
        "Areas of control",
        "As of 2026",
        "Claimed, unverified",
        extra=_LOCATOR + _CONTROL,
    )
    assert "evidence-unclassed" not in rules(graded)


def test_a_plate_with_no_control_layer_is_not_asked() -> None:
    """A relief plate has no zones, so it cannot grade them."""
    relief = plate("Switzerland: relief and water", "A reference plate", extra=_LOCATOR)
    assert "evidence-unclassed" not in rules(relief)


# ── the named disclaimers ────────────────────────────────────────────────


def test_kashmir_without_its_sentence_is_reported() -> None:
    assert "disputed-unflagged" in rules(plate("SRINAGAR", "Kashmir", extra=_LOCATOR))


def test_kashmir_with_its_sentence_is_not() -> None:
    carried = plate(
        "SRINAGAR",
        "Boundaries shown in Jammu and Kashmir are approximate; the final "
        "status of the territory has not yet been agreed by the parties.",
        extra=_LOCATOR,
    )
    assert "disputed-unflagged" not in rules(carried)


def test_a_dispute_with_no_standard_sentence_is_left_alone() -> None:
    """Crimea is a real dispute and no linter's business.

    The table holds the three boundaries the guidelines name a sentence
    for. One that tried to be complete would be wrong in a hundred places
    and would fire on plates that owe nothing -- and a cartographer's
    judgement is not a lookup table's.
    """
    crimea = plate("SEVASTOPOL", "As of 2024 · schematic", extra=_LOCATOR + _CONTROL)
    assert "disputed-unflagged" not in rules(crimea)
