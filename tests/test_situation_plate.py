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


# ── frontiers ─────────────────────────────────────────────────────────────


def test_a_shared_border_is_drawn_once_not_once_per_neighbour() -> None:
    """
    Walking the countries and drawing each one's outline draws every inland
    border twice, once from each side. Measured at 1.63x the real frontier
    length on the Ukraine plate, and the damage was not only ink: the two
    coincident dashed strokes start at different vertices, so their dash
    phases interleave and fill each other's gaps. The border came out
    near-solid while the coastline beside it stayed dashed -- the
    international-border convention lost exactly on international borders.
    """
    import re
    from collections import Counter

    cfg = {
        "title": "Frontier check",
        "region": {"bbox": [22.0, 44.0, 41.0, 53.0]},  # Ukraine and every neighbour
        "canvas_width": 1000,
        "basemap": {"relief": False},
        "frontiers": {"label_neighbours": False},
    }
    msm.validate_config(cfg)
    svg = msm.build_map(cfg)
    group = svg[svg.index('<g id="frontiers">') :].split("</g>")[0]
    paths = re.findall(r'<path d="([^"]+)"', group)
    # One union'd polyline -- mapshaper's ``-innerlines`` -- not one per country.
    assert len(paths) == 1, f"expected a single union'd frontier path, got {len(paths)}"

    # Count how often each segment of linework is actually stroked. Scale- and
    # projection-free: it asks the page directly whether it draws anything
    # twice. Before the fix, 506 of 783 distinct segments were drawn twice.
    drawn: Counter[tuple[tuple[float, float], tuple[float, float]]] = Counter()
    for d in paths:
        run: list[tuple[float, float]] = []
        for cmd, xy in re.findall(r"([ML])([-\d.]+,[-\d.]+)", d):
            point = tuple(round(float(v), 1) for v in xy.split(","))
            if cmd == "M":
                run = [point]  # type: ignore[list-item]
                continue
            run.append(point)  # type: ignore[arg-type]
            drawn[tuple(sorted((run[-2], run[-1])))] += 1  # type: ignore[index]

    assert len(drawn) > 500, "pick a region with real frontier linework in it"
    twice = [seg for seg, n in drawn.items() if n > 1]
    assert not twice, f"{len(twice)} of {len(drawn)} frontier segments are stroked more than once"


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


# ── how sure the assessment is ────────────────────────────────────────────
#
# The vocabulary is ISW's: their control-of-terrain plates keep assessed
# control, reported movement and a belligerent's unverified claim visually
# apart, and that separation is what lets a reader hold the map up against a
# ministry's communiqué. Collapsing the three into one fill is not a
# simplification, it is a stronger claim than the sources support.


def _zones(*features: Any) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def _zone(actor: str, confidence: str | None = None, west: float = -8.0) -> dict[str, Any]:
    props: dict[str, Any] = {"actor": actor}
    if confidence is not None:
        props["confidence"] = confidence
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[west, 38.0], [west + 3, 38.0], [west + 3, 42.0], [west, 42.0], [west, 38.0]]
            ],
        },
    }


def _control(*features: Any, **extra: Any) -> str:
    aoc: dict[str, Any] = {
        "category_field": "actor",
        "palette": {"Blue": "#9cc3d5", "Red": "#d98880"},
        "source": _zones(*features),
    }
    aoc.update(extra)
    return _plate(areas_of_control=aoc)


def test_a_claimed_zone_is_not_painted_the_colour_of_held_ground() -> None:
    """
    ISW draws a claim nobody has verified differently from ground a force is
    assessed to hold, and the difference has to survive into the ink: a zone
    filled at the same opacity as assessed control asserts control.
    """
    svg = _control(_zone("Red", "claimed"))
    group = svg[svg.index('<g id="areas-of-control">') :].split('<g id="frontiers"')[0]
    zone = [p for p in group.split("<path ") if 'class="hit"' in p][0]
    assert 'fill-opacity="0.00"' in zone, "a claimed zone must carry no solid fill"
    assert "stroke-dasharray" in zone, "and must be outlined as provisional"
    # It is still *drawn*, via its texture, or the claim would simply vanish.
    assert f'url(#{msm._pattern_id("dots", "#d98880")})' in group


def test_a_reported_zone_stays_the_same_class_only_less_certain() -> None:
    """
    Reported movement is not a fourth actor. It keeps the class colour and
    loses certainty through texture and opacity, so the reader still reads
    "the red side, probably" rather than "some fifth thing".
    """
    svg = _control(_zone("Red", "reported"))
    group = svg[svg.index('<g id="areas-of-control">') :].split('<g id="frontiers"')[0]
    zone = [p for p in group.split("<path ") if 'class="hit"' in p][0]
    assert 'fill="#d98880"' in zone, "the class colour must survive"
    assert 'fill-opacity="0.00"' not in zone, "reported ground is still drawn as ground"
    assert f'url(#{msm._pattern_id("hatches", "#d98880")})' in group


def test_an_unknown_confidence_is_refused_rather_than_rounded_to_assessed() -> None:
    """
    The dangerous direction is upward. Treating an unreadable code as
    "assessed" promotes an unverified claim into held ground, and nothing on
    the finished plate would show that it happened.
    """
    with pytest.raises(ValueError, match="unknown confidence"):
        _control(_zone("Red", "probably"))


def test_a_zone_with_no_confidence_still_means_assessed() -> None:
    """Every plate drawn before the ladder existed must render exactly as before."""
    plain = _control(_zone("Red"))
    stated = _control(_zone("Red", "assessed"))
    assert plain == stated


def test_a_textured_zone_can_still_be_hovered() -> None:
    """
    A pattern fill is painted, so it swallows the pointer -- and these overlays
    sit above the ``.hit`` path the ``.hit:hover~.tip`` rule needs. Without
    ``pointer-events="none"`` a textured zone is the one kind whose tooltip
    never opens, which was already true of every contested zone.
    """
    svg = _control(_zone("Red", "reported"), contested=["Red"])
    group = svg[svg.index('<g id="areas-of-control">') :].split('<g id="frontiers"')[0]
    overlays = [p for p in group.split("<path ") if "url(#" in p and "hit" not in p]
    assert overlays, "this plate must actually draw textures"
    for overlay in overlays:
        assert 'pointer-events="none"' in overlay


def test_the_legend_keys_every_tier_it_draws_and_no_others() -> None:
    """
    A texture the reader meets on the map and not in the legend is noise.
    ``assessed`` is the exception: it is what an unmarked zone already means,
    so keying it would add a row that says "the normal one".
    """
    svg = _control(_zone("Blue"), _zone("Red", "claimed", west=-4.0))
    legend = svg[svg.index('<g id="legend">') :]
    assert "Claimed, unverified" in legend
    assert "Reported, not assessed" not in legend, "no tier this plate never draws"
    assert "Assessed" not in legend.split("AREAS OF CONTROL")[1].split("</g>")[0]


def test_the_description_tells_a_screen_reader_which_tiers_are_drawn() -> None:
    """
    The textures are the one thing a sighted reader gets for free here. To a
    screen reader a claimed zone and an assessed zone are the same ``<path>``
    unless the description says which tiers the plate uses.
    """
    svg = _control(_zone("Red", "claimed"))
    desc = svg.split('<desc id="sm-desc">')[1].split("</desc>")[0]
    assert "claimed, unverified" in desc
    assert "does not verify who holds what" in desc


# ── where the thing actually happened ─────────────────────────────────────
#
# ACLED records a 1-3 ``geo_precision`` beside every event "to reflect the
# fact that the precise location of the incident may not be known": 3 means a
# provincial capital standing in for a whole province. Drawing all three as
# the same hard dot asserts a street corner the source never gave.


def test_an_approximate_event_loses_its_solid_centre() -> None:
    """
    A filled dot means "we know the place". An approximate position gives that
    up rather than inventing an area for itself: a hollow ring claims nothing
    it cannot support, where a disc of made-up radius would.
    """
    exact = _plate(events=[{"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 6}])
    approx = _plate(
        events=[{"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 6, "precision": 2}]
    )
    assert 'fill="#c0392b"' in exact.split('<g id="events">')[1].split("</g>")[0]
    ring = approx.split('<g id="events">')[1].split("</g>")[0]
    assert 'fill="#ffffff"' in ring and 'stroke="#c0392b"' in ring
    # And precision 3 -- a whole region pinned to its capital -- breaks the
    # ring as well as hollowing it: one step further from "a place".
    region = _plate(
        events=[{"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 6, "precision": 3}]
    )
    assert "stroke-dasharray" in region.split('<g id="events">')[1].split("</g>")[0]


def test_a_stated_uncertainty_radius_is_drawn_to_the_map_scale() -> None:
    """
    A halo is a measurement, so it has to survive the projection: 40 km on the
    ground must be 40 km on the plate, not a fixed number of pixels that means
    a different distance on every map.
    """
    import re

    bbox = [-10.0, 36.0, 4.0, 44.0]
    cfg = {
        "title": "Radius check",
        "region": {"bbox": list(bbox)},
        "canvas_width": 520,
        "basemap": {"relief": False},
        "events": [
            {"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 5,
             "precision": 2, "radius_km": 40}
        ],
    }
    msm.validate_config(cfg)
    svg = msm.build_map(cfg)
    group = svg[svg.index('<g id="events">') :]
    drawn = float(
        re.search(r'r="([\d.]+)" fill="#c0392b"\s+fill-opacity="0.12"', group).group(1)
    )
    vp = msm.make_viewport(
        msm.build_projection(list(bbox), "auto"), list(bbox), 520.0, 26.0
    )
    assert drawn * vp["m_per_unit"] / 1000 == pytest.approx(40.0, rel=0.01)


def test_an_unreadable_precision_code_is_refused() -> None:
    """Same reasoning as the confidence ladder: the silent failure runs upward."""
    with pytest.raises(ValueError, match="must be one of 1, 2, 3"):
        _plate(events=[{"lon": -4.0, "lat": 40.0, "precision": 4}])
    with pytest.raises(ValueError, match="time_precision"):
        _plate(events=[{"lon": -4.0, "lat": 40.0, "date": "x", "time_precision": 9}])


def test_a_dates_precision_is_spoken_not_implied() -> None:
    """A date known only to the month should not be read as a day."""
    svg = _plate(
        events=[
            {"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 5,
             "date": "March 2026", "time_precision": 3}
        ]
    )
    assert "month of March 2026" in svg


# ── the plate as something you can read back ──────────────────────────────


def test_the_assessment_can_be_read_back_out_of_the_finished_svg() -> None:
    """
    svgis writes a feature's own fields into ``data-*`` attributes so the
    drawing stays queryable after it is drawn. A situation plate is an
    argument about who holds what, and an argument a reader can only squint
    at is weaker than one they can extract.
    """
    import re

    svg = _control(_zone("Blue"), _zone("Red", "claimed", west=-4.0))
    found = {
        m.group(1): m.group(2)
        for m in re.finditer(r'data-category="([^"]*)" data-confidence="([^"]*)"', svg)
    }
    assert found == {"Blue": "assessed", "Red": "claimed"}
    shares = [float(s) for s in re.findall(r'data-area-share="([\d.]+)"', svg)]
    assert len(shares) == 2
    assert sum(shares) == pytest.approx(1.0, abs=1e-3)


def test_a_marker_carries_its_own_coordinates_and_precision() -> None:
    svg = _plate(
        events=[
            {"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 5,
             "precision": 2, "radius_km": 25}
        ]
    )
    assert 'data-precision="2"' in svg
    assert 'data-lon="-4.0000" data-lat="40.0000"' in svg
    assert 'data-radius-km="25"' in svg


def test_a_marker_can_cite_its_own_source() -> None:
    """
    LiveUAMap's discipline: provenance per event, not per plate. A caption
    saying "open sources" covers the map and tells a reader nothing about the
    one dot they are actually trying to check.
    """
    svg = _plate(
        events=[
            {"lon": -4.0, "lat": 40.0, "color": "#c0392b", "r": 5,
             "source": "Reuters, 3 March 2026"}
        ]
    )
    assert "Source: Reuters, 3 March 2026" in svg


def test_a_mistyped_marker_key_is_refused_not_ignored() -> None:
    """
    The same rule ``validate_config`` applies to top-level keys, one level
    down. ``percision: 3`` reads as no precision at all, which draws the
    confident solid dot -- the opposite of what was asked for, on a plate
    that still looks finished.
    """
    with pytest.raises(ValueError, match="percision"):
        _plate(events=[{"lon": -4.0, "lat": 40.0, "percision": 3}])
    with pytest.raises(ValueError, match="did you mean 'precision'"):
        _plate(events=[{"lon": -4.0, "lat": 40.0, "percision": 3}])


# ── a plate that has to fit a column ──────────────────────────────────────
#
# The widths that matter are not round numbers of our choosing: a one-column
# chart at The Economist is 595 units, Datawrapper defaults to 600, and a
# phone body column is about 375. Measured before this: the legend card is a
# fixed 262 units, which is 26% of a 1000-unit plate, 44% of a 600 and 70%
# of a 375 -- at which point it covers the map it exists to explain.


def _legend_cfg(width: int, **extra: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "title": "Who holds what",
        "region": {"bbox": list(_IBERIA)},
        "canvas_width": width,
        "basemap": {"relief": False},
        "areas_of_control": {
            "category_field": "actor",
            "palette": {"Blue": "#9cc3d5", "Red": "#d98880"},
            "source": _zones(_zone("Blue"), _zone("Red", west=-4.0)),
        },
    }
    cfg.update(extra)
    msm.validate_config(cfg)
    return cfg


def test_auto_keeps_the_card_while_the_card_is_a_minority_of_the_width() -> None:
    wide = _legend_cfg(1000, legend_position="auto")
    assert msm._resolve_legend_position(wide, 1.0, 1000.0) == "bottom-right"


def test_auto_moves_the_key_off_the_map_once_it_stops_being_a_minority() -> None:
    """
    The newsroom answer to a narrow column is not a smaller card, it is a
    different layout: Datawrapper's charts switch from direct labelling to a
    legend on mobile rather than shrinking what they had.
    """
    narrow = _legend_cfg(375, legend_position="auto")
    assert msm._resolve_legend_position(narrow, 1.0, 375.0) == "below"
    svg = msm.build_map(narrow)
    legend = svg[svg.index('<g id="legend">') :].split("</g>")[0]
    # A band, not a card: no panel rect, no drop shadow over the map.
    assert "filter=\"url(#panel-shadow)\"" not in legend
    assert "AREAS OF CONTROL" in legend


def test_a_below_legend_grows_the_plate_instead_of_covering_the_map() -> None:
    """The band has to buy its own space, or it is the same occlusion lower down."""
    import re

    def plate_height(cfg: dict[str, Any]) -> float:
        svg = msm.build_map(cfg)
        return float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg).group(1))

    assert plate_height(_legend_cfg(375, legend_position="below")) > plate_height(
        _legend_cfg(375, legend_position="bottom-right")
    )


def test_an_explicit_position_is_never_overridden_by_width() -> None:
    """``auto`` is opt-in; every plate drawn before it existed must be untouched."""
    for pos in ("bottom-right", "bottom-left", "top-left", "top-right", "right"):
        assert msm._resolve_legend_position(_legend_cfg(375, legend_position=pos), 1.0, 375.0) == pos
    # And the default, with no key set at all.
    assert msm._resolve_legend_position(_legend_cfg(375), 1.0, 375.0) == "bottom-right"


def test_the_scale_bar_is_long_enough_to_carry_its_own_labels() -> None:
    """
    The bar is labelled ``0`` at one end and the distance at the other, so a
    bar shorter than the two labels prints them on top of each other. On a
    375-unit plate the mile bar came out 34 units long and rendered as
    ``0100MI``.
    """
    import re

    for width in (1600, 1000, 600, 375, 320):
        bbox = [22.0, 44.0, 41.0, 53.0]
        vp = msm.make_viewport(msm.build_projection(bbox, "auto"), bbox, float(width), 26.0)
        svg = msm.scale_bar(0.0, 0.0, vp)
        labels = re.findall(r'text-anchor="end">([^<]+)</text>', svg)
        lengths = [float(x) + float(w) for x, w in
                   re.findall(r'<rect x="([-\d.]+)"[^>]*width="([\d.]+)"', svg)]
        assert len(labels) == 2 and len(lengths) == 4
        for label, length in zip(labels, (lengths[1], lengths[3]), strict=True):
            needed = (len("0") + len(label)) * 10 * vp["ts"] * msm._GLYPH_WIDTH_RATIO
            assert length >= needed, f"{width}: '{label}' does not fit its {length:.0f}-unit bar"
        # And neither bar may run off the plate.
        assert max(lengths) < width, f"{width}: a scale bar overruns the canvas"


# ── weight ────────────────────────────────────────────────────────────────


def test_vertices_below_the_output_resolution_are_not_written() -> None:
    """
    A generator that writes every vertex it was given spends bytes on detail
    the canvas cannot show. Thinning runs after projection, so the tolerance
    is in the units actually drawn.
    """
    import re

    cfg = {
        "title": "Weight",
        "region": {"bbox": [22.0, 44.0, 41.0, 53.0]},
        "canvas_width": 1000,
        "basemap": {"relief": False},
    }
    msm.validate_config(cfg)
    full = msm.build_map(dict(cfg, simplify=0))
    thin = msm.build_map(cfg)

    def vertices(svg: str) -> int:
        return sum(
            len(re.findall(r"[ML][-\d.]+,[-\d.]+", d))
            for d in re.findall(r'<path[^>]*d="([^"]*)"', svg)
        )

    assert vertices(thin) < vertices(full)
    assert len(thin) < len(full)
    # ``simplify: 0`` is the documented way to switch it off entirely.
    assert vertices(msm.build_map(dict(cfg, simplify=0))) == vertices(full)


def test_the_relief_raster_is_re_encoded_without_changing_a_pixel() -> None:
    """
    Shaded relief is a duotone ramp, so a 1.3-megapixel raster of it holds
    about 210 distinct colours and one alpha value -- stored as 32-bit RGBA,
    roughly twice the bytes it needs, for 96% of a finished plate's weight.
    An exact indexed palette is half the size and, unlike a quantiser,
    provably the same image.
    """
    import base64
    import io

    import numpy as np
    from PIL import Image

    relief = _load_script("_relief")
    rng = np.random.default_rng(0)
    # A duotone ramp over a smooth field: the shape of real shaded relief.
    field = np.linspace(0, 1, 64 * 64).reshape(64, 64)
    field = (field + rng.normal(0, 0.01, field.shape)).clip(0, 1)
    level = (field * 180).astype(np.uint8)
    rgba = np.dstack([level, (level * 0.9).astype(np.uint8),
                      (level * 0.8).astype(np.uint8),
                      np.full(level.shape, 140, dtype=np.uint8)])
    uri = relief.rgba_to_data_uri(rgba)
    raw = base64.b64decode(uri.split(",", 1)[1])
    decoded = Image.open(io.BytesIO(raw))
    assert decoded.mode == "P", "a palette fitting in a byte must be written indexed"
    back = np.asarray(decoded.convert("RGBA")).astype(int)
    assert (back[..., :3] == rgba[..., :3].astype(int)).all(), "re-encoding changed a colour"


def test_a_raster_too_colourful_to_index_still_encodes() -> None:
    """The indexed path is an optimisation, not a precondition."""
    import numpy as np

    relief = _load_script("_relief")
    rng = np.random.default_rng(1)
    noisy = rng.integers(0, 255, (40, 40, 4), dtype=np.uint8)
    assert relief.rgba_to_data_uri(noisy).startswith("data:image/png;base64,")


# ── the note that makes it an argument ────────────────────────────────────
#
# Every piece of newsroom guidance on news cartography says the same thing:
# the annotation *is* the map, and the other layers support it. Datawrapper's
# specific conventions: a circle rather than an arrow, the data's own palette
# rather than a contrasting one, and few notes well spread out.


def test_no_annotation_configured_means_an_empty_group_not_a_missing_one() -> None:
    assert '<g id="annotations"></g>' in _plate()


def test_an_annotation_circles_its_subject_rather_than_pointing_at_it() -> None:
    """
    An arrowhead points at a pixel and claims a precision a note about a
    region does not have. A ring says "around here", which is what an
    annotation almost always means -- and the radius is in kilometres on the
    ground, so it means the same thing at any plate size.
    """
    import re

    svg = _plate(
        annotations=[
            {"at": [-4.0, 40.0], "text": "The plateau emptied first.",
             "circle_km": 50, "color": "#2f5d92"}
        ]
    )
    group = svg[svg.index('<g id="annotations">') :].split("</g>")[0]
    assert "marker-end" not in group and "polygon" not in group, "a ring, not an arrowhead"
    ring = float(re.search(r'<circle[^>]*r="([\d.]+)" fill="none"', group).group(1))
    vp = msm.make_viewport(
        msm.build_projection(list(_IBERIA), "auto"), list(_IBERIA), 520.0, 26.0
    )
    assert ring * vp["m_per_unit"] / 1000 == pytest.approx(50.0, rel=0.01)
    # The note takes the colour it was given, so it sits back onto the map.
    assert group.count("#2f5d92") >= 2


def test_an_annotation_stays_legible_over_whatever_it_lands_on() -> None:
    """
    The one place a note has to hold up is over the relief and the control
    fills it is pointing at, which is exactly where plain text disappears.
    """
    svg = _plate(annotations=[{"at": [-4.0, 40.0], "text": "Held throughout."}])
    group = svg[svg.index('<g id="annotations">') :].split("</g>")[0]
    assert 'paint-order="stroke"' in group


def test_a_long_note_wraps_instead_of_running_off_the_plate() -> None:
    svg = _plate(
        annotations=[
            {"at": [-4.0, 40.0],
             "text": "A note long enough that it cannot possibly fit on one line "
                     "of a plate this size without being wrapped first."}
        ]
    )
    group = svg[svg.index('<g id="annotations">') :].split("</g>")[0]
    assert group.count("<text") >= 3


def test_a_mistyped_annotation_key_is_refused() -> None:
    """Same rule as the config and the markers: a silent drop is the worst answer."""
    with pytest.raises(ValueError, match="circle_kms"):
        _plate(annotations=[{"at": [-4.0, 40.0], "text": "x", "circle_kms": 10}])


# ── what the page around the map needs ────────────────────────────────────


def test_the_sidecar_is_read_out_of_the_plate_not_the_config() -> None:
    """
    A caption retyped into a CMS from looking at the picture is a caption
    that will disagree with the plate after one of them is corrected. The
    sidecar is derived from the finished SVG, so the two cannot drift.
    """
    from sprezzature_maps import article_sidecar

    svg = _control(_zone("Blue"), _zone("Red", "claimed", west=-4.0))
    card = article_sidecar(svg)
    assert card["title"] == "Test plate"
    assert {z["category"] for z in card["zones"]} == {"Blue", "Red"}
    assert {z["confidence"] for z in card["zones"]} == {"assessed", "claimed"}
    assert sum(z["area_share"] for z in card["zones"]) == pytest.approx(1.0, abs=1e-3)


def test_the_alt_text_carries_a_takeaway_not_just_an_inventory() -> None:
    """
    Accessibility practice for charts asks alt text for three things: what
    kind of thing it is, what is in it, and *what it shows*. The description
    on the plate had the first two; the third is the part a reader who
    cannot see it has no other way to get, and it has to be computed from
    what was drawn rather than asserted.
    """
    from sprezzature_maps import article_sidecar

    card = article_sidecar(_control(_zone("Blue"), _zone("Red", west=-4.0)))
    assert "largest mapped share" in card["alt"]
    assert card["alt"].startswith(card["description"])


def test_a_claim_is_not_spoken_as_a_holding() -> None:
    """
    "Covers" and "is claimed to cover" are different sentences, and keeping
    them apart is the whole point of the confidence tiers. A takeaway that
    flattened them would undo on the way out what the map does on the page.
    """
    from sprezzature_maps import article_sidecar

    # One big claimed zone, one small assessed one.
    big_claim = {
        "type": "Feature",
        "properties": {"actor": "Red", "confidence": "claimed"},
        "geometry": {"type": "Polygon", "coordinates": [
            [[-9.0, 37.0], [-1.0, 37.0], [-1.0, 43.0], [-9.0, 43.0], [-9.0, 37.0]]]},
    }
    small = {
        "type": "Feature",
        "properties": {"actor": "Blue"},
        "geometry": {"type": "Polygon", "coordinates": [
            [[0.0, 41.0], [1.0, 41.0], [1.0, 42.0], [0.0, 42.0], [0.0, 41.0]]]},
    }
    card = article_sidecar(_control(big_claim, small))
    assert "Red is claimed to cover the largest mapped share" in card["alt"]


def test_a_locator_with_no_thematic_layer_still_gets_a_sidecar() -> None:
    """The commonest map in an article has no zones at all."""
    from sprezzature_maps import article_sidecar

    card = article_sidecar(_plate())
    assert card["title"] == "Test plate"
    assert card["zones"] == [] and card["markers"] == []
    # No zones means no computable takeaway, and inventing one would be worse.
    assert card["alt"] == card["description"]


# ── furniture and labels, sharing one plate ───────────────────────────────


def test_a_label_yields_to_the_scale_bar_instead_of_being_struck_through() -> None:
    """
    The bar printed over ``TANZANIA`` on the eastern-DRC plate and over
    ``Amman`` and ``Jerusalem`` on the Syrian one. A name with a bar through
    it is not a name; a name that is simply absent costs the reader one
    place out of thirty.
    """
    vp = msm.make_viewport(
        msm.build_projection(list(_IBERIA), "auto"), list(_IBERIA), 520.0, 26.0
    )
    bar_x, bar_y = msm._scale_bar_origin({}, vp)
    assert msm._label_fits(bar_x + 10, bar_y, "LISBOA", size=10, tracking=2, vp=vp)
    vp["reserved"] = msm._reserved_boxes({}, vp)
    assert not msm._label_fits(bar_x + 10, bar_y, "LISBOA", size=10, tracking=2, vp=vp)
    # And a name nowhere near the furniture is untouched.
    assert msm._label_fits(260, 120, "LISBOA", size=10, tracking=2, vp=vp)


def test_the_reserved_box_tracks_the_bar_when_the_bar_moves() -> None:
    """
    A bottom-left legend pushes the scale bar to the other corner. Computing
    the reservation separately is how it ends up protecting empty paper while
    the bar prints over a name somewhere else.
    """
    cfg = _legend_cfg(1000, legend_position="bottom-left")
    vp = msm.make_viewport(
        msm.build_projection(list(_IBERIA), "auto"), list(_IBERIA), 1000.0, 26.0
    )
    bar_x, _bar_y = msm._scale_bar_origin(cfg, vp)
    assert bar_x > vp["width"] / 2, "precondition: a bottom-left card moves the bar right"
    reserved = msm._reserved_boxes(cfg, vp)
    assert any(x0 <= bar_x <= x1 for x0, _y0, x1, _y1 in reserved)


def test_the_caption_owns_its_band_rather_than_printing_on_the_map() -> None:
    """
    Grey monospace over a pale green control fill is not provenance, it is
    noise. The hairline rule above it already says a footer starts here.
    """
    svg = _plate(caption="full", source="Open-source reporting", as_of="2026")
    caption = svg[svg.index('<g id="caption">') :].split("</g>")[0]
    assert "<rect" in caption, "the caption band needs a ground"


# ── where on Earth this is ────────────────────────────────────────────────


def test_no_inset_configured_means_an_empty_group_not_a_missing_one() -> None:
    assert '<g id="inset"></g>' in _plate()


def test_the_inset_shows_the_region_inside_a_wider_context() -> None:
    """
    "Zoom out for perspective, zoom in for detail" is the locator map's one
    rule, and a plate that only ever zooms in answers half of it. A reader
    who does not already know where North Kivu is learns nothing from a map
    of North Kivu.
    """
    import re

    svg = _plate(inset={"position": "top-right"})
    group = svg[svg.index('<g id="inset"') :]
    group = group[: group.index("</g></g>") + 8]
    # Land, and the region drawn as a rectangle inside it.
    assert group.count("<path") >= 2
    coords = [
        tuple(float(v) for v in pair.split(","))
        for d in re.findall(r'<path d="([^"]+)"', group)
        for pair in re.findall(r"[ML]([-\d.]+,[-\d.]+)", d)
    ]
    assert coords, "the inset must draw something"
    # Everything stays inside the inset's own frame.
    box = msm._inset_box(
        _with_inset(),
        msm.make_viewport(
            msm.build_projection(list(_IBERIA), "auto"), list(_IBERIA), 520.0, 26.0
        ),
    )
    width, height = box[2] - box[0], box[3] - box[1]
    assert max(x for x, _y in coords) <= width + 1
    assert max(y for _x, y in coords) <= height + 1


def _with_inset() -> dict[str, Any]:
    return {"region": {"bbox": list(_IBERIA)}, "inset": {"position": "top-right"}}


def test_the_north_arrow_steps_clear_of_the_inset() -> None:
    """Both default to the top-right corner, and an arrow on a small map reads as part of it."""
    plain = _plate()
    with_inset = _plate(inset={"position": "top-right"})
    import re

    def arrow_x(svg: str) -> float:
        group = svg[svg.index('<g id="annotation-furniture">') :]
        return float(re.search(r"translate\(([\d.]+),", group).group(1))

    assert arrow_x(with_inset) < arrow_x(plain)


def test_a_mistyped_inset_key_is_refused() -> None:
    with pytest.raises(ValueError, match="positon"):
        _plate(inset={"positon": "top-right"})
