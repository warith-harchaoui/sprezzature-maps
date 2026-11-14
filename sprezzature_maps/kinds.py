"""
sprezzature-maps: the one list of map kinds every surface reads.

Module summary
--------------
Three kinds ship here — ``choropleth``, ``situation_map`` and ``density`` —
and before this module each surface said so separately. Four independent
enumerations, written by hand:

* ``cli.py``'s ``list`` command hard-coded ``("choropleth",
  "situation_map")``;
* ``gui.py``'s ``_TILES`` listed all three;
* ``api.py`` declared three routes;
* ``TRIGGERS.md`` routed on all three.

**Three of the four were right, which is the problem.** ``density`` was born
in this repository after `choropleth` and `situation_map` were extracted from
`sprezzature-figures`, so every list written before it had to be revisited by
hand, and the one nobody revisited is the one a reader asks directly:
``sprezzature-maps list`` answered **two kinds of three**. A reader asking the
tool what it can draw was told something false, and no test could notice —
there was nothing to compare the answer against.

So: one list, here, and every surface derives from it.
:mod:`tests.test_every_surface_carries_every_kind` compares this registry
against the CLI's real commands, the API's real routes, the gallery's real
tiles and the package's real exports, so a fourth kind cannot be half-added.

Why a registry and not a plain tuple of names
---------------------------------------------
Because the surfaces need different facts about the same kind, and a tuple of
names would leave each one to supply the rest — which is how the four lists
diverged in the first place. The gallery needs a title and a sentence of
prose; the HTTP surface needs its route; the command line needs its command
name; an editor needs all of it at once, which is what prompted writing this
down.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapKind:
    """One kind of map this package renders, and how each surface names it.

    Parameters
    ----------
    name : str
        The kind's identifier, as the library and ``list`` spell it
        (``snake_case``, e.g. ``situation_map``).
    label : str
        Human title, for a gallery tile or a menu.
    description : str
        One paragraph saying what the kind is *for*, in the gallery's voice.
        Moved here from ``gui.py``'s ``_TILES`` rather than rewritten: the
        prose was already reviewed, and rewriting it would have made this
        change look larger than it is.
    command : str
        The ``sprezzature-maps`` sub-command that renders it. Hyphenated where
        the CLI hyphenates, which is not always :attr:`name` — ``situation_map``
        answers to both ``situation-map`` and ``situation_map``.
    endpoint : str
        The HTTP route that renders it, as ``api.py`` declares it.
    renderer : str
        The name this package exports for it, e.g. ``make_choropleth``.
    data_shape : str
        What the kind *consumes*, which is the fact a chart library never has
        to carry: one of ``"rows"``, ``"config"`` or ``"points"``. A
        choropleth takes per-territory rows bound through roles, a situation
        map takes a region configuration with no table in it, and a density
        map takes a bare list of positions. Added when an editor needed to
        choose an input panel — one list, so an editor does not become the
        sixth place that knows which kind eats what.
    data_option : str
        The command-line option that supplies it, for an error message or a
        hint that has to name the real flag.
    payload_keyword : str
        The keyword argument :attr:`renderer` takes the data under — ``data``,
        ``config`` or ``points``. The three generators each named it for their
        own shape, which is reasonable in isolation and leaves any caller
        dispatching on the kind. Recorded here so the dispatch is a table
        lookup, and so a renamed parameter fails a test instead of a render.
    """

    name: str
    label: str
    description: str
    command: str
    endpoint: str
    renderer: str
    data_shape: str
    data_option: str
    payload_keyword: str


#: Every kind, in the order the gallery shows them: the two that came from
#: `sprezzature-figures` first, then the one born here.
KINDS: tuple[MapKind, ...] = (
    MapKind(
        name="choropleth",
        label="Choropleth",
        description=(
            "World map, one value per country on a perceptual OKLCH ramp "
            "(sequential or auto-detected diverging), Equal Earth projection "
            "so colored area is not lying about country size."
        ),
        command="choropleth",
        endpoint="/v1/choropleth",
        renderer="make_choropleth",
        data_shape="rows",
        data_option="--data",
        payload_keyword="data",
    ),
    MapKind(
        name="situation_map",
        label="Situation map",
        description=(
            "Layered areas-of-control plate for any region: real national "
            "outlines, bathymetry halo, classed pastel zones, dual-unit "
            "scale bar -- the geopolitics-desk look, parameterized."
        ),
        command="situation-map",
        endpoint="/v1/situation-map",
        renderer="make_situation_map",
        data_shape="config",
        data_option="--config",
        payload_keyword="config",
    ),
    MapKind(
        name="density",
        label="Density",
        description=(
            "An accumulation map: where events fell, rather than a value per "
            "territory. Points are binned into a luminous field and the "
            "geography emerges from the data rather than being drawn under it."
        ),
        command="density",
        endpoint="/v1/density",
        renderer="make_density",
        data_shape="points",
        data_option="--points",
        payload_keyword="points",
    ),
)


#: Every shape a kind can consume. Named so a reader of
#: :attr:`MapKind.data_shape` does not have to collect the set by eye, and so
#: :mod:`tests.test_every_surface_carries_every_kind` can refuse a typo in one.
DATA_SHAPES: frozenset[str] = frozenset({"rows", "config", "points"})


def kind_names() -> tuple[str, ...]:
    """Every kind's identifier, in registry order.

    Returns
    -------
    tuple of str
        What ``sprezzature-maps list`` prints, one per line.

    Examples
    --------
    >>> kind_names()
    ('choropleth', 'situation_map', 'density')
    """
    return tuple(kind.name for kind in KINDS)


def kind(name: str) -> MapKind:
    """Look one kind up by identifier.

    Parameters
    ----------
    name : str
        A kind identifier. Underscores and hyphens are accepted
        interchangeably, because the command line spells ``situation_map``
        both ways and a caller should not have to know which.

    Returns
    -------
    MapKind
        The registry entry.

    Raises
    ------
    KeyError
        When no kind answers to that name, naming the ones that do rather
        than leaving the caller to guess.

    Examples
    --------
    >>> kind("situation-map").label
    'Situation map'
    """
    wanted = name.strip().lower().replace("-", "_")
    for entry in KINDS:
        if entry.name == wanted or entry.command.replace("-", "_") == wanted:
            return entry
    raise KeyError(f"no map kind named {name!r}; this package renders {', '.join(kind_names())}")
