"""Tests for sub-national boundary tiering: bounding-box pre-filters, tier choice, real renders.

"Admin-1" and "admin-2" are a country's first and second levels of
internal division (a US state or a French region is admin-1; a US county
or a French department is admin-2). This file covers the sub-national
boundary work added to ``scripts/make_situation_map.py`` under project
task #31, which draws on three real boundary datasets: the U.S. Census
Bureau's TIGER data, France's IGN ADMIN EXPRESS data, and OpenStreetMap.
Before this file existed, that code had only ever been checked by hand,
real renders looked at during development, never captured as a test that
could catch a future regression automatically.
"""

from __future__ import annotations

from sprezzature_maps import _load_script

m = _load_script("make_situation_map")

# Real bboxes already verified by hand during development, reused here
# rather than invented fresh, so a failure here means an actual behavior
# regression, not a newly-guessed coordinate that never worked in the
# first place.
_COLORADO_BBOX = (-109.1, 36.9, -102.0, 41.1)  # single US state, ~7deg span
_BRETAGNE_BBOX = (-5.3, 47.1, -0.9, 49.0)  # single FR region, ~4.4deg span
_SWITZERLAND_BBOX = (5.9, 45.75, 10.55, 47.9)  # whole CH, ~4.6deg span
_CONUS_BBOX = (-125.0, 24.5, -66.9, 49.4)  # whole US, ~58deg span
# South of every registry's own bounds (the southernmost, France's, still
# only reaches -21.39) -- genuinely outside all five countries' bbox
# pre-filters. A mid-Pacific bbox would *not* work here: _US_STATES_BOUNDS
# spans nearly the whole longitude range (Alaska/Guam cross near the
# antimeridian), so almost any longitude at a moderate latitude still
# passes that one source's crude, deliberately-loose pre-filter.
_NOWHERE_BBOX = (0.0, -85.0, 10.0, -75.0)


def test_bbox_overlaps_basic_cases() -> None:
    bounds = (0.0, 0.0, 10.0, 10.0)
    assert m._bbox_overlaps((1.0, 1.0, 2.0, 2.0), bounds) is True
    assert m._bbox_overlaps((20.0, 20.0, 30.0, 30.0), bounds) is False
    # Touching exactly at the boundary counts as overlapping (<=/>=, not </>).
    assert m._bbox_overlaps((10.0, 10.0, 20.0, 20.0), bounds) is True
    assert m._bbox_overlaps(None, bounds) is False


def test_load_us_states_bbox_gate() -> None:
    assert m.load_us_states(bbox=None) == []
    assert m.load_us_states(bbox=_NOWHERE_BBOX) == []
    names = [name for name, _ in m.load_us_states(bbox=_COLORADO_BBOX)]
    assert "Colorado" in names


def test_load_fr_regions_bbox_gate() -> None:
    assert m.load_fr_regions(bbox=_NOWHERE_BBOX) == []
    names = [name for name, _ in m.load_fr_regions(bbox=_BRETAGNE_BBOX)]
    assert "Bretagne" in names


def test_load_osm_admin1_registry_spans_three_countries() -> None:
    assert m.load_osm_admin1(bbox=_NOWHERE_BBOX) == []
    ch_names = [name for name, _ in m.load_osm_admin1(bbox=_SWITZERLAND_BBOX)]
    assert "Zürich" in ch_names or "Bern/Berne" in ch_names
    assert m._bbox_in_osm_admin1(_SWITZERLAND_BBOX) is True
    assert m._bbox_in_osm_admin1(_NOWHERE_BBOX) is False


def test_load_admin2_covers_five_countries() -> None:
    assert m.load_admin2(bbox=_NOWHERE_BBOX) == []
    fr_names = [name for name, _ in m.load_admin2(bbox=_BRETAGNE_BBOX)]
    assert any("Finistère" in n or "Morbihan" in n for n in fr_names)


def test_admin1_tier_path_picks_fine_or_coarse_by_span() -> None:
    fine, coarse = m._US_STATES_TOPOJSON, m._US_STATES_TOPOJSON_COARSE
    assert m._admin1_tier_path(_COLORADO_BBOX, fine, coarse) == fine
    assert m._admin1_tier_path(_CONUS_BBOX, fine, coarse) == coarse
    assert m._admin1_tier_path(None, fine, coarse) == fine
    # A custom threshold (as admin-2 callers pass) is honored, not the
    # admin-1 default -- Colorado's ~7deg span is below the 25deg admin-1
    # default (fine) but above admin-2's own 3deg fine threshold (coarse).
    assert (
        m._admin1_tier_path(
            _COLORADO_BBOX, fine, coarse, threshold=m._ADMIN2_FINE_BBOX_DEGREES_THRESHOLD
        )
        == coarse
    )


def test_polygonal_boundary_source_handles_geometry_collection() -> None:
    from shapely.geometry import GeometryCollection, LineString, Point, Polygon

    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert m._polygonal_boundary_source(square) is square

    mixed = GeometryCollection([square, Point(5, 5), LineString([(0, 0), (1, 1)])])
    result = m._polygonal_boundary_source(mixed)
    assert result is not None
    assert result.geom_type in ("Polygon", "MultiPolygon")
    assert result.equals(square)

    no_polygons = GeometryCollection([Point(5, 5), LineString([(0, 0), (1, 1)])])
    assert m._polygonal_boundary_source(no_polygons) is None


def test_attribution_layer_only_credits_osm_when_in_view() -> None:
    cfg_switzerland = {
        "title": "test",
        "region": {"bbox": list(_SWITZERLAND_BBOX)},
        "canvas_width": 400,
    }
    svg = m.build_map(cfg_switzerland)
    assert "OpenStreetMap" in svg
    assert "ODbL" in svg

    # Bretagne overlaps no OSM admin-1/admin-2 source -- no credit owed, none added.
    cfg_bretagne = {
        "title": "test",
        "region": {"bbox": list(_BRETAGNE_BBOX)},
        "canvas_width": 400,
    }
    svg_fr = m.build_map(cfg_bretagne)
    assert "OpenStreetMap" not in svg_fr


def test_internal_and_admin2_borders_render_real_paths() -> None:
    cfg = {
        "title": "test",
        "region": {"bbox": list(_BRETAGNE_BBOX)},
        "canvas_width": 400,
        "internal_borders": {"show": True},
        "admin2_borders": {"show": True},
    }
    svg = m.build_map(cfg)
    assert '<g id="internal-borders">' in svg
    assert '<g id="admin2-borders">' in svg
    internal = svg.split('<g id="internal-borders">', 1)[1].split("</g>", 1)[0]
    admin2 = svg.split('<g id="admin2-borders">', 1)[1].split("</g>", 1)[0]
    assert "<path" in internal
    assert "<path" in admin2


def test_admin2_borders_hidden_above_zoom_gate() -> None:
    # CONUS-wide (~58deg span) is well past the 8deg admin-2 show/hide gate --
    # the group must exist (id present) but be empty, not merely un-labelled.
    cfg = {
        "title": "test",
        "region": {"bbox": list(_CONUS_BBOX)},
        "canvas_width": 400,
        "admin2_borders": {"show": True},
    }
    svg = m.build_map(cfg)
    assert '<g id="admin2-borders"></g>' in svg
