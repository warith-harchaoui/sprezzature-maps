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
