"""
Turn what a reader said about a picture into a change to a keyword.

The translation is a table, not a model. A language model is already in the
loop once — reading the rendered map — and letting it also choose the keyword
and the value would put an unvalidated string into a renderer call. So the
critique's *words* are matched against cues, and the change comes from
:mod:`sprezzature_maps.studio.ralph.policy`, which knows the ladder and where
it ends.

The cues are deliberately the words a reader uses, not a taxonomy: "illegible",
"too small", "overlapping". A critique that says something no rule matches
produces no repair, which is an honest outcome and a stopping condition — not a
reason to guess.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sprezzature_maps.studio.assistant.schemas import MapIssue, MapReading

from .policy import NoRoomLeft, default_for, is_safe, next_value, requires_confirmation


@dataclass(frozen=True)
class Repair:
    """One keyword change, ready to be applied.

    Parameters
    ----------
    option : str
        The declared option to change.
    value : Any
        What to set it to. Already resolved through the ladder, so a caller
        passes it straight to the renderer.
    direction : str
        The move that produced it, kept for the record a person reads.
    because : str
        The issue it answers, in the reader's own words.
    safe : bool
        Whether the loop may apply it unattended. False means offer it.
    """

    option: str
    value: Any
    direction: str
    because: str
    safe: bool


@dataclass(frozen=True)
class RepairRule:
    """A cue in a critique, and the move it calls for.

    Parameters
    ----------
    cues : tuple of str
        Lowercase substrings. Any one of them matching the issue text fires
        the rule.
    option : str
        The declared option to move.
    direction : str
        One of :data:`sprezzature_maps.studio.ralph.policy.DIRECTIONS`.
    """

    cues: tuple[str, ...]
    option: str
    direction: str


#: The table, most specific first. Several rules may name the same option; the
#: proposer keeps the first that can actually move, so a rule that has run out
#: of ladder does not block a later one.
RULES: tuple[RepairRule, ...] = (
    RepairRule(
        cues=("illegible", "unreadable", "too small", "tiny", "hard to read", "cannot read"),
        option="width",
        direction="up",
    ),
    RepairRule(
        cues=("cramped", "crowds", "squeezed", "no room", "cut off at the bottom"),
        option="height",
        direction="up",
    ),
    RepairRule(
        cues=("cluttered", "too many labels", "overlapping", "labels collide", "busy with text"),
        option="cities",
        direction="off",
    ),
    RepairRule(
        cues=("too many lines", "busy", "noisy background"),
        option="rivers",
        direction="off",
    ),
    RepairRule(
        cues=("terrain", "relief", "shading competes", "background competes"),
        option="relief",
        direction="off",
    ),
    RepairRule(
        cues=("blocky", "pixelated", "coarse", "chunky"),
        option="bins",
        direction="up",
    ),
    RepairRule(
        cues=("speckled", "noisy", "grainy", "too fine"),
        option="bins",
        direction="down",
    ),
    RepairRule(
        cues=("jagged", "ragged coastline", "angular"),
        option="simplify",
        direction="down",
    ),
    RepairRule(
        cues=("empty space at the bottom", "antarctica"),
        option="antarctica",
        direction="off",
    ),
    # Below here: declared, matched, and never applied unattended, because each
    # one can change what the map says about the data.
    RepairRule(
        cues=("indistinguishable", "same colour", "same color", "bands do not separate"),
        option="method",
        direction="next",
    ),
    RepairRule(
        cues=("too many colour steps", "too many color steps", "too many bands"),
        option="classes",
        direction="down",
    ),
    RepairRule(
        cues=("too few bands", "not enough steps", "all one colour", "all one color"),
        option="classes",
        direction="up",
    ),
)


def _issue_text(issue: MapIssue) -> str:
    return f"{issue.what} {issue.fix}".lower()


def _structural_issues(reading: MapReading) -> list[MapIssue]:
    """Findings that come from the reading's own fields rather than its prose.

    A reader who ticks "legend present, not readable" has said something
    actionable without writing a sentence about it. Leaving that to the prose
    would make the loop depend on wording it does not control.
    """
    found: list[MapIssue] = []
    if reading.legend_present and not reading.legend_readable:
        found.append(
            MapIssue(
                severity="blocking",
                what="the legend is present but its labels are illegible at this size",
                fix="render the map larger",
            )
        )
    return found


def issues_in(reading: MapReading) -> list[MapIssue]:
    """Every issue to act on, blocking first, structural ones included.

    Examples
    --------
    >>> reading = MapReading(legend_present=True, legend_readable=False)
    >>> [i.severity for i in issues_in(reading)]
    ['blocking']
    >>> issues_in(MapReading(legend_present=True, legend_readable=True))
    []
    """
    everything = [*reading.issues, *_structural_issues(reading)]
    return sorted(everything, key=lambda i: 0 if i.severity == "blocking" else 1)


def propose_repairs(
    reading: MapReading,
    kind_name: str,
    current: dict[str, Any] | None = None,
    *,
    include_unsafe: bool = True,
) -> list[Repair]:
    """Every change the critique calls for, that this kind can actually make.

    Parameters
    ----------
    reading : MapReading
        What was read off the rendered map.
    kind_name : str
        The kind that was rendered. An option the kind's renderer does not
        take is skipped — changing it would land in ``**kwargs`` and do
        nothing, which a loop would read as "the repair did not help".
    current : dict, optional
        The options as currently set. Anything absent is resolved from the
        renderer's real default, which differs by kind.
    include_unsafe : bool
        Whether to also propose the changes that need a person. True by
        default: a caller that is going to *offer* them needs to see them, and
        :attr:`Repair.safe` says which is which.

    Returns
    -------
    list of Repair
        At most one per option, in the order the issues were ranked.

    Examples
    --------
    >>> reading = MapReading(
    ...     legend_present=True,
    ...     legend_readable=False,
    ...     issues=[MapIssue(severity="notable", what="the map is cluttered with labels")],
    ... )
    >>> [(r.option, r.value, r.safe) for r in propose_repairs(reading, "choropleth")]
    [('width', 1000, True), ('cities', False, True)]
    """
    settings = dict(current or {})
    proposed: list[Repair] = []
    taken: set[str] = set()
    for issue in issues_in(reading):
        text = _issue_text(issue)
        for rule in RULES:
            if rule.option in taken or not any(cue in text for cue in rule.cues):
                continue
            safe = is_safe(rule.option, kind_name)
            if not safe and not requires_confirmation(rule.option, kind_name):
                continue  # this kind's renderer does not take it at all
            if not safe and not include_unsafe:
                continue
            at = settings.get(rule.option, _default(kind_name, rule.option))
            try:
                value = next_value(rule.option, at, rule.direction)
            except (NoRoomLeft, ValueError):
                continue
            proposed.append(
                Repair(
                    option=rule.option,
                    value=value,
                    direction=rule.direction,
                    because=issue.what,
                    safe=safe,
                )
            )
            taken.add(rule.option)
    return proposed


def _default(kind_name: str, name: str) -> Any:
    try:
        return default_for(kind_name, name)
    except KeyError:
        return None


def apply_safe(repairs: list[Repair], current: dict[str, Any] | None = None) -> dict[str, Any]:
    """The options after applying only the repairs a loop may apply alone.

    Parameters
    ----------
    repairs : list of Repair
    current : dict, optional

    Returns
    -------
    dict
        A new dict; `current` is not modified.

    Examples
    --------
    >>> applied = apply_safe(
    ...     [Repair("width", 1400, "up", "small text", True),
    ...      Repair("method", "jenks", "next", "bands alike", False)],
    ...     {"width": 745},
    ... )
    >>> applied
    {'width': 1400}
    """
    settings = dict(current or {})
    for repair in repairs:
        if repair.safe:
            settings[repair.option] = repair.value
    return settings
