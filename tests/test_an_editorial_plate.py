"""
The editorial register: a situation plate set the way a newsroom sets one.

Every test here guards something found by rendering the Ukraine plate both
ways and looking at it (``.private/ASSESSMENT.md``, rounds 1 to 4): the
status quo painted over the whole country, a serif town name beside sans
ones, the source line printed between the map and its key, an inset of land
that is not there. And the one promise the moving plate makes: whatever it
does when it opens, a rasteriser and a reader who asked for no motion get
the finished map.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from _plates import plate  # noqa: E402

_IBERIA = [-10.0, 36.0, 4.0, 44.0]

#: Two classes over Iberia: the status quo, and a corner that changed hands.
_ZONES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"actor": "Held"},
            "geometry": {"type": "Polygon", "coordinates": [[
                [-9.0, 37.0], [-3.0, 37.0], [-3.0, 43.0], [-9.0, 43.0], [-9.0, 37.0],
            ]]},
        },
        {
            "type": "Feature",
            "properties": {"actor": "Taken"},
            "geometry": {"type": "Polygon", "coordinates": [[
                [-3.0, 37.0], [2.0, 37.0], [2.0, 42.0], [-3.0, 42.0], [-3.0, 37.0],
            ]]},
        },
    ],
}


def _cfg(**overrides: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "title": "Test plate",
        "region": {"bbox": list(_IBERIA)},
        "canvas_width": 520,
        "basemap": {"relief": False},
        "areas_of_control": {
            "category_field": "actor",
            "baseline": "Held",
            "palette": {"Taken": "#e07a6c"},
            "source": _ZONES,
        },
        "front": {"line": [[-3.0, 43.0], [-3.0, 37.0]]},
        "events": [{"lon": -1.0, "lat": 40.0, "color": "#c0392b", "precision": 2}],
        "caption": "full",
        "source": "Test source",
    }
    cfg.update(overrides)
    msm.validate_config(cfg)
    return cfg


def _editorial(**overrides: Any) -> str:
    return plate(_cfg(style="editorial", **overrides))


# ── the register ──────────────────────────────────────────────────────────


def test_an_unknown_style_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown style"):
        plate(_cfg(style="tabloid"))


def test_the_editorial_plate_is_flat_and_has_no_north_arrow() -> None:
    svg = _editorial()
    assert 'filter="url(#' not in svg, "something on a flat plate still casts a shadow"
    assert 'id="north-arrow"' not in svg
    assert 'id="north-arrow"' in plate(_cfg()), "the atlas plate lost its arrow too"


def test_a_key_the_config_wrote_still_wins_over_the_style() -> None:
    """The style fills in what was left unset; it never overrides."""
    cfg = _cfg(style="editorial", north_arrow=True, frame={"margin": 9})
    msm._apply_style(cfg)
    assert cfg["north_arrow"] is True
    assert cfg["frame"]["margin"] == 9
    assert cfg["frame"]["radius"] == 0


def test_the_status_quo_is_paper_and_is_not_keyed() -> None:
    """
    Keying the baseline sent a reader looking for a white swatch on a white
    map; drawing it in a colour painted the whole country and left the eye
    nowhere to go.
    """
    cfg = _cfg(style="editorial")
    labels = [row["label"] for row in msm._legend_rows(cfg, 1.0)]
    assert "Held" not in labels
    assert "Taken" in labels
    svg = plate(cfg)
    held = re.search(r'<path class="hit"[^>]*data-category="Held"[^>]*/>', svg)
    assert held and 'fill="#ffffff"' in held.group(0)


# ── typography ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("style", ["atlas", "editorial"])
def test_every_text_has_a_sans_face_to_inherit(style: str) -> None:
    """
    The automatic town names, the tooltips and the control panel set no face,
    and both rsvg and a browser fell back to Times: a serif "Brest" beside a
    sans "KYIV". The root now carries the face they inherit.
    """
    svg = plate(_cfg(style=style))
    root = re.match(r"<svg\b[^>]*>", svg)
    assert root and "font-family=" in root.group(0) and "Roboto" in root.group(0)


@pytest.mark.parametrize("style", ["atlas", "editorial"])
def test_a_reader_without_roboto_is_sent_to_fetch_it(style: str) -> None:
    """
    Roboto first, from Google Fonts when the machine lacks it; only then the
    rest of the stack. Three ways to get that wrong, each seen or measured:
    an import below other rules is dropped by CSS; a bare ampersand is an
    XML error, and the browser shows no plate at all; and an import sharing
    a sheet with the plate's own rules takes them down with it in resvg,
    whose parser stops at the semicolons in the URL -- the PNG then printed
    every tooltip at once.
    """
    import xml.etree.ElementTree as ET

    svg = plate(_cfg(style=style))
    sheets = re.findall(r"<style>(.*?)</style>", svg, flags=re.S)
    imports = [s for s in sheets if "@import" in s]
    assert len(imports) == 1, "no Google Fonts import, or more than one"
    assert imports[0].startswith("@import url('https://fonts.googleapis.com/css2?family=Roboto")
    assert imports[0].rstrip().endswith(";"), "the import sheet carries more than the import"
    assert imports[0].count("@import") == 1 and "{" not in imports[0]
    assert any(".tip{opacity:0" in s for s in sheets if s not in imports)
    ET.fromstring(svg)


def test_the_editorial_source_line_is_not_monospace() -> None:
    svg = _editorial()
    line = re.search(r"<text[^>]*>Test source</text>", svg)
    assert line and "Mono" not in line.group(0)


def test_the_source_line_sits_under_the_key_not_between_it_and_the_map() -> None:
    """Map, key, sources: the order a newsroom page is read in."""
    svg = _editorial(legend_position="below")
    key = svg.index("Taken</text>", svg.index('id="legend"'))
    # The drawn line, not the accessible description that also quotes it.
    source = svg.index(">Test source</text>")
    assert source > key, "the source line still prints above the key it follows"
    assert msm._caption_height(_cfg(style="editorial", legend_position="below"), 1.0, 520) == 0


# ── the moving plate ──────────────────────────────────────────────────────


def test_the_editorial_plate_opens_with_its_sequence() -> None:
    svg = _editorial()
    style = "".join(re.findall(r"<style>(.*?)</style>", svg, flags=re.S))
    for name in ("sz-fade", "sz-draw", "sz-pop"):
        assert f"@keyframes {name}" in style
    assert 'mask="url(#front-reveal)"' in svg


def test_the_atlas_plate_does_not_move() -> None:
    svg = plate(_cfg())
    assert "@keyframes" not in svg
    assert "front-reveal" not in svg


def test_a_static_plate_does_not_move_even_in_the_editorial_style() -> None:
    svg = _editorial(interactivity="static")
    assert "@keyframes" not in svg


def test_no_keyframe_holds_a_state_of_its_own() -> None:
    """
    A ``forwards`` fill would leave the plate in the animation's last frame
    rather than its drawn state, and that state is the only one a rasteriser
    or a print ever sees. Every keyframe has to lead *into* the drawing.
    """
    style = msm._animation_css(_cfg(style="editorial"))
    assert "backwards" in style
    assert "forwards;" not in style.replace("backwards", "")
    assert "infinite" not in style


def test_reduced_motion_switches_every_animation_off() -> None:
    style = msm._animation_css(_cfg(style="editorial"))
    animated = re.findall(r"([^{}]+)\{animation:sz-", style)
    guard = style[style.index("prefers-reduced-motion"):]
    for selector_list in animated:
        for selector in selector_list.split(","):
            assert selector.strip() in guard, f"{selector.strip()} keeps moving under reduced motion"


def test_without_its_animation_the_front_mask_hides_nothing() -> None:
    """
    The reveal mask is a solid band; only the keyframes give it a dash. A
    dash in the mask's own attributes would print a dotted front in every
    PNG, where no animation ever runs.
    """
    svg = _editorial()
    mask = svg[svg.index('<mask id="front-reveal"'): svg.index("</mask>")]
    assert "stroke-dasharray" not in mask
    assert "stroke-dashoffset" not in mask


# ── the ground under the colour ───────────────────────────────────────────


def test_the_terrain_shows_through_a_flat_fill() -> None:
    """
    A flat fill averaged the hillshade under it away: Serbia's 1913 gains
    and the occupied south of Ukraine read as a sheet of red with the relief
    stopping at its edge. The same shading is laid back over them.
    """
    cfg = _cfg(style="editorial", basemap={"relief": True})
    svg = plate(cfg)
    assert 'id="relief"' in svg
    over = re.search(r'<g id="relief-over"[^>]*>(.*?)</g>', svg, flags=re.S)
    assert over, "no terrain over the flat fills"
    assert "soft-light" in over.group(0), "only soft-light leaves paper as paper"
    assert '<use href="#relief"/>' in over.group(1), "a second copy of the image"
    clip = svg[svg.index('<clipPath id="relief-over-clip">'):]
    clip = clip[: clip.index("</clipPath>")]
    assert clip.count("<path") >= 2, "the terrain is not clipped to the fills"


def test_a_multiplied_fill_gets_no_second_pass() -> None:
    svg = plate(_cfg(basemap={"relief": True}))
    assert 'id="relief-over"' not in svg


def test_no_relief_no_second_pass() -> None:
    assert 'id="relief-over"' not in _editorial()


def test_a_note_keeps_a_margin_around_itself() -> None:
    """Flush, two notes stacked read as one paragraph about two places."""
    cfg = _cfg(
        style="editorial",
        annotations=[{"at": [-6.0, 40.0], "text": "A note.", "place": "right"}],
    )
    msm._apply_style(cfg)
    bbox = cfg["region"]["bbox"]
    proj = msm.build_projection(bbox, "auto")
    vp = msm.make_viewport(proj, bbox, 520.0, 30.0)
    vp["ink"] = []
    msm._annotations_layer(cfg, proj, vp)
    text_boxes = [b for b in vp["ink"] if b[2] - b[0] > 20]
    widest = max(text_boxes, key=lambda b: b[2] - b[0])
    line = min(text_boxes, key=lambda b: b[3] - b[1])
    assert widest[0] < line[0] - 5 and widest[3] > line[3] + 5, "no margin around the note"
