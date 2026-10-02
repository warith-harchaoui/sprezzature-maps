# Changelog

All notable changes to sprezzature-maps are documented here.

## [0.11.0] - 2026-10-02: six maps nobody could rebuild, and a plateau that looked like a plain

The website's gallery carried twelve maps. Five had builders. The other
seven — four situation plates, three choropleths — were rendered once in
August, before this package was split out of the monorepo, and carried along
as files ever since. When the 0.10.1 fix went out, the five with recipes
were regenerated in one command and the rest were not, because nobody could.

Rebuilding them meant looking hard at four plates whose entire subject is
the physical base, and that turned up a run of things the conflict plates
had been hiding.

### Added

- **Four reference plates with builders**: `switzerland`, `iberia`,
  `western-europe` (the one `SKILL.md` cites as its worked example) and
  `himalaya`. They carry no thematic layer on purpose — a reader looking at
  Ukraine is looking at the front line, and the terrain under it only has to
  stay out of the way. Here there is nothing else to look at.

  These are not the lost configs recovered. The August files have neither a
  `<title>` nor a `<desc>`: they predate the accessibility work entirely, so
  reproducing them faithfully would have reissued four inaccessible maps.

- **`scripts/build_choropleth_examples.py`** for the three choropleth
  variants, which had no generator in either repository.

- **Hypsometric tinting.** The relief duotone maps *illumination*, which is
  a function of slope and aspect, so two pieces of flat ground shade
  identically however far apart they are vertically. On the Himalaya plate
  that is not a subtlety: the Tibetan Plateau at 4 500 m and the Gangetic
  Plain at 100 m are both flat, both came out the same colour, and the
  single most important fact about the region — that there is a
  four-kilometre step between them — was invisible on a plate whose subtitle
  promises eight kilometres of relief.

  Height now sets the colour and the hillshade sets the light on it, in that
  order. Default follows the visual hierarchy: on for a plate with no
  thematic layer, off under one, where a second colour scheme would compete
  with the one encoding who holds the ground. `basemap.hypsometric` settles
  it either way.

- **`basemap.relief_strength`.** The blend strength was a constant swept
  *with the control fills in place* — its own comment says so, because three
  multiplies stack. That is the right number for a plate about who holds the
  ground and the wrong one for a plate with nothing on top, where restraint
  just throws away contrast. Measured on the Himalaya, the tuned-for-conflict
  value rendered the whole range inside 13% of the available tonal range.

### Fixed

- **`labels.territories` drew nothing.** It was in the schema, in the
  validator and in the module docstring, and no layer read it. A config
  naming the Tibetan Plateau was accepted in full, rendered without
  complaint, and produced no text — strictly worse than a refusal, which is
  at least one error message. Found by looking at a picture, which is the
  only way it could have been found.

- **A water name that matches nothing is now refused.** This repository's
  rule is that a mistyped config key is refused rather than ignored, and it
  was only ever enforced on *keys*. `lakes.always_label`, `lakes.skip`,
  `lakes.former`, `lakes.historic`, `rivers.always_label` and `rivers.skip`
  take proper nouns matched by exact string equality against Natural Earth,
  and a name matching nothing did nothing, quietly.

  Not hypothetical: the Ukraine plate draws the Kakhovka Reservoir as
  drained purely because `lakes.former` matches Natural Earth's spelling of
  it. Had that drifted, the plate would have gone back to painting 2 150 km²
  of water that is not there and said nothing about it. Four names in
  configs written for this release were wrong.

  The check is against the whole dataset rather than the plate's own bbox:
  naming a river that exists but lies elsewhere is reasonable for a shared
  config, while naming one that exists nowhere is a typo every time.

- **The example builder never validated its own configs**, which is how
  `areas_of_control.hatch_color` — read by the generator, absent from the
  registry, therefore refused — survived on three shipped plates. These
  configs *are* the worked examples of what the generator accepts, so a dead
  option in one is not a private mistake; it is documentation that lies.

- **The subtitle was printed across the map, on every plate, always.** The
  title is drawn at a fixed baseline and the plate was fitted from `padding`
  alone, so the two were laid out as if the other did not exist: at the
  default padding the map began fourteen units *above* the title's own
  baseline. On the Ukraine plate the subtitle ran through a frontier and the
  Dnieper. No test noticed, because no test asks where text lands.

- **The legend swatch no longer matches the territory it keys.** Once the
  terrain is blended under the control fills, the Ukraine plate's declared
  `#bcd4ec` — a pale blue with the blue channel 24 levels above the green —
  renders as ground with blue five levels *below* green. The hue is not
  attenuated, it is gone. The swatch is now composited exactly the way the
  page composites it, against the terrain tone the plate measures off its
  own pixels; swatch-to-ground distance falls by 58–67%. Reported by a
  reader sampling the rendered plate in a browser.

- **The control panel could land on the legend.** The eastern DRC is the one
  portrait plate and the one whose legend sits bottom-left, exactly where the
  panel was nailed: "SHOW / Terrain / Water / …" printed straight through
  "AREAS OF CONTROL". Invisible to every rendered PNG, because the
  rasteriser draws the panel hidden. The panel now takes a free corner, and
  the guard is the property rather than a count — the two boxes must not
  intersect, on every plate that draws both.

- **A confidence ladder with one rung** was offered on all five conflict
  plates: a radio button already on and impossible to turn off. A control
  that cannot change anything is noise.

- `build_doc_map_figures.py` looked one directory level too high and found
  nothing.

- The Iberian plate labelled the Tagus twice, once under each country's name
  for it.

## [0.10.1] - 2026-10-02: two factions that 0.10.0 silently deleted

0.10.0 clipped control zones to land so a schematic rectangle would stop
painting the sea. On two of the five shipped plates it deleted a whole
faction instead, and the full suite stayed green.

### Fixed

- **Syria lost its government and Libya lost the NTC.** Damascus, Homs,
  Hama, Latakia, Tartus — the entire west and south of the Syrian plate —
  rendered as plain desert, indistinguishable from Turkey and Jordan beside
  it, on a map titled "Syria: Areas of Control". The legend went on
  promising both classes, because a legend swatch is drawn from the palette
  and never asks the geometry whether it made it to the page.

  The cause was two bugs meeting. Clipping a hand-drawn zone against a
  coastline returns a **`GeometryCollection`** whenever the zone's edge
  grazes the shore: the polygon the author meant, plus a stray line fragment
  where the two boundaries touch. And `projected_geom_to_path` recognised
  `Polygon`, `MultiPolygon`, `LineString` and `MultiLineString` — answering
  anything else with an empty string, which every caller reads as "nothing
  to draw".

  A silent empty string is the worst possible answer to a geometry you do
  not recognise, so that is fixed at the root: the path writer recurses into
  a collection rather than shrugging. The zone clip also keeps only the
  areal parts now, since a zone is an area and a tangential line fragment is
  an artefact of the clip, not territory.

- **The suite could not see it**, which is the more useful half. Counting
  elements would not have caught a class going missing. The guard now
  asserts the invariant that actually matters, on every shipped plate: **a
  class in the palette and in the source must reach the page as at least one
  path.** A legend that promises what the map does not draw is the failure
  mode this repo exists to avoid.

- **`build_doc_map_figures.py` could not run at all.** It read
  `repo_root/"web"/"img"`, a directory that has never existed since this
  package was split out of the `sprezzature` monorepo — while `doc/img/*.png`
  sat committed and current, regenerated by hand from somewhere else. It now
  defaults to the sibling repository, accepts a path argument, and says
  exactly which files it wants instead of dying on a `FileNotFoundError`.

- `areas_of_control.over_water` and `lakes.depth_rings` were added in 0.10.0
  and reached neither the module docstring nor any other document. The
  schema test only guards *top-level* keys, so nested ones slipped past it.

### Changed

The README's render-time figures were measured on a cold process and
attributed to the wrong things. Re-measured: the Europe demo is about 10 s
cold and 8 s warm, of which roughly 2 s is terrain shading and about 2 s is
one-time atlas loading and imports — so a server renders its second plate
faster than its first — while a regional plate like eastern DRC is about 3 s
warm. The previous text claimed 4 s of relief and 1.5 s of loading.

## [0.10.0] - 2026-10-02: the water is water, and the plate can be questioned

Two threads, both driven by rendering plates and looking at them. The natural
layers had no shared logic, and the plate had no life on a page.

### New config keys and flags, in one place

| Key | Where | Meaning |
|---|---|---|
| `interactivity` | top level | `"self-contained"` (default), `"external"`, `"static"` |
| `areas_of_control.over_water` | bool, default `false` | keep a zone's own shape instead of clipping it to land |
| `lakes.depth_rings` | int, default `4` | shelf rings stepped inward from a lake's shore; `0` is off |

No CLI flag changes. `make_situation_map`'s module docstring now carries the
complete key reference, enforced by
`tests/test_config_schema_is_documented.py`.

### Fixed — a control zone painted the sea

A schematic assessment is usually handed over as a rectangle, and nothing
stopped it filling the Black Sea, the Sea of Azov, the Kakhovka reservoir and
the Syvash lagoons the colour of held territory — a muddy purple-brown with
the bathymetry contours still faintly visible underneath. Armies hold ground.
Zones are clipped to land now, with `over_water: true` for a claim that
really is maritime.

### Fixed — one water system at two depths

Lakes were drawn under the control fills as "basemap" while rivers rode above
them. On a plate of southern Ukraine the Dnieper crossed a zone as a blue line
and then ran into its own reservoir, which the same zone had painted brown.
Water is physical fact and a claim does not move it, so the whole system —
bathymetry, lakes, rivers — now sits above the claim and reads as one thing.

### Added — lakes have depth

The sea's halo buffers outward from the coast into open water. A lake has no
open water to buffer into, so the same cue is built the other way round:
rings stepped inward from its own shore, which also makes them say something
true, since a wide lagoon fills with rings and a narrow trench barely takes
one. A lake was the only water on the plate with no shape to it.

### Added — one logic for transparency, replacing thirty numbers

Every alpha was its own literal, tuned alone in whichever pass added the
layer: 0.85, 0.9, 0.75, 0.7, 0.4, 0.3, 0.5 — thirty-odd of them, so two
things that meant the same to a reader were drawn at different strengths
because they were written in different months.

`COMPOSITING` states what an alpha is allowed to mean, and every natural
layer now draws from it:

- **ground** (land, sea, a lake's body) is **opaque** — nothing is beneath it,
  and a translucent substrate drifts towards whatever is;
- **modulation** (relief) is the one layer that blends rather than covers,
  taking the ground's luminance and never its hue;
- **depth_cue** (bathymetry rings, lake shelf) is faint — it answers a
  question the reader has not asked yet;
- **claim** (areas of control) is the *only* translucent fill, and it is
  translucent for a reason: the claim is about ground the reader must still
  see;
- **fact_line** (coast, frontiers, admin borders, rivers) is near-opaque — a
  boundary a reader can barely see is one they will doubt;
- **mark** (front line, axes, markers, every label) never fades.

The ordering is the argument: a hint is fainter than a claim, and a claim is
fainter than a fact. A test asserts both the ordering and that the layers
reference the table rather than literals, because a constant nobody
references is decoration.

### Added — the plate can be questioned on a page

A situation map now carries its own controls inside the SVG, with no page
script, no map library and no tile server:

- **layer switches** — terrain, water, borders, control, places, notes;
- **a confidence filter**, which is the control this genre exists for: show
  only what is assessed, or admit reported movement, or admit a belligerent's
  unverified claim;
- **a clickable legend** that isolates one class;
- **shareable state** in the URL fragment, so "assessed only, no terrain" is a
  link rather than an instruction.

It degrades by construction: the panel ships `display:none` and the script
reveals it, so an `<img>` embed, a rasteriser, a PDF or a browser with
scripting off all see exactly the plate that shipped before. A plate with no
thematic layer gets neither panel nor script.

Verified by executing the plate's own script against the plate's own markup
under Node, clicking every control and reading back what moved —
`tests/test_plate_is_interactive.py`, skipped where Node is absent. A
rasteriser cannot check this: `resvg` draws the document, it does not run it,
so it would report a healthy plate whose every control is dead.

### Fixed — blending leaked into the host page

The plate carries `isolation: isolate`. These SVGs are inlined into HTML, and
without a stacking context of its own a blended layer composites against
whatever the page has behind it: the same map came out different on a white
article and a dark one.

## [0.9.4] - 2026-10-02: terrain you can see through the thematic fill

A Ralph Eyeball Loop on the physical layers — relief, lakes, rivers — and how
they stack. Rendered, looked at, adjusted, looked at again.

### Changed — how terrain is composited

Shading was drawn **underneath** everything, with the land polygon left
translucent (`fill-opacity` 0.45) so it showed through. That works, and it
costs two things it need not:

- the land colour is diluted towards whatever lies beneath it, so a warm
  cream basemap drifts cold and green;
- the shading is composited by alpha, so a dark valley lightens the paper as
  much as it darkens it — the opposite of what a shadow does.

Shading is now blended **over an opaque land fill**, which behaves the way
terrain reads: a lit ridge is near-white in the shading and leaves the land
colour alone, a valley multiplies it down into its own darker, warmer self.
Hue is preserved by construction rather than by picking the opacity that
damages it least.

The blend mode comes from the plate, which already knew the answer:
`multiply` darkens a cream day plate, `screen` lifts a near-black night one.
Hardcoding either would have turned the night plate black — checked by
rendering it.

It is clipped to the land, which the old arrangement did not need: a blend
across the whole plate would work ground shading into the sea and the
bathymetry halo.

`relief_opacity` is 0.72, not 0.45, and the number means a different thing
now — blend strength rather than the fill opacity of a translucent land
polygon. Swept 0.45 / 0.65 / 0.85 / 1.0 against the Albertine Rift, the most
dissected terrain the bundled examples cover, and then again **with the
control fills in place**, which matters because the zones blend too and the
multiplies stack. Terrain contrast still climbs at 0.85, but the class
colours start going muddy in the valleys. A plate about who holds the ground
does not get to lose the ground's colour to the ground's shape.

The effect is most visible on the eastern-DRC and Sudan plates, where the
half of the map the plate is *about* previously rendered as a flat wash: the
Albertine Rift's drainage network, the Jebel Marra massif and the Red Sea
hills now read through the thematic fills.

### Fixed — blending leaked into the host page

The plate now carries `isolation: isolate`, so every blended layer inside it
composites against the plate and stops there. These maps are inlined into
HTML — that is how the gallery and any CMS embed them, rather than as an
`<img>` — and without a stacking context of its own a blended layer
composites against whatever the page has behind it, so the same map came out
different on a white article and a dark one. The relief change made this
urgent by giving the blend most of the plate's area.

## [0.9.3] - 2026-10-02: refuse what cannot be drawn honestly

Two more Ralph Loop passes, aimed at the inputs a real caller supplies rather
than at the plates. The drawing code held up throughout; the **refusals** did
not. The generators were careful about everything except the values they
cannot work without.

### Fixed — the choropleth rendered data that did not exist

- **An empty result set became the demo.** `rows = data if data else
  DEMO_DATA` cannot tell `None` ("I brought nothing, show me the demo") from
  `[]` ("my query ran and returned no rows"). The plate's subtitle kept the
  simple case honest — it says "synthetic demo data" — but it is applied only
  when the caller supplied no subtitle, so

  ```python
  build_svg([], title="Q3 revenue by country", subtitle="Millions of euros")
  ```

  produced a publishable world map of 174 countries of invented numbers under
  a real headline, with no warning anywhere on it and an accessible
  description reporting the synthetic range as though it were the caller's.

  `make_density` already answered an empty point list with "no point fell
  inside the bbox; nothing to draw", and `make_situation_map` already refused
  to render without a region. The choropleth was the odd one out of three.
  It now refuses, and the HTTP API turns that into a 422 with the reason.

- **One `nan` poisoned everything and still finished.** `min`/`max` both came
  back `nan`, so the ramp spanned nan, every class boundary was meaningless,
  the accessible description read "data ranging nan to nan" and the legend
  printed **nan** as its own axis labels. One empty cell in a spreadsheet is
  the ordinary way to arrive here. Non-finite values are now refused, naming
  the rows at fault and pointing at the state that already exists for this:
  omit the row and the country draws no-data grey.

### Fixed — a region could be the opposite of what was asked for

`validate_config` suggests the key you probably meant when you mistype one,
and never looked at `region`, the only key it requires.

- **A bbox crossing the antimeridian silently became its own complement.**
  `box(177, -19, -178, -16)` does not raise; shapely normalises it to
  `-178 .. 177`, so a five-degree window over Fiji drew **355 degrees of
  longitude** — the whole planet except the region requested — and the result
  rendered and looked finished. A transposed pair drew a different valid
  region just as quietly.
- Zero-width boxes reached a bare `ZeroDivisionError`, whole-world boxes a
  raw pyproj `CRSError`, and regions crossing ±180 a GEOS
  `TopologyException`.

`validate_region` now refuses each with a sentence naming the cause, and
where the cause is ambiguous it names both possibilities, because `west >
east` is either a swap or an antimeridian crossing and only the caller knows
which. Wrapped regions are refused rather than faked: drawing one properly
means splitting every layer at the seam, which is a feature and not an
argument check. `build_map` validates too, so the inner entry point no longer
answers a missing region with a bare `KeyError`.

- **A polar plate could not be drawn at all.** Projecting a coastline into a
  conic can leave it self-touching, and GEOS answers a boolean operation on
  an invalid operand with a raw exception rather than a result — so any plate
  of Svalbard and northern Greenland died in `region.difference(land)`.
  Repaired when `is_valid` says it is needed, which the bundled plates never
  trigger and therefore never pay for.

### Fixed — things that were documented nowhere, or wrongly

- **`make_situation_map`'s module docstring named ten of thirty-one config
  keys**, while `EXAMPLES.md` sends readers there "for the full list of
  fields it accepts". The reference is now complete, and
  `tests/test_config_schema_is_documented.py` fails if `CONFIG_KEYS` and the
  documentation disagree in either direction.
- **`lakes.historic` shipped in 0.9.1 and reached no user-facing document**,
  although it changes Lake Urmia's default rendering. Its sibling
  `lakes.former` was documented in both READMEs. Now both are.
- **`doc/CARTOGRAPHY.tex` opened with "Two generators are covered"** and never
  acknowledged the third.
- **`LISEZMOI.md` carried none of the courtesy credits** the English README
  does — mapped.earth, GloFAS, HydroSHEDS. In a repo that stamps an ODbL line
  onto any plate touching OSM data, an attribution section present in one
  language and absent in the other is not a translation backlog.
- **`article_sidecar` returned an empty record for anything but a situation
  map.** It is exported under a kind-agnostic name and keyed on
  `<title id="sm-title">`, which only one kind writes. It matches the element
  now.

### Added

- **`per_area=True` on `make_density`.** The grid is cut in degrees, so cells
  are equal in angle and unequal in ground: the poleward cell is 28% smaller
  than the equatorward one on the bundled US demo, 39% across Europe, **49%
  across Scandinavia** and 90% across a hemisphere. The legend's "per cell"
  was literally true, which kept this an undocumented choice rather than a
  lie — but this is the repo that put Equal Earth under the choropleth
  precisely so colour-by-area would not misrepresent size.

  Counts stay the default, because the form is an *accumulation* map and a
  count is what fell. What was missing was saying so, and offering the other
  question: `per_area=True` divides each cell by its own spherical area and
  relabels the legend in events per 1 000 km². The module docstring carries
  the measured table and `CARTOGRAPHY.tex` gained a section with the
  quadrangle-area formula.

- **`data-name` / `data-id` / `data-value` on choropleth countries**, so the
  svgis-style extraction the situation map already had works for the kind
  that did not. A country with no number carries an empty `data-value`
  rather than nothing, because "no data here" is a state the map draws on
  purpose.

### Verified rather than repeated

The README claims the ramps read correctly to someone who cannot distinguish
red from green. Simulated both at nine stops through Machado protan, deutan
and tritan matrices: the sequential ramp stays strictly monotonic in
luminance under all three (worst adjacent step 3.0% of span), and the
diverging ramp rises to its neutral and falls away from it under all three,
with the midpoint the lightest swatch every time. The claim holds.

## [0.9.2] - 2026-10-01: a Ralph Loop over the whole project

Two iterations of render-it-and-look-at-it across every surface, not just the
plates. The findings were mostly not in the drawing code, which is tested and
looked at constantly; they were in everything that *describes* the drawing
code, which nothing checks.

### Fixed

- **`density` was invisible on every surface that is written by hand.** The
  third generator has been real for a while — in the library, at
  `/v1/density`, in both CLIs, and in MCP as `render_density` — and it was
  absent from the GUI gallery (0 mentions in 5 522 bytes of HTML), from
  `EXAMPLES.md` (0 mentions in 162 lines), from both routing tables in
  `TRIGGERS.md`, and from `api.py`'s own module docstring, which still read
  "the two map kinds this repo carries".

  A user opening the server root was shown two of three products. An agent
  reading `TRIGGERS.md` — the file whose entire job is routing a request to
  the right call — had no path to `render_density` at all.

  Every surface that is *generated* from code (`/v1/kinds`, the route table,
  the MCP tool registry) was correct throughout. The staleness was entirely
  in prose, which is exactly where nothing was watching.

- **Two documented facts were false.** `EXAMPLES.md` showed
  `curl /v1/kinds` returning `["choropleth", "situation_map"]`; the server
  returns three names. And it promised the embedded demo images "can never
  silently drift from what the code in this repo actually produces" — while
  `situation_map.svg` was a month and three releases stale, from before
  lakes, axes of advance, the accessible root and the confidence tiers.
  `choropleth.svg` was current only because `make_choropleth`'s doctest
  rewrites it as a side effect: one file fresh by coincidence, the other by
  nothing, under prose asserting a process that did not exist.

  A promise in prose is not a mechanism. There is now a mechanism:
  `scripts/build_demo_examples.py` regenerates all three, and
  `tests/test_demo_examples_are_current.py` fails if a shipped file no
  longer matches what its generator produces.

- **`simplify` was in the API schema and did nothing.** The field validated
  and appeared in the published OpenAPI document, but the route never
  forwarded it: `simplify=0` and the default both returned the same bytes.
  Found by testing the behaviour rather than the schema key. It now does
  what it says (2 140 KB unthinned against 921 KB), and the Click CLI gained
  `--simplify` too.

- **The density plate never said where it was.** Not in its title, subtitle,
  caption, or accessible description — which described the method ("253,313
  points binned to 120 by 50 cells") and omitted the place. The README sold
  this as a virtue: "a reader recognises the shape without being shown it."
  That holds for a reader who can identify the contiguous United States from
  its outline and for nobody else, with no scale bar, graticule or place
  name to fall back on, and for no screen-reader user at all.

  It now always states its mapped extent, and names the region only when the
  region is the one we can name — a caller who brings their own bbox gets
  coordinates rather than somebody else's label.

- **The Dockerfile asserted something false and carried a workaround for it.**
  Its comment read "Neither sprezzature-maps nor sprezzature-figures is on
  PyPI yet". Both are, `pyproject.toml`'s own comment says so, and the
  README's install line is `pip install sprezzature-maps`. The workaround
  cost an `apt-get install git` layer and a shallow clone that **pinned
  nothing**, so every build baked in whatever the dependency's HEAD happened
  to be — which is the opposite of a reproducible image. Its `CMD` printed a
  `--help` message and exited, from an image carrying the HTTP API, the MCP
  surface and the GUI.

  Now installs from PyPI and serves uvicorn. Verified by building and
  running it: all three generators render inside the image, `/v1/kinds`
  answers over HTTP, the gallery returns 200.

- **`addopts = "-m 'not slow'"` was a trap.** It excluded nothing, because no
  test carries the marker — but the next contributor to add one would have
  silently removed it from every local run and from CI, which runs a bare
  `pytest -q`. A test nobody runs reads as coverage and is not.

- The Europe demo was titled "Western Europe" while framing Athens,
  Bucharest, Belarus and western Ukraine.

### Added

- `density` plates emit named layer groups (`field`, `title-block`,
  `legend`, `caption`), as the other two kinds do. A plate nobody can take
  apart cannot be inspected or restyled.
- `make_density(region=…)` names the mapped area on the plate and in the
  accessible description.

### A note on the freshness test

It first compared bytes, which is the obvious comparison and the wrong one.
Rendering the same demo inside this project's own Docker image and against a
macOS checkout gives different raw bytes and, with decimal numbers
normalised, an identical document: the projection's arithmetic differs by
ulps across platforms and moves coordinates in the last printed digit. That
test would have failed on CI on its first run and every run after, for a
reason unrelated to the thing it exists to catch, and a gate that cries wolf
is worse than no gate.

It compares a fingerprint instead — embedded rasters and decimal numbers
dropped, the whole document structure and every piece of text kept — so a
renamed layer, a changed label, a new legend row or an edited title still
trips it. Checked across both platforms for all three kinds.

## [0.9.1] - 2026-10-01: the two debts the roadmap kept naming

Both of these were known, written down, and carried anyway — one in a
docstring, one in the README's own roadmap. Neither was hard; they were just
never the thing in front of us.

### Fixed

- **Lake Urmia was drawn at an extent the world no longer has.** Natural
  Earth carries it near its historic ~4 200 km², and it has repeatedly fallen
  below a fifth of that since the 2010s. The two existing escape hatches both
  lie about it: `lakes.skip` hides the question, and `lakes.former` asserts a
  disappearance that has not happened — the lake still exists, at a fraction
  of the polygon on file.

  There is now a third treatment for the case that actually applies, and
  Urmia is drawn that way **by default**: a faded fill inside a dashed edge,
  the name suffixed `(historic extent)`. It says the outline is the historic
  maximum and declines to assert that the water fills it, which is the most
  that can be said honestly — there is no single current extent to vendor in
  its place, and one pinned today would be wrong by next season.

  `lakes.historic` replaces the built-in list, and `lakes.historic: []`
  restores the basemap's own extents. A default rather than an opt-in because
  the alternative is that every caller who draws this region is silently
  wrong until they happen to read a docstring.

- **The TopoJSON decoder was duplicated**, as the README's roadmap had been
  saying for three releases. `make_choropleth` and `make_situation_map` each
  carried their own delta decoding and their own ring stitching — two places
  for the same off-by-one to hide, and they had already drifted on one edge
  case (which arc contributes its first point when the first arc is empty).

  New `scripts/_topojson.py` is the single reader. It stops at coordinates:
  what a caller does with a ring — stitch it into a repaired shapely polygon
  to clip against, or project it straight to a path — is legitimately
  different between the two, and that difference stays where it belongs.

  Follows `_svg.py`'s rule for extracted code, and the extraction was held to
  it: all five shipped plates and the choropleth demo render **byte-identical**
  across the change. 57 lines removed, 7 added.

## [0.9.0] - 2026-10-01: drawing how sure you are, and fitting in a column

Two questions, asked one after the other. First: this generator could draw
*what* an analyst assessed but had no way to draw *how sure they were*, and
a map that cannot say "probably" says "certainly" by default. Second: what
changes when the deliverable is not the map but the article the map
illustrates.

Both were answered by reading the people who publish this kind of map for a
living — ISW, ACLED, Liveuamap on the assessment side, the graphics desks on
the page side — and by reading the two tools that already write SVG from
geodata, svgis and mapshaper. Then by rendering plates at the widths those
desks actually publish at and looking at what broke.

### What the plate knows, and how well

A close reading of five tools that publish or generate this kind of map —
[svgis](https://github.com/fitnr/svgis) and
[mapshaper](https://mapshaper.org) on the drawing side,
[ISW](https://www.understandingwar.org),
[Liveuamap](https://liveuamap.com) and
[ACLED](https://acleddata.com) on the publishing side — and the ideas worth
taking from each.

#### Added

- **A confidence ladder on areas of control, after ISW.** ISW's
  control-of-terrain plates keep three things visually apart that a single
  fill runs together: ground a force is assessed to hold, ground where
  movement has been *reported* but not assessed as held, and ground a
  belligerent *claims* and nobody has verified. That separation is what lets
  a reader hold the map up against a ministry's communiqué.

  Any zone may now carry `confidence: assessed | reported | claimed`
  (`areas_of_control.confidence_field`, default `confidence`). `assessed` is
  the default and renders exactly as before. `reported` keeps the class
  colour at lower opacity under a diagonal hatch — still plainly the same
  actor, plainly less certain. `claimed` gets **no solid fill at all**, only
  a dotted texture and a dashed outline: painting a claim the colour of held
  ground asserts the one thing nobody has verified.

  An unreadable value is refused rather than rounded down to `assessed`,
  because that failure runs in the dangerous direction and leaves a plate
  that still looks finished.

- **Four named fill textures, after mapshaper.** mapshaper's `-style
  fill-pattern=` offers "hatches, dots, squares and dashes"; one ad-hoc hatch
  was no longer enough once a zone had to say how well known it is as well as
  whose it is, and inventing a fifth texture per need is how a legend stops
  being learnable. All four are drawn in the zone's own colour, so the
  texture carries certainty and the hue carries the actor.

- **Locational uncertainty on markers, after ACLED.** ACLED records a 1–3
  `geo_precision` beside every event "to reflect the fact that the precise
  location of the incident may not be known": 3 means a *provincial capital
  standing in for a whole province*. Drawing all three as the same hard dot
  throws that away and asserts a street corner the source never gave.

  A marker may now carry `precision: 1 | 2 | 3`. Precision 1 is the solid dot
  and means what it always meant. An approximate position gives up its solid
  centre rather than inventing an area for itself — a hollow ring, the old
  cartographic signal for "about here" — and precision 3 breaks the ring as
  well. `radius_km` draws a stated uncertainty to the plate's own scale,
  verified to 0.06% against the viewport.

  Deliberately **not** done: defaulting a radius from the event type. ACLED
  publishes per-type buffers (5 km for battles and explosions, 2 km for
  riots), but those measure how far an effect reached, not how badly a
  position is known, and borrowing one for the other would dress a guess as a
  measurement.

  `date` + `time_precision: 1 | 2 | 3` speak a date's precision in the
  tooltip rather than implying a day: "month of March 2026".

- **Provenance per mark, after Liveuamap.** Every Liveuamap event carries its
  own source link. A plate-level caption saying "open sources" covers the map
  and tells a reader nothing about the one dot they are trying to check, so a
  marker may now carry `source:`, shown in its tooltip.

- **The plate can be read back out of the file, after svgis.** svgis writes a
  feature's own fields into `data-*` attributes (`--data-fields`) so the
  drawing stays queryable after it is drawn. Control zones now carry
  `data-category`, `data-confidence` and `data-area-share`; markers carry
  `data-precision`, `data-lon`, `data-lat` and `data-radius-km`. A situation
  plate is an argument about who holds what, and an argument a reader can
  only squint at is weaker than one they can extract with a regex.

#### Fixed

- **Every inland frontier was drawn twice.** `_frontiers_layer` walked the
  countries and drew each one's whole outline, so every border two countries
  share was stroked once from each side — measured at **1.63×** the real
  frontier length on the Ukraine plate, 506 of 783 distinct segments.

  The damage was not only ink. The two coincident dashed strokes start at
  different vertices, so their dash phases interleave and fill each other's
  gaps: measured on a rendered crop, the dash duty cycle went from 94% —
  which is to say a solid line — down to a legible 51% once fixed. The
  dashed hairline *is* the international-border convention, and it was being
  lost precisely on international borders, while the coastline beside it
  stayed correctly dashed. Fixed the way mapshaper's `-innerlines` does it:
  union the boundary pieces and stroke each one once.

- **A textured zone's tooltip never opened.** A pattern fill is painted, so
  it swallows the pointer, and the texture overlay sits above the `.hit` path
  the `.hit:hover~.tip` rule needs. Every contested zone on every plate had a
  dead tooltip. The overlays now carry `pointer-events="none"`.

- **A mistyped marker key is refused, not ignored** — the rule
  `validate_config` already applied to top-level keys, one level down.
  `percision: 3` read as no precision at all, which drew the confident solid
  dot: the opposite of what the author asked for, on a plate that still
  looked finished.

#### Changed

- The Ukraine example's flashpoints are drawn at precision 2 and its legend
  reads "Contested flashpoint" rather than "Contested flashpoint (approx.)".
  The approximation is carried by the ink now instead of being spelled out in
  the legend's wording.

### A map that has to fit in an article

The second half of the same pass. The question asked was what changes when
the deliverable is not the map but the *article the map illustrates*, and the
answer came from reading how the graphics desks that do this every day work —
[Datawrapper](https://www.datawrapper.de/blog/fix-my-chart-map-annotations)
on annotation, the ["essential lies in news maps"](https://datajournalism.com/read/longreads/the-essential-lies-in-news-maps)
long read on generalisation, and published accessibility practice on alt
text — and then from rendering plates at the widths those desks actually
publish at. A one-column chart at The Economist is 595 units wide;
Datawrapper defaults to 600; a phone column is about 375.

#### Fixed

- **At 375 units the legend covered the map.** The card is a fixed 262 units:
  26% of a 1000-unit plate, 44% of a 600, **70% of a 375**. The newsroom
  answer to a narrow column is not a smaller card but a different layout, so
  `legend_position` gains `"below"` (a full-width band under the map, packed
  into as many columns as fit) and `"auto"`, which picks between that and the
  floating card from the plate's own width. Both are opt-in: every existing
  plate renders byte-identically, which is checked by rebuilding all five
  shipped examples and comparing.

- **The scale bar printed its own labels on top of each other.** It is
  labelled `0` at one end and the distance at the other, with no check that
  the bar is long enough to hold both: on a 375-unit plate the mile bar came
  out 34 units long and rendered as `0100MI`. It now steps the distance up
  the same 1/2/5 sequence until the text fits.

  The two bars were also rounded independently, so both could land on "200"
  in different units and the mile bar came out **1.61×** the kilometre bar,
  overrunning the canvas. The mile distance is now rounded against the
  kilometre bar's length, and the pair holds a steady ratio at every width.

#### Added

- **Annotations.** The layer that makes a map an argument rather than a
  diagram, and the one thing every piece of newsroom guidance agrees is *the*
  news map. `annotations:` takes a point, a sentence, and optionally a radius
  in kilometres:

  ```yaml
  annotations:
    - at: [30.5, 51.3]
      text: "Columns withdrew north of Kyiv in April 2022."
      place: left
      color: "#2f5d92"
      circle_km: 90
  ```

  Datawrapper's conventions, for their stated reasons: **a circle, not an
  arrow**, because an arrowhead points at a pixel and claims a precision a
  note about a region does not have; **the data's own colour**, so the note
  sits back onto the map instead of jumping off it; and a deliberately narrow
  wrap, so a note that is turning into a paragraph looks wrong while it is
  being written. Each note carries a halo, because the one place an
  annotation must stay legible is over the relief it is pointing at.

- **An article sidecar.** `article_sidecar(svg)` returns the title, the zones
  with their confidence and area share, the markers with their coordinates
  and precision, and an `alt` string — read back out of the **finished SVG**
  rather than the config, via the `data-*` attributes added earlier, so a
  caption in a CMS cannot drift from the plate above it.

  The `alt` string carries a **takeaway**, which the accessible description
  did not: accessibility practice for charts asks for what kind of thing it
  is, what is in it, and what it *shows*, and the third was missing. The
  takeaway is computed from the areas actually drawn ("Ukrainian government
  control covers the largest mapped share, 81%"), never asserted — and a
  merely claimed largest share is spoken as *"is claimed to cover"*, because
  flattening that would undo on the way out exactly what the confidence tiers
  do on the page.

#### Changed — output weight

Two measurements, two different answers, and the first one corrects a
conclusion stated earlier in this changelog's other section.

- **The choropleth emitted 107 750 line segments at every output size.** At
  its default 1000×564, **97% of them are shorter than one unit** and 84%
  shorter than half a unit; at 375 units wide, 99% are sub-unit. The count
  never changed with the canvas, because nothing simplified to the render.
  New `scripts/_simplify.py` runs Douglas-Peucker **after projection**, in
  the units actually drawn — mapshaper's `-simplify resolution=`, which an
  earlier note here wrongly dismissed as worthless for this repo on the
  strength of a measurement taken on a *regional* plate, where it is indeed
  worthless. A world map in 600 units is the opposite case.

  Measured: 2346 KB → 1192 KB at 1000×564, and 2083 KB → 838 KB at 375×211,
  with at most 1.3% of pixels differing by more than 8/255 — all of it
  sub-pixel movement along coastlines, and the worst-case crop is
  indistinguishable by eye. `simplify: 0` switches it off.

  Small polygons are protected (mapshaper's `keep-shapes`): a ring that would
  drop below three points keeps the ones it had, because a map that quietly
  loses Malta is worse than one carrying redundant vertices.

- **The relief raster was stored at twice the bytes it needs.** Shaded relief
  is a duotone ramp, so a 1.3-megapixel raster of it holds about **210
  distinct colours and a single alpha value** — written as 32-bit RGBA, for
  96% of a finished situation plate's weight. It is now written as an indexed
  PNG built from the colours actually present. Not a quantisation: Pillow's
  octree gets another 70% off but *merges* colours, measured at up to 17/255
  of drift on a hillshade, where an exact palette is provably the same image.

  Every shipped plate roughly halved: Ukraine 2094 KB → 1006 KB, Sudan 2513 KB
  → 1277 KB, Syria 1708 KB → 995 KB, with ≤0.02% of pixels differing (and
  that from the geometry thinning, not the raster, which is bit-exact).

### The furniture stops fighting the map

Three defects found by the only method that finds them, which is rendering
the shipped plates and looking at them, plus the one locator convention the
repo could not do.

#### Fixed

- **The scale bar printed over place names.** It drew last, over whatever
  the label layers had already put there: straight across `TANZANIA` on the
  eastern-DRC plate and across `Amman` and `Jerusalem` on the Syrian one.
  Two of five shipped plates.

  Furniture now owns its rectangles and labels yield, which is the right way
  round — a name with a bar through it is not a name, while a name that is
  simply absent costs the reader one place out of thirty. `_reserved_boxes`
  is computed before any layer draws and read off the viewport by
  `_label_fits`, so every layer that places text obeys it without a new
  argument at each call site. The floating legend card is reserved too,
  which retires the "Mariupol hidden behind the legend" class of problem
  that `legend_position: "right"` existed to work around.

  The bar's position and its reserved box now come from one function
  (`_scale_bar_origin`), as do its two distances (`_scale_bar_lengths`).
  Computing either twice is how a reservation ends up protecting empty paper
  while the bar prints over a name somewhere else.

- **The provenance caption printed over the map.** On a tall portrait plate
  the map runs right into the caption band, and two of the eastern-DRC
  plate's three lines came out as grey monospace over a pale green control
  fill. The caption now has a ground. The hairline rule above it already
  said a footer starts here; the band is that promise kept.

#### Added

- **A locator inset.** *"Zoom out for perspective, zoom in for detail"* is
  the locator map's one rule, and a plate that only ever zooms in answers
  half of it — a reader who does not already know where North Kivu is learns
  nothing from a map of North Kivu.

  ```yaml
  inset:
    position: top-right    # or any corner
    zoom: 6                # how far out, when no bbox is given
  ```

  Drawn from the coarsest vendored atlas, because at a fifth of the plate's
  width a finer coastline is noise that costs bytes, with the plate's own
  region as a filled rectangle rather than an outline (at that size an
  outline reads as a stray border). The north arrow steps clear of it: both
  default to the top-right corner.

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
