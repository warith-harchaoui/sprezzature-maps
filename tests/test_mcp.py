"""MCP surface test: the FastAPI app mounts an MCP endpoint with the
expected tools allowlisted, nothing more.

Connectivity-only, per CODING.md Sec 23.5 ("keep MCP connectivity tests
separate from workflow tests") -- the underlying render behavior is
already covered by ``test_api.py`` since MCP wraps the same routes.
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
