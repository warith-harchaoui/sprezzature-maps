# sprezzature-maps

This library draws maps as SVG (Scalable Vector Graphics, an image format
built from lines and shapes described in text rather than a grid of
pixels, so it stays sharp at any zoom and its labels stay selectable
text). Every line is written by hand, by our own drawing code: nothing
here goes through Vega (a JSON-based charting engine) or matplotlib
(Python's classic plotting library). `sprezzature-maps` used to be part
of [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures);
it was split out as its own product, with its own release schedule and,
eventually, its own visual editor.

Part of the [sprezzature](https://harchaoui.org/warith/sprezzature/) suite.

---

## What's here

Two generators. Both draw on a real base map with a real geographic
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

## Install (local, pre-PyPI)

Neither `sprezzature-maps` nor `sprezzature-figures` is published on PyPI
(the Python Package Index, the standard `pip install <name>` registry)
yet. Install both editable, side by side, so local edits to either take
effect immediately without reinstalling:

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps ~/sprezzature-maps
pip install -e ~/sprezzature-maps
```

`sprezzature-maps` depends on `sprezzature-figures` for rendering
primitives the two products share (embedding fonts inside the SVG file
so it looks the same on a machine without those fonts installed, and
choosing between a self-contained SVG and one that links to external
files). It reuses that code rather than keeping its own copy.

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

See [`EXAMPLES.md`](EXAMPLES.md) for more recipes, including the HTTP API.
See [`doc/CARTOGRAPHY.tex`](doc/CARTOGRAPHY.tex) for the full method
behind every projection, colour scale, and relief (shaded-terrain)
technique this repo uses: the underlying maths, TikZ diagrams, citations,
and print-resolution figures, compiled with `xelatex`/`biber` (LaTeX's
Unicode-aware typesetter and its bibliography tool) into
[`doc/CARTOGRAPHY.pdf`](doc/CARTOGRAPHY.pdf).

## Why a separate repo, not a chart type in sprezzature-figures

Both generators used to sit inside `sprezzature-figures`' catalogue of
126 chart kinds. Splitting them out was a deliberate product decision:
Sprezzature Studio, the conversational chart editor that ships with
`sprezzature-figures`, will not grow map support. Maps get their own,
separate Studio once that is built. Until then, this repo is library and
command line only, with no editor UI.

## Status

Early. Freshly extracted from `sprezzature-figures` and smoke-tested:
`pytest` passes, both kinds render from their bundled demo data, and the
command line renders both kinds to real SVG files. There is no continuous
integration yet, no PyPI release yet, and no FIGURES.md-style catalogue
page yet (with only two kinds so far, this README is the catalogue).

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
showing how quickly the sea floor drops off; and, new, an automatic
choice between the coarser and finer Natural Earth detail level
depending on how zoomed-in the requested region is.

The library is reachable four ways: as a Python import, as an argparse
(Python's standard command-line-parsing library) command line, `make-map`,
installed by default; as an HTTP API (`sprezzature-maps[api]`) that
publishes an OpenAPI schema (a machine-readable description of every
endpoint, letting other tools generate documentation or client code
automatically) and a small gallery page at its root; and, coming next, a
Click-based command line and an MCP surface (Model Context Protocol, the
standard that lets an AI assistant call a tool directly) under
`sprezzature-maps[cli]` / `[mcp]`.

## Roadmap

Add shaded relief to `situation_map`'s Lambert conformal conic projection
too: the same technique `choropleth` already has, reworked for a
different projection's inverse (the maths that goes from a flat map
position back to a real latitude and longitude). A few lower-priority
items from the full cartography plan are tracked but not scheduled yet:
relief built from the ETOPO global elevation dataset, alternate
projections better suited to editorial maps (Robinson, Mollweide), and a
single shared reader for the TopoJSON format (a compact way of storing
map boundaries that records each shared border only once, instead of
once per neighbouring country).

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

## License

BSD-3-Clause.

## Author

[Warith Harchaoui, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)
