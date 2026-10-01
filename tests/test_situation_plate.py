"""
The situation plate itself: its accessible root, its labels, its water, its arrows.

Every test here guards a defect that was found by rendering a plate and
looking at it, not by reading the code — which is why several of them assert
about things that are invisible in the source and obvious on the page.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

REPO = Path(__file__).resolve().parents[1]

#: A small, fast region with land, a coast and a neighbour to label.
_IBERIA = [-10.0, 36.0, 4.0, 44.0]


def _plate(**overrides: Any) -> str:
    cfg: dict[str, Any] = {
        "title": "Test plate",
        "region": {"bbox": list(_IBERIA)},
        "canvas_width": 520,
        "basemap": {"relief": False},
    }
    cfg.update(overrides)
    msm.validate_config(cfg)
    return msm.build_map(cfg)


# ── the accessible root ───────────────────────────────────────────────────


def test_root_svg_is_announced_to_a_screen_reader() -> None:
    """
    The plate must open with the same accessible root the other two kinds have.

    ``make_choropleth`` and ``make_density`` have always emitted ``role="img"``
    wired to a ``<title>``/``<desc>`` pair; this generator emitted a bare
    ``<svg>``, so a screen reader announced "image" and stopped.
    """
    svg = _plate()
    assert 'role="img"' in svg
    assert 'aria-labelledby="sm-title sm-desc"' in svg
    assert '<title id="sm-title">Test plate</title>' in svg
    assert '<desc id="sm-desc">' in svg


def test_description_names_the_classes_and_keeps_the_caveat() -> None:
    """
    A plate that claims control must say so, and say it is a claim.

    The caveat is the contract ``TRIGGERS.md`` states for every consumer of
    this generator. A sighted reader gets it from the caption; it has to be in
    the accessible description for the same reason.
    """
    title, desc = msm.accessible_text(
        {
            "title": "Who holds what",
            "region": {"bbox": [22.0, 44.0, 40.0, 52.5]},
            "areas_of_control": {
                "palette": {"Blue": "#123456", "Red": "#654321"},
                "contested": ["Red"],
            },
        }
    )
    assert title == "Who holds what"
    assert "2 classes" in desc
    assert "Red (contested)" in desc
    assert "does not verify who holds what" in desc


def test_a_plain_basemap_carries_no_claim_and_so_no_caveat() -> None:
    """A map with no control layer asserts nothing, and must not pretend to."""
    _, desc = msm.accessible_text({"region": {"bbox": [-11.0, 35.0, 30.0, 60.0]}})
    assert "does not verify" not in desc
    assert "11.0°W" in desc and "60.0°N" in desc


# ── where a territory's name goes ─────────────────────────────────────────


def test_territory_label_goes_on_the_largest_part() -> None:
    """
    A country's name belongs on its body, not on an offshore fragment.

    ``representative_point()`` may pick any component of a MultiPolygon, and
    on the real basemap it put ``RUSSIA`` on Crimea for a Ukraine view.
    """
    from shapely.geometry import MultiPolygon, box

    mainland, island = box(0, 0, 10, 10), box(20, 20, 21, 21)
    pt = msm._label_point(MultiPolygon([island, mainland]))
    assert mainland.contains(pt)


def test_territory_label_sits_clear_of_the_border() -> None:
    """
    And deep inside, not merely inside.

    On the real Ukraine view the old placement left ``RUSSIA`` 0.36° from the
    frontier, close enough that the ``LUHANSK`` city label painted over it.
    """
    from shapely.geometry import Polygon

    notched = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 6), (8, 5), (0, 4)])
    near = notched.exterior.distance(notched.representative_point())
    deep = notched.exterior.distance(msm._label_point(notched))
    assert deep > 4 * near


def test_a_label_that_would_be_cropped_is_dropped_instead() -> None:
    """
    A cropped name reads as a different name: ``CENTRAL AFRICAN REPUBLIC``
    came off the plate's left edge as ``NTRAL … REP``.
    """
    vp = {"width": 200.0, "height": 100.0}
    assert msm._label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp)
    assert not msm._label_fits(6, 50, "CHAD", size=10, tracking=2, vp=vp)


def test_the_region_clip_is_the_real_bound_not_the_plate_rectangle() -> None:
    """
    Under a conic projection the drawn map is narrower than its plate, so a
    label can clear the rectangle and still be sliced. ``Asmara`` came out of
    the Sudan plate as ``Asm`` that way.
    """
    from shapely.geometry import box

    vp = {"width": 200.0, "height": 100.0}
    assert msm._label_fits(100, 50, "CHAD", size=10, tracking=2, vp=vp)
    assert not msm._label_fits(
        100, 50, "CHAD", size=10, tracking=2, vp=vp, region=box(0, 0, 60, 100)
    )


def test_a_hand_placed_name_suppresses_its_automatic_twin() -> None:
    """
    Both by name and by position.

    The name test read ``place["name"]`` while every config writes ``text``,
    so it matched nothing; and where the two datasets disagree they disagree
    on the name, not the place — Natural Earth calls El Obeid "Al-Ubayyid".
    """
    plain = _plate()
    labelled = _plate(
        labels={"places": [{"lon": -3.7038, "lat": 40.4168, "text": "Madrid"}]}
    )
    cities_plain = plain[plain.index('<g id="cities">') :].split("</g>")[0]
    cities_labelled = labelled[labelled.index('<g id="cities">') :].split("</g>")[0]
    assert "Madrid" in cities_plain, "precondition: the automatic layer draws Madrid"
    assert "Madrid" not in cities_labelled
    # ...and the hand-placed name is still there, in the labels layer, which
    # sets territory names in tracked capitals.
    assert ">MADRID<" in labelled


# ── water ─────────────────────────────────────────────────────────────────


def test_inland_lakes_are_water_not_land() -> None:
    """
    The coastline data is land-versus-ocean only, so every lake was painted as
    ground: a plate of the Kivus put Goma and Bukavu on dry land with nothing
    between them, when they face each other across Lake Kivu.
    """
    lakes = msm.load_lakes()
    assert lakes, "the vendored lake polygons must ship"
    by_name = {name for _g, name, _r in lakes}
    for expected in ("Lake Kivu", "Lake Tanganyika", "Lake Victoria"):
        assert expected in by_name

    svg = _plate(region={"bbox": [27.5, -4.0, 30.0, 0.5]}, basemap={"relief": False})
    lakes_group = svg[svg.index('<g id="lakes">') :].split("</g>")[0]
    assert lakes_group.count("<path") >= 2
    assert "Lake Kivu" in svg


def test_lakes_can_be_switched_off() -> None:
    svg = _plate(region={"bbox": [27.5, -4.0, 30.0, 0.5]}, lakes={"show": False})
    assert '<g id="lakes"></g>' in svg


def test_a_drained_water_body_can_be_drawn_as_former_rather_than_wet() -> None:
    """
    Natural Earth is a snapshot and the Kakhovka Reservoir is in it at its full
    ~2 150 km² extent. It drained within two weeks of the dam breach of 6 June
    2023; by 2026 the bed is willow and poplar scrub over sand and marsh.

    ``lakes.former`` draws the outline dashed with no fill and suffixes the
    name, which is the honest answer: on a map of this front the absence of
    the reservoir is itself information, and a reader who knows the geography
    will come looking for it. ``lakes.skip`` drops it entirely.
    """
    region = {"bbox": [32.0, 45.8, 37.0, 48.5]}
    wet = _plate(region=region)
    assert ">Kakhovka Reservoir<" in wet

    gone = _plate(region=region, lakes={"skip": ["Kakhovka Reservoir"]})
    assert "Kakhovka Reservoir" not in gone

    former = _plate(
        region=region,
        lakes={"former": ["Kakhovka Reservoir"], "always_label": ["Kakhovka Reservoir"]},
    )
    assert ">Kakhovka Reservoir (former)<" in former
    lakes_group = former[former.index('<g id="lakes">') :].split("</g>")[0]
    assert "stroke-dasharray" in lakes_group
    # No fill, because there is no water.
    assert 'fill="none"' in lakes_group


def test_always_label_still_matches_a_lake_marked_former() -> None:
    """
    The suffix is appended before the label-size gate, so the gate has to test
    the real name. Asking for a small former lake by name must still work.
    """
    svg = _plate(
        region={"bbox": [32.0, 45.8, 37.0, 48.5]},
        canvas_width=300,
        lakes={"former": ["Kakhovka Reservoir"], "always_label": ["Kakhovka Reservoir"]},
    )
    assert ">Kakhovka Reservoir (former)<" in svg


def test_a_lake_name_and_a_river_name_do_not_print_on_top_of_each_other() -> None:
    """
    Two layers, two datasets, one piece of water: "Dnieper" printed straight
    through "Kakhovka Reservoir" because each layer dodged only its own labels.

    Both names may perfectly well appear -- they are different water, and on
    this view they are 117 units apart. What must not happen is two of them
    landing on the same spot, so this measures the closest pair rather than
    counting labels.
    """
    import math
    import re

    svg = _plate(
        region={"bbox": [28.0, 44.0, 40.0, 52.0]},
        canvas_width=900,
        basemap={"relief": False},
    )
    water = [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(
            r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*font-style="italic"[^>]*>[^<]+</text>',
            svg,
        )
    ]
    assert len(water) >= 4, "precondition: this view carries several named waters"
    closest = min(math.dist(a, b) for i, a in enumerate(water) for b in water[i + 1 :])
    assert closest > 50


# ── axes of advance ───────────────────────────────────────────────────────


def test_no_arrows_configured_means_an_empty_group_not_a_missing_one() -> None:
    assert '<g id="arrows"></g>' in _plate()


def test_an_arrow_is_a_tapered_shaft_and_a_separate_head() -> None:
    """
    A stroke is one width for its whole length, so the shaft has to be a filled
    outline; the head is separate so it keeps a point however the shaft curves.
    """
    svg = _plate(
        arrows=[{"line": [[-8.0, 40.0], [-5.0, 40.5], [-2.0, 41.0]], "label": "Push"}]
    )
    group = svg[svg.index('<g id="arrows">') :].split("</g>")[0]
    # casing (2) + fill (2) for shaft and head.
    assert group.count("<path") == 4
    assert "PUSH" in group


def test_a_reported_axis_is_drawn_as_an_outline_not_a_solid() -> None:
    """``solid`` and ``dashed`` are two different claims, and must look it."""
    solid = _plate(arrows=[{"line": [[-8.0, 40.0], [-2.0, 41.0]]}])
    dashed = _plate(arrows=[{"line": [[-8.0, 40.0], [-2.0, 41.0]], "style": "dashed"}])
    assert "stroke-dasharray" not in solid[solid.index('<g id="arrows">') :].split("</g>")[0]
    assert "stroke-dasharray" in dashed[dashed.index('<g id="arrows">') :].split("</g>")[0]


def test_a_degenerate_arrow_is_skipped_rather_than_drawn_wrong() -> None:
    assert '<g id="arrows"></g>' in _plate(arrows=[{"line": [[-8.0, 40.0]]}])


def test_a_smooth_curve_still_passes_through_every_point_given() -> None:
    pts = msm._catmull_rom([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)], per_segment=4)
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (20.0, 0.0)
    assert all(abs(y) < 1e-9 for _x, y in pts)


# ── zones ─────────────────────────────────────────────────────────────────


def test_control_zones_are_clipped_to_the_region_before_drawing() -> None:
    """
    A caller who hands over a whole country for a plate of one province was
    emitting a path many times the canvas. Beyond the wasted bytes, the shape
    fell so far outside that resvg dropped its blended fill and the eastern
    DRC plate rendered with no control colours at all.
    """
    whole_world = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"actor": "Everyone"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-179, -85], [179, -85], [179, 85], [-179, 85], [-179, -85]]
                    ],
                },
            }
        ],
    }
    svg = _plate(
        areas_of_control={
            "category_field": "actor",
            "palette": {"Everyone": "#cccccc"},
            "source": whole_world,
        }
    )
    group = svg[svg.index('<g id="areas-of-control">') :].split('<g id="frontiers"')[0]
    coords = [
        abs(float(v))
        for chunk in group.split('d="')[1:]
        for pair in chunk.split('"')[0].replace("M", "").replace("Z", "").split("L")
        for v in pair.split(",")
        if v.replace(".", "").replace("-", "").isdigit()
    ]
    assert coords, "the zone must still be drawn"
    # Generous slack for the projection, but nothing like a whole-globe path.
    assert max(coords) < 4000


def test_the_legend_clears_the_provenance_caption() -> None:
    """
    The scale bar has always made room for the caption; the legend did not,
    and a bottom-corner card sat straight on all three caption lines.
    """
    ts = 1.0
    cfg = {
        "caption": "full",
        "method": "m",
        "source": "s",
        "as_of": "a",
    }
    assert msm._caption_height(cfg, ts) > 0
    assert msm._caption_height({"caption": "none"}, ts) == 0


# ── the shipped examples ──────────────────────────────────────────────────


def _builders() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "_situation_examples", REPO / "scripts" / "build_situation_examples.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_situation_examples"] = mod
    spec.loader.exec_module(mod)
    return mod.BUILDERS


@pytest.mark.parametrize("name", sorted(_builders()))
def test_every_shipped_example_is_a_config_the_generator_accepts(name: str) -> None:
    """
    The regression this exists for: ``build_ukraine`` carried a ``sprezzature``
    key where it meant ``front``, left by a word replacement that ran through
    the file. The generator never read it, so the contact line was silently
    absent from the flagship example — and once unknown keys became an error,
    the example could not render at all. Nothing tested it.
    """
    cfg = _builders()[name]()
    msm.validate_config(cfg)
    assert cfg.get("title")
    assert cfg["region"]["bbox"]
