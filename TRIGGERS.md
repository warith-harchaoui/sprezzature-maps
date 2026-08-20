# Triggers

Natural-language phrases that invoke the sprezzature-maps skill.

## Direct invocations

- "Draw a choropleth map"
- "Make a world map shaded by [indicator]"
- "Draw a situation map for [region]"
- "Make an areas-of-control map"
- "Render a map with country boundaries"
- "Draw a map with real coastlines, not a schematic"
- "Add a scale bar / north arrow / bathymetry to this map"
- "Show sub-national boundaries (states, regions, departments) on this map"
- "Run make_choropleth.py / make_situation_map.py"

## Intent-based phrases

- "Which country scores highest on [metric]?" (choropleth)
- "Show who controls what in [country/region]"
- "I need a real basemap, not a binned grid or hexmap"
- "Map this per-country data"
- "Draw front lines / contested zones / occupied territory"
- "Add shaded relief / terrain / hillshade to this map"

## File patterns

Files matching `*.svg` under `assets/svg-examples/`, or a YAML region
config passed to `situation_map`, routed to this skill when a real
geographic basemap (not a schematic point/grid map) is needed.

## Related scripts

- `scripts/make_choropleth.py`: world choropleth generator
- `scripts/make_situation_map.py`: layered areas-of-control generator
- `scripts/_geo_colors.py`, `scripts/_relief.py`, `scripts/_svg.py`,
  `scripts/_render.py`, `scripts/_interactive.py`: shared primitives

## Related surfaces

- `sprezzature_maps/api.py`: HTTP API, also serves the GUI gallery at `/`
- `sprezzature_maps/cli_click.py`: CSV-ingesting `sprezzature-maps` CLI
- `sprezzature_maps/mcp.py`: MCP tools for an AI assistant to call directly

## Related reference

- `doc/CARTOGRAPHY.tex` / `doc/CARTOGRAPHY.pdf`: the full method behind
  every projection, colour scale, and relief technique this repo uses.
