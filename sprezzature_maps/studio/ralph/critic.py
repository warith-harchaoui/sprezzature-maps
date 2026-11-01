"""
Ask a vision model to judge a rendered map, not merely to describe it.

The loop's first version asked what the picture *showed* — the kind, the
title, whether the legend was legible — and acted on the issues that came
back. That is enough to repair a map and not enough to know whether the
repair helped: a reading with no numbers in it cannot be compared with the
reading before it, so a loop built on one cannot tell progress from change.
It will happily trade a legible legend for a cluttered coastline and call it
a round.

So the critique carries five scores, and
:mod:`~sprezzature_maps.studio.ralph.stopping` compares their total round over
round. Four of the five are ``sprezzature-figures``' and one is not:
``geographic_honesty`` has no analogue on a bar chart, because the ways a map
misleads — a frame that crops the data, a projection that lies about area —
are not ways a chart can.

What is sent
------------
The image, and a description: the kind, the options it was rendered with, the
user's title, the shape of the data, and last round's issues. **Never a
value.** Judging whether a map is honest about its data needs to know what the
data is shaped like, not what is in it.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sprezzature_maps.studio.assistant.client import LLMClient
from sprezzature_maps.studio.assistant.prompts import CRITIQUE_SYSTEM, critique_prompt
from sprezzature_maps.studio.assistant.read_map import MapReadingError
from sprezzature_maps.studio.assistant.schemas import DataProfile, MapReading


def issues_as_text(reading: MapReading | None) -> str:
    """Last round's findings, for the next round's prompt.

    Empty when there is no previous round, which is the first round's case and
    not an error.
    """
    if reading is None or not reading.issues:
        return ""
    return "\n".join(f"- [{i.severity}] {i.what}" for i in reading.issues)


def request_critique(
    client: LLMClient,
    image: bytes | str | Path,
    kind_name: str,
    *,
    options: dict[str, Any] | None = None,
    title: str = "",
    profile: DataProfile | None = None,
    previous: MapReading | None = None,
) -> MapReading:
    """Look at the rendered map and score it.

    Parameters
    ----------
    client : LLMClient
        Must support :meth:`chat_vision`.
    image : bytes or str or pathlib.Path
        PNG bytes, or a path to them. SVG is refused — a vision model shown
        SVG source reads the markup and answers from the text in it, having
        never looked at a picture.
    kind_name : str
        The kind that was rendered.
    options : dict, optional
        What it was rendered with, so the reader can tell a default from a
        decision.
    title : str
        The title on the map.
    profile : DataProfile, optional
        The data, described without its values.
    previous : MapReading, optional
        Last round's reading. Its issues are quoted into the prompt, because a
        critique that cannot see what was already said repeats it — and a loop
        reads a repeated issue as "no progress" and stops.

    Returns
    -------
    MapReading

    Raises
    ------
    MapReadingError
        If there is no raster to look at.
    """
    payload = _raster(image)
    answer = client.chat_vision(
        critique_prompt(
            kind_name,
            options=options,
            title=title,
            profile=profile,
            previous=issues_as_text(previous),
        ),
        payload,
        system=CRITIQUE_SYSTEM,
        response_model=MapReading,
        temperature=0.1,
    )
    assert isinstance(answer, MapReading)  # chat_vision guarantees this with a response_model
    return answer


def _raster(image: bytes | str | Path) -> bytes:
    """The PNG bytes, or a refusal that says why.

    Shares its rules with
    :func:`sprezzature_maps.studio.assistant.read_map.read_map` deliberately:
    the two are the only paths to a vision model in this package and a reader
    shown SVG source is the failure both exist to avoid.
    """
    if isinstance(image, (str, Path)):
        path = Path(image)
        if not path.is_file():
            raise MapReadingError(f"no image to read at {path}")
        if path.suffix.lower() == ".svg":
            raise MapReadingError(
                f"{path.name} is SVG; render it to PNG first — a vision model "
                "reads SVG source as text and reports what the markup says"
            )
        payload = path.read_bytes()
    else:
        payload = bytes(image)
    if not payload:
        raise MapReadingError("no image to read: the payload is empty")
    if payload.lstrip()[:5] in (b"<?xml", b"<svg "):
        raise MapReadingError(
            "that payload is SVG source, not a raster image; a vision model "
            "would read its markup instead of looking at the picture"
        )
    return payload
