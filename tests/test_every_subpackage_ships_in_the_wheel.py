"""
Every sub-package of ``sprezzature_maps`` is listed for the wheel.

``[tool.setuptools] packages`` is an explicit list, and setuptools does not
follow it downwards: ``sprezzature_maps.studio`` and its two children sat
outside it, so the 1.1.0 wheel installed a ``sprezzature-maps-studio`` command
whose first import failed. Every test passed, because a checkout imports the
folder, not the wheel; only the release script's fresh venv saw it.

The check walks the tree for ``__init__.py`` files and asks that each dotted
name be in the list.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_every_subpackage_is_listed_for_the_wheel() -> None:
    # Read rather than parsed: ``tomllib`` is 3.11+, and the floor is 3.10.
    manifest = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^packages = \[(.*?)\]", manifest, re.S | re.M)
    assert block, "[tool.setuptools] packages list not found"
    listed = set(re.findall(r'"([\w.]+)"', block.group(1)))
    found = {
        ".".join(init.parent.relative_to(ROOT).parts)
        for init in (ROOT / "sprezzature_maps").rglob("__init__.py")
        if "__pycache__" not in init.parts
    }
    missing = sorted(found - listed)
    assert not missing, f"sub-packages the wheel would leave out: {missing}"
