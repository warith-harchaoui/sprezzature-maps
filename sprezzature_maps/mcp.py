"""
sprezzature-maps — Model Context Protocol (MCP) surface.

Module summary
--------------
Adapter that exposes the FastAPI app defined in :mod:`sprezzature_maps.api`
as MCP tools, so any MCP-aware host (agent runtimes, IDE integrations,
custom shells) can call ``render_choropleth`` / ``render_situation_map`` /
``list_kinds`` as first-class tools. Uses :mod:`fastapi_mcp`
(https://github.com/tadata-org/fastapi_mcp) -- one line wraps the whole
existing HTTP surface, so the route definitions are never duplicated here
(CODING.md Sec 23.1: MCP is an agent-facing surface, not a second place to
implement business logic).

Every route on the underlying app is tagged ``"actions"`` or ``"meta"``;
only those two tags are exposed (``include_tags`` below) rather than the
whole app by accident -- there is nothing *to* exclude today (this app has
no destructive or administrative routes), but the allowlist is written
explicitly anyway so a future route defaults to hidden from MCP until
someone deliberately tags it, not the other way around.

Install the extra to pull in ``fastapi-mcp``::

    pip install 'sprezzature-maps[api,mcp]'

Then run the MCP server::

    sprezzature-maps-mcp        # entry point (see pyproject.toml)
    # or, equivalently:
    python -m sprezzature_maps.mcp

Usage example
-------------
>>> # Register the MCP endpoint in your client. It publishes:
>>> #   health / list_kinds / render_choropleth / render_situation_map

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

try:
    from fastapi_mcp import FastApiMCP
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "The MCP surface requires the [mcp] extra. "
        "Install with: pip install 'sprezzature-maps[api,mcp]'"
    ) from exc

# Reuse the exact same FastAPI app -- MCP is a thin wrapper on top.
from sprezzature_maps.api import app

# FastApiMCP mounts an MCP endpoint on the existing FastAPI app; the
# wrapped instance is kept at module scope so downstream code (tests, ASGI
# runners) can access both the FastAPI app and the MCP handler.
mcp = FastApiMCP(
    app,
    name="sprezzature-maps",
    description=(
        "Sprezzature Maps MCP tools: render a world choropleth or a "
        "regional situation map as hand-authored SVG (or PNG/PDF/JPG)."
    ),
    include_tags=["meta", "actions"],
)
# Newer fastapi-mcp releases split mount() into transport-specific
# mount_http() (recommended) and mount_sse(); fall back to the legacy
# mount() on older versions so a range of fastapi-mcp versions still work.
if hasattr(mcp, "mount_http"):
    mcp.mount_http()
else:  # pragma: no cover - legacy fastapi-mcp
    mcp.mount()


def main() -> None:
    """Entry point for the ``sprezzature-maps-mcp`` console script.

    Boots the FastAPI app (which now serves both the HTTP routes and the
    MCP endpoint) with ``uvicorn`` in single-worker mode. Meant for local /
    container usage; behind a real load balancer use ``uvicorn``/``gunicorn``
    directly.
    """
    import os

    import uvicorn

    host = os.environ.get("SPREZZATURE_MAPS_HOST", "0.0.0.0")
    port = int(os.environ.get("SPREZZATURE_MAPS_PORT", "8000"))
    # Single worker: the generator-module cache (sys.modules, see
    # __init__.py's _load_script) is process-local state, so multiple
    # workers would each pay the same import cost independently rather
    # than sharing it.
    uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":  # pragma: no cover
    main()
