# Changelog

All notable changes to sprezzature-maps are documented here.

## [Unreleased] - 2026-08-20

Maintenance pass: no behavior change to the two generators or any of
their five access surfaces.

### Fixed

- `LICENSE` was missing even though `pyproject.toml` declares
  BSD-3-Clause. Added.
- Seven docstrings and comments across `sprezzature_maps/api.py`,
  `scripts/_relief.py`, `scripts/make_choropleth.py`, and two test
  files pointed at `.private/*.md`, files that are deliberately
  gitignored and never shipped. Removed the dead pointers; the
  substantive claim each comment made (a check was actually run, not
  just asserted) stays.
- Five `except Exception:` blocks in `scripts/make_situation_map.py`'s
  admin-boundary clipping loops had no explanatory comment, unlike two
  identical blocks earlier in the same file. Added the same
  "skip a malformed geometry rather than fail the plate" rationale to
  all seven, so a broad catch is never left unexplained.
- README.md's "Status" section claimed no CI existed and that the
  Click CLI and MCP surface were "coming next"; both were already
  built and tested. Corrected to describe the five surfaces that
  actually exist today (Python import, `make-map`, `sprezzature-maps`
  Click CLI, HTTP API, MCP) and the CI workflow that has been running
  since before that section was last touched.
- README.md's "Roadmap" listed relief shading for `situation_map`'s
  Lambert conformal conic projection as future work; `_relief_layer`
  has shipped and is on by default. Moved to "already done."
- `assets/svg-examples/choropleth.svg`, the tracked demo render
  EXAMPLES.md points to, predated the on-canvas hover-bubble tooltip
  feature (`1d4b6bc`) entirely: it carried none of the `.hit`/`.tip`
  markup the current generator emits. Regenerated from
  `make_choropleth()` with no arguments, restoring the "never silently
  drift from what the code produces" guarantee EXAMPLES.md itself
  states.
- 42 em-dash asides in docstrings and comments across `scripts/_render.py`,
  `_interactive.py`, `_svg.py`, `build_situation_examples.py`,
  `make_choropleth.py`, and `make_situation_map.py` (the earlier
  clarity pass covered README.md/CODING.md/EXAMPLES.md but not
  `scripts/`'s own comments). Three of those were in map titles
  actually rendered onto the output ("Ukraine — Areas of Control" and
  similar); `assets/svg-examples/situation_map.svg`, the one tracked
  asset affected, was regenerated to match.

### Added

- `LISEZMOI.md`, `PAYSAGE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`,
  `TRIGGERS.md`, `LANDSCAPE.md`, `Dockerfile`: repo structure brought
  in line with sibling `sprezzature-*` packages.

## [0.1.0] - 2026-08-07 through 2026-08-16

Initial standalone release, extracted from `sprezzature-figures`'
catalogue of chart kinds (`adc0fbb`).

### Added

- `scripts/make_choropleth.py`: world choropleth, hand-authored SVG, no
  Vega, no matplotlib. Equal Earth projection (closed-form forward,
  vectorised Newton-Raphson inverse for relief sampling), OKLCH
  sequential and diverging colour ramps, antimeridian-aware country
  outlines, native `<title>` tooltips plus an on-canvas hover bubble,
  rank and share-of-total enrichment.
- `scripts/make_situation_map.py`: layered "who controls what" plates
  for any region. Auto-centred Lambert conformal conic projection,
  real national outlines, bathymetry halo, classed zones, dual-unit
  scale bar, admin-1 and admin-2 sub-national boundary tiers (US
  states/counties, French regions/departments, Swiss cantons/districts,
  German Länder/Kreise, Italian regions/province, plus an OpenStreetMap
  registry for the rest), real elevation relief reprojected to LCC.
- `scripts/_geo_colors.py`, `scripts/_relief.py`, `scripts/_svg.py`,
  `scripts/_render.py`, `scripts/_interactive.py`: shared primitives
  (OKLab/OKLCH colour math, terrain shading, SVG helpers, the
  write-to-disk tail, fullscreen wiring), each carrying its own
  doctests, run in CI alongside `pytest`.
- `sprezzature_maps/api.py`: FastAPI HTTP surface (`/v1/choropleth`,
  `/v1/situation-map`, `/v1/kinds`, `/health`), plus the GUI gallery
  page at `/`.
- `sprezzature_maps/cli_click.py`: richer Click-based
  `sprezzature-maps` command, CSV/TSV/JSONL ingestion and
  `--map role=column` bindings on top of what the always-installed
  `make-map` (argparse) command reads.
- `sprezzature_maps/mcp.py`: Model Context Protocol surface over the
  same FastAPI app, via `fastapi-mcp`.
- `doc/CARTOGRAPHY.tex`: the full method behind every projection,
  colour scale, and relief technique, compiled with `xelatex`/`biber`
  into `doc/CARTOGRAPHY.pdf`.
- `.github/workflows/ci.yml`: ruff lint, pytest, and doctests on every
  push and pull request to `main`, with Git LFS fetch for the vendored
  relief rasters and the compiled PDF.
- 26 tests in `tests/`, all passing.
