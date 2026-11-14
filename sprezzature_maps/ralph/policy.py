"""
What a repair is allowed to do, and what the next value is.

Two separate questions, kept apart on purpose. *May* this option be changed
without asking — which :mod:`sprezzature_maps.options` answers, and which is
about whether the change can alter what the map says about the data. And *what*
would changing it mean — which is this module, because "make it wider" has to
become a number, from a ladder somebody chose, with an end.

The ladder matters more than it looks. A loop that doubles a width each round
reaches 6000 pixels in three rounds and renders something nobody asked for; one
that adds ten pixels never changes anything a reader would notice. The steps in
:data:`sprezzature_maps.options.OPTIONS` are the sizes these generators were
built and tested at, and running out of them is a reason to stop.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from typing import Any

from sprezzature_maps.options import MapOption, option, options_for, safe_options_for

#: The directions a repair can ask for.
DIRECTIONS: tuple[str, ...] = ("up", "down", "on", "off", "next")


class NoRoomLeft(RuntimeError):
    """Raised when an option cannot move further in the asked direction.

    Caught by the proposer, which drops that repair. It is an ordinary outcome
    — the ladder has an end — and not an error in the usual sense, which is
    why it carries the option and the value it was already at.
    """

    def __init__(self, name: str, current: Any, direction: str) -> None:
        super().__init__(f"{name} is already at {current!r}; nothing {direction} from there")
        self.name = name
        self.current = current
        self.direction = direction


def is_safe(name: str, kind_name: str) -> bool:
    """Whether an automatic loop may change `name` on this kind of map.

    Both halves are needed: an option can be safe in general and absent from
    this kind's renderer, in which case changing it would do nothing at all.

    Examples
    --------
    >>> is_safe("width", "density")
    True
    >>> is_safe("bins", "choropleth")
    False
    >>> is_safe("method", "choropleth")
    False
    """
    return any(o.name == name for o in safe_options_for(kind_name))


def requires_confirmation(name: str, kind_name: str) -> bool:
    """Whether the kind accepts it but a person should decide.

    Examples
    --------
    >>> requires_confirmation("method", "choropleth")
    True
    >>> requires_confirmation("width", "choropleth")
    False
    >>> requires_confirmation("bins", "choropleth")
    False
    """
    return any(o.name == name and not o.safe for o in options_for(kind_name))


def default_for(kind_name: str, name: str) -> Any:
    """What the named kind's renderer leaves the option at when nobody sets it.

    Read from the live signature, not recorded in
    :mod:`sprezzature_maps.options`, and for a reason that showed up as a bug
    the first time this was written: ``width`` defaults to 745 on a choropleth
    and to 1000 on a density map. A single default stored beside the option
    would have been wrong for one of them, and wrong in the direction that
    makes a loop's first repair shrink a map it was asked to enlarge.

    Parameters
    ----------
    kind_name : str
        A registered kind.
    name : str
        A declared option the kind accepts.

    Returns
    -------
    Any
        The default, which may be None — ``classes`` defaults to no
        classification at all.

    Raises
    ------
    KeyError
        If the renderer does not take that keyword.

    Examples
    --------
    >>> default_for("choropleth", "width")
    745
    >>> default_for("density", "width")
    1000
    >>> default_for("choropleth", "classes") is None
    True
    """
    import inspect

    from sprezzature_maps import _load_script
    from sprezzature_maps.kinds import kind

    resolved = kind(kind_name)
    renderer = getattr(_load_script(resolved.renderer), resolved.renderer)
    parameters = inspect.signature(renderer).parameters
    if name not in parameters:
        raise KeyError(f"{resolved.renderer} takes no keyword {name!r}")
    found = parameters[name].default
    return None if found is inspect.Parameter.empty else found


def _numeric_step(declared: MapOption, current: Any, direction: str) -> Any:
    ladder = sorted(declared.steps) or sorted(
        v for v in (declared.low, declared.high) if v is not None
    )
    if not ladder:
        raise NoRoomLeft(declared.name, current, direction)
    if current is None:
        # The option is unset, so the first move *sets* it rather than climbing
        # from somewhere. `classes` is the real case: it defaults to no
        # classification at all, and "more classes" from nothing means three.
        return int(ladder[0]) if declared.shape == "integer" else ladder[0] if direction == "up" \
            else (int(ladder[-1]) if declared.shape == "integer" else ladder[-1])
    try:
        value = float(current)
    except (TypeError, ValueError) as exc:
        raise NoRoomLeft(declared.name, current, direction) from exc
    candidates = [s for s in ladder if s > value] if direction == "up" else [
        s for s in reversed(ladder) if s < value
    ]
    if not candidates:
        raise NoRoomLeft(declared.name, current, direction)
    chosen = candidates[0]
    return int(chosen) if declared.shape == "integer" else chosen


def next_value(name: str, current: Any, direction: str) -> Any:
    """The value `name` takes when moved `direction` from `current`.

    Parameters
    ----------
    name : str
        A declared option.
    current : Any
        What it is set to now, or None for the renderer's own default.
    direction : str
        One of :data:`DIRECTIONS`.

    Returns
    -------
    Any

    Raises
    ------
    NoRoomLeft
        When the ladder has no further rung in that direction, which is how a
        loop learns it has nothing left to try.
    ValueError
        For a direction that makes no sense for the option's shape — turning a
        width "off", for instance. A loop that asks for that has a bug, and
        silently doing nothing would hide it.

    Examples
    --------
    >>> next_value("width", 745, "up")
    1000
    >>> next_value("width", default_for("density", "width"), "up")
    1400
    >>> next_value("classes", None, "up")   # unset: the first move sets it
    3
    >>> try:                                  # the ladder has an end
    ...     next_value("bins", 320, "up")
    ... except NoRoomLeft as end:
    ...     print(end)
    bins is already at 320; nothing up from there
    >>> next_value("relief", True, "off")
    False
    >>> next_value("method", "quantile", "next")
    'equal'
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {', '.join(DIRECTIONS)}, got {direction!r}")
    declared = option(name)
    if declared.shape == "boolean":
        if direction not in ("on", "off"):
            raise ValueError(f"{name} is a boolean; {direction!r} means nothing for it")
        wanted = direction == "on"
        if current is not None and bool(current) == wanted:
            raise NoRoomLeft(name, current, direction)
        return wanted
    if declared.shape == "choice":
        if direction != "next":
            raise ValueError(f"{name} is a choice; ask for 'next', not {direction!r}")
        choices = list(declared.choices)
        if current is None:
            return choices[0]
        if current not in choices:
            return choices[0]
        index = choices.index(current) + 1
        if index >= len(choices):
            raise NoRoomLeft(name, current, direction)
        return choices[index]
    if declared.shape in ("integer", "number"):
        if direction not in ("up", "down"):
            raise ValueError(f"{name} is numeric; {direction!r} means nothing for it")
        return _numeric_step(declared, current, direction)
    raise ValueError(f"{name} has shape {declared.shape!r}, which no direction moves")
