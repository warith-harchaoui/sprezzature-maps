"""
A regional plate draws the rivers the region is about.

The 1:50m centerlines hold a continent's trunks: no Vltava on a plate of
Czechoslovakia, no Morava and no Vardar on a plate of Serbia. A regional
plate now reads the 1:10m set (``scripts/build_rivers_10m.py``), in which
Natural Earth files the Vardar under its tributary's name; the Vardar comes
from OpenStreetMap, and a plate that draws it says so.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from shapely.geometry import Point

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

_SERBIA = (17.6, 40.2, 24.4, 45.6)
_CZECHOSLOVAKIA = (11.3, 47.0, 27.4, 51.6)


def _names(bbox) -> dict:
    return {name: geom for geom, name, _rank in msm.load_rivers(bbox)}


def test_a_regional_plate_reads_the_fine_rivers() -> None:
    assert msm._rivers_path_for_bbox(_SERBIA).name == "rivers-10m.geojson"
    assert msm._rivers_path_for_bbox((-11.0, 35.0, 30.0, 60.0)).name == "rivers-50m.geojson"
    assert {"Vltava", "Morava"} <= set(_names(_CZECHOSLOVAKIA))


def test_the_vardar_runs_from_gostivar_to_the_sea() -> None:
    vardar = _names(_SERBIA)["Vardar"]
    for town, (lon, lat) in {
        "Gostivar": (20.91, 41.80), "Skopje": (21.43, 42.00),
        "Veles": (21.78, 41.72), "the Thermaic Gulf": (22.72, 40.53),
    }.items():
        assert vardar.distance(Point(lon, lat)) * 111 < 3, f"the Vardar misses {town}"


def test_the_treska_is_only_the_treska() -> None:
    """Natural Earth's 'Treska' ran on down the Vardar to the sea."""
    treska = _names(_SERBIA)["Treska"]
    assert treska.bounds[3] <= 42.05 and treska.bounds[2] <= 21.4


def test_a_plate_that_draws_the_osm_vardar_credits_osm() -> None:
    assert msm.osm_rivers_in_view(list(_SERBIA))
    assert not msm.osm_rivers_in_view([-10.0, 36.0, 4.0, 44.0])


def test_a_name_only_the_fine_set_carries_is_a_known_name() -> None:
    assert "vardar" in msm._known_feature_names("rivers")
