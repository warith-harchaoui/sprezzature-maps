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

from typing import Any

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


CRITIQUE_SYSTEM = (
    "You look at a rendered map and judge it on five dimensions, each 0 to "
    "100, and you judge them by looking rather than by what you were told the "
    "map contains. A score you cannot justify from the image is a score you "
    "should put near 50 and explain in an issue. You answer only with JSON "
    "matching the schema you are given, and you never invent a kind of map."
)


def critique_prompt(
    kind_name: str,
    *,
    options: dict[str, Any] | None = None,
    title: str = "",
    profile: DataProfile | None = None,
    previous: str = "",
) -> str:
    """Ask for a judgement, with the context that makes one possible.

    Deliberately narrow, and the same discipline as
    :func:`choose_prompt`: the kind, the options it was rendered with, the
    user's title, and a description of the data. **Never a value.** A reader
    asked to judge whether a map is honest about its data does not need the
    data; it needs to know what the data is *shaped* like.

    The previous round's issues are passed through when there is one, because
    a critique that cannot see what was already said repeats it — which a loop
    reads as "no progress" and stops on.

    Parameters
    ----------
    kind_name : str
        The kind that was rendered.
    options : dict, optional
        The keyword options it was rendered with.
    title : str
        The title on the map, if any.
    profile : DataProfile, optional
        Headers, shapes and counts.
    previous : str
        Last round's issues, one per line.

    Returns
    -------
    str
    """
    kind = kinds.kind(kind_name)
    setting = ", ".join(f"{k}={v!r}" for k, v in sorted((options or {}).items())) or "(defaults)"
    shape = (
        f"{profile.rows} rows, columns: "
        + ", ".join(f"{c.name} ({c.looks_like})" for c in profile.columns)
        if profile and profile.columns
        else "(not described)"
    )
    tail = f"\n\nLast round you said:\n{previous}" if previous else ""
    return (
        f"This is a {kind.name}: {kind.description}\n"
        f"Rendered with: {setting}\n"
        f"Title on the map: {title!r}\n"
        f"The data behind it: {shape}\n\n"
        "Judge it on these five, 0 to 100 each:\n"
        "- readability: can the legend, the labels and the title be read at "
        "the size they are drawn?\n"
        "- colour_separation: can the classes be told apart, including by a "
        "reader with a colour vision deficiency?\n"
        "- geographic_honesty: does the frame hold the data without cropping "
        "it, and does the projection avoid lying about area or shape? This is "
        "the one a bar chart has no equivalent of — say what you see, not what "
        "you assume.\n"
        "- clarity: does the thing being shown stand out from the furniture — "
        "coastlines, relief, city labels?\n"
        "- answers_the_question: does this map answer what its title claims?\n\n"
        "Then a verdict: 'satisfied' if it can ship, 'needs_changes' if "
        "something fixable remains, 'blocked' if it cannot be read at all."
        f"{tail}"
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
