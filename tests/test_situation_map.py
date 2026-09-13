"""
Situation-map tests: the vendored assets, and the data they carry.

The plate itself is exercised by ``test_smoke.py``; this file guards the
inputs. Both tests here exist because of one real failure — see
:func:`test_every_referenced_geo_asset_is_present`.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import contextlib

# ── vendored assets ───────────────────────────────────────────────────────


def test_every_referenced_geo_asset_is_present() -> None:
    """
    Each asset the code names must actually ship.

    This exists because ``rivers-50m.geojson`` did not: it stayed behind in
    the monorepo when the situation-map code moved here, and ``load_rivers``
    answered a missing file with an empty list. Maps then rendered with no
    rivers at all, exit code 0, nothing in the log — a map of Ukraine with no
    Dnieper on it. A missing vendored asset is a packaging fault, and the
    only reliable moment to catch it is before release.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    referenced: set[str] = set()
    pattern = re.compile(
        r'_ASSETS\s*/\s*"([^"]+)"|geo_dir\(\)\s*/\s*"([^"]+)"|assets_dir\(\)\s*/\s*"([^"]+)"'
    )
    for source in list((root / "scripts").glob("*.py")) + list(
        (root / "sprezzature_maps").glob("*.py")
    ):
        for match in pattern.finditer(source.read_text(encoding="utf-8")):
            referenced.add(next(g for g in match.groups() if g))

    assert referenced, "no assets discovered — has the reference idiom changed?"
    missing = sorted(n for n in referenced if not list((root / "assets").glob(f"**/{n}")))
    assert not missing, f"referenced but not shipped: {missing}"


def test_rivers_load_and_include_major_waterways() -> None:
    """The river file is not merely present but usable and named."""
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "_msm_rivers", root / "scripts" / "make_situation_map.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    rivers = module.load_rivers()
    assert len(rivers) > 100, f"only {len(rivers)} river features loaded"
    names = {name.lower() for _, name, _ in rivers if name}
    for expected in ("dnieper", "danube", "rhine"):
        assert any(expected in n for n in names), f"{expected} missing from the river set"


# ── plates ────────────────────────────────────────────────────────────────


def _msm():
    """Load the generator by path, the way the other tests here do."""
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "_msm_plates", root / "scripts" / "make_situation_map.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_day_is_the_default_and_nothing_moves() -> None:
    """
    A config that never mentions a plate gets the colours it always had.

    Plates are a mode, not a redesign: every existing config has to render
    exactly as before, or the feature costs more than it gives.
    """
    module = _msm()
    day = module._PLATES["day"]
    assert day["sea"] == "#a9bccb"
    assert day["land"] == "#faf6e4"
    assert day["coast"] == "#7f97a8"
    assert day["relief_opacity"] == 0.45
    assert day["legend_ink"] == "#333"
    assert day["blend"] == "multiply"


def test_night_is_not_the_day_plate_inverted() -> None:
    """
    The night values are chosen, not computed.

    Inverting the day palette gives a muddy grey sea and cream land at 8 %
    lightness, which reads as a mistake rather than as a night plate.
    """
    module = _msm()
    night = module._PLATES["night"]
    for key in ("sea", "land", "plate", "page"):
        value = night[key].lstrip("#")
        luminance = sum(int(value[i : i + 2], 16) for i in (0, 2, 4)) / 3
        assert luminance < 60, f"{key} is not dark: {night[key]}"
    # the coastline is light on a dark plate: the shore is where light is
    coast = night["coast"].lstrip("#")
    assert sum(int(coast[i : i + 2], 16) for i in (0, 2, 4)) / 3 > 80


def test_night_lifts_the_fills_instead_of_darkening_them() -> None:
    """
    Multiply is right over pale paper and wrong over a dark plate.

    It dragged the control fills towards the plate rather than off it, which
    is the opposite of what a night plate is for.
    """
    module = _msm()
    assert module._PLATES["day"]["blend"] == "multiply"
    assert module._PLATES["night"]["blend"] == "screen"


def test_unknown_plate_is_refused() -> None:
    """A typo must not silently render the default."""
    import pytest

    module = _msm()
    with pytest.raises(ValueError, match="unknown plate"):
        module.build_map({"region": {"bbox": [0, 0, 1, 1]}, "basemap": {"plate": "dusk"}})


def test_a_named_plate_overrides_config_colours_audibly() -> None:
    """
    Asking for night and getting cream is never what anyone meant.

    Every config written before plates existed carries day colours, so the
    plate has to outrank them — but silently overriding what someone wrote
    is its own kind of wrong, hence the warning.
    """
    import warnings

    module = _msm()
    cfg = {
        "region": {"bbox": [30, 44, 40, 52]},
        "basemap": {"plate": "night", "land_color": "#faf6e4"},
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # The render may need assets this test does not provide; the warning
        # under test fires before that, so a failure here is not a failure of
        # the thing being asserted.
        with contextlib.suppress(Exception):
            module.build_map(cfg)
    assert any("overrides" in str(w.message) for w in caught), [str(w.message) for w in caught]


def test_river_width_is_even_unless_asked() -> None:
    """Every river at one weight, which is what this always did."""
    module = _msm()
    assert module._river_width(1, "even", 1.0) == module._river_width(6, "even", 1.0)


def test_ranked_width_tapers_from_trunk_to_tributary() -> None:
    """
    A rank-1 trunk is drawn thicker than a rank-6 tributary, monotonically.

    A taper that is not monotonic would put a headwater above a trunk
    somewhere in the middle, which reads as noise rather than as hierarchy.
    """
    module = _msm()
    widths = [module._river_width(r, "ranked", 1.0) for r in range(1, 7)]
    assert widths == sorted(widths, reverse=True), widths
    assert widths[0] > widths[-1] * 3, "the taper is too shallow to read"


def test_unknown_river_width_is_refused() -> None:
    """A typo must not silently fall back to the default."""
    import pytest

    module = _msm()
    with pytest.raises(ValueError, match="unknown rivers.width"):
        module.build_map({
            "region": {"bbox": [30, 44, 40, 52]},
            "rivers": {"width": "hydraulic"},
        })


def test_the_name_does_not_overclaim() -> None:
    """
    The mode is 'ranked', not 'hydraulic'.

    Hydraulic width means discharge. The vendored river file carries only
    name and scalerank — a cartographic prominence rank, not a measurement
    of water — so calling it hydraulic would be a claim a reader could not
    check and we could not support.
    """
    module = _msm()
    rivers = module.load_rivers()
    _, _, rank = rivers[0]
    assert isinstance(rank, int)
    # if a discharge attribute ever arrives, this test should be revisited
    import json
    from pathlib import Path

    data = json.loads(Path(module._RIVERS_GEOJSON).read_text(encoding="utf-8"))
    props = set(data["features"][0]["properties"])
    assert props == {"name", "scalerank"}, f"river attributes changed: {sorted(props)}"


# ── caption ───────────────────────────────────────────────────────────────


def test_caption_is_off_unless_asked() -> None:
    """An existing plate must not suddenly grow a footer under it."""
    module = _msm()
    # Nothing at all, not an empty group: an existing plate has to come out
    # of this byte-for-byte as it did before, and 20 bytes of empty <g> is
    # still a difference.
    assert module._caption_block({}, {"ts": 1.0, "width": 100, "height": 100}) == ""
    assert module._caption_height({}, 1.0) == 0.0


def test_caption_refuses_to_be_empty() -> None:
    """
    A caption with nothing in it is worse than none.

    It looks like provenance, occupies the space provenance would, and says
    nothing — which is how a plate ends up claiming a rigour it does not have.
    """
    import pytest

    module = _msm()
    with pytest.raises(ValueError, match="needs at least one"):
        module._caption_block({"caption": "full"}, {"ts": 1.0, "width": 100, "height": 100})


def test_caption_reserves_room_for_itself() -> None:
    """
    The scale bar and the caption share the bottom-left corner.

    They landed on top of each other the first time: legible text over a
    legible bar, both unreadable. The height is what lets the furniture
    move out of the way.
    """
    module = _msm()
    cfg = {"caption": "full", "method": "m", "source": "s", "as_of": "a"}
    assert module._caption_height(cfg, 1.0) > 40
    assert module._caption_height({"caption": "full", "method": "m"}, 1.0) < (
        module._caption_height(cfg, 1.0)
    )


def test_unknown_caption_mode_is_refused() -> None:
    """A typo must not silently render nothing."""
    import pytest

    module = _msm()
    with pytest.raises(ValueError, match="unknown caption"):
        module._caption_block({"caption": "short"}, {"ts": 1.0, "width": 100, "height": 100})
