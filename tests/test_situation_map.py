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
