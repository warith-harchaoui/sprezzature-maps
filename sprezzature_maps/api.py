"""
sprezzature-maps: the FastAPI HTTP surface.

Module summary
--------------
FastAPI is a Python web framework for building HTTP APIs. This module
uses it to expose :func:`sprezzature_maps.make_choropleth` and
:func:`sprezzature_maps.make_situation_map` over HTTP, so either map
type can be rendered from any programming language that can make an HTTP
request, not only from Python. These are the same shared functions the
``make-map`` command line and the richer ``sprezzature-maps`` Click
command line already call: one real implementation, several thin ways of
reaching it, never a second copy of the rendering logic (see CODING.md
§19.1). This module also serves the small GUI gallery page as one more
plain HTTP route rather than as a separate application, since that page
is really just another caller of these same two render functions.

What ships here
----------------
- ``GET /health``: a liveness probe, a route whose only job is to answer
  quickly so a monitoring system can tell the server is still running.
- ``GET /v1/kinds``: the two map kinds this repo carries (``choropleth``,
  ``situation_map``), for a caller, or the GUI, that wants to discover
  them programmatically rather than hardcode the names.
- ``POST /v1/choropleth``: render a choropleth from JSON rows (or the
  built-in demo data, if ``data`` is left out of the request).
- ``POST /v1/situation-map``: render a situation map from a configuration
  object shaped the same way the ``--config`` YAML file is, or the
  bundled Western Europe demo if ``config`` is left out.
- ``GET /``: the GUI gallery page (see :mod:`sprezzature_maps.gui`).

Install the extra to get the runtime dependencies::

    pip install 'sprezzature-maps[api]'

Then run the app with any ASGI server::

    uvicorn sprezzature_maps.api:app --host 0.0.0.0 --port 8000

Usage example
-------------
>>> # Start the server:
>>> #   uvicorn sprezzature_maps.api:app --reload
>>> # Render the demo choropleth as SVG:
>>> #   curl -X POST http://localhost:8000/v1/choropleth -o choropleth.svg
>>> # Full OpenAPI docs at http://localhost:8000/docs

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Any, Literal

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse, Response
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "The FastAPI HTTP surface requires the [api] extra. "
        "Install with: pip install 'sprezzature-maps[api]'"
    ) from exc

from pydantic import BaseModel, Field

from . import __version__ as _VERSION
from . import make_choropleth, make_situation_map
from .gui import render_gallery_html

#: Maps an output format name to the Content-Type the response carries.
#: Kept as a small local dict (rather than importing mimetypes) since this
#: repo only ever emits the four formats scripts/_render.py's
#: ``_write_in_format`` already knows how to produce.
_MEDIA_TYPES: dict[str, str] = {
    "svg": "image/svg+xml",
    "png": "image/png",
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
}

app = FastAPI(
    title="Sprezzature Maps API",
    description=(
        "HTTP surface for sprezzature-maps: hand-authored SVG world maps -- "
        "choropleth and layered areas-of-control situation maps."
    ),
    version=_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# The two generators write their output to a file (their shared contract,
# via scripts/_render.py) rather than returning bytes directly, and
# make_choropleth/make_situation_map cache their loaded generator module in
# sys.modules (see __init__.py's _load_script) rather than being
# thread-safe about any *global* mutable state inside those modules. No
# such global state exists today, but a lock here costs nothing and
# forecloses a future generator accidentally introducing one (e.g. an
# environment-variable-based render scale, the pattern sprezzature-figures'
# own API already has to guard against for exactly this reason).
_render_lock = threading.Lock()


class ChoroplethRow(BaseModel):
    """One data row for ``POST /v1/choropleth``."""

    id: str = Field(description='ISO-3166-1 numeric country code, e.g. "840" for the USA.')
    value: float = Field(description="The indicator's value for this country.")


class ChoroplethRequest(BaseModel):
    """Body for ``POST /v1/choropleth``."""

    data: list[ChoroplethRow] | None = Field(
        default=None,
        description="Per-country rows. Omit to render the built-in demo data.",
    )
    title: str | None = Field(default=None, description="Chart title. Omit for the default.")
    subtitle: str | None = Field(default=None, description="Chart subtitle. Omit for the default.")
    width: int = Field(default=745, ge=100, le=8000, description="Canvas width in pixels.")
    height: int = Field(default=420, ge=100, le=8000, description="Canvas height in pixels.")
    diverging: bool | None = Field(
        default=None,
        description="Force the diverging ramp on/off. Omit to auto-detect from the data's sign.",
    )
    relief: bool = Field(default=True, description="Composite the vendored hillshade texture.")
    format: Literal["svg", "png", "pdf", "jpg"] = Field(
        default="svg", description="Output format; picks the response Content-Type."
    )


class SituationMapRequest(BaseModel):
    """Body for ``POST /v1/situation-map``."""

    config: dict[str, Any] | None = Field(
        default=None,
        description="Region/layer config, the same shape the --config YAML uses. "
        "Omit to render the bundled Western-Europe demo.",
    )
    title: str | None = Field(default=None, description="Overrides config['title'] if set.")
    format: Literal["svg", "png", "pdf", "jpg"] = Field(
        default="svg", description="Output format; picks the response Content-Type."
    )


@app.get("/health", tags=["meta"], operation_id="health")
def health() -> dict:
    """Liveness probe -- no dependency check, just proves the app is up.

    Returns
    -------
    dict
        ``{"status": "ok"}``.
    """
    return {"status": "ok"}


@app.get("/v1/kinds", tags=["meta"], operation_id="list_kinds")
def kinds() -> list[str]:
    """List the map kinds this repo carries.

    Returns
    -------
    list of str
        Always ``["choropleth", "situation_map"]`` today -- this repo's
        whole scope, per ``.private/t.md``, is exactly those two kinds.
    """
    return ["choropleth", "situation_map"]


@app.get("/", include_in_schema=False)
def gallery() -> HTMLResponse:
    """Serve the GUI gallery page at the app root.

    Returns
    -------
    fastapi.responses.HTMLResponse
        The rendered gallery HTML (see :func:`sprezzature_maps.gui.render_gallery_html`).
    """
    return HTMLResponse(render_gallery_html())


@app.get("/docs-redirect", include_in_schema=False)
def docs_redirect() -> RedirectResponse:
    """Convenience redirect to the interactive API docs.

    Returns
    -------
    fastapi.responses.RedirectResponse
        Redirects to ``/docs``.
    """
    return RedirectResponse(url="/docs")


def _render_to_response(make_fn: Any, kwargs: dict[str, Any], fmt: str, stem: str) -> Response:
    """Call a ``make_<kind>`` function against a temp file and wrap the bytes.

    Parameters
    ----------
    make_fn : callable
        :func:`~sprezzature_maps.make_choropleth` or
        :func:`~sprezzature_maps.make_situation_map`.
    kwargs : dict
        Keyword arguments to forward, plus ``out`` (added here).
    fmt : str
        One of ``"svg"``, ``"png"``, ``"pdf"``, ``"jpg"`` -- picks both the
        temp file's suffix (so ``_render._write_in_format`` produces the
        right bytes) and the response's ``Content-Type``.
    stem : str
        Base filename for the temp file (cosmetic only -- the file is
        deleted with its containing directory before the response returns).

    Returns
    -------
    fastapi.responses.Response
        The rendered file's bytes with the matching ``Content-Type``.

    Raises
    ------
    fastapi.HTTPException
        422 for a bad input (caller's fault), 500 for anything else.
    """
    with tempfile.TemporaryDirectory(prefix="sprezzature-maps-api-") as tmp:
        out_path = Path(tmp) / f"{stem}.{fmt}"
        with _render_lock:
            try:
                make_fn(out=out_path, **kwargs)
            except (ValueError, KeyError, ImportError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive catch-all
                raise HTTPException(status_code=500, detail=str(exc)) from exc
        content = out_path.read_bytes()
    return Response(content=content, media_type=_MEDIA_TYPES[fmt])


@app.post("/v1/choropleth", tags=["actions"], operation_id="render_choropleth")
def render_choropleth(body: ChoroplethRequest = ChoroplethRequest()) -> Response:
    """Render a choropleth map and return the file bytes.

    Parameters
    ----------
    body : ChoroplethRequest
        See the model's field descriptions; every field is optional.

    Returns
    -------
    fastapi.responses.Response
        The rendered file with the matching ``Content-Type``.
    """
    kwargs: dict[str, Any] = {
        "width": body.width,
        "height": body.height,
        "diverging": body.diverging,
        "relief": body.relief,
    }
    if body.data is not None:
        kwargs["data"] = [row.model_dump() for row in body.data]
    if body.title is not None:
        kwargs["title"] = body.title
    if body.subtitle is not None:
        kwargs["subtitle"] = body.subtitle
    return _render_to_response(make_choropleth, kwargs, body.format, "choropleth")


@app.post("/v1/situation-map", tags=["actions"], operation_id="render_situation_map")
def render_situation_map(body: SituationMapRequest = SituationMapRequest()) -> Response:
    """Render a situation map and return the file bytes.

    Parameters
    ----------
    body : SituationMapRequest
        See the model's field descriptions; every field is optional.

    Returns
    -------
    fastapi.responses.Response
        The rendered file with the matching ``Content-Type``.
    """
    kwargs: dict[str, Any] = {}
    if body.config is not None:
        kwargs["config"] = body.config
    if body.title is not None:
        kwargs["title"] = body.title
    return _render_to_response(make_situation_map, kwargs, body.format, "situation_map")


def main() -> None:
    """Entry point for running the API with ``uvicorn`` directly.

    Boots the FastAPI app in single-worker mode -- meant for local /
    container usage; behind a real load balancer use ``uvicorn``/``gunicorn``
    directly instead of this helper.
    """
    import os

    import uvicorn

    host = os.environ.get("SPREZZATURE_MAPS_HOST", "0.0.0.0")
    port = int(os.environ.get("SPREZZATURE_MAPS_PORT", "8000"))
    # Single worker: the generator-module cache (sys.modules, see
    # __init__.py's _load_script) is process-local state -- multiple
    # workers would each pay the same import/relief-raster-load cost
    # independently rather than sharing it.
    uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":  # pragma: no cover
    main()
