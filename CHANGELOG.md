# Changelog

All notable changes to sprezzature-maps are documented here.

## [0.8.0] - 2026-09-30: the plate says what it is, and where it is going

The whole of this release came out of rendering real plates and looking at
them. Two current-affairs maps were built as tests — Sudan's east-west
partition and who holds the Kivus — and every item below is something one of
them exposed.

### Added

- **Axes of advance.** Areas of control say where the line *is*; nothing said
  which way it was moving, and without that a plate can only describe a
  frozen moment. `arrows:` takes a list of `line` coordinates and draws a
  tapered, white-cased arrow along a Catmull-Rom curve through them — the
  shaft is a filled outline rather than a stroke, because a stroke is one
  width for its whole length and a shaft that thickens towards the point is
  the mark that carries direction without a caption.

  `style: dashed` draws the same shape as an outline. An assessed advance and
  a reported one are not the same claim, and a reader of a plate like this
  will act on the difference.

- **Inland lakes.** The vendored coastline data is land-versus-ocean only, so
  every lake on Earth was painted as dry ground. A plate of the Kivus put
  Goma and Bukavu 100 km apart with nothing between them, when in fact they
  face each other across Lake Kivu and the lake is why the road between them
  goes where it goes. The same hole swallowed Tanganyika, Chad, the Caspian,
  the Great Lakes and the Dnieper reservoirs on the Ukraine plate.

  412 Natural Earth lake polygons now ship (`assets/geo/lakes-50m.geojson`,
  public domain, 405 KB), drawn in the sea colour under the control zones and
  labelled in the italic the rivers already use.

- **`lakes.former` and `lakes.skip`, because a basemap has a date.** Natural
  Earth is a snapshot and some of the world's best-known inland water has
  moved since it was taken — so a plate dated 2024 could render water that
  stopped existing in 2023. `lakes.skip` drops a body by name; `lakes.former`
  draws it as what it is, a dashed outline with no fill and the name suffixed
  `(former)`.

  `former` is usually the better answer: on a map of a front the absence of a
  reservoir is itself information, and a reader who knows the ground will come
  looking for it. The Ukraine example now draws the **Kakhovka Reservoir** that
  way. It drained within two weeks of the dam breach of 6 June 2023; by 2026
  the bed is willow and poplar scrub over sand and marsh, and infantry has
  been infiltrating through it — which makes it a feature of that plate rather
  than a footnote to it. The Dnieper runs through the outline as the river it
  now is, and the plate's provenance caption says why.

  The `_lakes_layer` docstring records the cases checked, with dates, so the
  next caller need not find them out in public: Kakhovka (correct here now),
  Lake Urmia (vendored near its historic ~4 200 km², since repeatedly below a
  fifth of that), Lake Chad (already the modern shrunken lake — no correction
  needed), and the Aral Sea (already split north/south, the post-2000s state).

- **An accessible root, at last.** `make_choropleth` and `make_density` have
  always opened with `role="img"` wired to a `<title>`/`<desc>` pair; the
  situation map opened with a bare `<svg>`, so a screen reader announced
  "image" and stopped. That mattered more here than on the other two, because
  this plate's whole content *is* a claim. The description names the region,
  the classes, the markers and the provenance, and ends with the contract
  `TRIGGERS.md` states for every consumer: the map draws the assessment it
  was given and does not verify who holds what.

- **Two current-affairs examples**, `sudan` and `drc`, alongside the three
  historical ones. Sudan is the first five-class plate in the gallery,
  because the war genuinely has five answers to "who holds this".

### Fixed

- **A neighbour's name could land on a different country.** `RUSSIA` printed
  on the Crimean peninsula on the Ukraine plate, and on a 0.47 deg² speck off
  northern Norway on a Nordic one — `representative_point()` guarantees only
  that a point is *inside* a geometry, and for a MultiPolygon it may pick any
  component. Territory labels now take the largest visible part, then the
  pole of inaccessibility inside it, which also moved `RUSSIA` from 0.36 deg
  off the frontier (where the `LUHANSK` city label painted over it) to
  1.55 deg clear of it.

- **Names ran off the plate.** The city layer has clipped its labels since
  `Istanbul` came out as `Ista`; the territory labels had no such check and
  `CENTRAL AFRICAN REPUBLIC` came off the Sudan plate's left edge as
  `NTRAL … REP`. Worse, the plate rectangle was the wrong bound in the first
  place: the geographic layers are clipped to the *projected region polygon*,
  narrower than the plate under a conic, which is how `Asmara` passed the
  rectangle check and still came out as `Asm`. Both layers now test the real
  clip, and drop rather than crop.

- **Every hand-placed name was printed twice.** The city layer's
  anti-duplication read `place["name"]` while every config in this repo — and
  every example in the module docstring — writes `text`, so it compared
  against a set of empty strings and suppressed nothing: `KHARTOUM` sat next
  to `Omdurman`, `EL GENEINA` next to `Geneina`. Fixed, and backed by a
  positional test as well, since where the two datasets disagree they
  disagree on the name rather than the place (Natural Earth calls El Obeid
  "Al-Ubayyid").

- **A whole control layer could fail to render.** Handing over a country's
  outline for a plate showing one province of it emitted a path many times
  the canvas; beyond the wasted bytes, the shape fell so far outside that
  resvg dropped its blended fill, and the eastern DRC plate came out with no
  control colours at all. Zones are now clipped to the region first, which
  also makes the area shares in the tooltips relative to what is on the page.

- **The legend sat on the caption**, and then on the scale bar. The scale bar
  has always made room for the provenance caption; the legend had not. Fixed,
  and a bottom-left legend now pushes the scale bar to the opposite corner,
  the same rule the north arrow already followed for a top-right legend.

- **Two layers named the same water.** `Dnieper` printed straight through
  `Kakhovka Reservoir`, because the rivers layer and the lakes layer each
  dodged only their own labels. They now share one list.

- **The Ukraine example could not render at all.** `build_ukraine` carried a
  `"sprezzature"` key where it meant `"front"` — left by a word replacement
  that had run through the file, which also turned "Contested (approx. front
  line)" into "Contested (approx. sprezzature)". The generator never read the
  key, so the contact line was silently missing from the flagship example;
  once unknown keys became an error (0.6.0), the example was simply broken.
  Nothing tested it. Something does now.

- **`build_situation_examples.py` ran nowhere but one machine.** It imported
  the generator from a sibling `sprezzature-figures` checkout, shelled out to
  a script path inside it, wrote this repo's examples *into* it, and skipped
  every PNG unless `rsvg-convert` happened to be installed. It now uses this
  repo and the `resvg-py` already declared as a dependency. The per-layer
  decomposition is behind `--layers`, being about 12 MB per example.

### Changed

- `assets/situation-maps/` is where the worked examples land, and the SVG is
  built by importing `build_map` rather than by subprocess, so a config the
  generator refuses fails with the generator's own message.

- The tracked `assets/svg-examples/choropleth.svg` had drifted from its own
  generator — it predates 0.7.0's rivers and computed relief — and is
  regenerated here. Same class of staleness as the `situation_map.svg` drift
  corrected in 0.3.0, and the same fix.

## [0.7.0] - 2026-09-16: a planet with rivers, cities and terrain that is computed

### Added

- **Cities on every map, by default.** A map of the Earth with nobody on it is
  a map of an empty planet: a reader could see where the Andes are and not
  where Lima is, and had no anchor for the scale of what they were looking at.

  Chosen by Natural Earth's cartographic prominence, **not** by "is it a
  capital" — that is a political list and it omits New York, Mumbai, São
  Paulo, Shanghai, Los Angeles and Karachi, six of the world's twelve largest.
  The vendored list carries 1 251 places, 1 051 of which are not capitals, and
  the selection widens as the map zooms in because prominence is exactly the
  question "does this belong at this scale".

  Labels that would collide are **dropped, never moved**. A name nudged clear
  of its own dot points at the wrong place and says nothing about it, which is
  worse than a name that simply is not there. The same rule catches a label
  that would run off the plate — "Istanbul" was coming out as "Ista".

- **Rivers on the choropleth**, tapered by prominence so a trunk reads thick
  and a tributary thin. The situation map already drew them; the world map had
  no water at all. Drawn **over** the country fills, not under: beneath them
  they were in the file and invisible on the page, which is also why every
  published choropleth puts its water above the thematic fill.

### Changed

- **The world choropleth's relief is computed now**, from the vendored
  elevation pyramid — a Lambertian hillshade blended with Brown's
  fractional-Laplacian texture shading — instead of resampling a pre-shaded
  picture. The old path was justified on two grounds, and neither survived
  measurement: the whole world transforms in 0.24 s at 8 arc-minutes, and at
  the plot area's own resolution the computed shade carries 3.7x the fine
  structure of the baked raster (the Himalaya 2.8x its contrast, the Andes
  2.7x, the Alps 3.0x).

  Said plainly, because it matters more than the headline: **under the country
  fills this is barely visible** — 1.0 to 1.4x in the finished map. The
  algorithm was never the bottleneck there; the compositing is. What the
  change buys is honest provenance and a relief that holds up wherever it is
  shown at strength.

### Fixed

- **Every coastline was ringing.** The elevation grids store sea as a flat
  zero — 64 % of the world grid — so each coast is a one-pixel step from 0 to
  whatever the land rises to, and texture shading is a high-pass filter: a
  step edge is the purest high-frequency signal there is. It came out as a
  bright halo tracing every coast plus broad ripples over open water, where
  there is no terrain to depict at all. The land is grown outward before the
  transform and the sea put back as neutral after it.

## [0.6.0] - 2026-09-15: a mistyped config key is refused, not ignored

### Fixed

- **A one-letter slip in a situation-map config silently dropped whatever it
  configured.** The plate is driven by two dozen optional keys, hand-edited in
  YAML, and an unrecognised key was simply never read. `canvas_widthl`
  rendered at the default width without a word. A slip on `areas_of_control`
  would have dropped an entire layer — and the plate would still have looked
  like a finished intelligence product, which is the worst possible response
  to a typo: the map is wrong and nothing says so.

  `validate_config` refuses any key the generator does not read, and names the
  closest known one, because the realistic cause is a typo and the realistic
  fix is one character. A missing `region` now explains what a region is
  instead of raising a bare `KeyError` from deep inside the layout code.

  `CONFIG_KEYS` is the list, and it is the generator's own: every key the code
  actually reads, nothing aspirational.

## [0.5.0] - 2026-09-15: no class may straddle zero on a diverging ramp

### Fixed

- **A classed diverging map could paint a recession the colour of growth.**
  A diverging scale exists to show which side of the midpoint a value falls
  on, and 0.3.0's classification had nothing stopping a class from spanning
  it. The class then takes the colour of its own centre: a quantile class
  holding −1.2 and +2.9 came out `#CFDBEC`, a blue from the positive side, for
  both.

  Not a theoretical risk. Over 3 986 random datasets with values of both
  signs, a class straddled zero in 2 537 of them under `quantile`, 1 573 under
  `jenks`, 1 203 under `headtail` and 985 under `equal`. After the fix: none,
  by any method.

  `diverging_classify` makes zero a boundary and classifies each side on its
  own values, so the breaks still answer the question the method was picked
  for. The class budget is split by how many values sit on each side, with at
  least one class per side — a side with no class of its own would have
  nowhere to put its values. One-sided data has nothing to straddle and is
  classified exactly as before.

  This is the failure mode a continuous ramp did *not* have: it passes through
  the neutral point, so the sign always showed. Classing is the better choice
  on skewed data and it brought its own way of lying; both are now closed.

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

### Added (0.4.0, continued)

- **`breaks=[…]` — class boundaries the caller chooses.** Overrides both
  `classes` and `method`, on every surface. Some bands have to mean something
  outside the data: a regulatory threshold, a percentage the newsroom already
  published, a number the reader arrives with. No algorithm lands on those by
  luck, and a map whose classes are editorial should say so — the legend
  reports them as *given* rather than naming a method that never ran.

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
