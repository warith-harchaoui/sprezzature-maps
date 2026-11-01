"""
The loop is reachable from the page, not only from the command line.

``sprezzature-maps improve`` existed before this and the editor did not offer
it, which is this repository's most frequent failure wearing a different hat:
the tool works, and nothing calls it. ``sprezzature-figures``' Studio has put
its own loop in front of a reader since it was written; this is the half that
was missing here.

What the page owes a reader who asks for an improvement is the account of it —
what each round read, what changed, and above all what the loop **declined** to
change. Those are the repairs that can alter what the map says about its data,
and printing them is the whole reason the loop is allowed to run unattended at
all.

No model is involved: ``default_client`` is replaced with a scripted fake. The
renderer is real, because a route that only drove a stub would not have proved
a map comes back.

Author
------
Project maintainers.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from sprezzature_maps.studio.app import PAGE_ROUNDS, create_app  # noqa: E402
from sprezzature_maps.studio.assistant import (  # noqa: E402
    FakeLLMClient,
    MapIssue,
    MapReading,
)

POINTS = json.dumps([[2.35, 48.85], [13.4, 52.52], [-0.12, 51.5]])


def _reading(**over: Any) -> MapReading:
    base: dict[str, Any] = {
        "kind_seen": "density", "legend_present": True, "legend_readable": True,
        "verdict": "satisfied", "readability": 80, "colour_separation": 80,
        "geographic_honesty": 80, "clarity": 80, "answers_the_question": 80,
        "issues": [],
    }
    base.update(over)
    return MapReading(**base)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _scripted(monkeypatch: pytest.MonkeyPatch, readings: list[MapReading]) -> FakeLLMClient:
    fake = FakeLLMClient(list(readings))
    monkeypatch.setattr(
        "sprezzature_maps.studio.assistant.default_client", lambda: fake
    )
    return fake


def test_the_editor_offers_the_loop(client: TestClient) -> None:
    """A button, on the same form, so the paste is not retyped to use it."""
    page = client.get("/", params={"kind": "density"}).text
    assert 'formaction="improve"' in page
    assert "Render, look, repair" in page


def test_it_renders_looks_and_reports(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scripted(monkeypatch, [_reading()])
    page = client.post(
        "/improve", data={"kind": "density", "payload": POINTS, "title": "Essai"}
    )
    assert page.status_code == 200
    body = page.text
    assert "map/" in body and ".png" in body, "no improved map came back"
    assert "round 1: read as density" in body
    assert "score 400/500" in body
    assert "stopped: satisfied" in body
    assert "nothing was changed" in body


def test_the_improved_map_is_served_as_a_raster(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scripted(monkeypatch, [_reading()])
    body = client.post("/improve", data={"kind": "density", "payload": POINTS}).text
    url = body.split('<img src="')[1].split('"')[0]
    got = client.get("/" + url)
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/png"
    assert got.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_what_the_loop_declined_is_printed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader's decision, and the reason the loop may run unattended."""
    stuck = _reading(
        kind_seen="choropleth",
        verdict="needs_changes",
        issues=[MapIssue(severity="blocking", what="two bands are the same colour")],
    )
    _scripted(monkeypatch, [stuck, stuck])
    body = client.post(
        "/improve",
        data={"kind": "choropleth", "payload": "id,value\nFRA,68\nDEU,83\n"},
    ).text
    assert "for you to decide: method=" in body
    assert "can change what the map says about the data" in body


def test_a_bad_paste_comes_back_with_the_page_and_the_paste(client: TestClient) -> None:
    """200 and the same page, not a 4xx with a bare detail: the reader is
    mid-edit and losing the paste to see the error is the worse outcome."""
    page = client.post("/improve", data={"kind": "density", "payload": "not json at all"})
    assert page.status_code == 200
    assert "not json at all" in page.text
    assert 'class="error"' in page.text


def test_a_model_that_does_not_answer_is_a_message_not_a_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backend that is not running is something the reader can act on."""
    def _refuse() -> Any:
        raise RuntimeError("no model backend answered")

    monkeypatch.setattr("sprezzature_maps.studio.assistant.default_client", _refuse)
    page = client.post("/improve", data={"kind": "density", "payload": POINTS})
    assert page.status_code == 200
    assert "the loop could not finish" in page.text
    assert "no model backend answered" in page.text
    assert POINTS in page.text, "the paste was lost"


def test_the_page_bounds_the_rounds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A click must not hang for minutes. The command line keeps the ceiling."""
    from sprezzature_maps.studio.ralph import MAX_ROUNDS

    assert PAGE_ROUNDS < MAX_ROUNDS, "the page allows as many rounds as a script"
    varying = [
        _reading(
            verdict="needs_changes",
            issues=[MapIssue(severity="blocking", what=f"the surface looks blocky, {n}")],
        )
        for n in range(10)
    ]
    fake = _scripted(monkeypatch, varying)
    client.post("/improve", data={"kind": "density", "payload": POINTS})
    assert len(fake.calls) <= PAGE_ROUNDS, f"{len(fake.calls)} rounds against {PAGE_ROUNDS}"


def test_an_unknown_token_is_a_404_not_a_path(client: TestClient) -> None:
    """Looked up in the registry rather than built from the token, so a
    crafted token cannot name a file."""
    assert client.get("/map/..%2f..%2fetc%2fpasswd.png").status_code == 404
    assert client.get("/map/deadbeef.png").status_code == 404
