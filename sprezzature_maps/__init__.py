"""sprezzature-maps — hand-authored SVG world maps: choropleth + situation maps.

A focused sibling of `sprezzature-figures <https://github.com/warith-harchaoui/sprezzature-figures>`_
carrying just its two Geospatial "real basemap" generators (`choropleth`,
`situation_map`) as an independent product with its own release cycle and,
eventually, its own Studio. Depends on ``sprezzature-figures`` for shared
rendering primitives (font embedding, self-contained-vs-linked SVG modes)
rather than duplicating them.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _load_script(name: str) -> Any:
    """Load a ``scripts/<name>.py`` module, matching sprezzature-figures' own loader.

    The generator scripts import sibling helpers by bare name (``from
    _render import ...``), so ``scripts/`` must be on ``sys.path`` before
    ``exec_module`` runs.
    """
    scripts_dir = str(_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load script: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def make_choropleth(*args: Any, **kwargs: Any) -> Path:
    """Render a world choropleth map. See ``scripts/make_choropleth.py`` for the full signature."""
    return _load_script("make_choropleth").make_choropleth(*args, **kwargs)


def make_situation_map(*args: Any, **kwargs: Any) -> Path:
    """Render a layered areas-of-control situation map. See ``scripts/make_situation_map.py`` for the full signature."""
    return _load_script("make_situation_map").make_situation_map(*args, **kwargs)


__all__ = ["make_choropleth", "make_situation_map"]
