"""
_sidecar: what a content management system needs next to the map file.

A map that illustrates an article is not the deliverable; the article is.
Around the image a page still needs an ``alt`` string, a caption, a credit
line and, if the piece is doing its job, the numbers the map asserts. Today
every one of those is typed a second time into the CMS, by hand, from
looking at the picture -- which is how a caption ends up disagreeing with
the plate above it after one of them is corrected and the other is not.

So this does not read the config. It reads **the finished SVG**: the
``<title>``/``<desc>`` the accessibility work already writes, and the
``data-*`` attributes the zones and markers already carry (svgis's
``--data-fields`` idea, which is what made this possible at all). A sidecar
derived from the artifact cannot drift from the artifact.

The ``alt`` string follows the formula accessibility practice has settled
on for charts -- *what kind of thing it is, what is in it, and what it
shows* -- because the third part is the one a generated description almost
always omits and the one a reader actually needs. Here the takeaway is
computed from the areas the plate really drew, not asserted.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from typing import Any

#: ``data-*`` on a control zone, written by ``_areas_of_control_layer``.
_ZONE_RE = re.compile(
    r'data-category="([^"]*)" data-confidence="([^"]*)" data-area-share="([\d.]+)"'
)

#: ``data-*`` on a marker, written by ``_markers_layer``. The radius is
#: optional, so it is captured as its own group that may be absent.
_MARKER_RE = re.compile(
    r'data-precision="(\d)" data-lon="(-?[\d.]+)" data-lat="(-?[\d.]+)"'
    r'(?: data-radius-km="([\d.]+)")?'
)

#: The root ``<title>``/``<desc>``, whichever kind wrote them. Matched on the
#: element rather than on an id: the situation map stamps ``sm-title`` and the
#: choropleth ``cx-title``, and keying on one of them made this return a
#: hollow record for the other kinds -- an empty title, an empty alt string
#: and no error, which is the quietest way to be useless.
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.S)
_DESC_RE = re.compile(r"<desc\b[^>]*>(.*?)</desc>", re.S)


def _unescape(text: str) -> str:
    """Undo the three-character XML escape the generators apply on the way out."""
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def article_sidecar(svg: str) -> dict[str, Any]:
    """Return the metadata a page needs around ``svg``, read back out of it.

    Parameters
    ----------
    svg : str
        A finished plate, as returned by a generator's ``build_map`` /
        ``build_svg``.

    Returns
    -------
    dict
        ``title``, ``alt``, ``description``, ``zones`` and ``markers``.
        ``zones`` and ``markers`` are empty lists for a plate that draws
        neither, which is the normal case for a locator map.

    Examples
    --------
    >>> svg = (
    ...     '<svg><title id="sm-title">Who holds what</title>'
    ...     '<desc id="sm-desc">Situation map covering 1.0°E to 2.0°E.</desc>'
    ...     '<path data-category="Blue" data-confidence="assessed" data-area-share="0.7000"/>'
    ...     '<path data-category="Red" data-confidence="claimed" data-area-share="0.3000"/>'
    ...     "</svg>"
    ... )
    >>> card = article_sidecar(svg)
    >>> card["title"]
    'Who holds what'
    >>> [z["category"] for z in card["zones"]]
    ['Blue', 'Red']
    >>> card["alt"]
    'Situation map covering 1.0°E to 2.0°E. Blue covers the largest mapped share, 70%.'

    A plate whose largest zone is only claimed says so, because "covers" and
    "is claimed to cover" are different sentences:

    >>> swapped = svg.replace('data-area-share="0.7000"', 'data-area-share="0.2000"')
    >>> article_sidecar(swapped)["alt"].endswith(
    ...     'Red is claimed to cover the largest mapped share, 30%.')
    True
    """
    title_match = _TITLE_RE.search(svg)
    desc_match = _DESC_RE.search(svg)
    title = _unescape(title_match.group(1)) if title_match else ""
    description = _unescape(desc_match.group(1)) if desc_match else ""

    zones = [
        {"category": _unescape(cat), "confidence": conf, "area_share": float(share)}
        for cat, conf, share in _ZONE_RE.findall(svg)
    ]
    markers = [
        {
            "precision": int(precision),
            "lon": float(lon),
            "lat": float(lat),
            **({"radius_km": float(radius)} if radius else {}),
        }
        for precision, lon, lat, radius in _MARKER_RE.findall(svg)
    ]
    return {
        "title": title,
        "description": description,
        "alt": _alt_text(description, zones),
        "zones": zones,
        "markers": markers,
    }


def _alt_text(description: str, zones: list[dict[str, Any]]) -> str:
    """Return the description with a takeaway appended, when one can be computed.

    The accessible ``<desc>`` on the plate says what kind of map it is and
    what is on it, which is two thirds of what alt text is supposed to do.
    The missing third is what it *shows*, and that is the part a reader who
    cannot see the plate has no other way to get.

    The takeaway here is deliberately the narrowest true statement
    available -- which class covers the most ground, and how much -- rather
    than a summary of the conflict. Anything larger would be the generator
    inventing an editorial line, and a plate's job is to draw the assessment
    it was given.

    A merely *claimed* largest share gets different wording, because a claim
    and a holding are not the same sentence and this is exactly the
    distinction the confidence tiers exist to preserve.
    """
    if not zones:
        return description
    # Several zones may share a class; the reader's question is about the
    # class, so sum them before ranking.
    by_class: dict[tuple[str, str], float] = {}
    for zone in zones:
        key = (str(zone["category"]), str(zone["confidence"]))
        by_class[key] = by_class.get(key, 0.0) + float(zone["area_share"])
    (category, confidence), share = max(by_class.items(), key=lambda kv: kv[1])
    verb = "is claimed to cover" if confidence == "claimed" else "covers"
    if confidence == "reported":
        verb = "is reported to cover"
    takeaway = f"{category} {verb} the largest mapped share, {share * 100:.0f}%."
    return f"{description} {takeaway}".strip()
