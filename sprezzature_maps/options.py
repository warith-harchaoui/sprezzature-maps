"""
The rendering options, declared — and which of them a loop may change alone.

Why this exists
---------------
``kinds.py`` says what each kind of map *is* and what it consumes. It says
nothing about the knobs, and the knobs are where an automatic loop does its
work: a critique that reads "the legend is illegible" is only actionable if
something knows that ``width`` exists, that it is an integer, that 745 is the
default and 1600 is not absurd.

Without a declaration that lives in one place, a loop ends up carrying its own
list — a sixth place that knows what the renderers accept, and the one place
nothing compares against the signatures. The failure is quiet and specific: a
renamed keyword leaves the loop proposing a change that raises ``TypeError``
three layers down, or worse, that is accepted into ``**kwargs`` and ignored.

So every entry below names a real keyword of a real renderer, and
``tests/test_the_options_are_the_renderers_own.py`` checks that against the
live signatures rather than against this prose.

Safe, and not safe
------------------
:attr:`MapOption.safe` marks the options an automatic loop may change without
asking. The line is not "harmless" — it is **whether the change can alter what
the map says about the data**. Making a map wider cannot. Changing the
classification method can: the same numbers, cut differently, put a country in
a different colour band, and a reader who trusts the picture is misled by a
repair nobody confirmed.

That is why ``method``, ``classes``, ``breaks``, ``diverging`` and ``per_area``
are declared and *not* safe. They are the ones a person should be offered, with
the picture, and never applied silently.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapOption:
    """One keyword a renderer accepts.

    Parameters
    ----------
    name : str
        The keyword, spelled as the renderer spells it.
    kinds : tuple of str
        The kinds that accept it. Checked against the real signatures.
    shape : str
        ``"integer"``, ``"number"``, ``"boolean"``, ``"choice"`` or ``"text"``.
    choices : tuple of str
        The permitted values when :attr:`shape` is ``"choice"``.
    low, high : float or None
        Bounds for the numeric shapes, inclusive. A loop that may widen a map
        needs to know where to stop; 745 to 2400 pixels is the range these
        renderers were built and tested against.
    safe : bool
        Whether an automatic loop may change it with nobody watching. False
        for anything that can change what the map says about the data.
    why : str
        What changing it is *for*, in the words a critique would use. This is
        the text a repair policy matches against, so it is part of the data,
        not a comment.
    """

    name: str
    kinds: tuple[str, ...]
    shape: str
    choices: tuple[str, ...] = ()
    low: float | None = None
    high: float | None = None
    safe: bool = False
    why: str = ""
    steps: tuple[float, ...] = field(default_factory=tuple)


def _classification_choices() -> tuple[str, ...]:
    """The class-break methods, read from where they are defined.

    :func:`sprezzature_maps.classification_methods` reads them out of
    ``scripts/_classify.py``, and its own docstring is the reason this is a
    call and not a literal: "a list repeated is a list that drifts: whichever
    copy a reader happens to hold becomes the set of methods they believe
    exists."

    Written after doing precisely that — this registry first offered
    ``equal-interval`` and ``std-dev``, neither of which exists, and omitted
    ``headtail``, which does.

    The import is local so that importing this module cannot depend on the
    package's ``__init__`` having finished; nothing in ``__init__`` imports
    this module, and that is the condition under which this stays true.
    """
    from sprezzature_maps import classification_methods

    return classification_methods()


#: Every option a loop or an editor may touch, in reporting order.
#:
#: Not every keyword the renderers accept: ``data``, ``points``, ``config`` and
#: ``out`` are the call itself, ``mode`` and ``provenance`` are output-format
#: decisions a caller makes once, and ``title``/``subtitle``/``caption`` are
#: the user's own words. :data:`NOT_AN_OPTION` names them all, so the test
#: below can insist the two sets together account for every keyword — an
#: omission has to be chosen, not merely overlooked.
OPTIONS: tuple[MapOption, ...] = (
    MapOption(
        name="width",
        kinds=("choropleth", "density"),
        shape="integer",
        low=600,
        high=2400,
        safe=True,
        steps=(745, 1000, 1400, 1800, 2400),
        why="small text, illegible legend, labels too close to read",
    ),
    MapOption(
        name="height",
        kinds=("choropleth",),
        shape="integer",
        low=340,
        high=1400,
        safe=True,
        steps=(420, 560, 790, 1010, 1350),
        why="the map is cramped vertically, the legend crowds the frame",
    ),
    MapOption(
        name="relief",
        kinds=("choropleth",),
        shape="boolean",
        safe=True,
        why="busy background, the colour bands are hard to separate from the terrain",
    ),
    MapOption(
        name="cities",
        kinds=("choropleth",),
        shape="boolean",
        safe=True,
        why="too many labels, clutter, overlapping text",
    ),
    MapOption(
        name="rivers",
        kinds=("choropleth",),
        shape="boolean",
        safe=True,
        why="too many lines, the map is busy",
    ),
    MapOption(
        name="antarctica",
        kinds=("choropleth",),
        shape="boolean",
        safe=True,
        why="a large empty mass at the bottom draws the eye and carries no data",
    ),
    MapOption(
        name="simplify",
        kinds=("choropleth",),
        shape="number",
        low=0.0,
        high=1.0,
        safe=True,
        steps=(0.0, 0.1, 0.2, 0.4),
        why="coastlines look jagged, or the file is heavier than it needs to be",
    ),
    MapOption(
        name="bins",
        kinds=("density",),
        shape="integer",
        low=20,
        high=400,
        safe=True,
        steps=(60, 120, 200, 320),
        why="the surface looks blocky, or so fine it reads as noise",
    ),
    # ---------------------------------------------------- not applied silently
    MapOption(
        name="method",
        kinds=("choropleth",),
        shape="choice",
        choices=_classification_choices(),
        safe=False,
        why="the colour bands do not separate the values the way the data is shaped",
    ),
    MapOption(
        name="classes",
        kinds=("choropleth",),
        shape="integer",
        low=3,
        high=9,
        safe=False,
        steps=(3, 5, 7, 9),
        why="too many or too few colour steps to tell apart",
    ),
    MapOption(
        name="breaks",
        kinds=("choropleth",),
        shape="text",
        safe=False,
        why="the class boundaries should fall at specific values",
    ),
    MapOption(
        name="diverging",
        kinds=("choropleth",),
        shape="boolean",
        safe=False,
        why="the values run either side of a meaningful middle, or they do not",
    ),
    MapOption(
        name="per_area",
        kinds=("density",),
        shape="boolean",
        safe=False,
        why="counts per cell against counts per unit of area — a different quantity",
    ),
    MapOption(
        name="bbox",
        kinds=("density",),
        shape="text",
        safe=False,
        why="the frame shows the wrong part of the world, or clips the data",
    ),
    MapOption(
        name="region",
        kinds=("density",),
        shape="text",
        safe=False,
        why="a named region instead of an explicit frame",
    ),
)

#: Renderer keywords that are deliberately not options.
#:
#: Named rather than left out, so :data:`OPTIONS` plus this set can be required
#: to account for every keyword the renderers take. A new keyword then has to
#: be classified by somebody, instead of being invisible to an editor and to
#: every loop.
NOT_AN_OPTION: dict[str, str] = {
    "data": "the call itself: the rows or the configuration being drawn",
    "points": "the call itself: the positions being drawn",
    "config": "the call itself: the situation configuration being drawn",
    "out": "where the file goes, which the caller owns",
    "mode": "self-contained or linked output; an output-format decision",
    "provenance": "whether to stamp the inputs into the file; a policy, not a look",
    "title": "the user's own words",
    "subtitle": "the user's own words",
    "caption": "the user's own words",
    # Declared here after being declared an *option* first, which was wrong in
    # the exact way this module warns about. `make_choropleth` accepts it and
    # discards it -- `_ = accessibility`, with a docstring that says so:
    # "accepted for CLI parity but a documented no-op", because both ramps are
    # mono-per-side hue scales where magnitude reads by lightness alone, and
    # that is verified with `_geo_colors.simulate_cvd_hex` rather than
    # asserted. A loop offered this as a repair would change it, see no
    # difference, and have no way to tell "it did not help" from "it did
    # nothing".
    "accessibility": "accepted for CLI parity and discarded; the ramps are "
                     "colour-vision-deficiency-safe by construction",
}


def options_for(kind_name: str) -> tuple[MapOption, ...]:
    """Every option the named kind accepts.

    Parameters
    ----------
    kind_name : str
        A kind identifier, underscores as :mod:`sprezzature_maps.kinds` spells
        them.

    Returns
    -------
    tuple of MapOption

    Examples
    --------
    >>> [o.name for o in options_for("density")]
    ['width', 'bins', 'per_area', 'bbox', 'region']
    >>> options_for("situation_map")
    ()
    """
    return tuple(o for o in OPTIONS if kind_name in o.kinds)


def safe_options_for(kind_name: str) -> tuple[MapOption, ...]:
    """The subset an automatic loop may change on its own.

    Examples
    --------
    >>> [o.name for o in safe_options_for("density")]
    ['width', 'bins']
    >>> all(o.safe for o in safe_options_for("choropleth"))
    True
    """
    return tuple(o for o in options_for(kind_name) if o.safe)


def option(name: str) -> MapOption:
    """One option by name.

    Raises
    ------
    KeyError
        With the known names listed, because a caller that got this wrong is
        usually one keyword away from right.

    Examples
    --------
    >>> option("bins").shape
    'integer'
    """
    for candidate in OPTIONS:
        if candidate.name == name:
            return candidate
    raise KeyError(f"no option named {name!r}; the options are {', '.join(o.name for o in OPTIONS)}")
