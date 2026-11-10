"""Held, taken, lost: the question a single frame cannot answer.

A control plate shows a moment. The question a researcher brings is about
two of them, and the package's answer until now was an arrow — which is
the wrong answer. An arrow asserts intent, momentum and success at once
while evidencing none of the three; the early maps of the 2022 invasion
used big ones and read as a blitzkrieg that was not happening, which is
why the graphics desks moved away from them.

A difference layer asserts nothing. It takes two extents, subtracts them,
and lets the reader see how much of the map is the third colour — the
ground where nothing happened, which is usually most of it and is usually
the finding.

What has to be right is not the subtraction. It is everything around it:
that both sides are present before anything is drawn, that a hand-traced
ring which crosses itself does not take the plate down, that the key shows
the colours the map actually drew, and that a class covering a tenth of a
per cent says so rather than taking a silent row a reader then hunts for.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import Polygon, mapping

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")


def _fc(*polygons: Polygon) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": mapping(p)}
            for p in polygons
        ],
    }


#: Two overlapping squares: half of the first is kept, half is lost, and
#: an equal area is taken.
_BEFORE = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
_AFTER = Polygon([(1, 0), (3, 0), (3, 2), (1, 2)])


def _config(**change: object) -> dict:
    return {
        "region": {"bbox": [-1.0, -1.0, 4.0, 3.0]},
        "canvas_width": 600,
        "basemap": {"relief": False},
        "change": {"before": _fc(_BEFORE), "after": _fc(_AFTER), **change},
    }


# ── the subtraction ──────────────────────────────────────────────────────


def test_the_three_classes_are_what_subtraction_says() -> None:
    parts = msm._change_geometries(_config(), Path("."))
    assert parts["held"].area == pytest.approx(2.0)
    assert parts["gained"].area == pytest.approx(2.0)
    assert parts["lost"].area == pytest.approx(2.0)


def test_one_side_missing_is_refused() -> None:
    """A difference with one side absent is not a difference.

    It is the other side, drawn in the colour of a change nobody
    computed — which is the most confident wrong picture this layer
    could produce.
    """
    cfg = {"region": {"bbox": [0.0, 0.0, 3.0, 3.0]}, "change": {"after": _fc(_AFTER)}}
    with pytest.raises(ValueError, match="needs a 'before' extent"):
        msm._change_geometries(cfg, Path("."))


def test_a_self_crossing_ring_is_repaired_rather_than_fatal() -> None:
    """A hand-traced extent is the normal input, and hands cross rings.

    GEOS answers an invalid ring with a "side location conflict" raised
    from inside the set operation, naming a coordinate and not the file
    it came from. Every other loader in the generator repairs on the way
    in; this one was the exception until a demo plate hit it.
    """
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])
    cfg = {
        "region": {"bbox": [0.0, 0.0, 3.0, 3.0]},
        "change": {"before": _fc(bowtie), "after": _fc(_AFTER)},
    }
    parts = msm._change_geometries(cfg, Path("."))
    assert parts["held"].area > 0.0


# ── the key ──────────────────────────────────────────────────────────────


def _draw(cfg: dict) -> str:
    bbox = cfg["region"]["bbox"]
    proj = msm.build_projection(bbox, "auto")
    vp = msm.make_viewport(proj, bbox, float(cfg["canvas_width"]), 30.0)
    return msm._change_layer(cfg, proj, vp)


def test_the_key_names_each_class_and_its_share() -> None:
    """The number is what a reader came for, and what stops a silent row.

    Shares are taken over the union of both extents, not over the plate:
    "how much of this changed hands" is asked of the ground either side
    ever held, not of a frame that is mostly ocean.
    """
    cfg = _config()
    _draw(cfg)
    shares = cfg["_change_key"]
    assert set(shares) == {"held", "gained", "lost"}
    assert shares["held"] == pytest.approx(1 / 3, abs=0.02)

    labels = [row["label"] for row in msm._legend_rows(cfg, 1.0)]
    assert any(label.startswith("Held throughout — 33%") for label in labels), labels
    assert any(label.startswith("Taken — 33%") for label in labels), labels


def test_a_class_that_drew_nothing_gets_no_row() -> None:
    """A key for a colour nothing used sends a reader looking for it."""
    same = _config()
    same["change"]["after"] = _fc(_BEFORE)
    _draw(same)
    assert set(same["_change_key"]) == {"held"}
    labels = [row["label"] for row in msm._legend_rows(same, 1.0)]
    assert not any(label.startswith("Taken") for label in labels), labels


def test_the_key_simulates_the_blend_the_layer_draws() -> None:
    """A key showing a different colour from the ground is worse than none.

    The layer drew a plain alpha fill while ``_as_rendered`` simulated a
    multiply, so a map drawn tan, red and blue was keyed olive, dark red
    and dark green. One function now answers "how do these fills meet the
    terrain" for both.
    """
    cfg = _config()
    cfg["basemap"] = {"relief": True}
    cfg["_plate"] = msm._PLATES["day"]
    how = msm._change_blend(cfg)
    assert how["blend"] == msm._PLATES["day"]["blend"]
    markup = _draw(cfg)
    assert f"mix-blend-mode:{how['blend']}" in markup


def test_the_interval_reaches_the_footer() -> None:
    """A difference layer is a claim about two moments.

    A plate that draws one without naming them is drawing arithmetic.
    """
    cfg = _config(**{"from": "April 2022", "to": "December 2024"})
    cfg["caption"] = "full"
    cfg["method"] = "schematic"
    lines = msm._caption_lines(cfg)
    assert "Change from April 2022 to December 2024" in lines


def test_a_mistyped_option_is_refused() -> None:
    cfg = _config(fromm="2022")
    with pytest.raises(ValueError, match="fromm"):
        msm.validate_config(cfg)


# ── whose ground ─────────────────────────────────────────────────────────


def _zone(actor: str, poly: Polygon) -> dict:
    return {
        "type": "Feature",
        "properties": {"actor": actor},
        "geometry": mapping(poly),
    }


def _camps(*zones: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(zones)}


def _two_camp_config(**change: object) -> dict:
    """A theatre two camps tile at both dates, with the line walking east.

    ``A`` holds the western half in January and pushes the line from 1.0
    to 1.5 by June, so it takes exactly 0.5 of ground and ``B`` loses the
    same 0.5. Nothing else changes, and critically the *union* of the two
    camps is the same rectangle on both dates.
    """
    before = _camps(
        _zone("A", Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])),
        _zone("B", Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])),
    )
    after = _camps(
        _zone("A", Polygon([(0, 0), (1.5, 0), (1.5, 1), (0, 1)])),
        _zone("B", Polygon([(1.5, 0), (2, 0), (2, 1), (1.5, 1)])),
    )
    return {
        "region": {"bbox": [-0.5, -0.5, 2.5, 1.5]},
        "canvas_width": 600,
        "basemap": {"relief": False},
        "areas_of_control": {
            "source": after,
            "palette": {"A": "#b03a3a", "B": "#5b7fa6"},
        },
        "change": {"before": before, "from": "January", "to": "June", **change},
    }


def test_a_control_layer_is_not_subtracted_from_itself() -> None:
    """The defect ``change`` shipped with, and the number that shows it.

    ``after`` defaults to ``areas_of_control.source``, which is every
    camp's zones at once. The camps of a control layer tile the same
    theatre at both dates, so that union barely moves: subtracting it
    from itself gave ``held`` the whole rectangle and ``gained`` an area
    of exactly 0.0 while the line between the camps had walked half a
    unit east. The plate stated that nothing happened.

    Refused now, naming the camps, because there is no honest difference
    to draw from a union — only a correct subtraction of the wrong two
    sets.
    """
    with pytest.raises(ValueError, match="carries 2 camps"):
        msm._change_geometries(_two_camp_config(), Path("."))


def test_an_actor_gets_the_ground_it_actually_took() -> None:
    """Both sides filtered by the same camp, and the two readings agree.

    0.5 taken by ``A`` is 0.5 lost by ``B``: a difference that does not
    balance across the camps is a difference of two different questions.
    """
    taken = msm._change_geometries(_two_camp_config(actor="A"), Path("."))
    assert taken["gained"].area == pytest.approx(0.5)
    assert taken["held"].area == pytest.approx(1.0)
    assert taken["lost"].area == pytest.approx(0.0)

    lost = msm._change_geometries(_two_camp_config(actor="B"), Path("."))
    assert lost["lost"].area == pytest.approx(taken["gained"].area)
    assert lost["gained"].area == pytest.approx(0.0)


def test_a_camp_nobody_is_fighting_cannot_move_the_numbers() -> None:
    """The class guard: both sides filtered, or neither side is.

    Ground belonging to a third camp, present identically on both dates
    and nowhere near the two that moved, must not appear in any of the
    three classes. It is the measurement that catches an unfiltered side
    whichever side that is — drop the filter from ``before`` and the
    third camp's ground lands in ``lost``; drop it from ``after`` and it
    lands in ``gained``; drop it from both and ``held`` swallows it.

    That is the shape of the defect, not one instance of it: a
    subtraction whose two sides are not filtered by the same actor.
    """
    elsewhere = _zone("C", Polygon([(5, 0), (7, 0), (7, 1), (5, 1)]))
    cfg = _two_camp_config(actor="A")
    cfg["region"]["bbox"] = [-0.5, -0.5, 8.0, 1.5]
    cfg["change"]["before"]["features"].append(elsewhere)
    cfg["areas_of_control"]["source"]["features"].append(elsewhere)
    cfg["areas_of_control"]["palette"]["C"] = "#8a8f96"

    parts = msm._change_geometries(cfg, Path("."))
    assert parts["gained"].area == pytest.approx(0.5)
    assert parts["held"].area == pytest.approx(1.0)
    assert parts["lost"].area == pytest.approx(0.0)
    # And nothing the function returned reaches as far east as C's ground,
    # which is the same statement made geometrically rather than by area:
    # two slivers that happened to cancel would pass the areas above.
    for key, geom in parts.items():
        if not geom.is_empty:
            assert geom.bounds[2] <= 2.0 + 1e-9, (key, geom.bounds)


def test_a_misspelt_actor_is_refused_rather_than_drawn() -> None:
    """An empty side is not an empty finding.

    ``actor`` filtering a side down to nothing would make the whole of
    the other side a change, so the plate would assert this actor took
    every square kilometre it holds. A typo in a hand-typed proper noun
    is the realistic cause, so the camps the side does spell are named.
    """
    with pytest.raises(ValueError, match="change.actor is 'Aa'"):
        msm._change_geometries(_two_camp_config(actor="Aa"), Path("."))


def test_the_actor_is_matched_the_way_every_other_name_here_is() -> None:
    """Folded, like the choropleth's unit names and for the same reason.

    A camp spelt "Côte" in the assessment and "Cote" in the config is not
    a disagreement about which camp is meant.
    """
    cfg = _two_camp_config(actor="a")
    assert msm._change_geometries(cfg, Path("."))["gained"].area == pytest.approx(0.5)


def test_the_camp_property_is_the_one_the_control_layer_already_names() -> None:
    """One spelling of "whose ground is this", not two.

    ``areas_of_control.category_field`` already answers it per feature. A
    ``change``-only field name would be a second thing to keep in step.
    """
    cfg = _two_camp_config(actor="A")
    cfg["areas_of_control"]["category_field"] = "side"
    for coll in (cfg["change"]["before"], cfg["areas_of_control"]["source"]):
        for feat in coll["features"]:
            feat["properties"] = {"side": feat["properties"]["actor"]}
    assert msm._change_geometries(cfg, Path("."))["gained"].area == pytest.approx(0.5)


def test_the_footer_says_whose_ground_moved() -> None:
    """ "Taken" names a direction and cannot name a camp.

    On a plate that also fills both camps' zones, a key reading "Taken —
    33%" with no actor is a genuine ambiguity. Answered once in the
    footer rather than three times in the key.
    """
    cfg = _two_camp_config(actor="A")
    cfg["caption"] = "full"
    cfg["method"] = "schematic"
    assert "Change in ground held by A, January to June" in msm._caption_lines(cfg)


def test_actor_is_an_option_the_validator_accepts() -> None:
    """The key was removed once for being read by no line. It is read now."""
    assert "actor" in msm.SECTION_KEYS["change"]
    msm.validate_config(_two_camp_config(actor="A"))


# ── the editorial register, the hover, the sequence ──────────────────────


def _story_config(style: str = "editorial") -> dict:
    cfg = _config(**{"from": "April 2022", "to": "December 2022"})
    cfg["style"] = style
    cfg["title"] = "Change"
    msm.validate_config(cfg)
    return cfg


def _plate(cfg: dict) -> str:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _plates import plate

    return plate(cfg)


def _class_path(svg: str, key: str) -> str:
    import re

    found = re.search(rf'<path class="hit"[^>]*data-change="{key}"[^>]*/>', svg)
    assert found, f"no {key} path on the plate"
    return found.group(0)


def test_the_editorial_change_is_one_hue_and_lost_ground_is_an_outline() -> None:
    """
    Held pale, taken full, lost an outline with nothing inside: what is
    drawn where ground was lost is an absence, and a second hue for it would
    read as a second camp (ASSESSMENT, round 7).
    """
    svg = _plate(_story_config())
    held, gained, lost = (_class_path(svg, k) for k in ("held", "gained", "lost"))
    assert f'fill="{msm._CHANGE_EDITORIAL["held"]}"' in held
    assert f'fill="{msm._CHANGE_EDITORIAL["gained"]}"' in gained
    assert 'fill-opacity="0"' in lost and "stroke-dasharray" in lost
    assert f'stroke="{msm._CHANGE_EDITORIAL["lost"]}"' in lost
    assert "mix-blend-mode" not in held, "a multiply cannot lighten the pale tint"


def test_the_key_draws_lost_ground_the_way_the_map_does() -> None:
    cfg = _story_config()
    _plate(cfg)
    rows = {row.get("change"): row for row in msm._legend_rows(cfg, 1.0)}
    swatch = msm._legend_mark(rows["lost"], 0.0, 10.0, 12.0, 1.0)
    assert 'fill="none"' in swatch and "stroke-dasharray" in swatch
    assert 'fill="none"' not in msm._legend_mark(rows["gained"], 0.0, 10.0, 12.0, 1.0)


def test_the_atlas_change_keeps_its_three_fills() -> None:
    svg = _plate(_story_config("atlas"))
    assert 'fill-opacity="0"' not in _class_path(svg, "lost")


def test_hovering_a_place_says_what_it_was_at_each_date() -> None:
    """
    The before / after, said of the place under the pointer rather than
    asked of the reader's memory of a second frame.
    """
    svg = _plate(_story_config())
    for key, words in (
        ("held", "held in April 2022 and in December 2022"),
        ("gained", "not held in April 2022, held in December 2022"),
        ("lost", "held in April 2022, not in December 2022"),
    ):
        path = _class_path(svg, key)
        assert 'tabindex="0"' in path and words in path
        group = svg[svg.index(path):]
        group = group[: group.index("</g>", group.index('class="tip"'))]
        assert words in group, f"the {key} bubble does not follow its own path"


def test_each_bubble_is_alone_with_its_path() -> None:
    """``.hit:hover~.tip`` reaches every following sibling: one group each."""
    import re

    svg = _plate(_story_config())
    layer = svg[svg.index('<g id="change">'):]
    for group in re.findall(r"<g><path class=\"hit\"(.*?)</g></g>", layer, flags=re.S)[:3]:
        assert group.count('class="hit"') == 0


def test_the_difference_is_never_counted_as_a_camp() -> None:
    """The sidecar and the auditor read camps off ``data-category``."""
    svg = _plate(_story_config())
    layer = svg[svg.index('<g id="change">'): svg.index("</g>", svg.index('data-change="lost"'))]
    assert "data-category" not in layer


def test_a_key_row_isolates_its_class() -> None:
    """The row's label carries a share; the button must carry the class."""
    cfg = _story_config()
    svg = _plate(cfg)
    assert 'data-legend-category="gained"' in svg
    from sprezzature_maps import _load_script as load

    script = load("_plate_controls").controls_script()
    assert "data-change" in script


def test_the_change_tells_its_interval_in_order() -> None:
    """First date's ground, then the loss empties, then the gain arrives."""
    import re

    style = msm._animation_css(_story_config())
    assert "@keyframes sz-lose" in style
    delay = {
        key: float(re.search(rf'data-change="{key}"\][^{{]*\{{animation:sz-fade [\d.]+s ease-out ([\d.]+)s', style).group(1))
        for key in ("held", "gained")
    }
    assert delay["gained"] > delay["held"]
    guard = style[style.index("prefers-reduced-motion"):]
    for key in ("held", "gained", "lost"):
        assert f'#change [data-change="{key}"]' in guard
    assert "forwards;" not in style.replace("backwards", "")


# ── two records of one border ────────────────────────────────────────────


def test_a_hairline_between_two_tracings_is_not_a_change() -> None:
    """
    Two records of one border never share their vertices. Subtracted, they
    left a hairline along the whole frontier, and the Munich plate keyed
    "Taken -- under 1%" for a state that took nothing in 1938.
    """
    nudged = Polygon([(0, 0), (2, 0), (2.004, 2), (0, 2)])
    cfg = _config()
    cfg["change"]["after"] = _fc(nudged)
    parts = msm._change_geometries(cfg, Path("."))
    assert parts["gained"].is_empty and parts["lost"].is_empty
    cfg["change"]["sliver_km"] = 0
    assert not msm._change_geometries(cfg, Path("."))["gained"].is_empty


def test_a_real_gain_beside_a_hairline_is_kept_whole() -> None:
    cfg = _config()
    parts = msm._change_geometries(cfg, Path("."))
    assert parts["gained"].area == pytest.approx(2.0), "the filter ate ground that moved"


def test_a_change_plate_keeps_its_key_corner_to_itself() -> None:
    """The locator took the corner the key was in: the Serbian plate's did."""
    cfg = _story_config()
    cfg["legend_position"] = "top-right"
    assert msm._has_key_card(cfg)
    assert msm._inset_corner(cfg, 1.0, 1000.0) != "top-right"


@pytest.mark.parametrize("name", ["munich-1938", "serbia-1913"])
def test_a_shipped_change_plate_is_two_records_not_a_memory(name: str) -> None:
    """
    Both sides come from tracked OpenHistoricalMap files, public domain,
    each naming the relation it was taken from, so the plate can be taken
    again with ``scripts/fetch_historical_extent.py``.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import build_situation_examples as examples

    change = examples.BUILDERS[name]()["change"]
    for side in ("before", "after"):
        props = change[side]["features"][0]["properties"]
        assert props["license"].startswith("CC0"), props
        assert props["source"].startswith("OpenHistoricalMap relation "), props
        assert props["start_date"] and props["end_date"], props
    assert change["before"]["features"][0]["properties"]["end_date"] <= (
        change["after"]["features"][0]["properties"]["start_date"]
    ), "the 'before' record ends after the 'after' one begins"
