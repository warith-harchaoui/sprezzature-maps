"""
When the loop stops.

A loop that only stops when the picture is good never stops: a reader asked
the same question twice gives slightly different answers, and "slightly
different" looks like progress. So most of the conditions here are about
*lack* of progress rather than about success, and the one that does most of
the work is the repeated signature.

Issue signatures are severity plus a normalised message, so the same complaint
worded differently does not read as new. There is no zone: a real one would
need a reader that grounds its answer in image coordinates, which is not wired
up. That is a stated simplification, not a silent omission.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re

from sprezzature_maps.studio.assistant.schemas import MapIssue, MapReading

from .repair import issues_in

#: How many rounds of unattended repair before handing back to a person. Two,
#: for the same reason figures stops at two: a third round has, in practice,
#: either fixed nothing or started trading one complaint for another.
MAX_AUTO_REPAIRS = 2

#: A hard ceiling on rounds, independent of progress. Every round renders and
#: reads a map, so this is the bill as much as the logic.
MAX_ROUNDS = 4

_WHITESPACE = re.compile(r"\s+")


def issue_signature(issue: MapIssue) -> str:
    """A stable identity for one complaint.

    Examples
    --------
    >>> a = MapIssue(severity="blocking", what="The  legend   is ILLEGIBLE")
    >>> b = MapIssue(severity="blocking", what="the legend is illegible")
    >>> issue_signature(a) == issue_signature(b)
    True
    """
    normalised = _WHITESPACE.sub(" ", issue.what.strip().lower())[:80]
    return f"{issue.severity}:{normalised}"


def signature_set(reading: MapReading) -> frozenset[str]:
    """Every complaint in a reading, as identities.

    Examples
    --------
    >>> signature_set(MapReading())
    frozenset()
    """
    return frozenset(issue_signature(i) for i in issues_in(reading))


def has_blocking(reading: MapReading) -> bool:
    """Whether anything makes the map unreadable.

    Examples
    --------
    >>> has_blocking(MapReading(legend_present=True, legend_readable=False))
    True
    >>> has_blocking(MapReading())
    False
    """
    return any(i.severity == "blocking" for i in issues_in(reading))


def should_stop(
    *,
    reading: MapReading,
    asked_for: str,
    rounds_done: int,
    repairs_applied: int,
    previous_signatures: frozenset[str] | None,
    repairs_available: int,
    previous_score: int | None = None,
) -> tuple[bool, str | None]:
    """Whether to stop after this round, and why.

    Parameters
    ----------
    reading : MapReading
        This round's reading.
    asked_for : str
        The kind that was requested. When the reader names a *different*
        registered kind, no option change can fix it and the loop says so
        rather than spending its rounds on the wrong question.
    rounds_done : int
        Including this one.
    repairs_applied : int
        Unattended repairs applied so far.
    previous_signatures : frozenset of str or None
        Last round's complaints, or None on the first round.
    repairs_available : int
        How many repairs the proposer found that may be applied unattended.
    previous_score : int or None
        Last round's :attr:`~sprezzature_maps.studio.assistant.schemas.MapReading.score_total`.
        None on the first round, when there is nothing to have regressed from.

    Returns
    -------
    (stop, reason) : tuple
        `reason` is None only when the loop should continue.

    Examples
    --------
    >>> clean = MapReading(kind_seen="density", legend_present=True, legend_readable=True)
    >>> should_stop(reading=clean, asked_for="density", rounds_done=1,
    ...             repairs_applied=0, previous_signatures=None, repairs_available=0)
    (True, 'readable')
    """
    if reading.verdict == "blocked":
        return True, "blocked"
    if asked_for and reading.kind_seen and reading.kind_seen != asked_for:
        return True, "wrong_kind_rendered"
    if reading.verdict == "satisfied":
        return True, "satisfied"
    if not has_blocking(reading):
        return True, "readable"
    if previous_score is not None and reading.score_total < previous_score:
        # The rule the first version could not have: a reading with no numbers
        # in it cannot be compared with the one before it, so a loop built on
        # one cannot tell progress from change — it will trade a legible
        # legend for a cluttered coastline and call it a round.
        return True, "render_regressed"
    current = signature_set(reading)
    if previous_signatures is not None and current == previous_signatures:
        return True, "repeated_issue_signature"
    if repairs_available == 0:
        return True, "no_repair_available"
    if repairs_applied >= MAX_AUTO_REPAIRS:
        return True, "max_repairs_applied"
    if rounds_done >= MAX_ROUNDS:
        return True, "max_rounds"
    return False, None
