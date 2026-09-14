"""
_classify: turn a list of values into class breaks, the choice a choropleth
lives or dies by.

Module summary
--------------
A choropleth has to map numbers to colours, and the rule it uses is the most
consequential setting on the map: the same dataset tells different stories
depending on how it is classed, and a reader given no statement of the method
cannot tell which story they are being told.

This generator used to do the simplest possible thing — stretch the colour
ramp linearly from the smallest value to the largest, with no classes at all.
That is *unclassed equal interval*, and it is the worst fit for the data
choropleths are usually made of. Real indicator data (income, density, GDP per
head, case counts) is right-skewed: a few very large values and a long tail of
small ones. On GDP per head for twenty countries, linear stretching puts nine
of them in the bottom quarter of the ramp and leaves India — ten times
Burundi's figure — visually identical to Burundi.

So this module offers the classifications cartography actually uses, each
answering a different question:

``quantile``
    Equal *count* per class. Guarantees every class is populated and supports
    ranked comparison ("which fifth is this region in?"). Its cost is that two
    regions with wildly different values can share a class when the data is
    uneven, and it flattens a skew by construction.
``equal``
    Equal *width* per class: ``min + i * (max - min) / k``. Honest about the
    number line, poor on skewed data, where most regions land in one class.
    Right when the values are roughly uniform, or when the classes have to
    mean something outside the data (decades, percentage bands).
``jenks``
    Fisher–Jenks natural breaks: the partition minimising variance inside
    classes and maximising it between them. Shows the groupings the data
    itself suggests. Best when the map should reveal structure rather than
    support ranking.
``headtail``
    Head/tail breaks (Jiang 2013), for heavy-tailed data: split at the mean,
    recurse into the head. Designed for the "far more small things than large
    things" shape, where quantile and equal interval both mislead.

No default is correct for every dataset, so nothing here picks one silently:
the caller chooses, and the legend states what was chosen. That statement is
the point. Without it two readers of the same map see two different truths.

Everything is standard library. The Fisher–Jenks solver is O(k·n²) in time and
memory, which is nothing for the few hundred territories a world map holds and
would be the wrong algorithm for a million points.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

#: The classification schemes this module knows, in the order a chooser
#: should consider them. ``None`` (no classification at all) stays the
#: generator's default and is deliberately not a member: it is the absence
#: of a choice, not one of the choices.
METHODS: tuple[str, ...] = ("quantile", "equal", "jenks", "headtail")

#: How each method should be named to a reader, on the legend. A method
#: nobody can name is a method nobody can question.
METHOD_LABELS: dict[str, str] = {
    "quantile": "quantiles",
    "equal": "equal intervals",
    "jenks": "natural breaks",
    "headtail": "head/tail breaks",
    # Not a member of METHODS: nothing computed these, the caller supplied
    # them. The legend still has to say so, because "given" is exactly the
    # provenance a reader needs -- it means the boundaries are editorial.
    "given": "given breaks",
}


def _clean(values: Sequence[float]) -> list[float]:
    """Sorted, finite values. Raises when nothing is left to classify."""
    finite = sorted(float(v) for v in values if v == v and abs(v) != float("inf"))
    if not finite:
        raise ValueError("no finite values to classify")
    return finite


def _dedupe_breaks(breaks: list[float]) -> list[float]:
    """Strictly increasing interior breaks, with duplicates collapsed.

    Ties are common — a quantile of mostly-zero data puts several breaks on
    the same number — and two classes sharing a boundary are one class with
    an empty neighbour. Collapsing is honest: the caller asked for k classes
    and gets the number the data can actually support.
    """
    out: list[float] = []
    for b in breaks:
        if not out or b > out[-1]:
            out.append(b)
    return out


def quantile_breaks(values: Sequence[float], k: int) -> list[float]:
    """Interior breaks putting an equal *count* of values in each class."""
    data = _clean(values)
    if k < 2 or len(data) < k:
        return []
    return _dedupe_breaks(
        [data[round(i * len(data) / k)] for i in range(1, k) if 0 < round(i * len(data) / k) < len(data)]
    )


def equal_breaks(values: Sequence[float], k: int) -> list[float]:
    """Interior breaks of equal *width* across the observed range."""
    data = _clean(values)
    lo, hi = data[0], data[-1]
    if k < 2 or hi <= lo:
        return []
    step = (hi - lo) / k
    return _dedupe_breaks([lo + step * i for i in range(1, k)])


def jenks_breaks(values: Sequence[float], k: int) -> list[float]:
    """
    Fisher–Jenks natural breaks: minimise the sum of within-class variance.

    Exact dynamic program, not the iterative approximation often shipped under
    the same name. O(k·n²); fine for the few hundred territories on a world
    map, wrong for a million points.
    """
    data = _clean(values)
    n = len(data)
    if k < 2 or n <= k:
        return []

    # cost[i][j]: within-class sum of squared deviations for data[i:j+1].
    prefix = [0.0] * (n + 1)
    prefix_sq = [0.0] * (n + 1)
    for i, v in enumerate(data):
        prefix[i + 1] = prefix[i] + v
        prefix_sq[i + 1] = prefix_sq[i] + v * v

    def sse(i: int, j: int) -> float:
        """Sum of squared deviations from the mean over ``data[i:j]``."""
        count = j - i
        if count <= 1:
            return 0.0
        total = prefix[j] - prefix[i]
        return (prefix_sq[j] - prefix_sq[i]) - total * total / count

    # best[c][j]: least cost of splitting the first j values into c classes.
    inf = float("inf")
    best = [[inf] * (n + 1) for _ in range(k + 1)]
    split = [[0] * (n + 1) for _ in range(k + 1)]
    best[0][0] = 0.0
    for c in range(1, k + 1):
        for j in range(c, n + 1):
            for i in range(c - 1, j):
                if best[c - 1][i] == inf:
                    continue
                cost = best[c - 1][i] + sse(i, j)
                if cost < best[c][j]:
                    best[c][j] = cost
                    split[c][j] = i

    cuts: list[int] = []
    j = n
    for c in range(k, 1, -1):
        j = split[c][j]
        cuts.append(j)
    return _dedupe_breaks([data[i] for i in reversed(cuts) if 0 < i < n])


def headtail_breaks(values: Sequence[float], k: int | None = None) -> list[float]:
    """
    Head/tail breaks (Jiang 2013) for heavy-tailed data.

    Split at the arithmetic mean, keep the head (the values above it), recurse.
    The number of classes falls out of the data's own hierarchy rather than
    being asked for; `k` caps the recursion when a caller needs a bound.
    """
    data = _clean(values)
    breaks: list[float] = []
    head = data
    limit = (k - 1) if k and k > 1 else 40
    while len(head) > 1 and len(breaks) < limit:
        mean = statistics.fmean(head)
        above = [v for v in head if v > mean]
        # Stop when the head stops being a minority: that is the signal the
        # distribution is no longer heavy-tailed, and splitting further would
        # invent a hierarchy the data does not have.
        if not above or len(above) >= len(head) / 2:
            break
        breaks.append(mean)
        head = above
    return _dedupe_breaks(breaks)


def classify(values: Sequence[float], k: int, method: str) -> list[float]:
    """
    Interior class breaks for `values`, by `method`.

    Returns ``k - 1`` boundaries at most — fewer when the data cannot support
    that many distinct ones. An empty list means the values admit no useful
    classification (all equal, or fewer values than classes), and the caller
    should fall back to its unclassed ramp rather than draw a legend of
    identical swatches.
    """
    if method not in METHODS:
        raise ValueError(f"unknown classification method {method!r}; expected one of {METHODS}")
    if method == "quantile":
        return quantile_breaks(values, k)
    if method == "equal":
        return equal_breaks(values, k)
    if method == "jenks":
        return jenks_breaks(values, k)
    return headtail_breaks(values, k)


def class_index(value: float, breaks: Sequence[float]) -> int:
    """Which class `value` falls in, given interior `breaks`. 0-based."""
    index = 0
    for b in breaks:
        if value < b:
            break
        index += 1
    return index
