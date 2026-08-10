# Coding standards

Adapted from [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures)'
own `CODING.md` (the repo `sprezzature-maps` was split out of) — kept in sync in
spirit, not automatically, since the two repos have diverged on surfaces (no
Studio or dataviz tier here).

## Language

Python 3.10+. Full type annotations on all public functions and classes.

## Style

- `ruff check` with zero warnings. `ruff format` applied.
- Line length: 100 characters (`[tool.ruff]` in `pyproject.toml`).
- Imports: stdlib → third-party → local, separated by blank lines. `scripts/`
  is not an installed package (its generators import siblings via a
  `sys.path.insert(0, str(Path(__file__).resolve().parent))` shim before the
  local imports, each with `# noqa: E402`) — keep that shim, do not turn
  `scripts/` into a package to work around it.

## Docstrings

NumPy-style docstrings on all public functions and classes. Short summary
line, then Parameters, Returns, Raises, Examples sections as needed.

```python
def make_choropleth(
    data: list[dict[str, Any]] | None = None,
    *,
    out: Path | str | None = None,
    title: str = "",
) -> Path:
    """
    Render a hand-authored choropleth map and write the SVG to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``id`` (ISO-3166-1 numeric country code) and
        ``value`` (float). Defaults to DEMO_DATA.
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/choropleth.svg``.
    title : str
        Chart title.

    Returns
    -------
    Path
        Absolute path to the written SVG file.
    """
```

## Comments

25–30 % comment density. Explain *why*, never *what*. No commented-out code.

## Script structure for make_*.py

Each generator (`scripts/make_choropleth.py`, `scripts/make_situation_map.py`)
follows this structure:

```python
#!/usr/bin/env python3
"""
Module docstring: what this map is, when to use it.

Author
------
Warith Harchaoui, Ph.D. <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

# ... stdlib / third-party imports ...

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _geo_colors import ...  # noqa: E402  (local sibling imports)

DEMO_DATA: list[dict[str, Any]] = [
    # minimal self-contained example data
]


def make_<kind>(
    data: list[dict[str, Any]] | None = None,
    *,
    out: Path | str | None = None,
    title: str = "",
    **kwargs,
) -> Path:
    """Render the map and return the written output path."""
    ...


if __name__ == "__main__":
    print(make_<kind>())
```

Shared, output-identical primitives used by both generators (SVG scaffolding,
color ramps, relief/terrain shading, TopoJSON decoding, render/write helpers)
live in the private `_*.py` modules alongside them, never duplicated inline —
see each module's own docstring for what it owns and why.

## Testing

- All tests in `tests/` must pass with `pytest -q` (`pyproject.toml` excludes
  `@pytest.mark.slow` — network/rasterization-heavy — from the default run).
- Every public function in `scripts/_relief.py` and `scripts/_geo_colors.py`
  carries a doctest exercising its documented contract; run with
  `python -m doctest scripts/_relief.py` (and the equivalent per file).
  Package modules (`sprezzature_maps/*.py`) use relative imports, so their
  doctests need module invocation instead of a bare file path:
  `python3 -c "import doctest, sprezzature_maps.api as m; doctest.testmod(m)"`.
- No mocking of file I/O or rendering. Test the real dispatcher.
- Visual/relief changes go through the Ralph Eyeball Loop (render → inspect
  the actual raster output → critique against a concrete defect → edit the
  *source*, never the output image → re-render) — a test passing is
  necessary, not sufficient, for a visual change; see
  `doc/CARTOGRAPHY.tex` § Validation methodology.

## Dependencies

Declare all dependencies in `pyproject.toml` under `[project.dependencies]` /
`[project.optional-dependencies]`. Do not pin exact versions in
`pyproject.toml` (use `>=` lower bounds only). `requirements.txt` /
`requirements-dev.txt` are pip entry points that select which extras to
install — `pyproject.toml` stays the single source of truth for version
constraints, so there is nothing in those two files to fall out of sync when
a bound changes.

## Vendored geo data

New boundary/relief sources under `assets/geo/` follow the pattern
`doc/CARTOGRAPHY.tex` documents in full (§ Sub-national admin-1 tiering
onward): vendor once via `mapshaper` into quantized TopoJSON, gate loading
behind a cheap bbox pre-filter, decide Git LFS by churn pattern (does this
file get regenerated often?) not by file size — see `.gitattributes`'
comments for the reasoning on each tracked pattern. Never fetch geo data at
render time; all rendering is offline.
