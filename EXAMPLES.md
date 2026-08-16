# Examples

Practical, runnable recipes for `sprezzature-maps`. See [`README.md`](README.md)
for install instructions.

This file grows alongside the project's surfaces (the Python library, the
command-line tools, the HTTP API, the Model Context Protocol or MCP
integration that lets an AI assistant call these tools directly, the
browser GUI). It is not written once and left as-is: expect new sections
as those surfaces land. The two example images below are not hand-picked
screenshots; they are the actual output of `make_choropleth()` and
`make_situation_map()` called with no arguments, regenerated regularly
and stored under `assets/svg-examples/`, so they can never silently drift
from what the code in this repo actually produces.

### `choropleth`

<img src="assets/svg-examples/choropleth.svg" alt="Choropleth demo: a world map shaded by a synthetic global exposure index, Equal Earth projection, OKLCH blue ramp, hillshade relief." width="700">

### `situation_map`

<img src="assets/svg-examples/situation_map.svg" alt="Situation map demo: Western Europe, real coastlines and borders, bathymetry halo, country labels, dual-unit scale bar." width="700">

## Python library

```python
from sprezzature_maps import make_choropleth, make_situation_map

# Demo data if none supplied.
make_choropleth(out="world.svg")
print("wrote world.svg")
# wrote world.svg

# Your own per-country data. "id" is the country's ISO-3166-1 numeric
# code (a 3-digit code every country has under the ISO 3166 standard,
# e.g. "840" for the United States, "124" for Canada).
make_choropleth(
    data=[{"id": "840", "value": 12.5}, {"id": "124", "value": -3.2}],
    title="Something, by country",
    out="custom.svg",
)

# A diverging colour scale (two colours pulling away from a neutral
# middle, for values that can be negative or positive) is picked
# automatically when the data spans both signs, as in the example above.
# Force it explicitly with diverging=True/False to override that.
make_choropleth(data=[...], diverging=True, out="growth.svg")

# The bundled Western-Europe demo config.
make_situation_map(out="region.svg")

# Your own region: a YAML config file (YAML is a human-readable text
# format for structured data, easier to hand-edit than JSON) loaded and
# passed in as a Python dict. See scripts/make_situation_map.py's module
# docstring for the full list of fields it accepts.
import yaml
config = yaml.safe_load(open("my-region.yaml"))
make_situation_map(config=config, out="region.svg")
```

## Command line (`make-map`)

Built with argparse, Python's standard library for parsing command-line
flags; this CLI is always installed, no extra to add.

```bash
# Demo data, default output path.
make-map choropleth --out world.svg

# Your own data (JSON file: a list of {"id": ..., "value": ...} rows).
make-map choropleth --data my-data.json --out world.svg --title "My indicator"

# A region config.
make-map situation_map --config my-region.yaml --out region.svg
```

## HTTP API (`sprezzature-maps[api]`)

```bash
pip install 'sprezzature-maps[api]'
# uvicorn is the server that actually runs the API code and listens for
# requests; --reload restarts it automatically whenever a source file
# changes, handy while developing.
uvicorn sprezzature_maps.api:app --reload
```

```bash
# Demo choropleth as SVG.
curl -X POST http://localhost:8000/v1/choropleth -o choropleth.svg

# Your own data, as PNG.
curl -X POST http://localhost:8000/v1/choropleth \
  -H "Content-Type: application/json" \
  -d '{"data": [{"id": "840", "value": 12.5}, {"id": "124", "value": -3.2}], "format": "png"}' \
  -o choropleth.png

# Demo situation map.
curl -X POST http://localhost:8000/v1/situation-map -o situation_map.svg

# Discover the two kinds programmatically instead of hardcoding them.
curl http://localhost:8000/v1/kinds
# ["choropleth", "situation_map"]

# Interactive docs: a page generated automatically from the API's
# OpenAPI schema, letting you try each endpoint from the browser
# (this particular UI for it is called Swagger UI). And the GUI gallery.
open http://localhost:8000/docs
open http://localhost:8000/
```

## Command line (`sprezzature-maps[cli]`)

A richer twin of `make-map`, built with Click (another Python
command-line library, one that makes subcommands like `sprezzature-maps
choropleth` easy to define). It reads CSV/TSV/JSONL files directly
(comma-separated, tab-separated, or one-JSON-object-per-line, not just a
pre-shaped JSON array) and accepts `--map role=column` bindings for a
file whose columns aren't already named `id`/`value`.

```bash
pip install 'sprezzature-maps[cli]'

sprezzature-maps list
# choropleth
# situation_map

# A CSV with your own column names, bound explicitly.
sprezzature-maps choropleth \
  --data my-data.csv --map id=CountryCode --map value=Score \
  --out world.svg --title "My indicator"

# Force the diverging ramp off even though the data has both signs.
sprezzature-maps choropleth --data my-data.csv --no-diverging --out world.svg

# Read the CSV from standard input (stdin: whatever another command
# pipes in, here via "|") instead of from a named file, using "-" in
# place of a path.
cat my-data.csv | sprezzature-maps choropleth --data - --out world.svg

sprezzature-maps situation-map --config my-region.yaml --out region.svg
```

## MCP (`sprezzature-maps[api,mcp]`)

MCP, the Model Context Protocol, is the standard that lets an AI
assistant call a tool directly instead of a human typing a command. This
extra exposes the same HTTP routes as MCP tools (`list_kinds`,
`render_choropleth`, `render_situation_map`) for any MCP-aware assistant
to call.

```bash
pip install 'sprezzature-maps[api,mcp]'
sprezzature-maps-mcp
# MCP endpoint at http://localhost:8000/mcp,
# alongside the regular HTTP routes and the GUI at http://localhost:8000/
```

Point an MCP client's server configuration at that URL. The tool
descriptions it advertises come straight from the FastAPI (the Python
web framework this API is built with) route docstrings in
`sprezzature_maps/api.py`, so they stay in sync with the HTTP API
automatically, with nothing to update by hand in two places.
