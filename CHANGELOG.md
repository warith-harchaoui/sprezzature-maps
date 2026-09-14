# Changelog

All notable changes to sprezzature-maps are documented here.

## [0.4.0] - 2026-09-14: the accumulation map becomes a kind, not a script

### Added

- **`density` is a map kind now**, on all five surfaces: `make_density()`,
  `make-map density`, `POST /v1/density`, the `render_density` MCP tool, and a
  row in the skill. It shipped in 0.2.0 as `scripts/make_density.py` — a file
  somebody had to run by hand. Not exported, no CLI kind, no route, and absent
  from `list_kinds`, so the map existed in the repository and nowhere else. A
  map nobody can reach is a map this package does not have.

  It is also the kind that inverts the other two: no coastline, no border, no
  graticule. Point events are binned into a luminous field, and the land
  appears because events fell on it while the sea stays dark because none did.
  The routing line that matters: a **choropleth** answers "what is the rate
  here" and needs one number per territory — fill it with a raw count and it
  draws population rather than your phenomenon. **`density`** answers "where
  did this happen" and needs no territories at all.

- `test_every_kind_this_repo_draws_is_reachable_from_every_surface`, which
  pins the doctrine rather than this one instance: whatever `list_kinds`
  advertises, the library exports and the HTTP surface renders. The next kind
  cannot ship half-wired.

### Fixed

- **`list_kinds` said "two" in the summary an MCP host displays** and in its
  docstring, while returning three. That summary is most of what an agent
  reads when choosing between tools from several servers.

## [0.3.0] - 2026-09-14: the choropleth can finally be classed, and says how

### Added

- **`classes` and `method` on the choropleth, across all five surfaces.** The
  generator had one rule for turning numbers into colours: stretch the ramp
  linearly from the smallest value to the largest. That is unclassed equal
  interval, and cartography is unanimous that it is the weakest choice for the
  right-skewed data indicators are made of. Measured rather than asserted: on
  GDP per head for twenty countries it puts nine of them in the bottom quarter
  of the ramp, and of the pairs a five-class quantile separates, four come out
  closer than the eye can resolve — India, at ten times Burundi's figure, lands
  0.0115 apart in OKLab where 0.02 is the threshold.

  Four methods, because no default is right for every dataset:

  - `quantile` — equal count per class. Supports ranking; flattens skew by
    construction, and two very different values can share a class.
  - `equal` — equal width. Honest about the number line, and the failure above
    on skewed data. Right when the classes must mean something outside the
    data.
  - `jenks` — Fisher–Jenks natural breaks, the exact dynamic program rather
    than the iterative approximation often shipped under that name. Verified
    against brute-force optimal partitions. Shows the groupings the data has.
  - `headtail` — head/tail breaks (Jiang 2013) for heavy tails; the class count
    comes from the data.

  **The legend prints the method and the boundaries.** That is the half that
  makes classification honest rather than merely prettier: the same values
  classed four ways tell four stories, so a map that does not say how it was
  classed is asking to be misread by a reader with no way to know it.

  `classes=None` stays the default and renders byte for byte what it always
  did. Classing is a decision, and this package does not make editorial
  decisions on the caller's behalf — it makes them available and names them.

- `scripts/_classify.py`, standard library only, and `tests/test_classify.py`,
  which pins each method's defining property, the Jenks solver against
  exhaustive search, and the perceptual measurement that justifies the feature.

## [0.2.0] - 2026-09-14: four modes, a provenance block, and a first publication

### Added

- **A night plate**, as a mode and nothing more — the same geography, read in
  the dark.
- **Rivers tapered by prominence**, opt-in. A river that matters is drawn
  thicker than one that does not, which is the only reason to draw rivers on a
  situation plate at all.
- **An accumulation map** (`scripts/make_density.py`), where the data draws the
  geography: point events binned to a luminous field, no coastline, no border,
  no graticule. The United States appears because events fell on it. Vector,
  binned, one path per level — measured rather than guessed: on 381,406 points
  a rect per cell costs 972 KB, quantising the ramp and merging each level into
  one path lands at ~100 KB in ten paths, and past ~260 bins the field becomes
  grain, so the visual limit arrives before the size limit.
- **A provenance caption the plate carries when it travels alone.** `source`,
  `as_of` and `method` are printed on the map itself, because a plate that
  looks like an intelligence product gets separated from the message that
  introduced it.

### Fixed

- **`make_situation_map.py` never parsed on Python 3.10 or 3.11.** It used
  PEP 701 f-strings, which are 3.12+, while `requires-python` says `>=3.10`.
  Invisible because CI only ran 3.12; the matrix covers 3.10, 3.11 and 3.12 now.
- **The dependency on `sprezzature-figures` was a direct git URL**, which PyPI
  refuses outright — a 400 on upload, not a warning. It is a version
  constraint now.
- **`…-mcp --help` started the server instead of answering.** Argument parsing
  before anything binds, `--host` / `--port` options, and the default host
  moved from `0.0.0.0` to `127.0.0.1`.
- **Every MCP tool carried a summary FastAPI invented from the function name**
  — the headline "Kinds" told an agent nothing. Written by hand now, with two
  tests that fail the build if a summary or description regresses.
- Three README links that would have 404'd on PyPI, caught before the first
  publication rather than after it.

### Changed

- **`TRIGGERS.md` routes on data attached to places**, not on the word "map",
  and names the trap explicitly: a hex map or dot density belongs to
  `sprezzature-figures`, because it is a layout convention rather than
  geography.
- No charting library is named anywhere in this repository any more. The
  package description, both READMEs, `_render.py`, `make_choropleth.py` and the
  two relief-figure scripts described what this code *does not* use — a
  migration note that outlived the migration. Each now states the positive
  fact: every line is authored as SVG directly, and the relief panels are
  composited with Pillow. `LANDSCAPE.md` / `PAYSAGE.md` keep their names:
  comparing against the alternatives is what they are for.

## [0.1.1] - 2026-08-20: maintenance


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
