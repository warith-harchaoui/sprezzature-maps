"""
The gallery page must fetch nothing from a third party, and must be able to
serve everything it asks for.

It used to open with three tags pointing at ``fonts.googleapis.com``, pulling
Roboto, Roboto Serif and Roboto Mono from Google on every load. Three things
were wrong with that, in rising order of how much they matter.

It was a network dependency in a tool that otherwise needs none: this package
renders maps from vendored rasters, and the suite routes even its model calls
through a local Ollama. A reader offline, or behind a filter, got the page
drawn in whatever their machine happened to own.

It was a third-party request from a page served off a developer's own machine
-- the kind of thing a privacy review flags and a user cannot opt out of.

And it reached past a dependency that already had the fonts. This package
depends on ``sprezzature-figures``, which vendors all three families and
exists in part to be the suite's single source of them. And the rule is
written down rather than assumed -- ``sprezzature-ui``'s SKILL.md, on the
three-Roboto rule: *"Self-host always (no Google Fonts CDN, no jsDelivr GH
proxy in production builds)"*. Checked across all eight repositories, this page
was the only place breaking it.

So the first test below is the rule, stated as the absence of any external
host. The second is its other half, and the reason the first is not enough on
its own: self-hosting means the app has to actually serve what the page links.
A rule pointing at a path the app does not mount is a 404 -- and a browser
swallows a dead ``@font-face`` source in silence, moving to the next family in
the stack, which is precisely how the serif went missing from
``sprezzature-figures``' wheel for a release without anyone noticing.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import re

import pytest

from sprezzature_maps.gui import FONTS_URL_PREFIX, render_gallery_html

fastapi = pytest.importorskip("fastapi", reason="the GUI is served by the [api] extra")

#: Hosts a self-hosted page may never reach for. Not an exhaustive blocklist
#: -- :func:`test_the_page_fetches_no_subresource_from_off_machine` is the
#: general rule and this
#: is the specific regression, kept because it is the one that actually
#: happened and should fail by name if it comes back.
_FONT_CDNS = ("fonts.googleapis.com", "fonts.gstatic.com")


@pytest.fixture(scope="module")
def client() -> object:
    from fastapi.testclient import TestClient

    from sprezzature_maps.api import app

    return TestClient(app)


def test_the_page_fetches_no_subresource_from_off_machine() -> None:
    """Nothing the browser loads on its own may come from another host.

    Deliberately broader than the font CDNs: an analytics beacon, a CSS reset
    from unpkg, an icon sprite would each be the same defect wearing different
    clothes, so the rule is about the category rather than the list of hosts
    thought of so far.

    The distinction that matters is *who decides to fetch*. A ``<a href>`` to
    the repository or to sprezzature.ai is navigation the reader chooses and
    the page stays entirely local until they click; a stylesheet, a script, an
    image or a ``url()`` is fetched the moment the page opens, whether the
    reader wanted it or not. Only the second kind is checked here -- which is
    why anchor tags are stripped before looking.
    """
    html = render_gallery_html()
    without_links = re.sub(r"<a\b[^>]*>", "", html, flags=re.IGNORECASE)
    external = sorted(set(re.findall(r"https?://[^\s\"'<>)]+", without_links)))
    assert not external, f"the gallery page fetches from off-machine: {external}"


def test_the_font_cdn_specifically_is_gone() -> None:
    """The regression, by name, so a reintroduction reads as itself."""
    html = render_gallery_html()
    for host in _FONT_CDNS:
        assert host not in html, f"{host} is back in the gallery page"


def test_every_font_the_page_links_is_served_by_the_app(client: object) -> None:
    """Self-hosting is a claim about the server, so ask the server.

    This is the half a "no CDN" check cannot cover: removing the external tags
    and leaving the ``@font-face`` rules pointing at an unmounted path would
    pass that check and still draw the page in Georgia.
    """
    page = client.get("/")  # type: ignore[attr-defined]
    assert page.status_code == 200

    linked = re.findall(rf"url\('({re.escape(FONTS_URL_PREFIX)}/[^']+)'", page.text)
    assert linked, "the page links no fonts at all"

    for url in linked:
        response = client.get(url)  # type: ignore[attr-defined]
        assert response.status_code == 200, (
            f"{url} is linked but not served ({response.status_code})"
        )
        assert response.headers["content-type"] == "font/woff2", url
        assert len(response.content) > 1024, f"{url} served an implausibly small file"


def test_the_page_sets_the_three_roboto_and_no_fourth_family(client: object) -> None:
    """The suite's typography is three Roboto -- sans, serif, mono -- and the
    page links exactly those three. Not the italics, not Latin Modern: they
    ship in the dependency too, and a rule for a face nothing sets is a
    download nobody needs."""
    page = client.get("/")  # type: ignore[attr-defined]
    families = sorted(set(re.findall(r"font-family:'([^']+)'", page.text)))
    assert families == ["Roboto", "Roboto Mono", "Roboto Serif"]


def test_the_stacks_are_imported_rather_than_retyped() -> None:
    """A retyped stack is a stack free to drift from the faces behind it.

    That is not hypothetical here: the density plate embedded Roboto while
    every one of its ``<text>`` elements asked for Georgia, because the names
    were typed in by hand on both sides. The page's three declarations now come
    from ``sprezzature_figures.fonts``, so a change there reaches this page
    instead of leaving it behind.
    """
    from sprezzature_figures.fonts import MONO_STACK, SANS_STACK, SERIF_STACK

    html = render_gallery_html()
    for stack in (SANS_STACK, SERIF_STACK, MONO_STACK):
        assert f"font-family: {stack};" in html, f"{stack!r} is not what the page sets"
