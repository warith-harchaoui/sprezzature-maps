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
    attrs = root_attrs if root_attrs is not None else ('role="img" aria-labelledby="t"')
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
        "Exposure, by country",
        "as of 2024",
        extra='<rect class="swatch"/><rect class="swatch"/>',
    )
    assert "method-unnamed" in {f.rule for f in audit(classed)}


def test_naming_the_method_satisfies_it() -> None:
    """And the note the generator already prints is what satisfies it."""
    named = plate(
        "Exposure, by country",
        "as of 2024",
        "4 classes, quantiles",
        "10",
        "20",
        "30",
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
        "Exposure",
        "as of 2024",
        extra='<path class="no-data" d="M0 0"/>',
    )
    assert "no-data-hidden" in {f.rule for f in audit(hidden)}

    shown = plate(
        "Exposure",
        "as of 2024",
        "No data",
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


@pytest.mark.parametrize("role", ["img", "graphics-document", "graphics-symbol"])
def test_both_accessible_roles_are_accepted(role: str) -> None:
    """
    `img` and `graphics-document` are both correct, and both are in use.

    A rule demanding `img` alone would push a maintainer to downgrade the
    better markup on an interactive plate to satisfy the linter, which is how
    a linter loses its users. The first version of this check did exactly
    that to five shipped situation maps.
    """
    named = plate(
        "Control",
        "as of 2024",
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


def test_the_shipped_plates_have_only_the_gap_we_know_about() -> None:
    """
    Run the audit over this repository's own assets.

    Four situation maps say neither when they were true nor that they are
    schematics; they are demo plates and re-rendering them is expensive, so
    the gap is recorded here rather than hidden. What this test actually
    guards is that no *other* kind of defect appears in them — a plate that
    loses its classification note or its accessible name fails immediately.
    """
    known_gap = {
        "himalaya.svg",
        "iberia.svg",
        "switzerland.svg",
        "western-europe.svg",
    }
    unexpected: list[str] = []
    plates = sorted((ROOT / "assets").rglob("*.svg"))
    assert plates, "no shipped plates found — the glob has stopped matching"

    for path in plates:
        for finding in audit(path.read_text(encoding="utf-8", errors="replace")):
            if finding.rule == "no-provenance" and path.name in known_gap:
                continue
            unexpected.append(f"{path.name}: {finding}")

    assert not unexpected, "\n".join(unexpected)
