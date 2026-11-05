# Coding standards

Adapted from [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures)'
own `CODING.md` (the repo `sprezzature-maps` was split out of). The two files
are kept in sync in spirit, by hand, not by an automated check, since the two
repos have since diverged on which surfaces they expose (this repository has
its own map Editor rather than the figures one, and no dataviz dependency
tier).

## Language

Python 3.10+. Full type annotations on all public functions and classes.

## Style

- `ruff check` with zero warnings. `ruff format` applied.
- Line length: 100 characters (`[tool.ruff]` in `pyproject.toml`).
- Imports: standard library, then third-party packages, then local modules,
  each group separated by a blank line. `scripts/` ships in the wheel as
  `sprezzature_maps_scripts`, but its modules are loaded by file path
  (`_load_script`), so its generators cannot simply `import` their sibling
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
        Output path (.svg). Defaults to ``choropleth.svg`` in the current
        working directory, never the committed example.
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

Each generator (`scripts/make_choropleth.py`, `scripts/make_situation_map.py`,
`scripts/make_density.py`) follows this structure:

```python
#!/usr/bin/env python3
"""
Module docstring: what this map is, when to use it.

Author
------
Warith HARCHAOUI, Ph.D. <warithmetics@deraison.ai>
"""

from __future__ import annotations

# ... stdlib / third-party imports ...

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _geo_colors import ...  # noqa: E402  (local sibling imports)
from _render import render_cli, write_svg  # noqa: E402

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
    # No `out` means `<kind>.svg` in the current working directory. Never
    # default to `assets/svg-examples/`: that is the committed example in a
    # checkout and a file inside site-packages once installed. Only
    # `scripts/build_demo_examples.py` (and a direct run of this script,
    # through `render_cli`) names that path, explicitly.
    dest = Path(out) if out else Path.cwd() / "<kind>.svg"
    ...


def main() -> None:
    # The shared click command line: --out, --mode, --accessibility,
    # --language. Run directly, the script's --out still defaults to the
    # committed example: that is the maintainer's regeneration path. make_situation_map.py keeps its own (--config, --out,
    # --render), also click.
    render_cli(__file__, "<kind>", build_svg, description="...")


if __name__ == "__main__":
    main()
```

Primitives shared by the generators, and rendered identically wherever
they're reused (SVG scaffolding, colour scales, relief/terrain shading,
TopoJSON decoding, the write-to-disk helpers), live in the private `_*.py`
modules next to them, never copy-pasted inline into a generator. See each
such module's own docstring for exactly what it owns and why it exists as
its own module.

## Testing

- Every test in `tests/` must pass with `pytest -q`. Nothing is deselected
  by default: tests marked `@pytest.mark.slow` (ones that hit the network or
  do heavy rasterization) run too, and `pytest -m slow` selects only them.
- Every public function in `scripts/_relief.py` and `scripts/_geo_colors.py`
  carries a doctest: an example call and its expected output, written right
  in the docstring, that Python can execute as a test. Run one file's
  doctests with `python -m doctest scripts/_relief.py` (repeat per file).
  The modules under `sprezzature_maps/` use relative imports (imports
  written relative to the package, `from .foo import bar` rather than
  `import foo`), which only work once the package is actually imported, so
  their doctests need to run through an import instead of a bare file path:
  `python -m pytest -q --doctest-modules sprezzature_maps`, which is what CI
  runs.
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

Declare every runtime dependency in `pyproject.toml`, under
`[project.dependencies]`. Since 2026-11-01 there are no feature extras: the
HTTP API, the MCP server and the command line are all in the base install.
`[project.optional-dependencies]` holds only `dev`, the test and lint
toolchain. Use a `>=` lower bound rather than an exact pin; a ceiling is
allowed when it is argued in a comment beside it (`mcp<2.0`, `mypy<3`).
`requirements.txt` installs the package itself (`-e .`) and
`requirements-dev.txt` adds the toolchain on top. `pyproject.toml` stays the
place version constraints are decided.

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

## The sibling repository

`sprezzature-figures` is not a dependency this repo happens to have. The two
were one project until the split, they ship into the same website, and a
reader meets both. **Before building something the sibling already has, read
its version and mirror it on purpose**, and when you have to deviate, say so
where the deviation lives rather than leaving the next reader to wonder which
of two near-identical files is right.

What is deliberately shared today:

| Here | There | Shared because |
|---|---|---|
| `make-map`'s Click shape | `make-figure` | Someone who knows one recognises the other |
| `web/tools/build_map_kits.py` | `web/tools/build_figure_kits.py` | Same download chip, same `--only` / `--check`, same per-language kits |
| `_load_script` in `sprezzature_maps/__init__.py` | the figures loader | Same `scripts/` layout, same caching |
| The Ralph Eyeball Loop | `references/ralph-eyeball-loop.md` | One verification discipline, not two |
| This file | its `CODING.md` | In spirit, by hand |

Where they part, and why — each stated in the code that parts:

- **A kit from here cannot bundle its engine.** A figure kit ships its drawing
  code and runs on the standard library. A plate needs a projection, geometry
  and a vendored atlas, so a map kit declares `pip install sprezzature-maps`
  instead. `build_map_kits.py` says this in its header.
- **Schematic place-shaped charts stay there.** Hex maps, dot density, spike
  maps and binned grids plot points or cells; this repo draws real coastlines
  under a real projection. `TRIGGERS.md` routes on exactly that question.
- **the editor here is its own, not the figures one extended.** That was the
  standing decision — "maps get their own when there is one" — and since
  2026-11-01 there is one: `sprezzature_maps.editor`, opened by
  `sprezzature-maps`. The reason it is separate is the data: a chart
  Editor can assume a table and ask which column plays which role, and these
  three kinds take rows, a configuration and a list of positions.

  It is FastAPI and server-rendered HTML, not NiceGUI, and that was measured
  rather than preferred: NiceGUI costs 20 packages nothing else here brings,
  FastAPI and uvicorn are already base dependencies, and `gui.py` already
  serves hand-written markup for the reason it states. What *is* copied from
  the editor is its accidental best property — 117 of its 5397 lines
  touch NiceGUI, and its engine subpackages touch it in 0 of 34 files — so
  everything here that decides anything is importable without a server.

A pattern proven on one side is the default for the other. That includes the
unglamorous ones: `TRIGGERS.md` is machine-read on both sides, and
`tests/test_triggers_are_real.py` resolving every command and tool name it
prints against the surface that must answer it is a test the sibling wants
too.
