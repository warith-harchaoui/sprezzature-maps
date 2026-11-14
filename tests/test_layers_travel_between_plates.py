"""A plate's layers leave it and come back, and the next plate reuses them.

The rule, from the geopolitics researcher who asked for it on 2026-11-13: the
work a cabinet put into one commission -- a coastline, a front, a checkpoint
-- must never be redone for the next one, at another scale or projection.
"Never any loss." These tests hold the mechanics of that to account: export
to GeoJSON and KML, import back, and a `layers:` library read by a plate
rendered from a folder that is not its own.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from click.testing import CliRunner

from sprezzature_maps import export_layers, import_layers
from sprezzature_maps.cli import main
from sprezzature_maps.gis import from_kml, to_kml

_PLATE = {
    "title": "Flux",
    "as_of": "2026-11-13",
    "source": "Panel d'experts",
    "region": {"bbox": [21.4, 12.6, 26.6, 16.8]},
    "arrows": [
        {
            "line": [[22.84, 16.07], [22.83, 15.0], [25.25, 13.68]],
            "bend": 0.08,
            "style": "dashed",
            "label": "flux",
        },
    ],
    "front": {"line": [[23.0, 13.0], [24.0, 14.0]], "label": "ligne"},
    "events": [{"lon": 22.83, "lat": 15.0, "label": "al-Tina", "color": "#9c3b2e"}],
    "annotations": [{"at": [25.35, 13.63], "text": "El Fasher", "place": "below-left"}],
    "labels": {"places": [{"lon": 24.88, "lat": 12.05, "text": "Nyala"}]},
    "areas_of_control": {
        "source": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[23, 13], [24, 13], [24, 14], [23, 13]]],
                    },
                    "properties": {"actor": "RSF", "confidence": "reported"},
                }
            ],
        }
    },
}

_BLOCKS = ("arrows", "front", "events", "annotations", "labels", "areas_of_control")


def test_export_then_import_gives_every_block_back_unchanged() -> None:
    back = import_layers(export_layers(_PLATE)["features"])
    for key in _BLOCKS:
        assert back[key] == _PLATE[key], key


def test_the_collection_carries_the_plates_provenance() -> None:
    meta = export_layers(_PLATE)["sprezzature"]
    assert meta["as_of"] == "2026-11-13" and meta["source"] == "Panel d'experts"
    assert meta["bbox"] == [21.4, 12.6, 26.6, 16.8]


def test_kml_round_trip_keeps_every_block() -> None:
    back = import_layers(from_kml(to_kml(export_layers(_PLATE))))
    for key in _BLOCKS:
        assert back[key] == _PLATE[key], key


def test_a_foreign_layer_is_placed_by_geometry() -> None:
    foreign = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [22.83, 15.0]},
            "properties": {"name": "al-Tina"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            "properties": {"name": "route"},
        },
    ]
    blocks = import_layers(foreign)
    assert blocks["events"][0]["label"] == "al-Tina"
    assert blocks["arrows"][0]["line"] == [[0, 0], [1, 1]]


def test_a_layer_library_is_read_from_the_configs_own_folder(tmp_path: Path) -> None:
    """Rendered from another directory, the plate still finds its layers.

    `make-map situation-map --config` used to drop the config's directory, so
    every relative path resolved against wherever the command was typed.
    """
    folder = tmp_path / "dossier"
    folder.mkdir()
    library = {k: _PLATE[k] for k in ("arrows", "events", "annotations")}
    (folder / "couches.geojson").write_text(json.dumps(export_layers(library)), encoding="utf-8")
    plate = {
        "title": "Reprise",
        "as_of": "2026-11-13",
        "region": {"bbox": [21.4, 12.6, 26.6, 16.8]},
        "layers": ["couches.geojson"],
        "cities": {"show": False},
        "rivers": {"show": False},
        "basemap": {"relief": False},
    }
    (folder / "plate.yaml").write_text(yaml.safe_dump(plate), encoding="utf-8")
    elsewhere = tmp_path / "ailleurs"
    elsewhere.mkdir()
    cwd = os.getcwd()
    try:
        os.chdir(elsewhere)
        result = CliRunner().invoke(
            main, ["situation-map", "--config", str(folder / "plate.yaml"), "--out", "p.svg"]
        )
    finally:
        os.chdir(cwd)
    assert result.exit_code == 0, result.output
    svg = (elsewhere / "p.svg").read_text(encoding="utf-8")
    assert "al-Tina" in svg and "El Fasher" in svg


def test_the_cli_exports_and_imports(tmp_path: Path) -> None:
    config = tmp_path / "plate.yaml"
    config.write_text(yaml.safe_dump(_PLATE, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "couches.kml"
    runner = CliRunner()
    exported = runner.invoke(main, ["export", "--config", str(config), "--out", str(out)])
    assert exported.exit_code == 0, exported.output
    imported = runner.invoke(main, ["import", str(out)])
    assert imported.exit_code == 0, imported.output
    assert yaml.safe_load(imported.output)["events"] == _PLATE["events"]


def test_a_layer_in_another_crs_is_refused_not_read_as_degrees(tmp_path: Path) -> None:
    """A Lambert-93 file read as degrees lands nowhere, without a word."""
    import pytest

    from sprezzature_maps.gis import read_features

    lambert = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [652000, 6862000]},
                "properties": {"name": "Paris"},
            }
        ],
    }
    path = tmp_path / "paris.geojson"
    path.write_text(json.dumps(lambert), encoding="utf-8")
    with pytest.raises(ValueError, match="EPSG::2154"):
        read_features(path)


def test_a_features_own_id_survives_the_trip(tmp_path: Path) -> None:
    from sprezzature_maps.gis import read_features

    path = tmp_path / "ids.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "cp-7",
                        "geometry": {"type": "Point", "coordinates": [22.8, 15.0]},
                        "properties": {"name": "checkpoint"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    events = import_layers(read_features(path))["events"]
    assert events[0]["id"] == "cp-7"
    again = export_layers({"events": events})["features"][0]["properties"]
    assert again["id"] == "cp-7"


def test_exported_zones_wind_by_the_right_hand_rule() -> None:
    clockwise = [[[23, 13], [23, 14], [24, 14], [24, 13], [23, 13]]]
    plate = {
        "areas_of_control": {
            "source": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": clockwise},
                        "properties": {"actor": "X", "confidence": "reported"},
                    }
                ],
            }
        }
    }
    ring = export_layers(plate)["features"][0]["geometry"]["coordinates"][0]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True))
    assert area > 0, "the exterior ring must run counter-clockwise (RFC 7946)"
