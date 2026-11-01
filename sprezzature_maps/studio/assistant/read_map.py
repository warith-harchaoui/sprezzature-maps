"""
Read a rendered map back off its own image.

Why this exists
---------------
Every renderer in this package can return successfully and draw the wrong
picture: a density map framed over the wrong continent, a choropleth whose
legend swatches are indistinguishable, a title laid outside the viewport. None
of that fails a unit test of the renderer, because nothing raised. The only
check that catches it is looking at the result — and the comparison that
matters is between the kind asked for and the kind *read back*.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from pathlib import Path

from .client import LLMClient
from .prompts import READ_SYSTEM, read_prompt
from .schemas import MapReading


class MapReadingError(RuntimeError):
    """Raised when there is no image to read."""


def read_map(
    client: LLMClient,
    image: bytes | str | Path,
    *,
    asked_for: str = "",
) -> MapReading:
    """Ask a vision model what the rendered map shows.

    Parameters
    ----------
    client : LLMClient
        Must support :meth:`chat_vision`.
    image : bytes or str or pathlib.Path
        PNG bytes, or a path to read them from. An SVG is not accepted: a
        vision model shown SVG source reads the *markup*, answers confidently
        from the text in it, and never looks at a picture — which is the one
        failure this function exists to catch.
    asked_for : str
        The kind that was requested, passed through to the prompt only when the
        caller wants the comparison stated. Empty by default.

    Returns
    -------
    MapReading

    Raises
    ------
    MapReadingError
        If `image` is an empty payload, a missing file, or an SVG.
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
        payload = image
    if not payload:
        raise MapReadingError("no image to read: the payload is empty")
    if payload.lstrip()[:5] in (b"<?xml", b"<svg "):
        raise MapReadingError(
            "that payload is SVG source, not a raster image; a vision model "
            "would read its markup instead of looking at the picture"
        )

    answer = client.chat_vision(
        read_prompt(asked_for),
        payload,
        system=READ_SYSTEM,
        response_model=MapReading,
        temperature=0.1,
    )
    assert isinstance(answer, MapReading)  # chat_vision guarantees this with a response_model
    return answer
