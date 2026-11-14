"""
sprezzature-maps: one call that renders any kind, from the registry.

Module summary
--------------
The three generators each named their data parameter for their own shape —
``make_choropleth(data=...)``, ``make_situation_map(config=...)``,
``make_density(points=...)`` — which is reasonable in isolation and leaves
every caller dispatching on the kind. The improve loop renders whichever kind
it is handed, so it would have been the place where that dispatch got written
a second time.

It is a table lookup instead:
:attr:`sprezzature_maps.kinds.MapKind.payload_keyword` records the keyword and
:attr:`~sprezzature_maps.kinds.MapKind.renderer` the function, so this module
has no ``if kind ==`` in it at all. A renamed parameter fails
``tests/test_every_surface_carries_every_kind.py`` — which introspects the
real signature — rather than failing a render.

Interface-free on purpose
-------------------------
Nothing here imports a web framework, so any interface can sit on top of it
without the engine knowing which.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import sprezzature_maps
from sprezzature_maps.kinds import kind as lookup_kind

#: How much room to leave around the points when a bounding box is inferred,
#: as a fraction of the span. Without it the outermost events sit exactly on
#: the edge, where the binning has half a cell of neighbours and the field
#: fades for a reason that is in the frame rather than in the data.
BBOX_MARGIN: float = 0.08

#: The smallest span an inferred box may have, in degrees. One event, or
#: several at one address, gives a zero-extent box that no projection can
#: scale; roughly ten kilometres is the smallest frame in which a single
#: luminous cell reads as a place rather than as a rendering artefact.
BBOX_MINIMUM_SPAN: float = 0.1


def infer_bbox(points: Sequence[Sequence[float]]) -> tuple[float, float, float, float]:
    """A bounding box around *points*, as ``(west, south, east, north)``.

    Why the command line infers one
    -------------------------------
    ``make_density``'s own default box is the continental United States, which
    is the right default for a generator with a demo dataset and no way to ask.
    It is the wrong one for a panel somebody pastes a file into: the first
    thing tried while writing this module was three European cities, and the
    answer was ``ValueError: no point fell inside the bbox; nothing to draw``.
    The message is accurate and the experience is a dead end — the data was
    fine and the frame was somewhere else.

    So this frames what it was given, and an explicit ``bbox`` still
    wins. ``make-map density --points`` relies on it, having no ``--bbox`` to
    ask with. The generator keeps its default: the library and the HTTP route
    can both state a box.

    Parameters
    ----------
    points : sequence of sequence of float
        ``[[lon, lat], ...]``, as :func:`sprezzature_maps.data.read_density_points`
        returns.

    Returns
    -------
    tuple of float
        ``(west, south, east, north)``, widened by :data:`BBOX_MARGIN` and
        never narrower than :data:`BBOX_MINIMUM_SPAN` in either direction.

    Raises
    ------
    ValueError
        When *points* is empty. A box around nothing would be a frame with no
        contents, and the caller is better told which of the two is missing.

    Examples
    --------
    >>> infer_bbox([[2.0, 48.0], [3.0, 49.0]])
    (1.92, 47.92, 3.08, 49.08)
    >>> # one point: widened to the minimum span rather than left at zero
    >>> infer_bbox([[2.0, 48.0]])
    (1.95, 47.95, 2.05, 48.05)
    """
    if not points:
        raise ValueError("cannot infer a bounding box from no points")
    longitudes = [float(point[0]) for point in points]
    latitudes = [float(point[1]) for point in points]
    west, east = min(longitudes), max(longitudes)
    south, north = min(latitudes), max(latitudes)

    def _widen(low: float, high: float) -> tuple[float, float]:
        span = high - low
        if span < BBOX_MINIMUM_SPAN:
            middle = (low + high) / 2.0
            half = BBOX_MINIMUM_SPAN / 2.0
            return round(middle - half, 10), round(middle + half, 10)
        pad = span * BBOX_MARGIN
        return round(low - pad, 10), round(high + pad, 10)

    west, east = _widen(west, east)
    south, north = _widen(south, north)
    return west, south, east, north


def render(
    kind_name: str,
    payload: Any = None,
    *,
    out: str | Path,
    title: str | None = None,
    **options: Any,
) -> Path:
    """Render one map of any kind, dispatching through the registry.

    Parameters
    ----------
    kind_name : str
        A kind identifier, hyphens or underscores (see
        :func:`sprezzature_maps.kinds.kind`).
    payload : object, optional
        The data, in whichever shape the kind consumes — rows, a config
        mapping, or a list of positions. ``None`` renders the kind's built-in
        demo, which is what every generator does when handed nothing and what
        gives a caller something to show before a file is chosen.
    out : str or pathlib.Path
        Where to write. The extension chooses the format, as on the command
        line.
    title : str, optional
        Overrides the kind's own default title. Left out rather than passed
        as ``None``: each generator has its own default and passing ``None``
        would replace a sentence with nothing.
    **options
        Passed through to the generator — ``bins`` for a density map,
        ``diverging`` for a choropleth. Not validated here on purpose: the
        generator owns its own options and is the only thing that can say
        which it has.

        One is filled in when it is absent: a ``points`` kind handed a payload
        and no ``bbox`` is framed by :func:`infer_bbox`, because the
        generator's own default box is the continental United States and a
        panel somebody pastes European events into would otherwise answer
        "nothing to draw" about data that is perfectly fine. An explicit
        ``bbox`` always wins.

    Returns
    -------
    pathlib.Path
        The written file, as the generator reports it.

    Raises
    ------
    KeyError
        When no kind answers to *kind_name*, naming the ones that do.

    Examples
    --------
    >>> from sprezzature_maps.kinds import kind
    >>> kind("density").payload_keyword
    'points'
    """
    entry = lookup_kind(kind_name)
    generator = getattr(sprezzature_maps, entry.renderer)
    arguments: dict[str, Any] = {"out": out, **options}
    if entry.data_shape == "points" and payload and "bbox" not in options:
        # Frame what was given. See `infer_bbox` for why this belongs here
        # and not in the generator.
        arguments["bbox"] = infer_bbox(payload)
    if payload is not None:
        arguments[entry.payload_keyword] = payload
    if title is not None:
        arguments["title"] = title
    return generator(**arguments)
