"""
_simplify: drop the vertices the output resolution cannot show.

A generator here projects real coastlines into a canvas of a few hundred
units and then writes every vertex it was given. Measured on
``make_choropleth`` at its default 1000x564: **107 750 line segments, of
which 97% are shorter than one unit and 84% shorter than half a unit.**
The same 107 750 are emitted at 375 units wide, where 99% are sub-unit.
They cost roughly 1.5 MB of path data per map and cannot be seen at any
size the map is ever published at.

This is the job mapshaper's ``-simplify resolution=`` exists for: simplify
to the output's own resolution rather than to a percentage of the source.
The difference from the vendored-geometry tiering already in this repo
(``_land_topojson_for_bbox`` picking 10m or 50m from the region's size) is
that tiering chooses a *source*, in degrees, before projection; this runs
after projection, in the units actually drawn, so it is the only place
that knows how big a feature will really be on the page.

Deliberately **not** done here: smoothing, snapping, or topology repair.
A shared border drawn from two sides would still be simplified twice and
could open a sliver between the two -- which is exactly why
``_frontiers_layer`` unions its linework *before* it reaches this module,
and why control zones are drawn from their own polygons rather than from
a shared mosaic. If a caller ever needs topology-preserving
simplification, that is mapshaper's ``-clean``/``-innerlines`` territory
and a different piece of work.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from collections.abc import Sequence

#: Default tolerance, in output units (SVG user units, which are pixels at
#: 1x). Chosen by measurement rather than taste: at 0.25 the worst-case
#: 260x260 crop of a world choropleth was indistinguishable from the full
#: geometry by eye, while 1.29% of pixels differed by more than 8/255 --
#: all of it sub-pixel movement along coastlines. 0.2 keeps a margin under
#: that, and still removes the overwhelming majority of the vertices,
#: because the distribution is not near the threshold: the *median* segment
#: on a default-size world map is 0.22 units long.
DEFAULT_TOLERANCE = 0.2


def simplify_screen(
    points: Sequence[tuple[float, float]], tolerance: float = DEFAULT_TOLERANCE
) -> list[tuple[float, float]]:
    """Return ``points`` with every vertex the tolerance cannot justify removed.

    Douglas-Peucker, run **in output units after projection**, so the
    tolerance means what it says on the finished page: no retained vertex
    moves the drawn line by more than ``tolerance`` units.

    Douglas-Peucker rather than Visvalingam here, despite mapshaper
    defaulting to weighted Visvalingam: the two optimise different things,
    and the one that matters at this scale is Douglas-Peucker's guarantee
    that the simplified line stays within a fixed distance of the original.
    Visvalingam's effective-area metric produces a more *pleasing* coastline
    at aggressive settings, which is the case mapshaper is built for; this
    runs at a sub-pixel setting where nothing should be visibly reshaped at
    all, and a hard distance bound is the honest way to promise that.

    Implemented with an explicit stack, not recursion: a single country ring
    in the vendored atlas runs to thousands of points, and the recursive
    form blows Python's stack on the first large one.

    Parameters
    ----------
    points : sequence of (float, float)
        The run of points, already projected into output units.
    tolerance : float, optional
        Maximum distance, in output units, any dropped vertex may lie from
        the line kept in its place. Zero or less returns the input
        unchanged, which is the documented way to switch this off.

    Returns
    -------
    list of (float, float)
        The retained points, first and last always among them, in order.

    Examples
    --------
    A straight run collapses to its endpoints:

    >>> simplify_screen([(0, 0), (1, 0), (2, 0), (3, 0)], 0.1)
    [(0, 0), (3, 0)]

    A real corner survives:

    >>> simplify_screen([(0, 0), (1, 5), (2, 0)], 0.1)
    [(0, 0), (1, 5), (2, 0)]

    Switching it off returns the input:

    >>> simplify_screen([(0, 0), (1, 0), (2, 0)], 0)
    [(0, 0), (1, 0), (2, 0)]

    Degenerate runs pass straight through:

    >>> simplify_screen([(0, 0), (1, 1)], 0.5)
    [(0, 0), (1, 1)]
    """
    n = len(points)
    if tolerance <= 0 or n < 3:
        return list(points)

    keep = [False] * n
    keep[0] = keep[n - 1] = True
    # (first, last) spans still to examine. Each pop either splits the span
    # at its farthest-out vertex or discards every interior vertex in it.
    stack: list[tuple[int, int]] = [(0, n - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        # Twice the triangle area divided by the base is the perpendicular
        # distance; comparing squared quantities avoids a square root per
        # vertex, which matters over ~100k of them. When the span's two ends
        # coincide the base is zero and plain squared distance is the right
        # measure instead.
        base_sq = dx * dx + dy * dy
        limit = tolerance * tolerance * base_sq if base_sq else tolerance * tolerance
        worst, worst_i = -1.0, first
        for i in range(first + 1, last):
            px, py = points[i]
            if base_sq:
                cross = dx * (py - ay) - dy * (px - ax)
                measure = cross * cross
            else:
                ex, ey = px - ax, py - ay
                measure = ex * ex + ey * ey
            if measure > worst:
                worst, worst_i = measure, i
        if worst > limit:
            keep[worst_i] = True
            stack.append((first, worst_i))
            stack.append((worst_i, last))

    return [p for p, k in zip(points, keep, strict=True) if k]


def simplify_ring(
    points: Sequence[tuple[float, float]], tolerance: float = DEFAULT_TOLERANCE
) -> list[tuple[float, float]]:
    """Simplify a closed ring, refusing to collapse it into nothing.

    A ring is simplified like an open run, but a polygon that drops below
    three points stops being a polygon: at a sub-pixel tolerance an island
    smaller than the tolerance would otherwise vanish silently, and a map
    that quietly loses Malta is worse than one that carries a few redundant
    vertices. This is mapshaper's ``keep-shapes`` in miniature.

    Parameters
    ----------
    points : sequence of (float, float)
        The ring's points in output units. The caller's closing convention
        is preserved: nothing is appended or removed at the ends.
    tolerance : float, optional
        As :func:`simplify_screen`.

    Returns
    -------
    list of (float, float)
        At least three points whenever the input had at least three.

    Examples
    --------
    >>> simplify_ring([(0, 0), (4, 0), (4, 4), (0, 4)], 0.1)
    [(0, 0), (4, 0), (4, 4), (0, 4)]

    A speck far below the tolerance keeps its three points rather than
    disappearing:

    >>> len(simplify_ring([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)], 5.0))
    4
    """
    if len(points) < 3:
        return list(points)
    out = simplify_screen(points, tolerance)
    return out if len(out) >= 3 else list(points)
