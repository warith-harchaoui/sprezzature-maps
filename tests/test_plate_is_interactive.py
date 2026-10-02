"""
The plate's own controls, driven rather than inspected.

A situation map now carries layer switches, a confidence filter and a
clickable legend inside the SVG file itself. None of that can be checked by
rendering: ``resvg`` draws the document, it does not run the script, so a
rasteriser would report a perfectly healthy plate whose every control is
dead.

So this builds a real plate, parses it into a minimal DOM, and executes the
plate's own script against it under Node — clicking the switches and reading
back what moved. It skips where Node is absent rather than pretending to
have checked.

The static half is checked here too, and matters just as much: the controls
ship hidden and are revealed by the script, so an ``<img>`` embed, a PDF or
a browser with scripting off must all still see exactly the map that shipped
before any of this existed.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")
pc = _load_script("_plate_controls")


def _band(west: float, east: float, actor: str, confidence: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"actor": actor, "confidence": confidence},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[west, 44.5], [east, 44.5], [east, 52.5], [west, 52.5], [west, 44.5]]
            ],
        },
    }


def _plate(**overrides: Any) -> str:
    cfg: dict[str, Any] = {
        "title": "Interactive plate",
        "region": {"bbox": [22.0, 44.0, 41.0, 53.0]},
        "canvas_width": 1000,
        "basemap": {"relief": False},
        "areas_of_control": {
            "category_field": "actor",
            "palette": {"Government": "#9cc3d5", "Occupying force": "#d98880"},
            "source": {
                "type": "FeatureCollection",
                "features": [
                    _band(22.5, 29, "Government", "assessed"),
                    _band(29, 33, "Government", "reported"),
                    _band(33, 37, "Occupying force", "assessed"),
                    _band(37, 40.5, "Occupying force", "claimed"),
                ],
            },
        },
    }
    cfg.update(overrides)
    msm.validate_config(cfg)
    return msm.build_map(cfg)


# ── the static half ───────────────────────────────────────────────────────


def test_the_controls_ship_hidden_so_a_picture_is_still_a_picture() -> None:
    """
    An ``<img>`` embed never runs the script. If the panel were visible by
    default, every existing use of these plates as a plain image would grow
    a control panel it cannot operate.
    """
    svg = _plate()
    assert '<g id="plate-controls" style="display:none"' in svg


def test_static_mode_ships_no_script_at_all() -> None:
    assert "<script" not in _plate(interactivity="static")
    assert "plate-controls" not in _plate(interactivity="static")


def test_an_unknown_interactivity_mode_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown interactivity"):
        _plate(interactivity="interactive")


def test_a_plate_with_no_thematic_layer_gets_no_panel() -> None:
    """A control that cannot change anything is noise, not a feature."""
    cfg = {
        "title": "Locator",
        "region": {"bbox": [22.0, 44.0, 41.0, 53.0]},
        "canvas_width": 600,
        "basemap": {"relief": False},
    }
    msm.validate_config(cfg)
    assert "plate-controls" not in msm.build_map(cfg)


def test_the_confidence_filter_offers_the_floor_it_filters_to() -> None:
    """
    ``_tiers_present`` answers "which tiers need a legend row" and omits
    ``assessed``, because an unmarked zone already means that. A *filter* is
    a different question: without the floor, the most useful setting on the
    panel — show me only what is assessed — is the one a reader cannot
    reach. It shipped that way for about ten minutes.
    """
    steps = re.findall(r'data-step="([a-z]+)"', _plate())
    assert steps == ["assessed", "reported", "claimed"]


# ── the half only a script can answer ─────────────────────────────────────

_HARNESS = r"""
const fs = require('fs');
function El(spec) {
  this.tag = spec.tag; this.attrs = spec.attrs; this.style = {}; this.handlers = {};
  this.children = (spec.children || []).map(c => new El(c));
}
El.prototype.getAttribute = function (k) { return k in this.attrs ? this.attrs[k] : null; };
El.prototype.setAttribute = function (k, v) { this.attrs[k] = v; };
El.prototype.addEventListener = function (k, fn) { (this.handlers[k] = this.handlers[k] || []).push(fn); };
El.prototype.click = function () { (this.handlers.click || []).forEach(fn => fn()); };
El.prototype.all = function () { return this.children.reduce((a, c) => a.concat(c.all()), [this]); };
function matches(el, sel) {
  if (sel[0] === '#') return el.attrs.id === sel.slice(1);
  if (sel[0] === '.') return (el.attrs.class || '').split(' ').includes(sel.slice(1));
  const m = sel.match(/^\[([^\]=]+)(?:="([^"]*)")?\]$/);
  if (m) return m[2] === undefined ? (m[1] in el.attrs) : el.attrs[m[1]] === m[2];
  return false;
}
El.prototype.querySelector = function (s) { return this.all().find(e => matches(e, s)) || null; };
El.prototype.querySelectorAll = function (s) { return this.all().filter(e => matches(e, s)); };

const svg = new El(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')));
global.window = { location: { hash: '' },
                  history: { replaceState: (a, b, h) => { global.window.location.hash = h; } } };
svg.ownerDocument = { defaultView: global.window };
global.document = { currentScript: { ownerSVGElement: svg }, documentElement: svg };
eval(fs.readFileSync(process.argv[3], 'utf8'));

const shown = sel => svg.querySelectorAll(sel).filter(e => e.style.display !== 'none').length;
const pick = (sel, attr, value) =>
  svg.querySelectorAll(sel).find(e => e.getAttribute(attr) === value);
const out = { steps: [], layers: {}, legend: null, hash: null };
out.zonesInitially = shown('[data-confidence]');
['assessed', 'reported', 'claimed'].forEach(tier => {
  pick('.pc-step', 'data-step', tier).click();
  out.steps.push(shown('[data-confidence]'));
});
pick('.pc-switch', 'data-switch', 'water').click();
out.layers.water = ['rivers', 'lakes', 'basemap-bathymetry']
  .map(id => (svg.querySelector('[data-layer-id="' + id + '"]') || {style: {}}).style.display || '');
pick('.pc-switch', 'data-switch', 'water').click();
out.layers.waterBack = (svg.querySelector('[data-layer-id="rivers"]') || {style: {}}).style.display || '';
const legend = svg.querySelectorAll('[data-legend-category]');
legend[0].click();
out.legend = shown('[data-confidence]');
out.hash = global.window.location.hash;
console.log(JSON.stringify(out));
"""


def _drive(svg: str, tmp_path: Path) -> dict[str, Any]:
    """Execute the plate's own script against the plate's own markup."""
    body = re.sub(r"<script>.*?</script>", "", svg, flags=re.S)
    root = ET.fromstring(body)

    def strip(tag: str) -> str:
        return tag.split("}")[-1]

    def node(element: ET.Element) -> dict[str, Any]:
        return {
            "tag": strip(element.tag),
            "attrs": {strip(k): v for k, v in element.attrib.items()},
            "children": [node(child) for child in element],
        }

    (tmp_path / "dom.json").write_text(json.dumps(node(root)), encoding="utf-8")
    script = re.search(r"<script><!\[CDATA\[(.*?)\]\]></script>", svg, re.S)
    assert script, "the plate must carry its own script in self-contained mode"
    (tmp_path / "controls.js").write_text(script.group(1), encoding="utf-8")
    (tmp_path / "harness.js").write_text(_HARNESS, encoding="utf-8")
    result = subprocess.run(
        ["node", str(tmp_path / "harness.js"), str(tmp_path / "dom.json"),
         str(tmp_path / "controls.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the plate's script")
def test_the_confidence_ladder_actually_filters(tmp_path: Path) -> None:
    """
    The control this genre exists for: show only what is assessed, or admit
    reported movement, or admit a belligerent's unverified claim.
    """
    driven = _drive(_plate(), tmp_path)
    assert driven["zonesInitially"] == 4
    # assessed only → the two assessed bands; then three; then all four.
    assert driven["steps"] == [2, 3, 4]


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the plate's script")
def test_a_layer_switch_moves_every_group_it_owns(tmp_path: Path) -> None:
    """"Water" is one switch and three drawn groups; a reader thinks in the switch."""
    driven = _drive(_plate(), tmp_path)
    assert driven["layers"]["water"] == ["none", "none", "none"]
    assert driven["layers"]["waterBack"] == "", "a switch must toggle, not latch"


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the plate's script")
def test_the_legend_isolates_a_class_and_the_reading_is_shareable(tmp_path: Path) -> None:
    driven = _drive(_plate(), tmp_path)
    assert driven["legend"] == 2, "isolating Government leaves its two bands"
    assert "only=Government" in driven["hash"]
