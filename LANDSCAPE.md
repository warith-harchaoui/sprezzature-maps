# Landscape

`sprezzature-maps` writes maps as SVG (Scalable Vector Graphics, an image
format built from lines and shapes described in text rather than a grid of
pixels), one element at a time, with no drawing library underneath. It is
part of the [sprezzature](https://sprezzature.ai/) suite, and it was split
out of `sprezzature-figures` so that maps could keep their own release
schedule. It aims at one thing: the finished plate, a figure a reader looks
at rather than a map a reader drives.

## How it fits in the ecosystem

```
sprezzature suite
├── sprezzature-maps          ← this package (numbers attached to real places)
├── sprezzature-figures       (167 chart types; everything that is not geography)
├── sprezzature-colors        (accessible palettes, OKLCH)
├── sprezzature-accessibility (static HTML lint, alt text)
├── sprezzature-publish       (a folder of Markdown into a findable site)
├── sprezzature-ui            (the screens the figure sits in)
└── best-engine-ai-helper     (local model selection)
```

**What comes before.** Somebody else does the geography. GeoPandas, QGIS or a
spatial database does the joins, the buffers and the reprojection; the Armed
Conflict Location and Event Data Project (ACLED) or the Uppsala Conflict Data
Program (UCDP) supplies the events; Natural Earth supplies the coastlines,
vendored here rather than fetched. This package assumes that work is finished
and draws the answer.

**What comes after.** The output is one SVG file. `sprezzature-publish` puts
it on a page with its meta tags; `sprezzature-ui` builds the screen around it;
`sprezzature-accessibility` lints the page it lands on. Nothing in that chain
has to run a map runtime, because there is none.

**The sibling.** `sprezzature-figures` is the other half of the same product,
and the two still share rendering primitives: font embedding, the responsive
accessible root tag, the self-contained or linked output choice. The split is
by subject, not by technique. If the numbers are attached to real places and
the shape of the land matters, it is this package. If they are not, it is
figures, which keeps the schematic map kinds (`hexbin-map`, `spike-map`,
`dotdensity`, `binned-grid-map`, `hexmap`) because those plot cells, not
coastlines.

## When to choose sprezzature-maps

- **A journal wants a vector figure and will reject a raster.** The output is
  real SVG, exports to PDF and EPS as vector, and carries its smallest type
  size as a checked property: the bundled Ukraine plate is 1768 units wide and
  its smallest label is 10.8 of them, which in a 90 mm column sets at 1.6 pt,
  a third of the floor any major publisher accepts. The package reports that
  rather than letting it through, because a vector file always renders.
- **The classification has to be defensible.** Quantiles, equal intervals,
  natural breaks (FISHER and JENKS) and head/tail breaks (JIANG, 2013) are all
  available, none is
  silently chosen, the legend names the one used, and a static rule reads the
  finished SVG back and reports a classed legend that does not say how its
  breaks were chosen.
- **You are mapping events whose position is approximate.** ACLED and UCDP
  both ship a precision code beside every coordinate. Here that code becomes
  cartography: a cased disc for a known place, a hollow ring for an
  approximate one, a broken ring for a region pinned to its capital, and UCDP
  rows that only know the country are dropped and counted in the plate's own
  method line.
- **The file has to still work in five years, offline.** One SVG, fonts
  embedded, no tile server, no API key, no account, no runtime. The sidecar
  that records what drew it carries no clock, so two renders of the same
  inputs stay identical.

## When to pick something else

- **[QGIS](https://qgis.org/) or [ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview)**
  when you need to analyse the geography rather than draw a conclusion about
  it. Their graduated renderers also beat this package on a point it cares
  about: they show the data histogram with the break lines drawn on it, so the
  classification is chosen by eye against the distribution. This package makes
  you choose without that picture.
- **[svgis](https://github.com/fitnr/svgis)** when you want the geometry and
  none of the opinions. It takes real geodata in any EPSG code and writes
  clean CSS-classed SVG, which is exactly the base map to finish in
  Illustrator. It is the closest living relative, and it wins outright on
  arbitrary coordinate reference systems.
- **[deck.gl](https://deck.gl/) or [kepler.gl](https://kepler.gl/)** when the
  data is large or the deliverable moves. Millions of rows, origin to
  destination arcs, trip animation, clustering by zoom. This package draws one
  static plate and does not pretend otherwise.
- **[MapLibre GL JS](https://maplibre.org/) with
  [Protomaps](https://protomaps.com/)** when the reader has to pan and zoom
  over a real basemap, self-hosted, with no vendor account. That stack is the
  2026 default for exactly that job, and the PMTiles single file is a better
  answer to tile hosting than anything here.
- **[Datawrapper](https://www.datawrapper.de/) or
  [Flourish](https://flourish.studio/)** when an editor who does not write
  code has to make the map at four in the afternoon. Datawrapper also ships
  more accessibility than this package does, at the level of the published
  page rather than of the file.
- **[mapsf](https://cran.r-project.org/package=mapsf) or
  [tmap](https://cran.r-project.org/package=tmap)** if the analysis is already
  in R. `mapsf` is the closest thing in any language to this package's goal:
  thematic cartography with the furniture (scale bar, north arrow, title,
  credits) treated as part of the map rather than as decoration.

## Ideas worth stealing

Studying a competitor and bringing nothing home is wasted reading. Seven
things the field does better, ordered by what they return for what they cost.
Two of them are refusals, with the reason, which is a result as well.

**[tmap](https://cran.r-project.org/package=tmap) and `classInt`: the
`pretty` style.** tmap names its classification styles in the argument itself
(`quantile`, `jenks`, `pretty`, `sd`, `fisher`, `headtails`), and the one
missing here is `pretty`: breaks on round numbers, chosen so the legend reads
0, 20, 40, 60 rather than 17.4, 38.9, 61.2. Here that is one more entry in
`METHODS` and one more label in `METHOD_LABELS`, both in
`scripts/_classify.py`, plus a `pretty_breaks()` of about thirty standard
library lines and one more parameter row in
`tests/test_classify.py::test_every_method_is_named_for_a_reader`. Cost: an
afternoon, no dependency. Best return on the list, because the repository
already built everything that makes a new method safe.

**[mapclassify](https://pysal.org/mapclassify/): publish the goodness of the
fit.** PySAL's classifiers expose how well a partition fits the data, the
goodness of variance fit, so you can tell that natural breaks separated this
dataset and quantiles did not. This package names the method and says nothing
about whether it worked. `scripts/_classify.py` would grow a
`fit_quality(values, breaks) -> float`, the plate's method line would read
`natural breaks (k = 5, fit 0.91)`, and `sprezzature_maps/audit.py` would grow
a rule reporting a chosen method whose fit is far below the best available on
the same data. Cost: fifty lines and one audit rule, no dependency, since the
natural-breaks solver here already computes within-class variance.

**[QGIS](https://qgis.org/) and
[ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview):
the histogram under the breaks.** Both show the data distribution with the
class boundaries drawn on it, in the dialog where the classification is
chosen. The legend code in `scripts/make_choropleth.py` already prints one
swatch per class and the boundary values between them; a
`legend_histogram: true` would add a thin frequency strip under the swatches
with the breaks as ticks, so a reader sees that four of the five classes hold
three countries each. Cost: half a day of drawing, and a layout risk the
repository already has a constant for: `_LEGEND_MAX_WIDTH_FRACTION = 0.38` in
`scripts/make_situation_map.py` exists because a legend card past 38 % of the
map width stops being furniture and becomes an occlusion.

**[Datawrapper](https://www.datawrapper.de/): a description that is not the
title again.** Datawrapper's charts ship a described alternative rather than a
repeated headline. Here every plate opens with `role="img"` and
`aria-labelledby` pointing at a `<title>` and a `<desc>` pair
(`scripts/_svg.py`), and `sprezzature_maps/audit.py` already reports a plate
with no accessible name at all. What it does not catch is the much commoner
failure: a `<desc>` that repeats the `<title>` word for word, which passes
every automated check and tells a screen reader nothing. One rule,
`desc-repeats-title`, plus a generator change that writes the extremes and the
class count into `<desc>` from data the generator is already holding. This is
the half-done case, and those are usually the best buy. Cost: a day.

**[svgis](https://github.com/fitnr/svgis): `--data-fields`, already taken, and
worth finishing.** svgis writes a feature's own fields into `data-*`
attributes so the drawing stays queryable after it is drawn. Control zones and
markers here carry theirs. Choropleth regions do not, which is the layer where
it would matter most: `data-value`, `data-class` and `data-method` on every
country path would let a page extract the table back out of the picture, and
would let `sprezzature_maps/audit.py` check the drawn colours against the
stated breaks instead of trusting the legend text. Cost: an afternoon in
`scripts/make_choropleth.py`, and it closes a loop the audit cannot close
today.

**[FlowmapBlue](https://www.flowmap.blue/) and
[flowmap.gl](https://github.com/visgl/flowmap.gl), by Ilya BOYANDIN: origin to
destination ribbons.** Tapered bands between places, width on a square root
scale so the eye reads area rather than length, with locations clustered as
the reader zooms out. Half the parts are here already: `scripts/_svg.py` has
cubic Bezier flow ribbon paths, used for the situation plate's axes of
advance, and `scripts/_conflict.py` already sizes marks area-true on a square
root for the same perceptual reason. A fourth kind, `make-map flow`, reading a
two column origin and destination CSV, is a real possibility. **Not taken for
now**, and the reason is maintenance rather than difficulty: a fourth
generator is a fourth set of legends, label collisions, scale bars and audit
rules, and the three that exist are the three this package can defend. The
honest statement is that the ribbon geometry exists and the plate kind does
not.

**[Protomaps](https://protomaps.com/) and PMTiles, by Brandon LIU: the whole
basemap as one indexed file.** PMTiles packs an entire tile pyramid into a
single file and serves it with HTTP Range requests, which is how a world
basemap ships with no tile server at all. `assets/geo/` here is 329 MB across
26 vector files and six elevation tiers. **Refused**, and the reason is the
direction of the suite rather than the format: a Range request is a server,
and the property this package sells is that a plate renders from a clone with
the network off. What is worth taking is the smaller half of the same idea,
the manifest: `assets/geo/` has a one line `__init__.py` and no index, so
nothing in the repository states, per file, where it came from, under which
licence, and how many bytes it costs. That file would make the provenance
caption generable instead of written. Cost: an afternoon, and it would be the
cheapest honesty in the repository.

## How the field divides

Most comparisons of mapping tools put everything on one axis and rank it. That
hides the distinction that actually decides anything: **how much of the
drawing does the tool do, and how much do you.**

- A **chart grammar** (Vega-Lite, Altair, Observable Plot) takes a
  specification and a projection name; a runtime decides every mark.
- A **plotting library** (matplotlib with Cartopy, GeoPandas, PyGMT) draws
  into a figure canvas built for statistical plots, with cartography added on
  top.
- A **thematic cartography package** (tmap, mapsf) treats the legend, the
  scale bar and the credits as part of the map. This family is a strong one
  and lives almost entirely in R.
- A **web map** (Leaflet, MapLibre GL JS, OpenLayers, Mapbox GL JS) ships
  tiles and a viewport, and the reader pans and zooms.
- A **GPU visualisation layer** (deck.gl, kepler.gl, pydeck) composites
  millions of rows over one of those viewports.
- A **tile supply** (Protomaps and PMTiles, Tippecanoe, Overture, Natural
  Earth, TopoJSON) is not a drawing tool at all: it is what the drawing tools
  read.
- A **desktop geographic information system** (QGIS, ArcGIS Pro) is software
  an analyst drives to analyse geography, which can also export a map.
- A **hosted editor** (Datawrapper, Flourish, Felt, CARTO) trades control for
  speed and keeps the map on someone else's server.
- An **SVG writer** emits the XML directly. No runtime, no canvas, no
  viewport: the geometry on the page is whatever the code decided to write.

The second division that matters is **when the tool runs**. A static writer
runs once, at authoring time, and the file is the deliverable. A web map runs
on every reader's machine, every time, and the deliverable is a page plus a
tile supply that has to stay up. The 2026 shift in that second family is
worth knowing even if you never go there: Mapbox GL JS stopped being open in
2020, MapLibre became the fork everybody uses, and PMTiles removed the tile
server entirely, so the self-hosted stack is now MapLibre plus a single
Protomaps file.

The third division is **who is allowed to drive**. Datawrapper, Flourish, Felt
and CARTO exist because an editor on deadline is not going to write Python,
and they are genuinely better at that than any library will ever be. Every
library on this page, including this one, is worse on that axis by
construction.

`sprezzature-maps` is in the SVG writer family, and that family is not empty.
Being honest about who else is in it is more useful than claiming the
category.

### The SVG writers, specifically

| Tool | Language | Alive? | Thematic kinds | Projection | Designed plate |
|---|---|---|---|---|---|
| **sprezzature-maps** | Python | yes | choropleth, situation map, density | Equal Earth / auto-centred LCC | legend, scale bar, relief, provenance caption |
| [svgis](https://github.com/fitnr/svgis) | Python | yes (0.6.0, September 2026) | none, geometry styled by CSS class | any EPSG | no |
| [kartograph.py](https://github.com/kartograph/kartograph.py) | Python | **no**, unmaintained, points to mapshaper | choropleth via CSS | several | no |
| [map-generator](https://github.com/schiste/map-generator) | Rust | yes | none | several | no |
| [map-gen](https://github.com/coxmi/map-gen) | JS | low | none | D3 projections | no |
| py-staticmaps | Python | yes (0.5.0) | markers and lines only | Web Mercator (tiles) | no |

The useful reading of that table: the niche has occupants, and what separates
them is not "writes SVG", it is whether the tool has an opinion about the
finished page. svgis is the closest living relative and a good tool. It does
not classify your data, choose a colour scale, place a legend, draw a scale
bar or shade terrain, because that is not what it is for. Kartograph, which
did aim at the designed thematic map, has been unmaintained for years and its
own README sends you to mapshaper.

## How it compares

Twenty-five tools rated 1 to 5 on fourteen criteria, higher is always better
(⭐ weak to ⭐⭐⭐⭐⭐ strongest). A star is a considered judgement, not a
benchmark: nothing here was timed, and where a tool does not do what a
criterion measures at all it scores one star, because on a capability scale
"does not do this" is a 1. Every criterion is oriented so that more stars mean
better, which is why there is no cost column and no install-size column: there
is an openness column and a lightness column instead. The machine-readable
source is [`assets/landscape.csv`](assets/landscape.csv).

| Mapping tool | Publication quality without restyling | Output needs no runtime to view | Selectable text in the output | Projection breadth | Named classification of values | Flow and link maps | Interactivity, zoom and tiles | Large datasets | Open and account-free | Light install | Reproducibility | Accessibility built in | Maturity and ecosystem | Reach for a non-programmer |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| sprezzature-maps | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ |
| svgis | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ |
| D3 + d3-geo | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| Observable Plot | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Vega-Lite / Altair | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| matplotlib + Cartopy | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| GeoPandas | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| PyGMT | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| Folium / Leaflet | ⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| MapLibre GL JS | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| Mapbox GL JS | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| OpenLayers | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| deck.gl | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ |
| kepler.gl | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Plotly maps | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Highmaps | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Datawrapper | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Flourish | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Felt | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| CARTO | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| QGIS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| ArcGIS Pro | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| tmap (R) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| mapsf (R) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ |
| Protomaps / PMTiles | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |

The one-star rows are the ones to read first. **Maturity and ecosystem** is a
single star and should be: this package was published in 2026, it has one
author, and against it sit D3, Leaflet, QGIS and matplotlib, each with twenty
years and tens of thousands of dependants. **Large datasets** is a single
star: the generators walk geometry in Python and write XML, and a million
points is not the shape of problem they are for, where deck.gl and CARTO eat
it. **Interactivity, zoom and tiles** is two stars and that is generous: there
is a fullscreen control and there are tooltips, there is no pan, no zoom and
no tile at any scale. **Reach for a non-programmer** is two stars: there is a
gallery page behind the HTTP surface, and everything real goes through Python,
a command line or a YAML file. **Projection breadth** is two stars against
five for svgis, OpenLayers, Cartopy and QGIS: two projections chosen on
purpose are still two projections, and if your data belongs in a national grid
this is the wrong tool.

### The same table, drawn

![Twenty-five mapping tools positioned on two axes derived from the table above. sprezzature-maps sits alone in the top right corner; mapsf, tmap, PyGMT, svgis and matplotlib with Cartopy run along the top of the figure to its left; deck.gl is diametrically opposite in the bottom left, with kepler.gl, Mapbox GL JS, Felt and CARTO along the bottom; Datawrapper is on the right, level with the horizontal axis. The horizontal axis runs from Robustness on the left to Usability on the right, the vertical from Dynamism at the bottom to Clarity at the top.](assets/landscape.svg)

This page opens by refusing to rank these tools on one axis. A map is the
other half of that refusal: it uses two, and it says how much it leaves out.

The source is [`assets/landscape.csv`](assets/landscape.csv), which is the
star table above and nothing else, transposed. Regenerate with:

```sh
python scripts/landscape_to_csv.py ~/sprezzature-maps/LANDSCAPE.md
standpoint ~/sprezzature-maps/assets/landscape.csv \
  --outdir ~/sprezzature-maps/assets --stem landscape --check
python scripts/date_the_map.py ~/sprezzature-maps/assets/landscape*.svg \
  --asof "October 2026" --source LANDSCAPE.md
```

That third line is not decoration. A figure carrying no vintage trips this
package's own `no-provenance` rule, which exists because a map with no date is
read as current forever. The rule fired on this very figure the first time it
was added, which is the useful way for it to arrive.

`sprezzature-maps` is the first row, and `standpoint` places the first row top
right and orients everything else around it. That is a convention of the
drawing, not a claim about quality.

The geometry is ordinary correlation principal component analysis (PCA) and it
is **deterministic**: the same table gives the same map every run. The four
words at the edges come from a local model, and they are vaguer than what is
behind them, so the loadings are the control. Here they are.

**Horizontal.** Accessibility built in (+0.50), publication quality without
restyling (+0.38), reach for a non-programmer (+0.37) and named
classification of values (+0.33) pull one way; open and account-free (−0.29),
large datasets (−0.28) and maturity and ecosystem (−0.21) pull the other. The
model called the two ends Robustness and Usability. What the numbers oppose
is narrower and more interesting than that: a map built to be read against a
system built to carry load. `sprezzature-maps` is at the far right by
construction, because it is the reference row, and Datawrapper lands on
exactly the same horizontal coordinate, 3.25. That is the map agreeing that a
newsroom tool and this package are after the same thing.

**Vertical.** Output needs no runtime to view (+0.38), reproducibility
(+0.38), selectable text in the output (+0.35), projection breadth (+0.30)
and open and account-free (+0.26) at the top; interactivity, zoom and tiles
(−0.41), large datasets (−0.24), reach for a non-programmer (−0.23) and light
install (−0.22) at the bottom. The model called them Clarity and Dynamism.
This is the file against the service: an artefact you keep versus a thing you
drive, with convenience on the side of the thing you drive. `mapsf` shares the
top coordinate exactly, 3.64; `svgis`, PyGMT and matplotlib with Cartopy sit
just below; deck.gl is diametrically opposite this package and CARTO is at the
floor. Datawrapper is the one tool that scores high on the horizontal and low
on the vertical, which is the whole of what it trades away.

**Two axes carry 56 %** of the table: 36.0 % on the horizontal, 20.2 % on the
vertical. The remaining 44 % is in the table and not on the picture. Two
columns in particular are barely carried by either axis: flow and link maps
(−0.10 and −0.18) and maturity and ecosystem (−0.21 and −0.16). If you came
for either, the map will not answer you and the table will.

The four pole words come from a local model, and it named each language
separately: the English map says Robustness, Usability, Dynamism and Clarity,
the French one says Autonomie, Clarté, Dynamisme and Rigueur. The geometry is
identical in both, and the loadings above are what answers for it.

`standpoint --check` reports the layout as not fully readable: two pairs of
point labels risk overlapping, Vega-Lite / Altair with QGIS, and MapLibre GL
JS with Protomaps / PMTiles. Both pairs are close together because they
genuinely score alike, which is the figure being crowded rather than wrong.

`standpoint` also writes a prose interpretation beside the figure. It is not
reproduced here, because a model reading back ratings somebody wrote is not a
finding, and this file is more useful if the judgements stay visibly mine.

## The conflict-research field, specifically

The table above compares drawing tools. A conflict researcher does not start
by choosing a drawing tool: they start with a dataset, and the dataset is
almost always one of two.

| Dataset | Unit | Where it says it is | When it says it is | Updated |
|---|---|---|---|---|
| [ACLED](https://acleddata.com/methodology/acled-codebook) | one political violence or protest event | `latitude`/`longitude` plus `geo_precision` 1 to 3 | `event_date` plus `time_precision` 1 to 3 | weekly |
| [UCDP GED](https://ucdp.uu.se/downloads/) | one organised violence event with at least one death | `latitude`/`longitude` plus `where_prec` **1 to 7** | `date_start`/`date_end` plus `date_prec` 1 to 5 | yearly |

Both ship a precision code beside every coordinate, and both mean something
specific by it. ACLED's 3 is a provincial capital standing in for a whole
province. UCDP's 6 means only the country is known, and the coordinates are a
representative point for an entire state. **Every tool in this space draws all
of those as the same dot.** `acled` and `acled.api` fetch the rows; `acledR`
and `conflictr` reshape them; GeoPandas, Cartopy and QGIS will put a point
layer on a basemap; Datawrapper will make it pretty. None of them renders a
`geo_precision` 3 differently from a 1, which means every one of those maps
asserts a street corner its source never gave, several hundred times per
figure, without saying so.

That is this project's opening, and the marker layer takes it: a cased disc
for a named location, a hollow ring for an approximate one, a broken ring for
a region pinned to its capital, a drawn radius where the dataset states one,
with the wording taken from ACLED's own codebook. `scripts/_conflict.py` is
the twenty lines between the researcher's file and that marker:

```python
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
```

What the suite still leaves to others, stated as plainly as the rest:

| Need | Here | Where it is better served |
|---|---|---|
| Fetch the data | no | `acled` (PyPI), `acled.api` and `acledR` (CRAN), the UCDP API |
| Filter, aggregate, join to admin units | no | GeoPandas, QGIS |
| Historical borders for a pre-2019 map | yes, `frontiers.source` plus `frontiers.as_of`, nothing vendored | you supply [CShapes 2.0](https://doi.org/10.1177/00220027211013563), which is CC BY-NC-SA and cannot ship inside a BSD package |
| A grid of equal cells for a statistical model | no | [PRIO-GRID](https://doi.org/10.1177/0022343311431287) 0.5° |
| Subnational polygons beyond the bundled tiers | partly (admin-1, admin-2) | geoBoundaries CGAZ, GADM |
| NATO APP-6D unit symbols | no | `milsymbol` (JS), `mil-sym-java`; there is no Python renderer |
| Draw the result as a finished, citable plate | **yes** | |

The last row is the claim. The row above it is the most interesting gap in
the field: the joint military symbology standards have open implementations in
JavaScript, Java, Android and Rust, and none in Python.

## The house position

Own the exact output rather than hand it to a runtime, and pay for that by
writing more of the drawing code. It is the same trade `sprezzature-figures`,
`sprezzature-accessibility` and `sprezzature-ux-laws` make elsewhere in this
suite. It is a bad trade for exploration and a good one for publication.

## Sources

Ratings as of October 2026, from the project documentation and from the
following, read in October 2026:

- [Geospatial stack 2026: PostGIS, MapLibre, Mapbox, deck.gl, kepler.gl, Protomaps, Overture, H3, S2](https://ttlab.hopto.org/blog/culture/2026-05-16-geospatial-stack-2026-postgis-maplibre-mapbox-deckgl-kepler-protomaps-overture-h3-deep-dive?lang=en)
- [Protomaps, the open source map in a file](https://protomaps.com/)
- [deck.gl versus MapLibre, compared](https://atlas.co/comparisons/deck-gl-vs-maplibre/)
- [Best geospatial data visualization tools in 2026](https://atlas.co/blog/best-geospatial-data-visualization-tools-in-2026/)
- [Equal Earth projection, ŠAVRIČ, PATTERSON and JENNY, 2018](https://en.wikipedia.org/wiki/Equal_Earth_projection)
- [Equal Earth in PROJ 9.8](https://proj.org/en/9.8/operations/projections/eqearth.html)
- [Choropleth maps, a guide to data classification](https://gisgeography.com/choropleth-maps-data-classification/)
- [tmap 4.4 on CRAN](https://cran.r-project.org/package=tmap) and [mapsf 1.3 on CRAN](https://cran.r-project.org/package=mapsf)
- [kepler.gl under OpenJS Foundation governance](https://opensource.foursquare.com/kepler-gl/)
- [FlowmapBlue](https://www.flowmap.blue/)
- [ADA accessibility requirements for government maps, April 2026 deadline](https://dymaptic.com/blog/the-clock-is-ticking)
- [GeoLinter, a linting framework for choropleth maps](https://arxiv.org/pdf/2310.13707)
