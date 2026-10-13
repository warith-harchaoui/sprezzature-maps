"""
``TRIGGERS.md`` is read by machines, so it is held to machine standards.

That file exists to route an agent — a Claude Code or OpenCode skill, an MCP
host, anything choosing a tool on someone's behalf — to the right call. It is
not prose about the package; it is an interface description, and an interface
description nobody checks is a map of a building that has been renovated.

The failure it guards against is specific and quiet. A command is renamed, a
tool is added, a surface grows a third generator, and the routing table still
names yesterday's. The agent does not read the error: it reports that the tool
does not work. So every command and every tool name that file prints is
resolved here against the surface that would have to answer it.

The same applies to the public API: a README that shows `acled_events` has to
be a README whose `acled_events` is importable.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import sprezzature_maps

REPO = Path(__file__).resolve().parents[1]
TRIGGERS = (REPO / "TRIGGERS.md").read_text(encoding="utf-8")


def _cli_subcommands() -> set[str]:
    """The sub-commands ``make-map`` really accepts, read off its own parser."""
    from sprezzature_maps.cli import build_parser  # noqa: PLC0415

    parser = build_parser()
    return {
        name
        for action in parser._subparsers._group_actions  # type: ignore[union-attr]
        for name in action.choices
    }


def _operation_ids() -> set[str]:
    """Every MCP tool name, which FastAPI takes from each route's operation id."""
    fastapi = pytest.importorskip("fastapi", reason="the API extra is not installed")
    assert fastapi  # the import is the check
    from sprezzature_maps.api import app  # noqa: PLC0415

    return {
        route.operation_id
        for route in app.routes
        if getattr(route, "operation_id", None)
    }


#: Every ``make-map <sub>`` TRIGGERS.md tells an agent to run.
CLI_CALLS = sorted(set(re.findall(r"`make-map ([a-z_]+)", TRIGGERS)))

#: Every MCP tool name it names. They are the only backticked snake_case
#: tokens in the file that are not CLI flags, and each appears in the
#: routing tables as a bare name.
MCP_CALLS = sorted(set(re.findall(r"`(render_[a-z_]+|list_kinds)`", TRIGGERS)))


def test_the_file_actually_names_some_calls() -> None:
    """A parse that silently matched nothing would make every test below pass."""
    assert len(CLI_CALLS) >= 3, f"parsed only {CLI_CALLS} out of TRIGGERS.md"
    assert len(MCP_CALLS) >= 3, f"parsed only {MCP_CALLS} out of TRIGGERS.md"


@pytest.mark.parametrize("sub", CLI_CALLS)
def test_every_command_triggers_names_is_a_command(sub: str) -> None:
    """
    An agent that runs what this file says must not get "invalid choice".

    Spelling counts: the dispatcher's sub-command is ``situation_map`` with an
    underscore, and a routing table that printed ``situation-map`` would send
    every agent that trusts it into an argparse error.
    """
    assert sub in _cli_subcommands(), (
        f"TRIGGERS.md tells an agent to run `make-map {sub}`, and the "
        f"dispatcher accepts {sorted(_cli_subcommands())}"
    )


@pytest.mark.parametrize("tool", MCP_CALLS)
def test_every_tool_triggers_names_is_a_tool(tool: str) -> None:
    """MCP tool names are the FastAPI routes' operation ids, so resolve them there."""
    ids = _operation_ids()
    assert tool in ids, (
        f"TRIGGERS.md advertises the MCP tool {tool!r}; the API exposes {sorted(ids)}"
    )


def test_no_generator_is_missing_from_the_routing_table() -> None:
    """
    The other direction, which is the one that rots.

    A kind added to the dispatcher and not to the routing table is a kind no
    agent will ever choose: the feature ships, and the only document that
    would have sent anyone to it does not mention it.
    """
    missing = sorted(_cli_subcommands() - set(CLI_CALLS))
    assert not missing, (
        f"`make-map` can render {missing}, and TRIGGERS.md never tells an "
        "agent to. Add a row to the routing table."
    )


def test_the_loaders_are_routed_too() -> None:
    """
    A conflict export is a trigger, and it is not the word "map".

    The datasets are named because that is what a user says: they say "I have
    an ACLED file", not "I would like a situation map with precision-aware
    markers".
    """
    for token in ("ACLED", "UCDP", "acled_events", "ucdp_events"):
        assert token in TRIGGERS, f"TRIGGERS.md never mentions {token}"


@pytest.mark.parametrize(
    "name", ["make_choropleth", "make_density", "make_situation_map", "acled_events", "ucdp_events"]
)
def test_every_name_the_docs_promise_is_importable(name: str) -> None:
    """``from sprezzature_maps import X`` has to work for every X the docs show."""
    assert hasattr(sprezzature_maps, name), f"sprezzature_maps.{name} does not exist"
    assert name in sprezzature_maps.__all__, f"{name} is not in __all__"


@pytest.mark.parametrize("doc", ["README.md", "EXAMPLES.md", "TRIGGERS.md", "LANDSCAPE.md"])
def test_the_documented_python_names_exist(doc: str) -> None:
    """
    Any ``from sprezzature_maps import ...`` line in the docs is executable.

    A README is the first thing a new user runs, so a name that drifted out
    of it fails for them before anything else has a chance to work.
    """
    text = (REPO / doc).read_text(encoding="utf-8")
    for line in re.findall(r"from sprezzature_maps import ([^\n]+)", text):
        for name in (n.strip() for n in line.split(",")):
            assert hasattr(sprezzature_maps, name), f"{doc} imports {name}, which does not exist"
