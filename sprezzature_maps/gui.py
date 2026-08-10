"""
sprezzature-maps — GUI gallery page.

Module summary
--------------
Renders the single HTML page served at the FastAPI app's root (see
:mod:`sprezzature_maps.api`): a two-tile gallery, one per map kind, modeled
on the sprezzature-figures gallery
(https://harchaoui.org/warith/sprezzature/figures.html) but scaled down --
that page groups ~95 chart kinds into thematic sections; this repo has
exactly two kinds, so it is one section, two tiles, no navigation needed
between them.

Design intent (the ``sprezzature-ui`` house rules, applied by hand rather
than through the actual Tailwind build toolchain -- introducing an npm/
Tailwind pipeline for a two-tile static page would be disproportionate to
what it buys): semantic HTML, light/dark via ``prefers-color-scheme``,
the three-Roboto typography pairing (Roboto sans for UI text, Roboto Serif
for the page title, Roboto Mono for the kind names), visible focus rings,
and a ``prefers-reduced-motion`` guard around the one CSS transition this
page has (the theme-appropriate tile hover).

Each tile's map is not a static screenshot: a small vanilla-JS module
``fetch()``-calls this same app's own ``/v1/choropleth`` and
``/v1/situation-map`` routes (empty body -> each generator's built-in demo
data) and injects the returned SVG text directly into the page. That is a
deliberate choice, not a shortcut -- it keeps the GUI honestly wired to the
same API surface a caller would use, rather than shipping a screenshot that
could silently drift from what the generators actually produce.

Usage example
-------------
>>> html = render_gallery_html()
>>> "<!doctype html>" in html.lower()
True

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

#: The two tiles this gallery shows, in display order. Kept as a plain
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400;500&family=Roboto+Serif:opsz,wght@8..144,600&display=swap" rel="stylesheet">
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
    font-family: "Roboto", -apple-system, BlinkMacSystemFont, sans-serif;
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
    font-family: "Roboto Serif", Georgia, serif;
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
    font-family: "Roboto Mono", ui-monospace, monospace;
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
  Part of the <a href="https://harchaoui.org/warith/sprezzature/">sprezzature</a> suite.
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
