"""Test for the MCP surface: the FastAPI app mounts an MCP endpoint with exactly the
expected tools allowed through, nothing more.

MCP, the Model Context Protocol, is the standard that lets an AI
assistant call a tool directly. This test only checks that the endpoint
exists and exposes the right allowlist; it does not re-check that
rendering actually works, following CODING.md §23.5 ("keep MCP
connectivity tests separate from workflow tests"), since the underlying
render behaviour is already covered by ``test_api.py``, and MCP here is
just a wrapper around those same routes.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi_mcp")

from sprezzature_maps.mcp import app, mcp  # noqa: E402


def test_mcp_endpoint_is_mounted() -> None:
    """The /mcp route exists on the shared FastAPI app."""
    assert any(route.path == "/mcp" for route in app.routes)


def test_mcp_only_exposes_the_allowlisted_tags() -> None:
    """include_tags is exactly {"meta", "actions"} -- nothing exposed by accident."""
    assert set(mcp._include_tags) == {"meta", "actions"}


def _documented_routes(app):
    """This package's own tools -- fastapi-mcp mounts its transport route on
    the same app, and that one is not ours to document."""
    return [
        route
        for route in app.routes
        if getattr(route, "operation_id", None)
        and not getattr(route, "path", "").startswith("/mcp")
    ]


def test_every_tool_has_a_written_summary() -> None:
    """The first line an MCP host shows is FastAPI's `summary`, and its
    default is the function name title-cased: `cvd` became "Cvd", `wer`
    became "Wer". An agent choosing between tools from several servers reads
    those headlines and little else, so each has to be a written phrase
    saying what the tool does -- not a restatement of the Python identifier.
    """
    from sprezzature_maps.api import app

    for route in _documented_routes(app):
        summary = (getattr(route, "summary", "") or "").strip()
        assert summary, f"{route.operation_id}: no summary, so the headline is a function name"
        derived = getattr(route, "name", "").replace("_", " ").title()
        assert summary != derived, (
            f"{route.operation_id}: summary {summary!r} is FastAPI's default (the "
            f"function name title-cased). Write one that says what the tool does."
        )
        assert " " in summary and len(summary) > 15, (
            f"{route.operation_id}: summary {summary!r} is too terse to route on."
        )


def test_every_tool_says_when_to_call_it() -> None:
    """A description that only restates the summary does not help an agent
    choose. Each route's docstring carries the deciding context: when to
    reach for it, what it needs first, or what it must not be used for.
    """
    from sprezzature_maps.api import app

    for route in _documented_routes(app):
        description = (getattr(route, "description", "") or "").strip()
        assert len(description) > 120, (
            f"{route.operation_id}: description is {len(description)} chars. Say when "
            f"to call it, not just what it is."
        )
