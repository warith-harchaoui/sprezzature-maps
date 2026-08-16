# Coding standards

Adapted from [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures)'
own `CODING.md` (the repo `sprezzature-maps` was split out of). The two files
are kept in sync in spirit, by hand, not by an automated check, since the two
repos have since diverged on which surfaces they expose (no Studio, the
conversational chart editor, and no dataviz dependency tier here).

## Language

Python 3.10+. Full type annotations on all public functions and classes.

## Style

- `ruff check` with zero warnings. `ruff format` applied.
- Line length: 100 characters (`[tool.ruff]` in `pyproject.toml`).
- Imports: standard library, then third-party packages, then local modules,
  each group separated by a blank line. `scripts/` is not an installed
  Python package, so its generators cannot simply `import` their sibling
  helper modules the normal way; each one first runs
  `sys.path.insert(0, str(Path(__file__).resolve().parent))` (adding its own
  folder to Python's list of places to search for a module) and only then
  imports the sibling, marking that import `# noqa: E402` (telling `ruff`
  this particular import is deliberately not at the top of the file). Keep
  that pattern; do not turn `scripts/` into a proper package just to avoid
  it.

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

Roughly a quarter to a third of lines should be comments. Each one should
explain *why* the code does something non-obvious, never restate *what* the
code already says by itself. No commented-out code left lying around.

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

Primitives shared by both generators, and rendered identically wherever
they're reused (SVG scaffolding, colour scales, relief/terrain shading,
TopoJSON decoding, the write-to-disk helpers), live in the private `_*.py`
modules next to them, never copy-pasted inline into a generator. See each
such module's own docstring for exactly what it owns and why it exists as
its own module.

## Testing

- Every test in `tests/` must pass with `pytest -q`. `pyproject.toml`
  excludes tests marked `@pytest.mark.slow` (ones that hit the network or do
  heavy rasterization) from that default run.
- Every public function in `scripts/_relief.py` and `scripts/_geo_colors.py`
  carries a doctest: an example call and its expected output, written right
  in the docstring, that Python can execute as a test. Run one file's
  doctests with `python -m doctest scripts/_relief.py` (repeat per file).
  The modules under `sprezzature_maps/` use relative imports (imports
  written relative to the package, `from .foo import bar` rather than
  `import foo`), which only work once the package is actually imported, so
  their doctests need to run through an import instead of a bare file path:
  `python3 -c "import doctest, sprezzature_maps.api as m; doctest.testmod(m)"`.
- No mocking of file I/O or rendering. Test the real dispatcher (the
  function that actually writes the SVG), not a stand-in for it.
- A visual or relief change also needs a render-and-look pass: render the
  new output, inspect the actual image (not just the code that produced
  it), check it against a specific, named defect, fix the *source* file
  rather than touching the output image by hand, then render again. A
  passing test is necessary but not sufficient proof that a visual change
  is actually correct; see `doc/CARTOGRAPHY.tex` § Validation methodology
  for the full process.

## Dependencies

Declare every dependency in `pyproject.toml`, under `[project.dependencies]`
or `[project.optional-dependencies]`. Do not pin an exact version there
(use a `>=` lower bound only). `requirements.txt` and `requirements-dev.txt`
exist only as `pip` entry points that pick which optional extras to
install; `pyproject.toml` stays the one place version constraints are
decided, so there is nothing in those two files that could drift out of
sync when a bound changes.

## Vendored geo data

Any new boundary or relief source added under `assets/geo/` follows the
pattern `doc/CARTOGRAPHY.tex` documents in full (§ Sub-national admin-1
tiering onward, "admin-1" meaning a country's first level of internal
division: a US state, a French region, a German Land). In short: convert
the source once with `mapshaper` (a command-line tool for simplifying and
converting map data) into TopoJSON with reduced coordinate precision;
gate loading behind a cheap bounding-box pre-filter (checking a shape's
rough rectangular extent before doing the expensive work of reading its
full outline, so a map of France does not pay the cost of loading every
country's detailed borders); and decide whether a file goes into Git LFS
(Git's system for storing large binary files outside the normal
version-controlled history) by how often it changes, not by its size.
`.gitattributes` documents the reasoning behind each tracked pattern.
Never fetch geo data over the network at render time; every render runs
offline, against data already vendored into the repo.
