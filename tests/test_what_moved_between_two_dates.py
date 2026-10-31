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
