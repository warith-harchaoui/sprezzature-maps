"""
Five surfaces named the same three kinds, and one of them was wrong.

The defect, which no test could have caught
-------------------------------------------
``sprezzature-maps`` renders ``choropleth``, ``situation_map`` and
``density``. Before :mod:`sprezzature_maps.kinds` each surface said so
separately — five hand-written lists of the same three:

* ``cli.py``'s ``list`` command: ``("choropleth", "situation_map")``;
* ``api.py``'s ``GET /v1/kinds``: ``["choropleth", "density", "situation_map"]``;
* ``gui.py``'s ``_TILES``: three tiles;
* ``api.py``'s routes: three ``POST`` endpoints;
* ``TRIGGERS.md``: three rows.

**Four of the five were right, which is exactly the problem.** ``density`` was
born in this repository after the other two were extracted from
`sprezzature-figures`, so every list written before it had to be revisited by
hand — and the one nobody revisited is the one a reader asks directly:
``sprezzature-maps list`` answered **two kinds of three**. Nothing could notice,
because there was no list to compare an answer against. The `/v1/kinds` route
even carried the right intention in its own docstring, "so a caller can
discover them programmatically rather than hardcode the names", above a body
that hardcoded them.

So there is one registry now, and this file is what makes it binding: every
surface is read back from the running code — the Click group's real commands,
the FastAPI app's real routes, the gallery's real tiles, the package's real
exports — and compared against it. A fourth kind cannot be half-added.

Why read the surfaces rather than the source
--------------------------------------------
Grepping would pass on a command defined and never registered, or a route
declared under an unreachable prefix. ``main.commands`` and ``app.routes`` are
what a user reaches, so they are what gets compared.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import sprezzature_maps
from sprezzature_maps.cli import main
from sprezzature_maps.gui import _TILES
from sprezzature_maps.kinds import DATA_SHAPES, KINDS, kind, kind_names

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The registry must not be allowed to shrink to nothing. Every assertion below
#: iterates it, so an empty or truncated registry would turn this whole file
#: into a set of vacuous passes — the failure mode the defect above *was*.
EXPECTED_KINDS = 3


def test_the_registry_is_not_empty_or_truncated() -> None:
    """First, because everything else iterates it."""
    assert len(KINDS) == EXPECTED_KINDS, (
        f"the registry holds {len(KINDS)} kinds and this file expects "
        f"{EXPECTED_KINDS}. If a kind was genuinely added or removed, change "
        f"the number here — deliberately, because every other test in this "
        f"file iterates the registry and would pass vacuously on an empty one."
    )
    assert len(set(kind_names())) == len(KINDS), f"duplicate names in {kind_names()}"


def test_list_prints_every_kind() -> None:
    """The command that was wrong, now read from the registry.

    Asserted through the runner rather than by calling the function, because
    what went wrong was what a reader *sees*.
    """
    printed = tuple(
        line.strip()
        for line in CliRunner().invoke(main, ["list"]).output.splitlines()
        if line.strip()
    )
    assert printed == kind_names(), (
        f"`sprezzature-maps list` prints {printed} and the registry holds "
        f"{kind_names()}. This is the exact shape of the original defect: a "
        f"reader asking the tool what it can draw being told something false."
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_has_the_command_it_claims(entry) -> None:
    """The registry's ``command`` has to be a command the group really has."""
    assert entry.command in main.commands, (
        f"{entry.name} claims the command {entry.command!r}, which the CLI "
        f"group does not carry. It has: {sorted(main.commands)}"
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_has_the_route_it_claims(entry) -> None:
    """And the ``endpoint`` has to be a route the app really serves."""
    api = pytest.importorskip(
        "sprezzature_maps.api", reason="fastapi is a base dependency; a skip means a broken install"
    )
    served = {getattr(route, "path", None) for route in api.app.routes}
    assert entry.endpoint in served, (
        f"{entry.name} claims {entry.endpoint!r}, which the app does not "
        f"serve. Its /v1 routes: {sorted(p for p in served if p and p.startswith('/v1'))}"
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_exports_its_renderer(entry) -> None:
    """``make_choropleth`` and friends: exported, and callable.

    Both halves: a name in ``__all__`` that does not resolve is a documented
    function nobody can call, and a resolvable one missing from ``__all__`` is
    a function the package does not admit to having.
    """
    assert entry.renderer in sprezzature_maps.__all__, (
        f"{entry.renderer} is not in sprezzature_maps.__all__, so the package "
        f"does not admit to rendering {entry.name}"
    )
    assert callable(getattr(sprezzature_maps, entry.renderer, None)), (
        f"sprezzature_maps.{entry.renderer} is not callable"
    )


def test_the_gallery_shows_exactly_the_registry() -> None:
    """One tile per kind, no more, no fewer, in registry order.

    Order included: the gallery is the page a reader scans, and a tile order
    that drifts from the registry is the start of two lists again.
    """
    assert tuple(tile["kind"] for tile in _TILES) == kind_names(), (
        f"the gallery shows {[t['kind'] for t in _TILES]} and the registry "
        f"holds {list(kind_names())}"
    )
    for tile in _TILES:
        entry = kind(tile["kind"])
        assert tile["title"] == entry.label
        assert tile["description"] == entry.description
        assert tile["endpoint"] == entry.endpoint


def test_the_kinds_route_answers_the_registry() -> None:
    """``GET /v1/kinds`` is what a caller discovers the set from.

    Sorted, which is what its docstring documents and what this preserves —
    the point is that it is *derived*, not that the order changed.
    """
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from sprezzature_maps.api import app

    assert TestClient(app).get("/v1/kinds").json() == sorted(kind_names())


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_triggers_routes_every_kind(entry) -> None:
    """``TRIGGERS.md`` is machine-read, so a kind missing from it is unroutable.

    An agent picks a tool from that table. A kind the table does not mention
    exists in the package and not in the vocabulary anyone reaches it by,
    which is a quieter version of the same defect: present, and undiscoverable.
    """
    triggers = (REPO_ROOT / "TRIGGERS.md").read_text(encoding="utf-8")
    needle = entry.name.replace("_", "")
    assert entry.name in triggers or needle in triggers.replace("_", ""), (
        f"TRIGGERS.md routes nothing to {entry.name}. An agent reading that "
        f"table cannot reach a kind it does not name."
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_declares_a_shape_that_exists(entry) -> None:
    """``data_shape`` has to be one of the three, not a typo of one.

    A free-form string would let ``"row"`` through, and the Studio's input
    panel would then fall through to whatever its default branch is — which is
    a map drawn from the wrong reader rather than an error.
    """
    assert entry.data_shape in DATA_SHAPES, (
        f"{entry.name} declares the shape {entry.data_shape!r}; the shapes are "
        f"{sorted(DATA_SHAPES)}"
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_names_a_real_data_option(entry) -> None:
    """And ``data_option`` has to be an option the command really takes.

    Read off the Click command's own parameters rather than its ``--help``
    text: help output is prose and would match a flag mentioned in a sentence.
    This is the half that catches a renamed flag — the registry would keep
    printing the old name in an error message that tells the reader to pass
    something that no longer exists.
    """
    command = main.commands[entry.command]
    declared = {opt for param in command.params for opt in getattr(param, "opts", [])}
    assert entry.data_option in declared, (
        f"{entry.name} names {entry.data_option!r}, which `{entry.command}` does "
        f"not take. It takes: {sorted(declared)}"
    )


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_names_the_keyword_its_renderer_takes(entry) -> None:
    """``payload_keyword`` has to be a parameter the generator really has.

    The three generators each named their data parameter for their own shape —
    ``data``, ``config``, ``points`` — which is reasonable in isolation and
    leaves every caller dispatching on the kind.
    :mod:`sprezzature_maps.studio.render` looks it up here instead, so it has
    no ``if kind ==`` in it.

    Introspected from the loaded generator rather than read from its
    docstring: a renamed parameter would leave the docstring saying the old
    name for as long as nobody re-read it, and the failure would be a
    ``TypeError`` from inside a render rather than a sentence here.
    """
    import inspect

    import sprezzature_maps

    generator = sprezzature_maps._load_script(entry.renderer).__dict__[entry.renderer]
    parameters = inspect.signature(generator).parameters
    assert entry.payload_keyword in parameters, (
        f"{entry.name} says its data goes in as {entry.payload_keyword!r}, and "
        f"{entry.renderer} takes {sorted(parameters)}"
    )
