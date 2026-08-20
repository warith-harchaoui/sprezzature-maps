# Landscape

Tools that draw a real geographic map split by how much of the
rendering pipeline they own. A **grammar-driven** tool (Vega-Lite,
D3 with a projection library) takes a data specification and a
projection name, and a runtime turns that into pixels; the runtime
owns every drawing decision. A **desktop GIS** tool (QGIS) is
interactive software built for an analyst to explore data, not for a
script to call unattended. A **hosted no-code** tool (Datawrapper,
Flourish) trades control for speed: pick a template, upload data, done,
with the map living on someone else's server. `sprezzature-maps` is a
fourth kind: a small Python library that writes the SVG's XML text
directly, no chart-grammar runtime, no browser, no account, so the exact
geometry on the page is whatever this repo's own code decided to draw.

## Tool comparison

| Tool | Type | Runtime needed | Real (non-schematic) basemap | Self-hosted | Python |
|---|---|---|---|---|---|
| **sprezzature-maps** | Hand-authored SVG | No | Yes (Equal Earth, LCC) | Yes | Yes |
| Vega-Lite `geoshape` | Chart grammar | JS (or `vl-convert` headless) | Yes | Yes | Via `altair` |
| D3.js + a projection library | Chart grammar, lower-level | JS | Yes (any D3 projection) | Yes | No |
| matplotlib + cartopy/geopandas | Plotting library | No (pure Python) | Yes | Yes | Yes |
| deck.gl / kepler.gl | WebGL data-viz | JS, browser/WebGL | Yes (tile-based) | Yes | Via `pydeck` |
| Folium / Leaflet | Interactive web map | JS, browser | Yes (tile-based) | Yes | Yes (`folium`) |
| Datawrapper / Flourish | Hosted no-code | None (SaaS) | Yes | No | No |
| QGIS | Desktop GIS | Desktop app | Yes | Yes | Scriptable (PyQGIS) |

### Ratings

| Dimension | sprezzature-maps | Vega-Lite | matplotlib+cartopy | Folium/deck.gl | Datawrapper |
|---|---|---|---|---|---|
| Zero-runtime rendering | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | N/A |
| Output file size (static SVG) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ (HTML+JS) | N/A |
| Interactive pan/zoom | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Projection accuracy control | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ (Web Mercator only) | ⭐⭐ |
| Design control (typography, palette, legend) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Time to first map | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## When to use what

Use `sprezzature-maps` when the map is a static (or CSS/JS-light
interactive) figure that has to look intentionally designed, ship as a
single self-contained SVG file with no runtime dependency at view time,
and stay geographically honest: Equal Earth for the world view keeps
country area proportional (unlike the Web Mercator every tile-based
tool below defaults to, which inflates high-latitude countries),
Lambert conformal conic for a regional view keeps local shapes and
angles true. This is the same trade-off `sprezzature-accessibility` and
`sprezzature-ux-laws` make elsewhere in this suite: own the exact
output rather than hand it to a runtime, at the cost of writing more of
the drawing code by hand.

Vega-Lite's `geoshape` mark is the right call when the map is one chart
type among several a data analyst is already producing in the same
grammar, and browser-side interactivity (brushing, linked views) matters
more than pixel-level control over the output file.

matplotlib with cartopy or geopandas is the right call for exploratory,
throwaway geographic plots inside a notebook, or when the map needs to
sit alongside statistical plots from the same library in one figure.
It is not built to emit a polished, publication-styled SVG without
substantial manual styling.

deck.gl, kepler.gl, and Folium/Leaflet own the interactive-web-map
niche this repo deliberately does not compete in: real pan, zoom, and
tile-based basemaps at every scale. Reach for one of them when the
deliverable is a page a user explores, not a figure a reader looks at.

Datawrapper and Flourish are the fastest path from a spreadsheet to a
published map when self-hosting, offline rendering, and exact design
control do not matter as much as speed and a non-technical editing
workflow.

QGIS is a full desktop GIS: the right tool for actually analysing
geographic data (spatial joins, buffer analysis, coordinate-system
conversion), not for scripting a repeatable figure. `sprezzature-maps`
assumes the geographic analysis is already done; it only draws the
result.
