# Contributing

## Setup

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps
cd sprezzature-maps
pip install -e ".[dev,cli,api,mcp]"
```

`sprezzature-maps` depends on `sprezzature-figures` for shared rendering
primitives; neither package is on PyPI yet, so both are installed
editable from a local checkout (see README.md § Install).

## Tests

```bash
python -m pytest -q
```

Tests marked `@pytest.mark.slow` (network- or rasterisation-heavy) are
excluded by default (`pyproject.toml`'s `addopts`); run them explicitly
with `pytest -m slow` when touching relief sampling or PNG/PDF export.

## Doctests

Every public function in `scripts/_relief.py` and `scripts/_geo_colors.py`
carries a doctest. Run one file's doctests directly:

```bash
python -m doctest scripts/_geo_colors.py
```

The `sprezzature_maps/` package modules use relative imports, so their
doctests need to run through an actual import instead of a bare file
path:

```bash
python3 -c "import doctest, sprezzature_maps.api as m; doctest.testmod(m)"
```

## Lint

```bash
ruff check sprezzature_maps scripts tests
```

## Adding a boundary source

New sub-national boundary data (an admin-1 or admin-2 tier for a
country `situation_map` doesn't cover yet) follows the pattern
`doc/CARTOGRAPHY.tex` documents in full (§ Sub-national admin-1
tiering onward): convert the source once with `mapshaper` into
TopoJSON with reduced coordinate precision, gate loading behind a
cheap bounding-box pre-filter, and decide Git LFS tracking by how
often the file changes, not by its size. `.gitattributes` documents
the reasoning behind each tracked pattern. Add the fine/coarse pair to
the relevant registry in `scripts/make_situation_map.py` and a test in
`tests/test_admin_boundaries.py` with a real, hand-verified bounding
box, not an invented one (see that file's own comments for why).

## Code standards

See `CODING.md`. NumPy docstrings, full typing, roughly a quarter to a
third of lines as comments explaining *why*, `ruff check` clean.

## Prose standards

English prose (README, docstrings, comments) follows WRITING.md:
https://gist.github.com/warith-harchaoui/f45304d066abc81dd7d4f059a1f4e45f

French prose (LISEZMOI, PAYSAGE) follows ECRITURE.md:
https://gist.github.com/warith-harchaoui/7cc42b038e86c5195ec09f0531111ba4

No punctuation dashes, no machine tells ("Moreover", "In conclusion",
reflexive "not only X but also Y"). Acronyms glossed on first use.

## A visual or relief change needs a render-and-look pass

A passing test proves the code runs, not that the output looks right.
Render the new output, inspect the actual image against a specific,
named defect, fix the source file (never touch the rendered SVG by
hand), then render again. See `doc/CARTOGRAPHY.tex` § Validation
methodology for the full process.

## Releases

Releases live in `CHANGELOG.md`, tagged `vX.Y.Z` in git, and published
as GitHub releases.

## Authorship

Sole author: [Warith Harchaoui](https://www.linkedin.com/in/warith-harchaoui/).
External contributions are welcome. Open an issue or pull request on GitHub.

## License

[BSD-3-Clause](LICENSE).
