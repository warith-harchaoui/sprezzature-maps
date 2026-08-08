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
    """Load (and cache) a ``scripts/<name>.py`` module, matching
    sprezzature-figures' own loader.

    The generator scripts import sibling helpers by bare name (``from
    _render import ...``), so ``scripts/`` must be on ``sys.path`` before
    ``exec_module`` runs.

    Parameters
    ----------
    name : str
        Module stem under ``scripts/`` (e.g. ``"make_choropleth"``).

    Returns
    -------
    module
        The loaded module, from ``sys.modules`` on every call after the
        first. This is the application-service layer every CLI/API/MCP/GUI
        surface calls through (see CODING.md Sec 19.1) -- once those
        surfaces exist, a FastAPI worker handling many requests would
        otherwise re-parse and re-``exec`` this file (plus its numpy/PIL
        imports) on *every single call*, which the earlier unconditional
        ``exec_module`` did. Checking ``sys.modules`` first makes this a
        cheap dict lookup after the first load, same as a normal
        ``import``.
    """
    scripts_dir = str(_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    # A second call for the same generator is the common case once any
    # long-lived surface (API, MCP) calls into this repeatedly -- reuse
    # the already-executed module instead of re-loading it from disk.
    if name in sys.modules:
        return sys.modules[name]
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
