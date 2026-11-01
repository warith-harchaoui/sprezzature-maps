"""
sprezzature-maps Studio: the HTTP surface, which is the whole interface.

Module summary
--------------
Three routes. A page, a render, and the rendered file:

``GET /``
    The editor for one kind, chosen by ``?kind=``. Addressable, so a kind can
    be shared, bookmarked and tested with one request.
``POST /render``
    Reads the pasted payload, renders, and comes back with the same page
    carrying the map — and carrying what was typed, so a refusal does not lose
    it.
``GET /map/{token}.svg``
    The rendered file. Served rather than inlined: a situation plate is 2.2 MB
    of SVG and inlining that into every re-render makes the page heavier than
    the map.

Mounted as a router so it can live under the main app or stand alone, which is
what ``sprezzature-maps-studio`` does.

The pasted text is read by the command line's own readers
----------------------------------------------------------
Not by a second parser. The textarea's content is written to a temporary file
with the right suffix and handed to :mod:`sprezzature_maps.data` — the very
functions ``--data``, ``--config`` and ``--points`` call. So "what counts as a
usable file" has one answer, and the Studio inherits every error message the
command line already has, including the ones that name the row, the real
columns and the flag that fixes it.

It costs a write to a temporary file per render, which is nothing beside
projecting a coastline, and it buys the one property that matters: the Studio
cannot come to a different conclusion than the command line about the same
bytes.

Author
------
Warith HARCHAOUI<warithmetics@deraison.ai>
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from sprezzature_maps.data import (
    read_choropleth_rows,
    read_density_points,
    read_situation_config,
)
from sprezzature_maps.kinds import KINDS, kind_names
from sprezzature_maps.kinds import kind as lookup_kind
from sprezzature_maps.studio.page import render_editor_html
from sprezzature_maps.studio.render import render

#: Where rendered maps go, for this process only. A Studio is a local
#: single-user tool -- the command it ships as binds 127.0.0.1 -- so a
#: per-process directory is the honest scope. Nothing persists across a
#: restart, which is correct: the input is in the page, not here.
_OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="sprezzature-maps-studio-"))

#: Token to file, so a URL cannot name a path. The token is random rather than
#: derived from the input: a content hash in a URL would let one reader's
#: filename be guessed from their data, and there is no reason to offer that.
_RENDERED: dict[str, Path] = {}

#: The suffix each shape's text is written under, so the shared readers in
#: `data.py` dispatch exactly as they do for a file on disk. ``rows`` is
#: decided per paste -- see :func:`_suffix_for`.
_SHAPE_SUFFIX: dict[str, str] = {"config": ".yaml", "points": ".json"}

router = APIRouter()


def _suffix_for(shape: str, text: str) -> str:
    """The extension to write *text* under, for the shared readers.

    ``rows`` is the only ambiguous one, because a choropleth accepts both CSV
    and JSON. Decided on the first non-blank character: a document starting
    ``[`` or ``{`` is JSON and anything else is CSV. That is the same guess a
    reader makes looking at it, and getting it wrong produces one of
    ``data.py``'s own messages rather than a wrong map.
    """
    if shape in _SHAPE_SUFFIX:
        return _SHAPE_SUFFIX[shape]
    return ".json" if text.lstrip()[:1] in "[{" else ".csv"


def _payload_from_text(shape: str, text: str) -> Any:
    """Parse pasted text into the shape its kind consumes.

    Returns ``None`` for empty text, which every generator answers with its
    built-in demo -- the first screen of a Studio, before a file is chosen.

    Raises
    ------
    ValueError
        Straight from :mod:`sprezzature_maps.data`, with its messages intact.
    """
    if not text.strip():
        return None
    suffix = _suffix_for(shape, text)
    with tempfile.NamedTemporaryFile(
        "w", suffix=suffix, dir=_OUTPUT_DIR, delete=False, encoding="utf-8"
    ) as handle:
        handle.write(text)
        path = Path(handle.name)
    try:
        if shape == "points":
            return read_density_points(path)
        if shape == "config":
            return read_situation_config(path)
        return read_choropleth_rows(path)
    finally:
        path.unlink(missing_ok=True)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def editor(kind: str = Query(default=KINDS[0].name)) -> HTMLResponse:
    """The editor page for one kind.

    An unknown ``?kind=`` is a 404 naming the kinds that exist, rather than a
    silent fall back to the first one: a typed or stale URL should say so.
    """
    try:
        entry = lookup_kind(kind)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HTMLResponse(render_editor_html(entry))


@router.post("/render", response_class=HTMLResponse, include_in_schema=False)
def render_map(
    kind: str = Form(...),
    payload: str = Form(default=""),
    title: str = Form(default=""),
) -> HTMLResponse:
    """Render what was pasted, and come back with the page plus the map.

    A refusal returns **200 with the same page**, carrying the message and
    everything that was typed. A 4xx with a bare detail would be correct for
    an API and wrong here: the reader is mid-edit, and losing the paste to see
    the error is a worse outcome than the error.
    """
    try:
        entry = lookup_kind(kind)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        data = _payload_from_text(entry.data_shape, payload)
    except ValueError as exc:
        return HTMLResponse(
            render_editor_html(entry, payload_text=payload, title=title, error=str(exc))
        )

    token = uuid.uuid4().hex
    out = _OUTPUT_DIR / f"{token}.svg"
    try:
        written = render(entry.name, data, out=out, title=title or None)
    except ValueError as exc:
        # The generators refuse for reasons a reader can act on -- an empty
        # frame, a code that is not a country -- so the message is shown as
        # written rather than wrapped.
        return HTMLResponse(
            render_editor_html(entry, payload_text=payload, title=title, error=str(exc))
        )
    _RENDERED[token] = Path(written)
    return HTMLResponse(
        render_editor_html(
            entry, payload_text=payload, title=title, svg_url=f"map/{token}.svg"
        )
    )


#: How many rounds the page allows. The command line allows more.
#:
#: A click should not hang for minutes. Each round renders a 4K map and shows
#: it to a vision model, so two rounds is already several seconds of work with
#: a local model and more with a remote one. Somebody who wants the full
#: ceiling has `sprezzature-maps improve`, which is the surface for a thing you
#: script rather than a thing you click.
PAGE_ROUNDS: int = 2


@router.post("/improve", include_in_schema=False)
def improve_map(
    kind: str = Form(...),
    payload: str = Form(default=""),
    title: str = Form(default=""),
) -> HTMLResponse:
    """Render what was pasted, look at it, and repair what is safe to repair.

    The same form as ``/render``, and the same refusal shape: a failure comes
    back as **200 with the page**, carrying the message and everything that was
    typed. A reader mid-edit should not lose their paste to see an error.

    What comes back that ``/render`` does not give is the account: what each
    round read, what was changed, and — the part that matters — what the loop
    *declined* to change on its own. Those are the repairs that can alter what
    the map says about its data, and they are the reader's decision, so they
    are printed rather than applied.
    """
    try:
        entry = lookup_kind(kind)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        data = _payload_from_text(entry.data_shape, payload)
    except ValueError as exc:
        return HTMLResponse(
            render_editor_html(entry, payload_text=payload, title=title, error=str(exc))
        )

    # Imported here and not at module scope: the editor must open, and its
    # other two routes must work, on a machine with no model installed.
    from sprezzature_maps.studio.assistant import default_client
    from sprezzature_maps.studio.ralph import improve

    token = uuid.uuid4().hex
    out = _OUTPUT_DIR / f"{token}.png"
    try:
        result = improve(
            default_client(),
            entry.name,
            data,
            out=out,
            title=title or None,
            max_rounds=PAGE_ROUNDS,
        )
    except Exception as exc:  # noqa: BLE001 - the page says what happened
        # Anything from here is a model that did not answer, a backend that is
        # not running, or a renderer that refused. All of them are things the
        # reader can act on, and none of them should cost them their paste.
        return HTMLResponse(
            render_editor_html(
                entry, payload_text=payload, title=title,
                error=f"the loop could not finish: {exc}",
            )
        )

    _RENDERED[token] = Path(result.image)
    return HTMLResponse(
        render_editor_html(
            entry,
            payload_text=payload,
            title=title,
            png_url=f"map/{token}.png",
            report=report_lines(result),
        )
    )


def report_lines(result: Any) -> list[str]:
    """The loop's account, as the page prints it.

    A function rather than a comprehension inside the route, because it is the
    part a test should be able to read without driving HTTP.
    """
    lines = [
        f"round {r.index}: read as {r.reading.kind_seen or 'could not tell'}, "
        f"score {r.reading.score_total}/500, {len(r.reading.issues)} issue(s)"
        for r in result.rounds
    ]
    for round_ in result.rounds:
        for repair in round_.applied:
            lines.append(f"applied {repair.option}={repair.value} — {repair.because}")
    lines.append(f"stopped: {result.reason}")
    if not result.improved:
        lines.append("nothing was changed")
    for repair in result.for_a_person:
        lines.append(
            f"for you to decide: {repair.option}={repair.value} — {repair.because} "
            "(it can change what the map says about the data)"
        )
    return lines


@router.get("/map/{token}.png", include_in_schema=False)
def rendered_png(token: str) -> FileResponse:
    """Serve one improved map. The loop writes PNG; see :func:`improve_map`."""
    path = _RENDERED.get(token)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="no such rendered map")
    return FileResponse(path, media_type="image/png")


@router.get("/map/{token}.svg", include_in_schema=False)
def rendered(token: str) -> FileResponse:
    """Serve one rendered map.

    Looked up in :data:`_RENDERED` rather than built from the token, so a
    crafted token cannot name a path. An unknown token is a 404 — which is
    also what a reload after a restart gets, and the page it came from still
    holds the input to render again.
    """
    path = _RENDERED.get(token)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="no such rendered map")
    return FileResponse(path, media_type="image/svg+xml")


def create_app() -> Any:
    """A standalone FastAPI app serving the Studio at the root.

    Separate from :mod:`sprezzature_maps.api` on purpose: that app is the
    headless HTTP surface, documented and schema'd, and this one is an
    interface. Mounting the router under it as well would make ``/docs`` list
    pages.
    """
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from sprezzature_maps.api import _FONTS_DIR, FONTS_URL_PREFIX

    app = FastAPI(
        title="Sprezzature Studio — maps",
        description=(
            "A conversational editor for the three kinds of map this package "
            f"renders: {', '.join(kind_names())}."
        ),
    )
    app.include_router(router)
    # The same mount the gallery uses, for the same reason: the three Roboto
    # families are served from sprezzature-figures' bundled directory so the
    # page asks nothing of a third party.
    app.mount(
        FONTS_URL_PREFIX,
        StaticFiles(directory=str(_FONTS_DIR), html=False, check_dir=True),
        name="fonts",
    )
    return app
