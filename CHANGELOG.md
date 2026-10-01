# Changelog

All notable changes to sprezzature-maps are documented here.

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
