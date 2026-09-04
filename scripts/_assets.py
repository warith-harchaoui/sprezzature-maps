"""
_assets — locate the vendored geo data directory and sprezzature-figures' scripts/.

In the source tree the data lives in ``assets/geo/``; once installed it
ships (collision-free) as the sibling package ``sprezzature_maps_geo/``,
the same pattern the generator scripts themselves follow
(``scripts/`` → ``sprezzature_maps_scripts/``). The installed wheel only
bundles the vector data and the coarse elevation tiers — the fine tiers
(2 arc-minute and below) stay source-tree only, and ``_relief.py``'s tier
selection degrades to the finest tier actually present.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def geo_dir() -> Path:
    """The vendored geo data directory (source tree or installed wheel)."""
    root = Path(__file__).resolve().parent.parent
    for candidate in (root / "assets" / "geo", root / "sprezzature_maps_geo"):
        if candidate.is_dir():
            return candidate
    return root / "assets" / "geo"


def figures_scripts_dir() -> Path:
    """Locate sprezzature-figures' ``scripts/`` (for ``_svg.tooltip_bubble``).

    ``pyproject.toml`` declares ``sprezzature-figures`` as a real
    dependency (a direct GitHub reference, since it is not on PyPI yet),
    so a normal ``pip install`` of this package already installs it as
    the sibling package ``sprezzature_figures_scripts`` — checked first,
    via :func:`importlib.util.find_spec` rather than a guessed filesystem
    path, so this works regardless of venv layout (site-packages, an
    editable install, a different Python version directory, ...).

    The two dev-checkout fallbacks (a sibling ``../sprezzature-figures``
    directory, or ``~/sprezzature-figures``) only matter for someone
    working from a source checkout of *this* repo without having
    actually run ``pip install`` at all (e.g. invoking the script
    directly against an ad hoc ``sys.path``); a real install of any kind
    resolves through the first branch.
    """
    spec = importlib.util.find_spec("sprezzature_figures_scripts")
    if spec is not None and spec.submodule_search_locations:
        installed = Path(next(iter(spec.submodule_search_locations)))
        if installed.is_dir():
            return installed

    root = Path(__file__).resolve().parent.parent
    for candidate in (
        root.parent / "sprezzature-figures" / "scripts",
        Path.home() / "sprezzature-figures" / "scripts",
    ):
        if candidate.is_dir():
            return candidate
    # Nothing found. Return the installed-package guess so a downstream
    # FileNotFoundError points at "pip install did not do what it should
    # have" rather than an arbitrary sibling-checkout path.
    return root.parent / "sprezzature-figures" / "scripts"
