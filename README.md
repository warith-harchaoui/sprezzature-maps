# sprezzature-maps

Hand-authored SVG world maps — no Vega, no matplotlib — split out of
[sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures)
as an independent product with its own release cycle and, eventually, its
own Studio.

Part of the [sprezzature](https://harchaoui.org/warith/sprezzature/) suite.

---

## What's here

Two generators, both real-basemap, real-projection maps (as opposed to the
schematic/binned geospatial types that stayed in `sprezzature-figures`:
`binned-grid-map`, `dotdensity`, `hexbin-map`, `hexmap`, `spike-map`):

| Kind | Script | What it draws |
|---|---|---|
| `choropleth` | `scripts/make_choropleth.py` | World map, per-country fill on a single pale-to-navy blue ramp; no-data countries fall back to neutral grey. |
| `situation_map` | `scripts/make_situation_map.py` | Layered areas-of-control plate for any region: auto-centred Lambert conformal conic projection, real national outlines from a vendored Natural Earth basemap, bathymetry contours, classed pastel fills, flashpoint markers, dual-unit scale bar. |

## Install (local, pre-PyPI)

Neither `sprezzature-maps` nor `sprezzature-figures` is published on PyPI
yet. Install both editable, side by side:

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps ~/sprezzature-maps
pip install -e ~/sprezzature-maps
```

`sprezzature-maps` depends on `sprezzature-figures` for shared rendering
primitives (font embedding, self-contained-vs-linked SVG modes) — it does
not duplicate that logic.

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
See [`doc/CARTOGRAPHY.tex`](doc/CARTOGRAPHY.tex) for the methodology
behind every projection, color ramp, and relief technique this repo
draws with (math, TikZ diagrams, citations, print-resolution figures),
compiled with `xelatex`/`biber` to [`doc/CARTOGRAPHY.pdf`](doc/CARTOGRAPHY.pdf).

## Why a separate repo, not a chart type in sprezzature-figures

Both generators used to live in `sprezzature-figures`' 126-kind catalogue.
Splitting them out was a deliberate product decision: Sprezzature Studio
(the `sprezzature-figures` conversational editor) will not grow map
support — maps get their own, separate Studio when that's built. Until
then, this repo is library + CLI only.

## Status

Early — freshly extracted, smoke-tested (`pytest`, both kinds render from
demo data; the CLI renders both kinds to real SVG files). No CI yet, no
PyPI release yet, no FIGURES.md-style catalogue doc yet (only two kinds,
this README is the catalogue for now).

`choropleth` carries: an Equal Earth (equal-area) projection, 50m Natural
Earth borders, an OKLCH-interpolated sequential ramp plus an
auto-detecting diverging ramp (both verified colour-vision-deficiency-safe,
not just asserted), a 30-degree graticule, a legend with min/median/max,
tooltips enriched with rank and share of total, and a reprojected Natural
Earth hillshade composited under the vector layers. `situation_map`
carries: an auto-centred Lambert Conformal Conic projection, a bathymetry
halo, and (new) an automatic 10m-vs-50m basemap tier keyed to the region's
zoom level.

Surfaces: Python library, an argparse CLI (`make-map`, always installed),
an HTTP API (`sprezzature-maps[api]`) with an OpenAPI schema and a small
GUI gallery page at its root. A Click CLI and an MCP surface
(`sprezzature-maps[cli]` / `[mcp]`) are next.

## Roadmap

Relief/hillshade for `situation_map`'s Lambert Conformal Conic projection
(the same technique `choropleth` already has, ported to a different
projection's inverse). Optional, lower-priority items from the full
cartography plan (ETOPO-based hypsometric relief, alternate editorial
projections like Robinson/Mollweide, a shared TopoJSON decoder) are
tracked but not scheduled.

## License

BSD-3-Clause.

## Author

[Warith Harchaoui, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)
