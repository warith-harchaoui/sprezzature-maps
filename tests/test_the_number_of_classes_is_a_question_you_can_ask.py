"""
The most consequential decision on a choropleth, reachable from the surface
people actually type.

``scripts/_classify.py`` has held four classifications since it was written,
including an exact Fisher–Jenks dynamic program, and its own module docstring
explains at length why the unclassed linear stretch it replaced is "the worst
fit for the data choropleths are usually made of". The HTTP body has offered
``classes`` and ``method`` all along. The command line offered neither, so
every map anybody made by typing got the unclassed ramp — the one reading the
module exists to argue against. Two hundred and sixty-nine lines of
classification nothing a user could type would reach.

That is this repository's dominant failure mode in its purest form: the tool
exists, nothing calls it.

Three checks, because they fail apart and each would leave a different half
broken:

1. the command line offers every method the module knows, and nothing else;
2. so does the HTTP body, which carried a hand-written copy of the list;
3. asking for classes through the command line actually classes the plate,
   and the auditor that polices classed legends agrees it names its method.

Why not ``elbow-helper`` for the number
---------------------------------------
Because it was measured, and its floor sits above this question's ceiling.
``robust_knee`` wants 20 points on a curve before it will commit
(``min_samples = 20``); the curve here is residual within-class variance
against k, and k is capped at 12 by both surfaces that offer it — the
``IntRange(2, 12)`` on the command line and the ``le=12`` on the HTTP field.
At every length the question can produce it returns
``NoClearKnee(INSUFFICIENT_DATA)`` — for the repository's own 174 values, for
a deliberately flat ramp, and for a control built from three separated steps
whose variance curve is 1.000, 0.250, 0.000 and whose answer is three. A
verdict constant over the whole domain is not a verdict. Stretched to 20 and
25 points, which is no longer a map, it still refuses that same control
(``ALL_CANDIDATES_WEAK``, then ``NO_PERSISTENT_CLUSTER``). The abstention is
honest about its own input size; it is just not a tool for picking k on a
choropleth, so the number stays the caller's to state.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sprezzature_maps import classification_methods  # noqa: E402
from sprezzature_maps.audit import audit  # noqa: E402
from sprezzature_maps.cli import main  # noqa: E402

#: The note a classed legend prints, e.g. "5 classes, natural breaks". Same
#: shape the auditor looks for; asserted here against the plate the command
#: line produced rather than against a plate written by hand.
_LEGEND_NOTE = re.compile(r">\s*(\d+)\s+classes?,\s*([^<]+?)\s*</text>")

#: Enough of a render to read the legend, and no more. Relief composites a
#: hillshade raster and the city and river layers cost vertices; none of them
#: say anything about classification, and each one is a second per plate.
_FAST = ("--no-relief",)


def _option(name: str):
    """The declared Click option *name* on the choropleth command."""
    found = [p for p in main.commands["choropleth"].params if p.name == name]
    assert found, (
        f"the choropleth command declares no --{name.replace('_', '-')}; the "
        "generator takes it and the HTTP body offers it, so a reader who types "
        "rather than imports cannot ask for it at all"
    )
    return found[0]


def test_the_command_line_offers_every_method_the_module_knows() -> None:
    """A method added to ``_classify`` must not stay unreachable by typing.

    The list is derived, not written here, so this is about the wiring and
    not about today's four names: add a fifth to ``METHODS`` and the command
    line carries it the same minute.
    """
    assert tuple(_option("method").type.choices) == classification_methods()


def test_the_http_body_offers_every_method_the_module_knows() -> None:
    """The one surface that did carry a second copy of the list."""
    pytest.importorskip("fastapi", reason="the [api] extra is not installed")
    from typing import get_args

    from sprezzature_maps.api import ChoroplethRequest

    declared = get_args(ChoroplethRequest.model_fields["method"].annotation)
    assert tuple(declared) == classification_methods(), (
        "the request model's Literal and scripts/_classify.METHODS disagree; "
        "whichever copy a reader holds becomes the set of methods they "
        "believe exists"
    )


def test_asking_for_five_natural_breaks_gets_five_natural_breaks(tmp_path) -> None:
    """End to end through the command line, read back off the plate."""
    out = tmp_path / "classed.svg"
    done = CliRunner().invoke(
        main,
        ["choropleth", "--out", str(out), "--classes", "5", "--method", "jenks", *_FAST],
    )
    assert done.exit_code == 0, done.output + str(done.exception)
    svg = out.read_text(encoding="utf-8")
    assert _LEGEND_NOTE.findall(svg) == [("5", "natural breaks")], (
        "the plate does not state five natural breaks on its legend, so either "
        "the option fell on the floor or the legend stopped naming the method"
    )
    # And the rule that polices classed legends is satisfied by this one,
    # which is the point of having both halves: the auditor has had a
    # `method-unnamed` rule all along for a state the command line could not
    # even produce.
    assert "method-unnamed" not in {f.rule for f in audit(svg)}


def test_not_asking_keeps_the_unclassed_ramp(tmp_path) -> None:
    """The default is unchanged: no classes, and no legend note claiming any.

    The other half of the same risk. A default that quietly became "five
    quantiles" would invent five plateaus on every flat distribution anybody
    ever maps, which is a map that misleads harder than the one it replaced.
    """
    out = tmp_path / "unclassed.svg"
    done = CliRunner().invoke(main, ["choropleth", "--out", str(out), *_FAST])
    assert done.exit_code == 0, done.output + str(done.exception)
    assert _LEGEND_NOTE.findall(out.read_text(encoding="utf-8")) == []


def test_a_method_without_classes_is_not_a_silent_classification(tmp_path) -> None:
    """``--method jenks`` alone must not read as a request that was honoured.

    It is accepted, because the generator ignores it the way the HTTP surface
    does; what matters is that the plate does not come back claiming classes
    nobody asked for.
    """
    out = tmp_path / "method-only.svg"
    done = CliRunner().invoke(main, ["choropleth", "--out", str(out), "--method", "jenks", *_FAST])
    assert done.exit_code == 0, done.output + str(done.exception)
    assert _LEGEND_NOTE.findall(out.read_text(encoding="utf-8")) == []
