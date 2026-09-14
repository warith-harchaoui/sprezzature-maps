"""
Class breaks: the setting a choropleth lives or dies by.

The generator stretched its colour ramp linearly from the smallest value to
the largest, with no classes. That is unclassed equal interval, and it is the
weakest choice for the right-skewed data indicators are made of. These tests
pin both halves of the fix: that each classification does what cartography
says it does, and that the map built on it separates what it claims to.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import itertools
import math
import random
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _classify import (  # noqa: E402
    METHOD_LABELS,
    METHODS,
    class_index,
    classify,
    jenks_breaks,
)

#: GDP per head, 2023 orders of magnitude, twenty countries. Right-skewed the
#: way real indicators are — which is the whole point: a linear ramp handles
#: it badly and that is not a corner case, it is the common case.
GDP = [
    128259, 103685, 99995, 87925, 82769, 68453, 64572, 54343, 44461, 38373,
    33511, 22113, 13790, 12614, 10295, 2485, 1950, 1294, 529, 238,
]

#: Just-noticeable difference in OKLab for a flat area of colour. Below this
#: two territories read as the same shade however different their numbers.
JND = 0.02


def _delta_e(hex_a: str, hex_b: str) -> float:
    from _geo_colors import _hex_to_linear, _linear_to_oklab

    la, aa, ba = _linear_to_oklab(_hex_to_linear(hex_a))
    lb, ab, bb = _linear_to_oklab(_hex_to_linear(hex_b))
    return math.sqrt((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)


@pytest.mark.parametrize("method", METHODS)
def test_every_method_is_named_for_a_reader(method: str) -> None:
    """A method nobody can name is a method nobody can question."""
    assert METHOD_LABELS[method].strip()


def test_quantile_fills_every_class() -> None:
    """Equal count per class is the property quantile exists to have."""
    breaks = classify(GDP, 5, "quantile")
    counts = [0] * (len(breaks) + 1)
    for value in GDP:
        counts[class_index(value, breaks)] += 1
    assert counts == [4, 4, 4, 4, 4]


def test_equal_interval_collapses_skewed_data() -> None:
    """
    The failure that motivated the whole feature, pinned rather than assumed.

    Equal width over a right-skewed indicator puts nearly half the countries
    in the bottom class. That is not a bug in the method — it is what equal
    interval does, and it is why it must not be the only option.
    """
    breaks = classify(GDP, 5, "equal")
    counts = [0] * (len(breaks) + 1)
    for value in GDP:
        counts[class_index(value, breaks)] += 1
    assert counts[0] >= len(GDP) / 2 - 1, counts


def test_jenks_matches_the_optimal_partition() -> None:
    """
    Fisher–Jenks is exact here, not the iterative approximation.

    Checked against brute force over every contiguous partition, comparing
    cost rather than break values: several partitions can tie, and an
    implementation that finds a different one of equal cost is still correct.
    """

    def sse(classes: list[list[float]]) -> float:
        total = 0.0
        for group in classes:
            if len(group) > 1:
                mean = sum(group) / len(group)
                total += sum((v - mean) ** 2 for v in group)
        return total

    rng = random.Random(20260914)
    for _ in range(25):
        n = rng.randint(6, 12)
        k = rng.randint(2, min(4, n - 1))
        data = sorted(round(rng.expovariate(1 / 50), 2) for _ in range(n))

        best = min(
            sse([data[a:b] for a, b in itertools.pairwise((0, *cuts, n))])
            for cuts in itertools.combinations(range(1, n), k - 1)
        )

        breaks = jenks_breaks(data, k)
        groups: list[list[float]] = []
        start = 0
        for boundary in breaks:
            stop = next(i for i, v in enumerate(data) if v >= boundary)
            groups.append(data[start:stop])
            start = stop
        groups.append(data[start:])
        assert sse(groups) == pytest.approx(best, abs=1e-9)


def test_classification_refuses_what_it_cannot_do() -> None:
    """Fewer values than classes, or no spread, yields no breaks at all."""
    assert classify([5.0, 5.0, 5.0], 4, "quantile") == []
    assert classify([1.0, 2.0], 5, "jenks") == []
    assert classify([7.0], 3, "equal") == []
    with pytest.raises(ValueError):
        classify(GDP, 5, "rainbow")


def test_the_map_separates_what_it_claims_to_separate() -> None:
    """
    The measurement that justifies the feature, in perceptual units.

    Of the pairs a five-quantile classing puts in different classes, the old
    linear ramp leaves several closer than the eye can resolve — it claims a
    distinction it does not deliver. India at ten times Burundi's figure came
    out 0.0115 apart, below the 0.02 threshold.

    Pairs *inside* one class are deliberately identical, so counting
    indistinguishable pairs overall would punish classing for doing its job.
    The honest question is only about pairs it says are different.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("mc", SCRIPTS / "make_choropleth.py")
    assert spec and spec.loader
    mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc)

    v_min, v_max = min(GDP), max(GDP)
    span = v_max - v_min
    breaks = classify(GDP, 5, "quantile")
    buckets: list[list[float]] = [[] for _ in range(len(breaks) + 1)]
    for value in GDP:
        buckets[class_index(value, breaks)].append(value)
    centres = [(min(b) + max(b)) / 2 for b in buckets]

    def linear(value: float) -> str:
        return str(mc._ramp_hex((value - v_min) / span))

    def classed(value: float) -> str:
        return str(mc._ramp_hex((centres[class_index(value, breaks)] - v_min) / span))

    unresolved_linear = 0
    worst_classed = 1.0
    for a, b in itertools.combinations(GDP, 2):
        if class_index(a, breaks) == class_index(b, breaks):
            continue
        if _delta_e(linear(a), linear(b)) < JND:
            unresolved_linear += 1
        worst_classed = min(worst_classed, _delta_e(classed(a), classed(b)))

    assert unresolved_linear >= 4, (
        "the linear ramp used to leave at least four separated pairs below the "
        "perceptual threshold; if that is no longer true the ramp changed and "
        "this justification needs rewriting, not deleting"
    )
    assert worst_classed >= JND, (
        f"classed map's closest separated pair is {worst_classed:.4f}, under the "
        f"{JND} threshold: it claims a distinction the eye cannot make"
    )


def test_given_breaks_override_any_method_and_say_so() -> None:
    """
    Editorial boundaries win, and the legend reports them as given.

    Some bands have to mean something outside the data — a regulatory
    threshold, a percentage the newsroom already published, a number the
    reader arrives with. No algorithm lands on those by luck, so passing them
    has to be possible; and once passed, naming a method that did not run
    would be a lie about where the boundaries came from.
    """
    import importlib.util
    import re

    spec = importlib.util.spec_from_file_location("mc", SCRIPTS / "make_choropleth.py")
    assert spec and spec.loader
    mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc)

    rows = [
        {"id": "250", "value": 3.2},
        {"id": "840", "value": 12.0},
        {"id": "156", "value": 27.5},
        {"id": "356", "value": 41.0},
    ]
    svg = mc.build_svg(rows, breaks=[5, 10, 25], classes=7, method="jenks")

    legend = re.search(r">(\d+ classes, [a-z/ ]+)<", svg)
    assert legend, "the classed legend is missing"
    assert legend.group(1) == "4 classes, given breaks", legend.group(1)

    printed = re.findall(r'font-size="9" text-anchor="middle"[^>]*>([^<]+)<', svg)
    assert printed == ["5", "10", "25"], printed


def test_no_class_straddles_zero_on_a_diverging_ramp() -> None:
    """
    A diverging scale exists to show which side of zero a value falls on.

    A class spanning zero destroys exactly that: the class takes the colour of
    its own centre, so a country in recession comes out the blue of growth.
    This was not a theoretical risk — over random growth-rate data all four
    methods produced one, quantile in roughly two thirds of cases. Zero is a
    boundary now, and each side is classified on its own values so the method
    still answers the question it was picked for.
    """
    from _classify import diverging_classify

    rng = random.Random(1)
    straddling_before = 0
    checked = 0

    for _ in range(600):
        values = [round(rng.uniform(-6, 9), 1) for _ in range(rng.randint(8, 30))]
        if not (min(values) < 0 < max(values)):
            continue
        checked += 1
        for method in METHODS:
            plain = classify(values, 5, method)
            if plain and _straddles_zero(values, plain):
                straddling_before += 1

            fixed = diverging_classify(values, 5, method)
            assert not _straddles_zero(values, fixed), (
                f"{method}: a class still spans zero — {values}"
            )
            if len(values) > 5:
                assert 0.0 in fixed, f"{method}: zero is not a boundary — {fixed}"

    assert checked > 100, "the generator produced too few diverging datasets to be a test"
    assert straddling_before > 100, (
        "the unguarded classifiers used to straddle zero constantly; if they no "
        "longer do, this test is measuring the wrong thing"
    )


def _straddles_zero(values: list[float], breaks: list[float]) -> bool:
    """True when some class holds values on both sides of zero."""
    buckets: list[list[float]] = [[] for _ in range(len(breaks) + 1)]
    for value in values:
        buckets[class_index(value, breaks)].append(value)
    return any(bucket and min(bucket) < 0 < max(bucket) for bucket in buckets)


def test_one_sided_data_is_classified_normally() -> None:
    """Nothing to straddle: the diverging path must not distort the breaks."""
    from _classify import diverging_classify

    for method in METHODS:
        assert diverging_classify(GDP, 5, method) == classify(GDP, 5, method)
