"""
The prompts, and the one rule they all obey: the catalogue of kinds is
generated from the registry, never typed out here.

A prompt that lists the kinds by hand is a fifth place that knows what this
package can draw, and the one place nothing compares against the others. It
would stay plausible after a fourth kind shipped — the model would simply never
offer it, and nothing would fail.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sprezzature_maps.kinds as kinds
from sprezzature_maps.data import CHOROPLETH_ROLES

from .schemas import DataProfile

CHOOSE_SYSTEM = (
    "You choose which map to draw. You answer only with JSON matching the "
    "schema you are given. You never invent a kind of map: if none of the "
    "listed kinds fits, pick the closest, say so in `why`, and set a low "
    "`confidence`. You never see the data itself, only a description of its "
    "columns, and you must not pretend otherwise."
)

READ_SYSTEM = (
    "You are shown a rendered map and you report what you can actually read "
    "off the image, not what you expect to be there. If you cannot tell what "
    "kind of map it is, leave `kind_seen` empty -- that is a useful answer. "
    "Read the title letter for letter, or leave it empty if there is none. "
    "You answer only with JSON matching the schema you are given."
)


def kind_catalogue() -> str:
    """The kinds, as a prompt fragment, straight from the registry.

    Returns
    -------
    str

    Examples
    --------
    >>> "choropleth" in kind_catalogue()
    True
    >>> all(k.name in kind_catalogue() for k in kinds.KINDS)
    True

    Notes
    -----
    The registry is reached through the module (``kinds.KINDS``) rather than
    bound at import. With ``from ... import KINDS`` this function keeps the
    tuple it saw first, so a test that adds a kind to check the catalogue
    follows it would pass while proving nothing.
    """
    lines = []
    for kind in kinds.KINDS:
        lines.append(
            f"- {kind.name}: {kind.description} It consumes {kind.data_shape} "
            f"(supplied with {kind.data_option})."
        )
    return "\n".join(lines)


def _profile_lines(profile: DataProfile) -> str:
    if not profile.columns:
        return "(no columns)"
    return "\n".join(
        f"- {c.name!r}: looks like {c.looks_like}, {c.distinct} distinct values, {c.nulls} empty"
        for c in profile.columns
    )


def choose_prompt(request: str, profile: DataProfile) -> str:
    """Ask which map to draw.

    Parameters
    ----------
    request : str
        The user's own words.
    profile : DataProfile
        Headers, shapes and counts. No cell value is included here, and that
        is enforced by the profile's own shape rather than by this function.

    Returns
    -------
    str
    """
    return (
        f"The kinds of map available:\n{kind_catalogue()}\n\n"
        f"A choropleth binds these roles to columns: {', '.join(CHOROPLETH_ROLES)}. "
        "The other kinds bind none; leave `roles` empty for them.\n\n"
        f"The dataset{f' ({profile.source})' if profile.source else ''} has "
        f"{profile.rows} rows and these columns:\n{_profile_lines(profile)}\n\n"
        f"What the person asked for:\n{request or '(they did not say)'}\n\n"
        "Choose one kind, bind the roles if the kind binds any, and say why in "
        "one or two sentences a person could disagree with."
    )


def read_prompt(asked_for: str = "") -> str:
    """Ask what the rendered map shows.

    Parameters
    ----------
    asked_for : str
        The kind that was requested, if the caller wants the comparison made
        explicit. Left empty deliberately when the point is an unprimed
        reading: naming the expected answer in the question is how a reader
        comes to report it whether or not it is there.

    Returns
    -------
    str
    """
    tail = (
        f"\n\nFor reference, this was rendered as a {asked_for}. Say what you "
        "see regardless; if it does not look like one, that is the finding."
        if asked_for
        else ""
    )
    return (
        "Look at this map and report what you can read off it: which of these "
        f"kinds it looks like, its title, whether there is a legend and whether "
        f"its labels are legible at the size they are drawn.\n\n{kind_catalogue()}"
        f"{tail}"
    )
