# sprezzature-maps

[🇫🇷 LISEZMOI.md](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/LISEZMOI.md) · 🇬🇧 README.md

This library draws maps as SVG (Scalable Vector Graphics, an image format
built from lines and shapes described in text rather than a grid of
pixels, so it stays sharp at any zoom and its labels stay selectable
text). Every line is written by hand, by our own drawing code: no
charting library sits underneath it. `sprezzature-maps` used to be part
of [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures);
it was split out as its own product, with its own release schedule and,
eventually, its own visual editor.

Part of the [sprezzature](https://harchaoui.org/warith/sprezzature/) suite.

---

## What's here

Three generators. Two draw on a real base map with a real geographic
projection (a projection is the mathematical recipe that flattens the
round Earth onto a flat image; every recipe distorts something, and the
choice of recipe below is deliberate). That sets them apart from the
schematic, binned map types that stayed behind in `sprezzature-figures`
(`binned-grid-map`, `dotdensity`, `hexbin-map`, `hexmap`, `spike-map`),
which plot points or grid cells rather than real coastlines:

| Kind | Script | What it draws |
|---|---|---|
| `choropleth` (a map where each region is filled with a colour that encodes a number, the classic "which country scores highest" map) | `scripts/make_choropleth.py` | A world map, one fill colour per country on a single pale-to-navy blue scale; countries with no data fall back to neutral grey. |
| `situation_map` | `scripts/make_situation_map.py` | A layered "who controls what" plate for any region: the map auto-centres itself on that region using a Lambert conformal conic projection (see below), draws real national outlines from a bundled Natural Earth base map, shades the sea floor near the coast, fills zones by category in pastel colours, marks flashpoints, and adds a scale bar in two units at once (kilometres and miles). |
| `density` (an accumulation map: where events *fell*, rather than a value per territory) | `scripts/make_density.py` | No coastline, no border, no graticule. Point events are binned into a luminous field; the land appears because events fell on it and the sea stays dark because none did, so a reader recognises the shape without being shown it. Vector, binned, one path per level. |

## Install

```bash
pip install sprezzature-maps                 # the three generators
pip install 'sprezzature-maps[api,mcp]'      # plus the HTTP API and the MCP server
```

`sprezzature-maps` depends on `sprezzature-figures` for rendering primitives
the two products share (embedding fonts inside the SVG file so it looks the
same on a machine without those fonts installed, and choosing between a
self-contained SVG and one that links to external files). It reuses that code
rather than keeping its own copy, and pip pulls it in for you.

To work on either, install both editable side by side so local edits take
effect without reinstalling:

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps ~/sprezzature-maps
pip install -e ~/sprezzature-maps
```

## Use

```python
from sprezzature_maps import make_choropleth, make_situation_map

make_choropleth(out="world.svg")          # demo data if none supplied
make_situation_map(out="region.svg")      # bundled demo config
```

```bash
make-map choropleth --out world.svg
make-map situation_map --config my-region.yaml --out region.svg
```

See [`EXAMPLES.md`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/EXAMPLES.md) for more recipes, including the HTTP API.
See [`doc/CARTOGRAPHY.tex`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/doc/CARTOGRAPHY.tex) for the full method
behind every projection, colour scale, and relief (shaded-terrain)
technique this repo uses: the underlying maths, TikZ diagrams, citations,
and print-resolution figures, compiled with `xelatex`/`biber` (LaTeX's
Unicode-aware typesetter and its bibliography tool) into
[`doc/CARTOGRAPHY.pdf`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/doc/CARTOGRAPHY.pdf).

## Why a separate repo, not a chart type in sprezzature-figures

`choropleth` and `situation_map` used to sit inside `sprezzature-figures`'
catalogue of 126 chart kinds (`density` was born here, after the split).
Splitting them out was a deliberate product decision:
Sprezzature Studio, the conversational chart editor that ships with
`sprezzature-figures`, will not grow map support. Maps get their own,
separate Studio once that is built. Until then, this repo is library and
command line only, with no editor UI.

## Status

Published on PyPI ([`sprezzature-maps`](https://pypi.org/project/sprezzature-maps/)),
with a green CI workflow (lint, tests, and doctests on every push and pull
request to `main`; see `.github/workflows/ci.yml`): `pytest` passes, all
three kinds render from their bundled demo data, and both command lines
render them to real SVG files. Still early — the API is not frozen, and
there is no FIGURES.md-style catalogue page yet (with three kinds, this
README is the catalogue).

Five worked situation maps live in `scripts/build_situation_examples.py`,
regenerated with `python scripts/build_situation_examples.py`: Ukraine,
Syria and Libya as historical snapshots, and Sudan and eastern DRC drawn
from open-source reporting to late September 2026. Each is schematic by
construction, says so on the plate, and keeps its claim lines in readable
Python rather than an opaque data file, so a reader who disagrees can see
exactly which coordinates to argue with.

`choropleth` draws with: an Equal Earth projection (a projection that
keeps every country's true relative area, so a huge but visually
flattened landmass like Greenland or Russia is not exaggerated the way
it is on a classic Mercator map); Natural Earth country borders at
1:50,000,000 scale (a level of simplification suited to a whole-world
view, coarser than the 1:10,000,000 detail used for a single region);
a colour scale computed in the OKLCH colour space (a way of describing
colour, chosen here because equal steps in OKLCH look like equal steps
in perceived brightness, so the scale still reads correctly to someone
who cannot distinguish red from green, the most common form of colour
blindness) for values that only go up, plus a second, automatically
chosen "diverging" scale (two colours pulling away from a neutral middle,
for values that can be either above or below some reference point) when
the data calls for it; a 30-degree latitude/longitude grid; a legend
showing the minimum, median, and maximum; hover tooltips that add each
country's rank and share of the total; and a shaded-relief image of
Earth's terrain, reprojected to match, sitting under the country fills.
`situation_map` draws with: an auto-centred Lambert conformal conic
projection (a projection that keeps local shapes and angles correct
around a chosen centre, the standard choice for a single country or
region rather than the whole globe); a shaded band along the coast
showing how quickly the sea floor drops off; an automatic choice between
the coarser and finer Natural Earth detail level depending on how
zoomed-in the requested region is; inland lakes drawn as water rather
than land (the coastline data knows only land and ocean, so before this
Lake Kivu, Lake Chad and the Dnieper reservoirs were all painted as dry
ground) — with `lakes.former` for water that has since gone, because a
vendored basemap has a capture date a dated map can contradict: the
Ukraine example draws the Kakhovka Reservoir as a dashed, unfilled
outline, it having drained after the dam breach of 6 June 2023; and
**axes of advance** — tapered, cased arrows along a smooth
curve, solid for an assessed movement and drawn as an outline for a
reported one, the element that separates a map of where the line *is*
from a map of where it is *going*:

```yaml
arrows:
  - line: [[30.45, 13.05], [29.55, 14.05], [29.05, 14.45]]
    color: "#2f5d92"
    label: "SAF advance"
  - line: [[34.02, 10.00], [34.12, 10.95]]
    style: dashed          # reported, not assessed
    label: "SPLM-N (reported)"
```

Like the other two kinds, the plate now opens with an accessible root
(`role="img"` wired to a `<title>`/`<desc>` pair), and its description
names the classes drawn and repeats the caveat the caption carries: the
map draws the assessment it was given and does not verify it.

The library is reachable five ways: as a Python import; as an argparse
(Python's standard command-line-parsing library) command line, `make-map`,
installed by default; as a richer Click-based command line,
`sprezzature-maps` (`sprezzature-maps[cli]`), which adds CSV ingestion and
column mapping on top of what `make-map` reads; as an HTTP API
(`sprezzature-maps[api]`) that publishes an OpenAPI schema (a
machine-readable description of every endpoint, letting other tools
generate documentation or client code automatically) and a small gallery
page at its root; and as an MCP surface (Model Context Protocol, the
standard that lets an AI assistant call a tool directly) under
`sprezzature-maps[api,mcp]`.

## Roadmap

`situation_map` already shades real elevation onto its Lambert conformal
conic projection, on by default (`scripts/make_situation_map.py`'s
`_relief_layer`), the same terrain-shading technique `choropleth` uses
for the whole-world Equal Earth view, reworked for the region-scale
projection's own analytic inverse. A few lower-priority items from the
full cartography plan are tracked but not scheduled yet: relief built
from the ETOPO global elevation dataset, alternate projections better
suited to editorial maps (Robinson, Mollweide), and a single shared
reader for the TopoJSON format (a compact way of storing map boundaries
that records each shared border only once, instead of once per
neighbouring country).

## Data credits

The code is BSD-3-Clause (see below). The geographic data bundled under
`assets/geo/` carries its own, separate licences; the full list with
sources is in `doc/CARTOGRAPHY.tex`, § Data provenance and licensing.
Most of it (Natural Earth, the USGS/NGA's GMTED2010 elevation dataset,
the U.S. Census Bureau's TIGER/Line boundaries) is public domain and
needs no credit. Two sources do:

- France's region and department boundaries: © IGN (France's national
  mapping agency), ADMIN EXPRESS dataset, via the
  [`gregoiredavid/france-geojson`](https://github.com/gregoiredavid/france-geojson)
  mirror, under the Licence Ouverte / Etalab 2.0
  (France's official open-data licence).
- Switzerland, Germany, and Italy's first-level administrative
  boundaries (regions, cantons, Länder): ©
  [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors,
  under ODbL 1.0 (the Open Database Licence).

  Whenever `situation_map` draws using either of these sources, it adds
  the required credit line to the map itself automatically; see
  `_attribution_layer` in `scripts/make_situation_map.py`.

### Credited as a courtesy, not as an obligation

Nothing below is bundled here and none of it requires a credit. It is named
because the work borrowed from it, and saying so costs nothing.

The night plate, the tapered rivers, the accumulation field and the
scrolling story are all forms taken from [mapped.earth](https://mapped.earth)
(Aaron J. BECKER), which does them better than this does. The datasets those
maps are built on, in case you want the real thing rather than our synthetic
demonstrations:

- **Lightning**: NOAA's GOES Geostationary Lightning Mapper over the
  Americas, EUMETSAT's Meteosat Lightning Imager over Europe and Africa,
  and national ground networks. `make_density.py` ships synthetic points and
  says so on the plate; it has never seen a real flash.
- **River discharge**: [GloFAS v4](https://global-flood.emergency.copernicus.eu/)
  (Copernicus Emergency Management Service) on the
  [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers) network.
  Our `rivers.width: ranked` sizes by Natural Earth's `scalerank`, a
  cartographic prominence rank, **not** by discharge — which is why it is
  not called hydraulic width.
- **River basins**: [HydroSHEDS / BasinATLAS](https://www.hydrosheds.org/hydroatlas),
  CC-BY 4.0.
- **Water temperature**: DynQual 1980–2019 climatology.

## License

BSD-3-Clause.

## Author

[Warith HARCHAOUI, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)
