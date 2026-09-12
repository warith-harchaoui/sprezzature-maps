"""
sprezzature-maps: the Model Context Protocol (MCP) surface.

Module summary
--------------
MCP, the Model Context Protocol, is the standard that lets an AI
assistant call a tool directly, the way a human would click a button or
run a command. This module adapts the FastAPI application defined in
:mod:`sprezzature_maps.api` into MCP tools, so any MCP-aware host (an
agent runtime, an IDE integration, a custom shell) can call
``render_choropleth``, ``render_situation_map``, and ``list_kinds`` as
first-class tools of its own. It does this with :mod:`fastapi_mcp`
(https://github.com/tadata-org/fastapi_mcp): one line of code wraps the
entire existing HTTP surface, so none of the route logic gets written a
second time here (per CODING.md §23.1: MCP is a way of reaching existing
functionality, not a second place to implement it).

Every route on the underlying application is tagged either ``"actions"``
or ``"meta"``; only routes carrying one of those two tags are exposed
through MCP (see ``include_tags`` below), rather than the whole
application being exposed by accident. There is nothing that actually
needs excluding today, since this application has no destructive or
administrative routes, but the allowlist is written explicitly anyway so
that any future route stays hidden from MCP by default, until someone
deliberately tags it as safe to expose, rather than the reverse.

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
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys

try:
    from fastapi_mcp import FastApiMCP
except ImportError:  # pragma: no cover - dependency guard

    def main() -> None:
        """
        Entry point when the MCP extra is not installed.

        Says which extra is missing and stops. Reaching an MCP
        command without the ``[mcp]`` extra needs a one-line fix,
        not a stack trace.
        """
        print(
            "sprezzature-maps MCP surface requires fastapi-mcp. "
            "Install with: pip install 'sprezzature-maps[api,mcp]'",
            file=sys.stderr,
        )
        sys.exit(1)

else:

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


    def main(argv: "list[str] | None" = None) -> None:
        """
        Entry point for the ``sprezzature-maps-mcp`` console script.

        Serves the FastAPI app — which carries both the HTTP routes and the
        MCP endpoint — with ``uvicorn``, in single-worker mode. Meant for
        local or container use; behind a real load balancer, run ``uvicorn``
        or ``gunicorn`` directly.

        Arguments are parsed before anything is bound, so ``--help`` answers
        instead of starting a server and hanging.

        Parameters
        ----------
        argv : list of str or None, optional
            Arguments to parse. ``None`` reads ``sys.argv``.
        """
        import argparse
        import os

        parser = argparse.ArgumentParser(
            prog="sprezzature-maps-mcp",
            description=(
                "Serve the sprezzature-maps MCP tools over HTTP. Every tool is a "
                "route on the same FastAPI app, with the MCP endpoint "
                "mounted beside them."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "Defaults come from SPREZZATURE_MAPS_HOST and "
                "SPREZZATURE_MAPS_PORT when those are set.\n"
                "The host defaults to 127.0.0.1: pass --host 0.0.0.0 to "
                "accept connections from outside this machine."
            ),
        )
        parser.add_argument(
            "--host",
            default=os.environ.get("SPREZZATURE_MAPS_HOST", "127.0.0.1"),
            help="Interface to bind (default: %(default)s).",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=int(os.environ.get("SPREZZATURE_MAPS_PORT", "8000")),
            help="Port to bind (default: %(default)s).",
        )
        args = parser.parse_args(argv)

        import uvicorn

        # Single worker: the generator-module cache (sys.modules, see
        # __init__.py's _load_script) is process-local state, so multiple
        # workers would each pay the same import cost independently rather
        uvicorn.run(app, host=args.host, port=args.port, workers=1)

if __name__ == "__main__":  # pragma: no cover
    main()
