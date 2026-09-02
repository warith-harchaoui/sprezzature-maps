"""
_assets — locate the vendored geo data directory.

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

from pathlib import Path


def geo_dir() -> Path:
    """The vendored geo data directory (source tree or installed wheel)."""
    root = Path(__file__).resolve().parent.parent
    for candidate in (root / "assets" / "geo", root / "sprezzature_maps_geo"):
        if candidate.is_dir():
            return candidate
    return root / "assets" / "geo"
