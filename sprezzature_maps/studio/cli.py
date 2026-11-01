"""
sprezzature-maps Studio: the command that opens it.

Module summary
--------------
``sprezzature-maps-studio`` runs the editor on a local address. One command,
because a Studio is a thing you open rather than a service you deploy: the
default host is ``127.0.0.1``, which is a decision and not a placeholder —
this page renders whatever is pasted into it and keeps the results in a
temporary directory, and neither belongs on an address anyone else can reach.
``--host`` is there for a container that maps a port, and says so.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import click

from sprezzature_maps.kinds import kind_names

#: Loopback, deliberately. See the module docstring.
DEFAULT_HOST = "127.0.0.1"

#: Not 8000: `sprezzature_maps.api` documents that port, and a reader running
#: both should not have to discover the clash by reading a traceback.
DEFAULT_PORT = 8010


@click.command()
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="Address to bind.")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Port to bind.")
@click.option(
    "--reload/--no-reload",
    default=False,
    show_default=True,
    help="Restart on code changes. For working on the Studio itself.",
)
def main(host: str, port: int, reload: bool) -> None:
    """Open Sprezzature Studio for maps on a local address.

    The editor renders every kind this package carries, and the kinds come
    from the registry — so it needs no argument to know what it can draw.
    """
    import uvicorn

    click.echo(f"Sprezzature Studio — maps ({', '.join(kind_names())})")
    click.echo(f"  http://{host}:{port}/")
    uvicorn.run(
        "sprezzature_maps.studio.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="warning",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
