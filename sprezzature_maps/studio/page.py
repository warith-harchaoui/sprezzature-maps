"""
sprezzature-maps Studio: the editor page, server-rendered.

Module summary
--------------
One HTML document, built the way :mod:`sprezzature_maps.gui` builds the
gallery — hand-written markup, the palette and typographic base from
:data:`sprezzature_maps.gui.THEME_CSS`, the three Roboto families from
:func:`sprezzature_maps.gui.font_face_css`. No build step, no NiceGUI, and no
second palette: the tokens are the gallery's, because two pages with two
hand-kept copies of one palette is the same defect as the five hand-kept lists
of three map kinds this package has just finished ending.

Why there is no JavaScript in it
--------------------------------
Because the page does not need any. Choosing a kind is a link, supplying data
is a form, and rendering is a POST that comes back with the map in it. The
input panel differs per kind — rows, a config, a list of positions — and the
server already knows which from
:attr:`sprezzature_maps.kinds.MapKind.data_shape`, so the branch happens where
the knowledge is rather than being shipped to the browser to happen again.

A conversational panel is next and will need a request per message. That is
still a form.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from html import escape

from sprezzature_maps.gui import FONTS_URL_PREFIX, THEME_CSS, font_face_css
from sprezzature_maps.kinds import KINDS, MapKind

#: What to put in the payload box, per shape, when it is empty. Not a
#: placeholder attribute: a placeholder vanishes the moment anybody types, and
#: this is the one piece of help a reader needs *while* typing. Shown as a
#: caption under the box instead.
SHAPE_HELP: dict[str, str] = {
    "rows": (
        "One row per territory. CSV with an <code>id</code> and a "
        "<code>value</code> column, or JSON like "
        "<code>[{&quot;id&quot;: &quot;840&quot;, &quot;value&quot;: 12.5}]</code>. "
        "The id is an ISO country code."
    ),
    "config": (
        "A region configuration, YAML or JSON: a mapping with a "
        "<code>title</code> and a <code>zones</code> list in it. The zones are "
        "a list <em>inside</em> the config, not the whole document."
    ),
    "points": (
        "Event positions as <code>[[lon, lat], ...]</code>. The frame is "
        "inferred from the points, so events anywhere on earth render — the "
        "generator's own default box is the continental United States."
    ),
}

#: Shown when the box is left empty, which is a real choice rather than a
#: mistake: every generator renders a built-in demo when handed nothing, and
#: that is what a Studio should show before a file has been chosen.
EMPTY_IS_FINE = "Leave it empty to render this kind's built-in demo."


def _kind_nav(current: str) -> str:
    """The kind selector, as links rather than a control.

    A link is addressable: ``/studio?kind=density`` can be shared, bookmarked
    and tested with one GET, and the back button does what a reader expects.
    """
    items = []
    for entry in KINDS:
        active = ' aria-current="page"' if entry.name == current else ""
        items.append(
            f'<a href="?kind={entry.name}"{active}>{escape(entry.label)}</a>'
        )
    return '<nav class="kinds">' + "".join(items) + "</nav>"


def render_editor_html(
    entry: MapKind,
    *,
    payload_text: str = "",
    title: str = "",
    svg_url: str | None = None,
    png_url: str | None = None,
    error: str | None = None,
    report: list[str] | None = None,
) -> str:
    """Render the editor page for one kind.

    Parameters
    ----------
    entry : sprezzature_maps.kinds.MapKind
        The kind being edited. Its ``data_shape`` chooses the help text and
        its ``label`` the heading, so adding a fourth kind to the registry
        gives this page a fourth tab with no edit here.
    payload_text : str, optional
        What the reader typed, echoed back so a failed render does not lose
        it. This is the whole reason the page re-renders rather than
        redirecting.
    title : str, optional
        The map title, echoed back for the same reason.
    svg_url : str, optional
        Where the rendered map can be fetched. Served from a route rather
        than inlined: a situation plate is 2.2 MB of SVG, and inlining that
        into every re-render makes the page heavier than the map.
    error : str, optional
    png_url : str, optional
        Where an improved map can be fetched, when the loop produced one. The
        loop renders PNG because a vision model has to be shown a picture.
    report : list of str, optional
        What the loop did, one line per round, plus what it refused to do
        alone. Shown under the map: a reader who asked for an improvement is
        owed the account of it, and the changes it declined are the ones they
        have to decide.
    error : str, optional
        A message to show instead of a map. Shown *above* the form, because a
        reader who has just been refused is looking at what they typed.

    Returns
    -------
    str
        A standalone HTML document.

    Examples
    --------
    >>> from sprezzature_maps.kinds import kind, kind_names
    >>> html = render_editor_html(kind("density"))
    >>> "<form" in html and "Density" in html
    True
    >>> # the three kinds are always reachable, whichever one is open
    >>> all(name in html for name in kind_names())
    True
    """
    help_text = SHAPE_HELP[entry.data_shape]
    error_html = (
        f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    )
    report_html = (
        '<section class="report" aria-label="What the loop did"><ol>'
        + "".join(f"<li>{escape(line)}</li>" for line in report)
        + "</ol></section>"
        if report
        else ""
    )
    if png_url:
        # The loop renders PNG, because what it does is show the picture to a
        # vision model, and a model handed SVG source reads the markup instead
        # of looking. So the improved map arrives as a raster and is shown as
        # one; `alt` names the kind rather than describing the map, because
        # nothing here has read it.
        figure_html = (
            f'<figure><img src="{escape(png_url)}" '
            f'alt="The improved {escape(entry.label.lower())}, rendered."></figure>'
        )
    elif svg_url:
        figure_html = (
            f'<figure><object type="image/svg+xml" data="{escape(svg_url)}">'
            f"<p>The rendered {escape(entry.label.lower())} could not be displayed "
            f'inline. <a href="{escape(svg_url)}">Open the SVG</a>.</p>'
            f"</object></figure>"
        )
    else:
        figure_html = (
            '<figure class="empty"><p>Nothing rendered yet. '
            f"{escape(EMPTY_IS_FINE)}</p></figure>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sprezzature Studio — maps</title>
<meta name="description" content="A conversational editor for choropleth, situation and density maps.">
<style>{font_face_css()}</style>
<style>{THEME_CSS}</style>
<style>
  header {{
    display: flex; align-items: baseline; justify-content: space-between;
    padding: 1.25rem 2rem; border-bottom: 1px solid var(--border);
    flex-wrap: wrap; gap: 0.75rem;
  }}
  header h1 {{ font-family: var(--serif, serif); font-size: 1.3rem; margin: 0; }}
  nav.kinds a {{
    color: var(--fg-secondary); text-decoration: none; margin-left: 1.1rem;
    padding-bottom: 2px; border-bottom: 2px solid transparent;
  }}
  nav.kinds a[aria-current="page"] {{ color: var(--fg); border-bottom-color: var(--accent); }}
  main {{
    display: grid; grid-template-columns: minmax(18rem, 24rem) 1fr;
    gap: 1.5rem; padding: 1.5rem 2rem; align-items: start;
  }}
  @media (max-width: 52rem) {{ main {{ grid-template-columns: 1fr; }} }}
  form {{ display: flex; flex-direction: column; gap: 0.75rem; }}
  .report ol {{ margin: 1rem 0 0; padding-left: 1.4rem; line-height: 1.5; }}
  .report li {{ margin-bottom: 0.35rem; }}
  label {{ font-size: 0.85rem; color: var(--fg-secondary); }}
  textarea, input[type=text] {{
    width: 100%; background: var(--card-bg); color: var(--fg);
    border: 1px solid var(--border); border-radius: 6px; padding: 0.6rem;
    font-family: var(--mono, monospace); font-size: 0.85rem;
  }}
  textarea {{ min-height: 11rem; resize: vertical; }}
  button {{
    background: var(--accent); color: #fff; border: 0; border-radius: 6px;
    padding: 0.6rem 1rem; font-size: 0.95rem; cursor: pointer;
  }}
  p.help {{ font-size: 0.8rem; color: var(--fg-secondary); margin: 0; }}
  p.error {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-left: 3px solid #d7263d; border-radius: 6px;
    padding: 0.7rem 0.9rem; margin: 0 0 1rem; font-size: 0.88rem;
  }}
  figure {{ margin: 0; }}
  figure object {{ width: 100%; min-height: 24rem; }}
  figure.empty p {{
    border: 1px dashed var(--border); border-radius: 8px; padding: 3rem 1rem;
    text-align: center; color: var(--fg-secondary);
  }}
  :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
</style>
</head>
<body>
<header>
  <h1>Sprezzature Studio <span style="color:var(--fg-secondary)">— maps</span></h1>
  {_kind_nav(entry.name)}
</header>
<main>
  <section>
    {error_html}
    <form method="post" action="render">
      <input type="hidden" name="kind" value="{escape(entry.name)}">
      <label for="title">Title</label>
      <input type="text" id="title" name="title" value="{escape(title)}">
      <label for="payload">{escape(entry.data_option)} &mdash; {escape(entry.data_shape)}</label>
      <textarea id="payload" name="payload" spellcheck="false">{escape(payload_text)}</textarea>
      <p class="help">{help_text} {escape(EMPTY_IS_FINE)}</p>
      <button type="submit">Render</button>
      <button type="submit" formaction="improve">Render, look, repair</button>
    </form>
  </section>
  <section>{figure_html}{report_html}</section>
</main>
<p style="padding:0 2rem 2rem;color:var(--fg-secondary);font-size:0.8rem">
  Fonts served from <code>{escape(FONTS_URL_PREFIX)}</code>; nothing is fetched
  from a third party.
</p>
</body>
</html>
"""
