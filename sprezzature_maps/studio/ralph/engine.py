"""
The loop: render, read it back, change one thing, render again.

What it does not do
-------------------
It does not let a model touch the picture, and it does not let a model choose
the keyword. The model's only job is to look at a PNG and say what it can read;
the table in :mod:`~sprezzature_maps.studio.ralph.repair` turns that into a
keyword change, and :mod:`~sprezzature_maps.studio.ralph.policy` turns the
change into a value from a ladder that ends.

It also never applies anything that can alter what the map says about the data.
Those repairs are proposed, carried in the result, and left for a person —
see :data:`sprezzature_maps.options.OPTIONS` for where that line is drawn.

Rasterising
-----------
The loop asks the renderer for a ``.png``, which the generators already
support: ``_render._write_in_format`` honours the destination extension, so a
vision model is shown a picture rather than SVG markup. That is not an
optimisation — a model handed SVG source reads the markup and answers from the
text in it, confidently, having never looked at the image.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sprezzature_maps.studio.assistant.client import LLMClient
from sprezzature_maps.studio.assistant.read_map import read_map
from sprezzature_maps.studio.assistant.schemas import MapReading

from .repair import Repair, apply_safe, propose_repairs
from .stopping import MAX_ROUNDS, should_stop, signature_set

#: Signature of the renderer the loop drives. Matches
#: :func:`sprezzature_maps.studio.render.render`, and is injectable so a test
#: can drive the loop without drawing a map.
Renderer = Callable[..., Path]


@dataclass
class RalphRound:
    """One pass of the loop.

    Parameters
    ----------
    index : int
        1 for the first round.
    options : dict
        The options this round was rendered with.
    image : pathlib.Path
        The PNG that was read.
    reading : MapReading
        What the reader said about it.
    proposed : list of Repair
        Everything the critique called for, safe or not.
    applied : list of Repair
        The subset applied unattended, which is what the next round used.
    """

    index: int
    options: dict[str, Any]
    image: Path
    reading: MapReading
    proposed: list[Repair] = field(default_factory=list)
    applied: list[Repair] = field(default_factory=list)


@dataclass
class RalphResult:
    """What the loop ended with.

    Parameters
    ----------
    rounds : list of RalphRound
        In order. Never empty: the loop always renders and reads once.
    reason : str
        Why it stopped, as :func:`~sprezzature_maps.studio.ralph.stopping.should_stop`
        names it.
    options : dict
        The options the final image was rendered with.
    image : pathlib.Path
        The final PNG.
    for_a_person : list of Repair
        Changes the critique called for that the loop refused to make alone,
        deduplicated, newest first. Empty when there is nothing to offer.
    """

    rounds: list[RalphRound]
    reason: str
    options: dict[str, Any]
    image: Path
    for_a_person: list[Repair] = field(default_factory=list)

    @property
    def improved(self) -> bool:
        """Whether anything was actually changed.

        A loop that stopped on its first reading improved nothing, which is a
        perfectly good outcome and must not read as a success story.
        """
        return any(r.applied for r in self.rounds)


def improve(
    client: LLMClient,
    kind_name: str,
    payload: Any,
    *,
    out: str | Path,
    renderer: Renderer | None = None,
    options: dict[str, Any] | None = None,
    title: str | None = None,
    max_rounds: int | None = None,
) -> RalphResult:
    """Render the map, read it back, and repair what is safe to repair.

    Parameters
    ----------
    client : LLMClient
        Must support :meth:`chat_vision`. Injected; this module never builds one.
    kind_name : str
        A registered kind.
    payload : Any
        The rows, configuration or points, as the kind consumes them.
    out : str or pathlib.Path
        Where the final image goes. A ``.png`` suffix is enforced, because the
        reader needs a raster.
    renderer : callable, optional
        Defaults to :func:`sprezzature_maps.studio.render.render`.
    options : dict, optional
        Starting options. Anything absent keeps the renderer's own default.
    title : str, optional
        Passed through unchanged. The loop never rewrites a user's words.
    max_rounds : int, optional
        Overrides :data:`~sprezzature_maps.studio.ralph.stopping.MAX_ROUNDS`
        downward only; a caller cannot ask for more rounds than the ceiling.

    Returns
    -------
    RalphResult

    Raises
    ------
    ValueError
        If `out` does not end in ``.png``.
    """
    destination = Path(out)
    if destination.suffix.lower() != ".png":
        raise ValueError(
            f"the loop reads the rendered map back, so it needs a raster; "
            f"{destination.name} is not a .png"
        )
    if renderer is None:
        from sprezzature_maps.studio.render import render as renderer  # noqa: PLW0127

    ceiling = MAX_ROUNDS if max_rounds is None else min(max_rounds, MAX_ROUNDS)

    settings: dict[str, Any] = dict(options or {})
    rounds: list[RalphRound] = []
    offered: list[Repair] = []
    previous: frozenset[str] | None = None
    applied_count = 0
    reason = "max_rounds"

    for index in range(1, ceiling + 1):
        image = renderer(kind_name, payload, out=destination, title=title, **settings)
        reading = read_map(client, image)
        proposed = propose_repairs(reading, kind_name, settings)
        safe_now = [r for r in proposed if r.safe]
        this_round = RalphRound(
            index=index,
            options=dict(settings),
            image=Path(image),
            reading=reading,
            proposed=proposed,
        )
        rounds.append(this_round)
        offered.extend(r for r in proposed if not r.safe)

        stop, why = should_stop(
            reading=reading,
            asked_for=kind_name,
            rounds_done=index,
            repairs_applied=applied_count,
            previous_signatures=previous,
            repairs_available=len(safe_now),
        )
        if stop:
            reason = why or "readable"
            break

        settings = apply_safe(safe_now, settings)
        this_round.applied = safe_now
        applied_count += len(safe_now)
        previous = signature_set(reading)

    seen: set[tuple[str, Any]] = set()
    unique: list[Repair] = []
    for repair in reversed(offered):
        key = (repair.option, repair.value)
        if key not in seen:
            seen.add(key)
            unique.append(repair)

    return RalphResult(
        rounds=rounds,
        reason=reason,
        options=rounds[-1].options,
        image=rounds[-1].image,
        for_a_person=unique,
    )
