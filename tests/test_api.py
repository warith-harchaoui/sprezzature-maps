"""Tests that the HTTP API keeps its contract: the FastAPI surface renders both map kinds correctly.

These tests cover the same scenarios that were checked by hand while
building ``sprezzature_maps/api.py``: the health check, kind discovery,
both render routes (using
demo data and caller-supplied data, in more than one output format), the
GUI gallery route, and the case where a caller sends a malformed request
and the server should answer with HTTP status 422, "Unprocessable
Entity" (the standard response code for "your request was well-formed
but its content doesn't make sense"). This is one scenario-style file
covering many small cases together, following CODING.md's "prefer
functional tests over one test per function" guidance, since these
routes are thin adapters over generators that already have their own
unit tests.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from sprezzature_maps.api import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    """The liveness probe reports ok with no side effects."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_kinds() -> None:
    """The two map kinds this repo carries are discoverable, not hardcoded by callers."""
    response = client.get("/v1/kinds")
    assert response.status_code == 200
    assert response.json() == ["choropleth", "situation_map"]


def test_render_choropleth_demo_svg() -> None:
    """An empty body renders the built-in demo data as a valid, non-trivial SVG."""
    response = client.post("/v1/choropleth", json={})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert b"<svg" in response.content
    assert len(response.content) > 1000


def test_render_choropleth_custom_data_png() -> None:
    """Caller-supplied rows (including a negative value, triggering the diverging
    ramp) render as PNG with the matching Content-Type."""
    body = {
        "data": [{"id": "840", "value": 12.5}, {"id": "124", "value": -3.2}],
        "format": "png",
    }
    response = client.post("/v1/choropleth", json=body)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # PNG magic bytes -- proves this is really a raster image, not the SVG
    # text mislabelled.
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_choropleth_rejects_bad_row() -> None:
    """A row missing the required 'value' field is a caller error (422), not a 500."""
    response = client.post("/v1/choropleth", json={"data": [{"id": "840"}]})
    assert response.status_code == 422


def test_render_situation_map_demo() -> None:
    """An empty body renders the bundled Western-Europe demo config."""
    response = client.post("/v1/situation-map", json={})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert b"<svg" in response.content


def test_gallery_page_serves_html() -> None:
    """The GUI gallery is served at the app root."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert response.text.count("<article") == 2


def test_a_classed_map_always_names_its_method() -> None:
    """
    The legend states the classification, because omitting it misleads.

    The same values classed four ways tell four stories. A map that does not
    say how it was classed asks to be misread, and the reader has no way to
    know they are being asked. So this is not cosmetic: the method belongs on
    the artefact, not only in the call that made it.
    """
    rows = [
        {"id": "356", "value": 2485},
        {"id": "108", "value": 238},
        {"id": "442", "value": 128259},
        {"id": "250", "value": 44461},
        {"id": "840", "value": 82769},
    ]
    for method, label in (
        ("quantile", "quantiles"),
        ("equal", "equal intervals"),
        ("jenks", "natural breaks"),
        ("headtail", "head/tail breaks"),
    ):
        resp = client.post(
            "/v1/choropleth", json={"data": rows, "classes": 3, "method": method}
        )
        assert resp.status_code == 200, resp.text
        assert label in resp.text, f"{method}: the legend does not name the method"


def test_an_unclassed_map_is_unchanged() -> None:
    """Omitting `classes` renders exactly what this generator always did."""
    rows = [{"id": "250", "value": 3.0}, {"id": "840", "value": 9.0}]
    without = client.post("/v1/choropleth", json={"data": rows})
    explicit_none = client.post("/v1/choropleth", json={"data": rows, "classes": None})
    assert without.status_code == explicit_none.status_code == 200
    assert without.content == explicit_none.content
