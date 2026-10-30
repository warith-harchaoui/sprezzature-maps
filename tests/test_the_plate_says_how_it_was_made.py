"""
The audit half: does a plate say enough for a reader to question it?

`sprezzature-figures`' auditor reads a rendered SVG as a chart, and it is
right to. What it cannot ask are the questions that only apply to a map, and
they are the ones a map most often gets wrong — above all, how the values
were cut into classes. Quantile, equal interval and natural breaks put the
same numbers in different colours and tell different stories. This repository
has already paid for an unnamed classification once.

Each test below is a plate wrong in exactly one way. A plate that says
everything must produce nothing, or the suite is measuring its own fixtures.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sprezzature_maps.audit import audit

ROOT = Path(__file__).resolve().parent.parent


def plate(*labels: str, root_attrs: str | None = None, extra: str = "") -> str:
    """A minimal SVG carrying the given visible text."""
    attrs = root_attrs if root_attrs is not None else (
        'role="img" aria-labelledby="t"'
    )
    texts = "".join(f"<text>{label}</text>" for label in labels)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" {attrs}>'
        f'<title id="t">A plate</title>{texts}{extra}</svg>'
    )


WHOLE = plate(
    "Control of territory, by district",
    "Positions as of 2024 · schematic",
)


def test_a_plate_that_says_everything_reports_nothing() -> None:
    """The baseline. Without it, nothing else here proves anything."""
    assert audit(WHOLE) == []


def test_a_classed_legend_must_name_its_method() -> None:
    """
    The finding this auditor exists for.

    A reader looking at five shades has no way to tell whether the darkest
    one means "top fifth of the list" or "top fifth of the range" — two very
    different claims about the same data.
    """
    classed = plate(
        "Exposure, by country", "as of 2024",
        extra='<rect class="swatch"/><rect class="swatch"/>',
    )
    assert "method-unnamed" in {f.rule for f in audit(classed)}


def test_naming_the_method_satisfies_it() -> None:
    """And the note the generator already prints is what satisfies it."""
    named = plate(
        "Exposure, by country", "as of 2024",
        "4 classes, quantiles", "10", "20", "30",
        extra='<rect class="swatch"/>',
    )
    assert "method-unnamed" not in {f.rule for f in audit(named)}


def test_a_classed_legend_without_breaks_is_a_key_less_table() -> None:
    """
    Swatches with no boundary values are decoration.

    The reader can see that one country is darker and cannot say than what,
    which is the same as not having a legend.
    """
    keyless = plate("Exposure", "as of 2024", "5 classes, natural breaks")
    assert "breaks-missing" in {f.rule for f in audit(keyless)}


def test_absent_must_not_read_as_low() -> None:
    """The commonest way a choropleth misleads."""
    hidden = plate(
        "Exposure", "as of 2024",
        extra='<path class="no-data" d="M0 0"/>',
    )
    assert "no-data-hidden" in {f.rule for f in audit(hidden)}

    shown = plate(
        "Exposure", "as of 2024", "No data",
        extra='<path class="no-data" d="M0 0"/>',
    )
    assert "no-data-hidden" not in {f.rule for f in audit(shown)}


def test_a_plate_with_no_date_and_no_disclaimer_is_reported() -> None:
    """A map with neither is read as current, forever."""
    assert "no-provenance" in {f.rule for f in audit(plate("Control of territory"))}


def test_declaring_the_data_synthetic_counts_as_provenance() -> None:
    """
    And counts for more than a date would.

    Stamping a vintage on invented numbers would be a fabrication, not an
    improvement. Saying "synthetic illustrative values" is the honest
    statement, and the rule has to accept it or it pushes authors toward the
    dishonest one.
    """
    demo = plate("Exposure index", "Synthetic illustrative values")
    assert "no-provenance" not in {f.rule for f in audit(demo)}


@pytest.mark.parametrize(
    "role", ["img", "graphics-document", "graphics-symbol"]
)
def test_both_accessible_roles_are_accepted(role: str) -> None:
    """
    `img` and `graphics-document` are both correct, and both are in use.

    A rule demanding `img` alone would push a maintainer to downgrade the
    better markup on an interactive plate to satisfy the linter, which is how
    a linter loses its users. The first version of this check did exactly
    that to five shipped situation maps.
    """
    named = plate(
        "Control", "as of 2024",
        root_attrs=f'role="{role}" aria-labelledby="t"',
    )
    assert "unlabelled" not in {f.rule for f in audit(named)}


def test_a_plate_with_no_accessible_name_is_reported() -> None:
    """A screen reader otherwise announces "graphic" and stops."""
    bare = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<text>Control of territory</text><text>as of 2024</text></svg>"
    )
    assert "unlabelled" in {f.rule for f in audit(bare)}


# ── The shipped plates ─────────────────────────────────────────────────────


#: Plates that still report, with the reason each one is still open.
#:
#: Recorded rather than hidden, and recorded *per rule* rather than per
#: plate: a blanket exemption for a file would let the next defect in it
#: through unseen, which is the failure mode an allowlist usually has.
#:
#: All four are the same shape of gap and none of them is the renderer's
#: to close. ``evidence-unclassed`` wants the plate to say on what footing
#: its zones are drawn -- every one of these is hand-traced from reporting
#: at a single confidence, which is a perfectly honest thing to be and an
#: unstated one. ``undated-control`` wants a vintage, and the two Syrian
#: and Libyan plates carry no provenance footer at all. Both are sentences
#: an author has to write; the generator inventing either would be the
#: fabrication the auditor exists to catch.
_OPEN_GAPS: dict[str, set[str]] = {
    "drc.svg": {"evidence-unclassed"},
    "libya.svg": {"evidence-unclassed", "undated-control"},
    "syria.svg": {"evidence-unclassed", "undated-control"},
    "ukraine.svg": {"evidence-unclassed"},
}


def test_the_shipped_plates_have_only_the_gaps_we_know_about() -> None:
    """
    Run the audit over this repository's own assets.

    What this guards is that no *other* kind of defect appears in them. A
    plate that loses its classification note, its accessible name or its
    locator fails here immediately -- which is how the locator being
    absent from all fourteen of them stopped being invisible.
    """
    unexpected: list[str] = []
    plates = sorted((ROOT / "assets").rglob("*.svg"))
    assert plates, "no shipped plates found — the glob has stopped matching"

    for path in plates:
        for finding in audit(path.read_text(encoding="utf-8", errors="replace")):
            if finding.rule in _OPEN_GAPS.get(path.name, set()):
                continue
            unexpected.append(f"{path.name}: {finding}")

    assert not unexpected, "\n".join(unexpected)


def test_the_recorded_gaps_are_still_real() -> None:
    """An allowlist that outlives its entries is a lie about the state.

    A gap that has been closed must come off the list, or the list stops
    describing the repository and starts excusing it.
    """
    stale: list[str] = []
    for name, rules in _OPEN_GAPS.items():
        matches = sorted((ROOT / "assets").rglob(name))
        if not matches:
            continue  # the plate is gitignored and may simply not be built
        found = {f.rule for f in audit(matches[0].read_text(errors="replace"))}
        for rule in sorted(rules - found):
            stale.append(f"{name}: {rule} no longer reports — take it off the list")
    assert not stale, "\n".join(stale)
