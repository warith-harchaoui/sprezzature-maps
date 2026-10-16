"""
sprezzature-maps: the GUI gallery page.

Module summary
--------------
Renders the single HTML page served at the FastAPI app's root address
(see :mod:`sprezzature_maps.api`): a gallery, one tile per map
kind, modeled on the sprezzature-figures gallery
(https://sprezzature.ai/figures.html) but scaled down to
match this smaller repository. That larger page groups around 95 chart
kinds into thematic sections; this repo has exactly two kinds, so it
needs only one section, one tile per kind, and no navigation between them.

The design follows the ``sprezzature-ui`` house rules, applied here by
hand rather than through an actual build toolchain: bringing in an
npm/Tailwind build pipeline (Tailwind is a CSS framework normally
compiled by a JavaScript build step) just for a small static page
would cost more in tooling than it would ever pay back. The rules it
still follows: semantic HTML (markup chosen for its meaning, like
``<nav>`` or ``<article>``, not just generic ``<div>``s); a light or dark
appearance chosen automatically via the browser's
``prefers-color-scheme`` setting; the project's three-typeface pairing
(Roboto for interface text, Roboto Serif for the page title, Roboto Mono
for the kind names); a visible outline around whichever element is
focused, for keyboard users; and a ``prefers-reduced-motion`` guard
(a browser setting a user turns on to ask sites to skip animations)
around the page's one CSS transition, the tile hover effect.

Each tile's map is not a static screenshot. A small vanilla JavaScript
module (plain JavaScript, no framework) calls this same app's own
``/v1/choropleth`` and ``/v1/situation-map`` routes with an empty
request body, which makes each generator fall back to its own built-in
demo data, and inserts the SVG text that comes back directly into the
page. That is a deliberate choice, not a shortcut: it keeps the GUI
honestly wired to the same API surface any other caller would use,
rather than shipping a screenshot that could silently go stale as the
generators change.

Usage example
-------------
>>> html = render_gallery_html()
>>> "<!doctype html>" in html.lower()
True

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from sprezzature_figures.fonts import (
    MONO_STACK,
    SANS_STACK,
    SERIF_STACK,
    available_faces,
    web_font_faces_css,
)

#: Where the FastAPI app mounts sprezzature-figures' bundled font directory
#: (see :mod:`sprezzature_maps.api`). Named here rather than in ``api.py``
#: because the CSS below has to point at the same path the app serves, and
#: two literals that must agree should be one literal.
FONTS_URL_PREFIX = "/fonts"

#: The three families this page sets, and the only ones it links. The suite's
#: typography is three Roboto -- sans for interface text, serif for the page
#: title, mono for the kind names -- so the page names exactly three faces and
#: no more. Latin Modern and the italics ship too and are deliberately absent:
#: linking a face nothing sets is a download nobody needs.
_PAGE_FACES: tuple[str, ...] = ("sans", "serif", "mono")

#: The tiles this gallery shows, in display order. Kept as a plain
#: tuple-of-dicts (not a dataclass) since this is the only place the shape
#: is used -- a dataclass here would be ceremony without a second consumer.
_TILES: tuple[dict[str, str], ...] = (
    {
        "kind": "choropleth",
        "title": "Choropleth",
        "description": (
            "World map, one value per country on a perceptual OKLCH ramp "
            "(sequential or auto-detected diverging), Equal Earth projection "
            "so colored area is not lying about country size."
        ),
        "endpoint": "/v1/choropleth",
    },
    {
        "kind": "situation_map",
        "title": "Situation map",
        "description": (
            "Layered areas-of-control plate for any region: real national "
            "outlines, bathymetry halo, classed pastel zones, dual-unit "
            "scale bar -- the geopolitics-desk look, parameterized."
        ),
        "endpoint": "/v1/situation-map",
    },
    {
        "kind": "density",
        "title": "Density",
        "description": (
            "An accumulation map: where events fell, rather than a value per "
            "territory. Points are binned into a luminous field and the "
            "geography emerges from the data rather than being drawn under it."
        ),
        "endpoint": "/v1/density",
    },
)


def _tile_html(tile: dict[str, str]) -> str:
    """Render one gallery tile's HTML.

    Parameters
    ----------
    tile : dict of str
        One entry of :data:`_TILES`.

    Returns
    -------
    str
        The tile's ``<article>`` markup, including the empty thumbnail
        container the page-load script fills in with a live-rendered SVG.

    Examples
    --------
    >>> "choropleth" in _tile_html(_TILES[0])
    True
    """
    # data-endpoint drives the fetch() call in the inline script below --
    # keeping the URL in markup (not duplicated in the script) means the
    # two tiles share one script instead of one per tile.
    return f"""
    <article class="tile">
      <div class="tile-thumb" id="thumb-{tile["kind"]}" data-endpoint="{tile["endpoint"]}"
           role="img" aria-label="{tile["title"]} example render">
        <p class="tile-loading">Rendering demo&hellip;</p>
      </div>
      <div class="tile-body">
        <h2 class="tile-title">{tile["title"]}</h2>
        <p class="tile-description">{tile["description"]}</p>
        <code class="tile-kind">{tile["kind"]}</code>
      </div>
    </article>"""


def _font_face_css() -> str:
    """``@font-face`` rules for this page's three families, self-hosted.

    The page used to pull Roboto, Roboto Serif and Roboto Mono from
    ``fonts.googleapis.com``. Three things were wrong with that. It put a
    third-party request on every page load of a tool that otherwise runs
    entirely offline -- the same posture as routing every model call through a
    local Ollama. It made the page's typography depend on a network that may
    not be there, falling back to whatever the reader's machine happens to own.
    And it reached past a dependency that already had the fonts:
    ``sprezzature-figures`` vendors all three families and exists partly to be
    the suite's one source of them. ``web/fonts/roboto-serif/fonts.css`` on the
    site states the rule outright -- *self-hosted; do NOT load from a
    third-party CDN* -- and this page was the one place in the suite breaking
    it.

    The faces are filtered through :func:`~sprezzature_figures.fonts.available_faces`
    rather than named blind, because a rule is a URL the app has to be able to
    serve: :mod:`sprezzature_maps.api` mounts the font directory at
    :data:`FONTS_URL_PREFIX`, so a rule for a file that is not there is a 404.
    A browser swallows that one silently and moves to the next family in the
    stack, which is exactly how the serif went missing for a release without
    anyone noticing.

    Returns
    -------
    str
        CSS text, ready to splice into a ``<style>`` element.
    """
    present = set(available_faces())
    return web_font_faces_css(FONTS_URL_PREFIX, tuple(key for key in _PAGE_FACES if key in present))


def render_gallery_html() -> str:
    """Render the complete gallery HTML page.

    Returns
    -------
    str
        A standalone HTML document (doctype through closing ``</html>``),
        self-contained except for the Google Fonts stylesheet request for
        the three Roboto families -- everything else (CSS, JS) is inline,
        so this can be served as-is with no static-file directory.

    Examples
    --------
    >>> html = render_gallery_html()
    >>> html.count("<article")
    2
    """
    tiles_html = "\n".join(_tile_html(tile) for tile in _TILES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>sprezzature-maps</title>
<meta name="description" content="Hand-authored SVG world maps: choropleth and situation maps.">
<style>{_font_face_css()}</style>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #ffffff;
    --fg: #1d1d1f;
    --fg-secondary: #6e6e73;
    --border: #e5e5ea;
    --card-bg: #fafafa;
    --accent: #007aff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0b0b0d;
      --fg: #f2f2f7;
      --fg-secondary: #9a9aa0;
      --border: #2c2c2e;
      --card-bg: #151517;
      --accent: #409cff;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--fg);
    font-family: {SANS_STACK};
    line-height: 1.5;
  }}
  header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 1.5rem 2rem;
    border-bottom: 1px solid var(--border);
  }}
  header h1 {{
    font-family: {SERIF_STACK};
    font-size: 1.4rem;
    font-weight: 600;
    margin: 0;
  }}
  header nav a {{
    color: var(--fg-secondary);
    text-decoration: none;
    margin-left: 1.25rem;
    font-size: 0.9rem;
  }}
  header nav a:focus-visible, .tile:focus-within {{
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }}
  main {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1.5rem;
  }}
  .tile {{
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    background: var(--card-bg);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }}
  @media (prefers-reduced-motion: reduce) {{
    .tile {{ transition: none; }}
  }}
  .tile:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
  .tile-thumb {{
    aspect-ratio: 16 / 9;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    overflow: hidden;
  }}
  .tile-thumb svg {{ width: 100%; height: 100%; }}
  .tile-loading {{ color: var(--fg-secondary); font-size: 0.85rem; }}
  .tile-body {{ padding: 1.1rem 1.25rem 1.4rem; }}
  .tile-title {{ margin: 0 0 0.4rem; font-size: 1.1rem; }}
  .tile-description {{ margin: 0 0 0.7rem; color: var(--fg-secondary); font-size: 0.92rem; }}
  .tile-kind {{
    font-family: {MONO_STACK};
    font-size: 0.78rem;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
  }}
  footer {{
    text-align: center;
    padding: 2rem;
    color: var(--fg-secondary);
    font-size: 0.85rem;
  }}
  footer a {{ color: inherit; }}
</style>
</head>
<body>
<header>
  <h1>sprezzature&#8202;.&#8202;maps</h1>
  <nav>
    <a href="/docs">API docs</a>
    <a href="https://github.com/warith-harchaoui/sprezzature-maps">GitHub</a>
  </nav>
</header>
<main>
{tiles_html}
</main>
<footer>
  Part of the <a href="https://sprezzature.ai/">sprezzature</a> suite.
</footer>
<script>
  // Each tile fetches its own live demo render from this same app's API
  // (not a pre-baked screenshot) and injects the returned SVG text
  // directly -- so the gallery can never silently drift from what the
  // generators actually produce.
  document.querySelectorAll(".tile-thumb").forEach(async (el) => {{
    const endpoint = el.dataset.endpoint;
    try {{
      const res = await fetch(endpoint, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: "{{}}",
      }});
      if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
      el.innerHTML = await res.text();
    }} catch (err) {{
      el.innerHTML = `<p class="tile-loading">Could not load demo (${{err.message}}).</p>`;
    }}
  }});
</script>
</body>
</html>"""
