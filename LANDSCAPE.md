# Landscape

Most comparisons of mapping tools put everything on one axis and rank it.
That hides the only distinction that decides anything: **how much of the
drawing does the tool do, and how much do you.**

- A **chart grammar** (Vega-Lite, Altair, Observable Plot) takes a
  specification and a projection name; a runtime decides every mark.
- A **plotting library** (matplotlib with cartopy or geopandas) draws into
  a figure canvas built for statistical plots, with cartography added on top.
- A **web map** (Folium/Leaflet, deck.gl, MapLibre) ships tiles and a
  viewport, and the reader pans and zooms.
- A **desktop GIS** (QGIS) is software an analyst drives to *analyse*
  geography, which can also export a map.
- A **hosted editor** (Datawrapper, Flourish) trades control for speed and
  keeps the map on someone else's server.
- An **SVG writer** emits the XML directly. No runtime, no canvas, no
  viewport: the geometry on the page is whatever the code decided to write.

`sprezzature-maps` is in the last group, and that group is not empty. Being
honest about who else is in it is more useful than claiming the category.

## The SVG writers, specifically

| Tool | Language | Alive? | Thematic kinds | Projection | Designed plate |
|---|---|---|---|---|---|
| **sprezzature-maps** | Python | yes | choropleth, situation map, density | Equal Earth / auto-centred LCC | legend, scale bar, relief, provenance caption |
| [svgis](https://github.com/fitnr/svgis) | Python | yes (0.6.0, Sept 2026) | none — geometry styled by CSS class | any EPSG | no |
| [kartograph.py](https://github.com/kartograph/kartograph.py) | Python | **no** — unmaintained, points to mapshaper | choropleth via CSS | several | no |
| [map-generator](https://github.com/schiste/map-generator) | Rust | yes | none | several | no |
| [map-gen](https://github.com/coxmi/map-gen) | JS | low | none | D3 projections | no |
| py-staticmaps | Python | yes (0.5.0) | markers/lines only | Web Mercator (tiles) | no |

The useful reading of that table: **the niche has occupants, and what
separates them is not "writes SVG" — it is whether the tool has an opinion
about the finished page.** svgis is the closest living relative and a good
tool; it converts geodata to styled SVG and hands you a base map to take into
Illustrator. It does not classify your data, choose a colour scale, place a
legend, draw a scale bar, or shade terrain, because that is not what it is
for. Kartograph, which did aim at the designed thematic map, has been
unmaintained for years and its own README sends you to mapshaper.

`sprezzature-maps` aims at the part those tools leave to you: the finished,
publishable plate. Data in, designed map out, with the cartographic decisions
made and defended in `doc/CARTOGRAPHY.tex` rather than left open.

## The wider field

| Tool | Type | Runtime at view time | Real basemap | Self-hosted | Python |
|---|---|---|---|---|---|
| **sprezzature-maps** | Hand-authored SVG | none | yes (Equal Earth, LCC) | yes | yes |
| svgis | Hand-authored SVG | none | yes (any EPSG) | yes | yes |
| Vega-Lite `geoshape` | Chart grammar | JS (or `vl-convert`) | yes | yes | via `altair` |
| D3 + d3-geo | Chart grammar, lower | JS | yes | yes | no |
| matplotlib + cartopy/geopandas | Plotting library | none | yes | yes | yes |
| PyGMT | GMT bindings | GMT binary | yes | yes | yes (≥3.12) |
| deck.gl / kepler.gl | WebGL | JS + WebGL | yes (tiles) | yes | via `pydeck` |
| Folium / Leaflet | Interactive web map | JS, browser | yes (tiles) | yes | yes |
| Datawrapper / Flourish | Hosted no-code | none (SaaS) | yes | no | no |
| QGIS | Desktop GIS | desktop app | yes | yes | PyQGIS |

### Where this tool is actually strong, and where it is not

| Dimension | sprezzature-maps | svgis | Vega-Lite | matplotlib+cartopy | Folium/deck.gl | Datawrapper |
|---|---|---|---|---|---|---|
| Output needs no runtime to view | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | n/a |
| Publishable without restyling | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Areas-of-control / situation plate | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ |
| Arbitrary geodata in arbitrary CRS | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Spatial analysis | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| Interactive pan / zoom | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Time to first map | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

The two-star rows are the honest ones. This library reads a small set of
vendored, bundled geographies; it is not a general geodata pipeline, and if
your data is a shapefile in a national grid you want svgis, geopandas, or
QGIS. It does no spatial analysis at all: it assumes the joins, buffers and
reprojections are already done and only draws the result.

### The same table, drawn

![Six mapping tools positioned on two axes derived from the table above, with sprezzature-maps anchored top-right](assets/sprezzature_maps.svg)

This page opens by refusing to rank these tools on one axis. A map is the
other half of that refusal: it uses **two**, and says how much they leave out.

The source is [`assets/landscape.csv`](assets/landscape.csv) — the table above
and nothing else, with `n/a` read as a 1, since in that table it means *this
tool does not give you that*. Regenerate with:

```sh
standpoint assets/landscape.csv --outdir assets --stem sprezzature_maps
```

…then stamp the result with the date its ratings were made. The suite
repository has `scripts/date_the_map.py` for it; by hand it is one `<text>`
element reading `Ratings as of October 2026`. That step is not decoration: a
figure carrying no vintage trips this package's own `no-provenance` rule,
which exists because a map with no date is read as current forever. The rule
fired on this very figure the first time it was added, which is the useful way
for it to arrive.

The geometry is ordinary correlation PCA and is **deterministic**; the four
words at the edges come from a local model and are vaguer than what is behind
them, so here are the loadings.

**Horizontal** — "output needs no runtime to view" (+0.54) and "areas-of-
control plate" (+0.41) against "interactive pan/zoom" (−0.49) and "time to
first map" (−0.49). A file you own versus a thing you drive, with speed on the
side of the thing you drive. That is the same distinction this page opens
with, arrived at from the numbers rather than asserted.

**Vertical** — "publishable without restyling" (+0.60) and the plate (+0.42)
against "arbitrary geodata in arbitrary CRS" (−0.51) and "spatial analysis"
(−0.41). Finished-as-drawn versus analytical reach. This is the trade the
two-star rows above are admitting to, and it is the more interesting of the
two axes because nothing in the field scores high on both ends.

**Two axes carry 79 %** of a seven-criterion table across six tools. Where the
points land: `matplotlib+cartopy` sits diametrically opposite `Datawrapper` —
all reach and no finish against all finish and no reach — and
`sprezzature-maps` and `svgis` share the right-hand side, which is the earlier
claim that svgis is the closest living relative, drawn rather than argued.
`Folium/deck.gl` is far left, as a thing you drive should be.

`standpoint` also writes a prose interpretation beside the figure; it is not
reproduced here, because a model reading back ratings somebody wrote is not a
finding, and this file is more useful if the judgements stay visibly mine.

## When to use what

**Use `sprezzature-maps`** when the deliverable is a *figure* — something a
reader looks at rather than explores — that has to look intentionally
designed, ship as one self-contained file with nothing to load at view time,
and stay geographically honest: Equal Earth for the world so country areas
stay true (unlike the Web Mercator every tile tool defaults to), Lambert
conformal conic auto-centred on a region so local shapes and angles do.

The `situation_map` kind is the sharpest case. Areas of control, a contact
line, tapered axes of advance, relief, rivers and lakes, a scale bar in two
units and a provenance caption, from a YAML file — that is a genre with
plenty of *publishers* (ISW, Liveuamap, ACLED) and, as far as we can find,
no open-source *generator*. Those organisations publish maps and data; none
of them ships a library that turns your own assessment into a plate.

Not shipping a generator does not mean having nothing to teach, and what
they have to teach is not geometry. It is **how to be less confident on
purpose**:

- **ISW** keeps assessed control, reported movement and a belligerent's
  unverified claim visually apart, which is what lets a reader hold the map
  up against a ministry's communiqué. `areas_of_control` takes a
  `confidence` of `assessed` / `reported` / `claimed`, and a claimed zone
  gets no solid fill at all.
- **ACLED** records a 1–3 `geo_precision` beside every event because the
  precise location often is not known — precision 3 being a provincial
  capital standing in for a whole province. Markers take the same code, and
  an approximate one is drawn as a hollow ring rather than a confident dot.
- **Liveuamap** attaches a source to each event rather than to the page. A
  marker takes its own `source:`.

The drawing side has its own two lessons. **mapshaper**'s `-innerlines`
exists because walking polygons and stroking each one's outline draws every
shared border twice; this repo was doing exactly that, at 1.63× on the
Ukraine plate, and the doubled dash phases had quietly turned the
international-border convention into a solid line. Its `fill-pattern=`
vocabulary — hatches, dots, squares, dashes — is the texture set the
confidence tiers are drawn with. **svgis**'s `--data-fields` writes a
feature's own fields into `data-*` attributes so the drawing stays queryable
after it is drawn; control zones and markers now carry theirs, so a plate's
argument can be extracted rather than only looked at.

**Use svgis** when you want the geometry and none of the opinions: real
geodata in, clean CSS-classed SVG out, styling and layout yours to finish.

**Use Vega-Lite** when the map is one mark type among several in a grammar
you already use, and linked browser interaction matters more than the file.

**Use matplotlib with cartopy or geopandas** for exploratory geographic
plots in a notebook, or when the map must sit in a figure beside statistical
plots from the same library. It is not built to emit a polished publication
SVG without substantial manual styling.

**Use PyGMT** when you need the Generic Mapping Tools' depth — geophysical
projections, grids, professional topographic output — and a GMT install is
acceptable.

**Use deck.gl, kepler.gl or Folium/Leaflet** when the deliverable is a page
the reader explores: real pan, zoom and tiles at every scale. This repo does
not compete there and does not try to.

**Use Datawrapper or Flourish** when speed and a non-technical editing
workflow beat self-hosting, offline rendering and exact control.

**Use QGIS** to actually *analyse* geography — spatial joins, buffers,
coordinate conversion. `sprezzature-maps` assumes that work is done; it only
draws the answer.

## The conflict-research field, specifically

The table above compares *drawing* tools. A political scientist, a conflict
researcher or an analyst at a think tank does not start by choosing a drawing
tool: they start with a dataset, and the dataset is almost always one of
two.

| Dataset | Unit | Where it says it is | When it says it is | Updated |
|---|---|---|---|---|
| [ACLED](https://acleddata.com/methodology/acled-codebook) | one political-violence or protest event | `latitude`/`longitude` + `geo_precision` 1–3 | `event_date` + `time_precision` 1–3 | weekly |
| [UCDP GED](https://ucdp.uu.se/downloads/) | one organised-violence event with ≥1 death | `latitude`/`longitude` + `where_prec` **1–7** | `date_start`/`date_end` + `date_prec` 1–5 | yearly, monthly candidate |

Both ship a precision code beside every coordinate, and both mean something
specific by it. ACLED's 3 is a provincial capital standing in for a whole
province. UCDP's 4 is a first-order administrative centroid; its 6 means
*only the country is known* and the coordinates are a representative point
for an entire state.

**Every tool in this space draws all of those as the same dot.** `acled`
and `acled.api` fetch the rows; `acledR`, `conflictr` and
`acled_conflict_analysis` reshape and plot them; GeoPandas, cartopy and QGIS
will put a point layer on a basemap; Datawrapper will make it pretty. None of
them renders a `geo_precision` 3 differently from a 1, which means every one
of those maps asserts a street corner its source never gave, several hundred
times per figure, without saying so.

That is this project's opening. The marker layer already draws precision as
cartography — a solid cased disc for a named location, a hollow ring for an
approximate one, a broken ring for a region pinned to its capital, a drawn
radius where the dataset states one — with the wording taken from ACLED's own
codebook. `scripts/_conflict.py` is the twenty lines between the researcher's
file and that marker:

```python
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
```

What the suite still leaves to others, stated as plainly as the rest of this
page:

| Need | Here | Where it is better served |
|---|---|---|
| Fetch the data | no | `acled` (PyPI), `acled.api`/`acledR` (CRAN), the UCDP API |
| Filter, aggregate, join to admin units | no | GeoPandas, `acled_conflict_analysis`, QGIS |
| Historical borders for a pre-2019 map | no — Natural Earth is present-day | [CShapes 2.0](https://doi.org/10.1177/00220027211013563), 1886–2019 |
| A grid of equal cells for a statistical model | no | [PRIO-GRID](https://doi.org/10.1177/0022343311431287) 0.5° |
| Subnational polygons beyond the bundled tiers | partly (admin-1, admin-2) | geoBoundaries CGAZ, GADM |
| NATO APP-6D / MIL-STD-2525D unit symbols | no | `milsymbol` (JS), `mil-sym-java`; **there is no Python renderer** |
| Draw the result as a finished, citable plate | **yes** | — |

The last row is the whole claim, and the row above it is the most interesting
gap in the field: the joint military symbology standards have open
implementations in JavaScript, Java, Android and Rust, and none in Python.

## The house position

Own the exact output rather than hand it to a runtime, and pay for that by
writing more of the drawing code. It is the same trade `sprezzature-figures`,
`sprezzature-accessibility` and `sprezzature-ux-laws` make elsewhere in this
suite. It is a bad trade for exploration and a good one for publication.
