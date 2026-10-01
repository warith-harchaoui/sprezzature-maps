"""
_topojson: the one decoder both generators used to carry a copy of.

TopoJSON stores a map's geometry once rather than once per feature. Shared
boundaries become *arcs*, numbered and referenced by index; a feature is a
list of those indices, and a negative index means "that arc, traversed
backwards". The coordinates themselves are quantised to integers and
delta-encoded, so each point is a step from the one before it, recovered
with a ``scale``/``translate`` transform carried on the topology.

Both ``make_choropleth`` and ``make_situation_map`` read vendored TopoJSON
atlases and both had grown their own decoder for it: two spellings of delta
decoding, two spellings of ring stitching, two places for the same off-by-one
to hide. The repo's README named the duplication in its own roadmap. This is
that single reader.

It stops at coordinates. What a caller does with a ring -- stitch it into a
shapely polygon and repair it, or project it straight to a path -- is the
caller's business, and the two generators legitimately differ there: one
needs validated geometry to clip and intersect against, the other only needs
points to draw.

Follows ``_svg.py``'s rule for extracted code: every function here is a
drop-in for the inline code it replaced, producing the identical bytes of
output, so factoring it out changes nothing about what renders.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def decode_arcs(topo: dict[str, Any]) -> list[list[tuple[float, float]]]:
    """Return every arc in ``topo``, delta-decoded to absolute (lon, lat).

    Parameters
    ----------
    topo : dict
        A parsed TopoJSON topology, carrying ``arcs`` and a ``transform``
        with ``scale`` and ``translate``.

    Returns
    -------
    list of list of (float, float)
        One list of points per arc, in the topology's own order, so a
        caller can index into it with the arc numbers a geometry carries.

    Examples
    --------
    >>> topo = {
    ...     "transform": {"scale": [0.5, 0.25], "translate": [10.0, 20.0]},
    ...     "arcs": [[[0, 0], [2, 4], [2, -4]]],
    ... }
    >>> decode_arcs(topo)
    [[(10.0, 20.0), (11.0, 21.0), (12.0, 20.0)]]
    """
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out: list[list[tuple[float, float]]] = []
    for arc in topo["arcs"]:
        x = y = 0
        points: list[tuple[float, float]] = []
        for dx, dy in arc:
            x += dx
            y += dy
            points.append((x * sx + tx, y * sy + ty))
        out.append(points)
    return out


def stitch_ring(
    indices: Iterable[int], arcs: Sequence[Sequence[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """Assemble one ring from the arc ``indices`` a TopoJSON geometry carries.

    A negative index ``i`` means arc ``~i`` traversed in reverse, which is
    how TopoJSON lets two neighbours share one boundary and still wind their
    own rings correctly. Consecutive arcs meet at a point they both hold, so
    every arc after the first contributes all but its own first point --
    omitting that is how a stitched ring grows a duplicate vertex at each
    join.

    Parameters
    ----------
    indices : iterable of int
        The arc indices for this ring, in order.
    arcs : sequence of sequence of (float, float)
        Decoded arcs, as returned by :func:`decode_arcs`.

    Returns
    -------
    list of (float, float)
        The ring's points in order.

    Examples
    --------
    >>> arcs = [[(0.0, 0.0), (1.0, 0.0)], [(1.0, 0.0), (1.0, 1.0)]]
    >>> stitch_ring([0, 1], arcs)
    [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]

    A negative index reverses its arc, and the join point is still shared
    only once:

    >>> stitch_ring([0, ~1], [[(0.0, 0.0), (1.0, 0.0)], [(2.0, 2.0), (1.0, 0.0)]])
    [(0.0, 0.0), (1.0, 0.0), (2.0, 2.0)]
    """
    ring: list[tuple[float, float]] = []
    for position, index in enumerate(indices):
        points = list(arcs[index]) if index >= 0 else list(arcs[~index])[::-1]
        ring.extend(points if position == 0 else points[1:])
    return ring
