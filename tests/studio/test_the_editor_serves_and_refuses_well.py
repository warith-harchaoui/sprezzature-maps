"""
The Studio's three routes, and the property a refusal has to keep.

Why this file exists
--------------------
The interface *is* the HTTP surface here — there is no NiceGUI layer to test
through — so these are the tests of the Studio as a reader meets it: open a
kind, paste something, get a map or a sentence.

The one worth naming is the refusal. A render that fails returns **200 with
the same page**, carrying the message and everything that was typed. A 4xx
with a bare detail would be correct for an API and wrong here: the reader is
mid-edit, and losing the paste in order to see the error is a worse outcome
than the error. Two tests below assert exactly that, because it is the kind of
behaviour a later refactor "tidies" into a proper status code.

And the messages are not the Studio's own. The pasted text is written to a
temporary file and handed to :mod:`sprezzature_maps.data` — the functions
``--data``, ``--config`` and ``--points`` call — so the Studio cannot come to
a different conclusion than the command line about the same bytes. The test
for that asserts a message this package wrote for a terminal appears in a web
page, which is the point rather than a coincidence.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re

import pytest

from sprezzature_maps.kinds import KINDS, kind_names

fastapi = pytest.importorskip(
    "fastapi", reason="fastapi is a base dependency; a skip here means a broken install"
)
from fastapi.testclient import TestClient  # noqa: E402

from sprezzature_maps.studio.app import create_app  # noqa: E402

#: A rendered map's URL in the returned page, which is how a test gets from a
#: POST to the file it produced without the Studio having to expose a token.
_SVG_IN_PAGE = re.compile(r'data="(map/[0-9a-f]+\.svg)"')

#: The error paragraph, matched by its role so this does not depend on the
#: class name surviving a restyle.
_ERROR_IN_PAGE = re.compile(r'role="alert">(.*?)</p>', re.S)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


# ── the page ──────────────────────────────────────────────────────────────


def test_the_default_page_opens_on_a_real_kind(client: TestClient) -> None:
    """No ``?kind=`` is not an error; it is the first kind in the registry."""
    response = client.get("/")
    assert response.status_code == 200
    assert KINDS[0].label in response.text


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_every_kind_has_its_own_addressable_page(entry, client: TestClient) -> None:
    """A kind is a URL, so it can be shared, bookmarked and tested with one GET.

    The page has to name the option that supplies this kind's data, because
    that is the one word connecting the box on screen to the documentation a
    reader already has.
    """
    response = client.get(f"/?kind={entry.name}")
    assert response.status_code == 200
    assert entry.data_option in response.text, (
        f"the {entry.name} page does not name {entry.data_option}"
    )
    assert all(name in response.text for name in kind_names()), (
        "the other kinds are not reachable from this one"
    )


def test_a_hyphenated_kind_in_the_url_works(client: TestClient) -> None:
    """``?kind=situation-map`` and ``?kind=situation_map`` are one page.

    The command line spells it both ways; a URL a reader types by hand should
    not have to know which.
    """
    assert client.get("/?kind=situation-map").status_code == 200
    assert client.get("/?kind=situation_map").status_code == 200


def test_an_unknown_kind_is_a_404_that_names_the_real_ones(client: TestClient) -> None:
    """A stale bookmark says so, rather than silently opening something else.

    Falling back to the first kind would be friendlier and wrong: the reader
    asked for a map this package does not draw, and would spend a while
    wondering why the page looks unfamiliar.
    """
    response = client.get("/?kind=hexmap")
    assert response.status_code == 404
    for name in kind_names():
        assert name in response.json()["detail"]


# ── rendering ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("entry", KINDS, ids=lambda e: e.name)
def test_an_empty_paste_renders_the_demo(entry, client: TestClient) -> None:
    """Empty is a choice, not a mistake.

    Every generator renders its built-in demo when handed nothing, which is
    what a Studio should show before a file has been chosen.
    """
    response = client.post("/render", data={"kind": entry.name, "payload": "", "title": ""})
    assert response.status_code == 200
    found = _SVG_IN_PAGE.search(response.text)
    assert found, f"{entry.name} rendered no map from an empty paste"
    served = client.get("/" + found.group(1))
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/svg+xml")
    assert len(served.content) > 1000


@pytest.mark.parametrize(
    ("kind_name", "payload"),
    [
        ("choropleth", "id,value\n840,12.5\n124,-3.2\n"),
        ("choropleth", '[{"id": "840", "value": 12.5}]'),
        ("density", "[[2.35, 48.86], [-0.13, 51.51], [13.4, 52.5]]"),
    ],
    ids=["rows-as-csv", "rows-as-json", "points-in-europe"],
)
def test_a_pasted_payload_renders(kind_name: str, payload: str, client: TestClient) -> None:
    """Both row formats, and points the generator's own default box excludes.

    The European points are the regression: before the Studio inferred a
    bounding box, three capitals answered "no point fell inside the bbox".
    """
    response = client.post(
        "/render", data={"kind": kind_name, "payload": payload, "title": "a test"}
    )
    found = _SVG_IN_PAGE.search(response.text)
    assert found, f"no map came back:\n{_ERROR_IN_PAGE.findall(response.text)}"
    assert client.get("/" + found.group(1)).status_code == 200


def test_a_refusal_keeps_the_paste_and_stays_on_the_page(client: TestClient) -> None:
    """The property this surface exists to keep.

    200, the same page, the message, and the text still in the box. A reader
    mid-edit who loses their paste to see an error has been punished for a
    typo.
    """
    payload = "Code,Score\n840,12.5\n"
    response = client.post(
        "/render", data={"kind": "choropleth", "payload": payload, "title": "mine"}
    )
    assert response.status_code == 200, "a refusal must not take the page away"
    assert _SVG_IN_PAGE.search(response.text) is None, "a refusal must not show a stale map"
    assert "Code" in response.text and "Score" in response.text, (
        "the pasted text was not echoed back, so the reader has lost it"
    )
    assert 'value="mine"' in response.text, "the title was not echoed back"


def test_the_refusal_carries_the_command_lines_own_message(client: TestClient) -> None:
    """Because the Studio reads through `data.py`, not through a second parser.

    This is the assertion that proves the reuse rather than describing it: the
    sentence below was written for a terminal, names the row, the real columns
    and the flag that fixes it, and arrives unchanged in a web page.
    """
    response = client.post(
        "/render", data={"kind": "choropleth", "payload": "Code,Score\n840,1\n", "title": ""}
    )
    message = " ".join(_ERROR_IN_PAGE.findall(response.text))
    assert "Row 0" in message
    assert "--map" in message, f"the fix is not named: {message}"


def test_a_geojson_paste_into_the_points_box_says_what_it_got(client: TestClient) -> None:
    """The mistake someone actually makes, and the message it earns."""
    response = client.post(
        "/render",
        data={"kind": "density", "payload": '{"type": "FeatureCollection"}', "title": ""},
    )
    message = " ".join(_ERROR_IN_PAGE.findall(response.text))
    assert "must be a list, got dict" in message


def test_a_generator_refusal_is_shown_as_written(client: TestClient) -> None:
    """Not every refusal comes from the reader's paste.

    A frame with no events in it is the generator's own judgement, and it is
    actionable as written, so it is shown rather than wrapped in something
    about the Studio.
    """
    response = client.post(
        "/render",
        data={"kind": "density", "payload": "[[200.0, 80.0]]", "title": ""},
    )
    assert response.status_code == 200
    assert _ERROR_IN_PAGE.search(response.text) or _SVG_IN_PAGE.search(response.text), (
        "neither a map nor a message came back, which is the one outcome a "
        "reader cannot act on"
    )


# ── the rendered file ─────────────────────────────────────────────────────


def test_an_unknown_token_is_a_404(client: TestClient) -> None:
    """Which is also what a reload after a restart gets.

    The page it came from still holds the input, so the way out is to render
    again — and that is why the input lives in the page rather than here.
    """
    response = client.get("/map/deadbeefdeadbeef.svg")
    assert response.status_code == 404


def test_a_token_cannot_name_a_path(client: TestClient) -> None:
    """Looked up in a dict, not built from the token.

    Traversal is the obvious thing to try on a route ending ``.svg``, so the
    lookup is a dict and this is the test that it stays one.
    """
    for crafted in ("..%2F..%2Fetc%2Fpasswd", "....//....//etc/passwd"):
        assert client.get(f"/map/{crafted}.svg").status_code in (404, 400)
