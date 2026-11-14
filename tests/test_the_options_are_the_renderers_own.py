"""
The option registry must describe the renderers, not a memory of them.

``sprezzature_maps/options.py`` exists so that an editor, the assistant and
any automatic loop stop carrying their own lists of what the renderers accept.
That only helps while the list is true. A registry that has drifted from the
signatures is worse than none: it proposes a keyword that raises three layers
down, or — the quiet case — one that lands in ``**kwargs`` and is ignored,
which looks exactly like a change that had no visible effect.

So this reads the live signatures and compares. It also insists that
:data:`OPTIONS` and :data:`NOT_AN_OPTION` together account for *every* keyword,
which is the part that catches an addition: a new knob has to be classified by
somebody, rather than being invisible to everything downstream.

Author
------
Project maintainers.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from sprezzature_maps import _load_script, classification_methods
from sprezzature_maps.kinds import KINDS, kind_names
from sprezzature_maps.options import (
    NOT_AN_OPTION,
    OPTIONS,
    MapOption,
    option,
    options_for,
    safe_options_for,
)

ROOT = Path(__file__).resolve().parent.parent
SHAPES = {"integer", "number", "boolean", "choice", "text"}


def _keywords(kind_name: str) -> set[str]:
    """Every keyword the named kind's renderer really accepts."""
    kind = next(k for k in KINDS if k.name == kind_name)
    module = _load_script(kind.renderer)
    signature = inspect.signature(getattr(module, kind.renderer))
    return {p.name for p in signature.parameters.values() if p.default is not p.empty}


def test_the_signatures_were_actually_read() -> None:
    """Non-vacuity: a broken loader would make every assertion below trivial."""
    for name in kind_names():
        assert _keywords(name), f"{name}'s renderer reported no keywords at all"
    assert "width" in _keywords("choropleth")
    assert "bins" in _keywords("density")


@pytest.mark.parametrize("declared", OPTIONS, ids=[o.name for o in OPTIONS])
def test_every_declared_option_is_a_real_keyword(declared: MapOption) -> None:
    for kind_name in declared.kinds:
        assert declared.name in _keywords(kind_name), (
            f"options.py declares {declared.name!r} for {kind_name}, whose renderer "
            f"does not take it; it would land in **kwargs and be ignored"
        )


@pytest.mark.parametrize("kind_name", kind_names())
def test_every_keyword_is_classified(kind_name: str) -> None:
    """An option, or a named exemption. Not neither."""
    declared = {o.name for o in options_for(kind_name)}
    unclassified = _keywords(kind_name) - declared - set(NOT_AN_OPTION)
    assert not unclassified, (
        f"{kind_name}'s renderer takes {', '.join(sorted(unclassified))}, which "
        "options.py neither offers nor exempts; add it to OPTIONS or to "
        "NOT_AN_OPTION with a reason"
    )


@pytest.mark.parametrize("declared", OPTIONS, ids=[o.name for o in OPTIONS])
def test_every_option_names_registered_kinds(declared: MapOption) -> None:
    assert declared.kinds, f"{declared.name} is declared for no kind at all"
    for kind_name in declared.kinds:
        assert kind_name in kind_names(), f"{declared.name} names kind {kind_name!r}"


@pytest.mark.parametrize("declared", OPTIONS, ids=[o.name for o in OPTIONS])
def test_every_option_is_well_formed(declared: MapOption) -> None:
    assert declared.shape in SHAPES, f"{declared.name} has shape {declared.shape!r}"
    assert declared.why, f"{declared.name} says nothing about what changing it is for"
    if declared.shape == "choice":
        assert declared.choices, f"{declared.name} is a choice with no choices"
    else:
        assert not declared.choices, f"{declared.name} is not a choice but lists some"
    if declared.shape in ("integer", "number"):
        assert declared.low is not None and declared.high is not None, (
            f"{declared.name} is numeric with no bounds; a loop would not know where to stop"
        )
        assert declared.low < declared.high
    for step in declared.steps:
        assert declared.low <= step <= declared.high, (
            f"{declared.name} offers the step {step}, outside its own bounds"
        )


def test_the_safe_set_excludes_everything_that_can_change_the_reading() -> None:
    """The line that matters, stated as a test rather than only as prose.

    Widening a map cannot change what it says about the data. Re-cutting the
    classes can: the same numbers, different breaks, a country in a different
    band, and a reader who trusts the picture is misled by a repair nobody
    confirmed.
    """
    data_affecting = {"method", "classes", "breaks", "diverging", "per_area", "bbox", "region"}
    safe = {o.name for o in OPTIONS if o.safe}
    assert not (safe & data_affecting), (
        f"these are marked safe and can change what the map says: "
        f"{', '.join(sorted(safe & data_affecting))}"
    )
    assert safe, "nothing is safe to change, so no loop can do anything"


@pytest.mark.parametrize("declared", OPTIONS, ids=[o.name for o in OPTIONS])
def test_no_option_is_a_documented_no_op(declared: MapOption) -> None:
    """An option that changes nothing is the worst entry this registry can hold.

    A loop offered one would change it, see no difference, and have no way to
    tell "it did not help" from "it did nothing" — so it would go on trying,
    or stop and report a repair it never made.

    ``make_choropleth`` holds exactly one such parameter: ``accessibility``,
    accepted for command-line parity and discarded with ``_ = accessibility``,
    which its own docstring explains. It was in :data:`OPTIONS` until this test
    was written, with three invented colour-blindness values beside it.

    The idiom is what gets searched for, not the name: ``_ = <name>`` is how
    this codebase marks a parameter it keeps for its signature and ignores.
    """
    for kind_name in declared.kinds:
        kind = next(k for k in KINDS if k.name == kind_name)
        module = _load_script(kind.renderer)
        source = inspect.getsource(module)
        assert f"_ = {declared.name}" not in source, (
            f"{kind.renderer} accepts {declared.name!r} and discards it, so "
            f"offering it as an option promises a change that cannot happen"
        )


def test_the_classification_choices_are_the_package_own() -> None:
    """Compared against the canonical list, not against the renderer's text.

    Two earlier versions of this test searched source text for each value and
    were wrong both times — the first because the parameter is handled in
    another module, the second because ``headtail`` is defined in
    ``_classify.py`` and never written in ``make_choropleth.py``. The thing
    worth asserting is set equality with the one function that owns the list.
    """
    declared = option("method")
    canonical = classification_methods()
    assert canonical, "classification_methods() answered nothing; the comparison is empty"
    assert set(declared.choices) == set(canonical), (
        f"options.py offers {sorted(declared.choices)} and the package defines "
        f"{sorted(canonical)}"
    )


def test_importing_the_options_does_not_need_a_finished_package() -> None:
    """``method``'s choices are resolved at import, through a local import of
    the package. That holds only while ``__init__`` does not import this
    module; if it ever does, this fails rather than deadlocking somewhere
    else."""
    source = (ROOT / "sprezzature_maps" / "__init__.py").read_text(encoding="utf-8")
    assert "options" not in source.replace("rendering options", ""), (
        "__init__.py mentions options; check it does not import this module"
    )
    proc = subprocess.run(
        [sys.executable, "-c", "import sprezzature_maps.options as o; print(len(o.OPTIONS))"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert int(proc.stdout.strip()) > 0


def test_a_situation_map_offers_nothing_and_says_so() -> None:
    """Its renderer takes only the call itself and a title. Not a gap: the
    kind draws from a configuration file, which is where its knobs live."""
    assert options_for("situation_map") == ()
    assert safe_options_for("situation_map") == ()


def test_an_unknown_name_lists_the_known_ones() -> None:
    with pytest.raises(KeyError, match="width"):
        option("widht")
