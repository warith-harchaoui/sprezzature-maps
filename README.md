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

Part of the [sprezzature](https://sprezzature.ai/) suite.

---

## How it works

![Flow diagram. At the top, a value per region, point events or a plate configuration feed two lanes. The left lane draws: it centres and projects on a real base map, classifies the values and names the method used, and draws one of three plates, returning an SVG, with a scale bar in two units on a regional plate. The right lane audits: eleven static rules read the rendered plate back and ask whether it names its classification, prints its breaks, says when it was true and can be read word by word. Both meet in one outcome, a plate a reader can argue with.](https://raw.githubusercontent.com/warith-harchaoui/sprezzature-maps/main/assets/how-it-works.svg)

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
| `choropleth` (a map where each region is filled with a colour that encodes a number, the classic "which country scores highest" map) | `scripts/make_choropleth.py` | A world map, one fill colour per country on a pale-to-navy blue scale, or on a diverging scale when the values change sign; countries with no data fall back to neutral grey. |
| `situation_map` | `scripts/make_situation_map.py` | A layered "who controls what" plate for any region: the map auto-centres itself on that region using a Lambert conformal conic projection (see below), draws real national outlines from a bundled Natural Earth base map, shades the sea floor near the coast, fills zones by category in pastel colours, marks flashpoints, and adds a scale bar in two units at once (kilometres and miles). |
| `density` (an accumulation map: where events *fell*, rather than a value per territory) | `scripts/make_density.py` | No coastline, no border, no graticule. Point events are binned into a luminous field; the land appears because events fell on it and the sea stays dark because none did, so a reader recognises the shape without being shown it. Vector, binned, one path per level. |

## Install

```bash
pip install sprezzature-maps
```

One line, and it is everything: the three generators, the library, the
command line, the HTTP API, the MCP server and the Studio. There are no
feature extras. `[dev]` holds the test toolchain (pytest, ruff, mypy and
the rest) and adds no feature. Python 3.10 to 3.13.

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
from sprezzature_maps import make_choropleth, make_density, make_situation_map

make_choropleth(out="world.svg")          # demo data if none supplied
make_situation_map(out="region.svg")      # bundled demo config
make_density(out="where.svg")             # synthetic demo points
```

```bash
make-map choropleth --out world.svg
make-map situation_map --config my-region.yaml --out region.svg
make-map density --points events.json --out where.svg
```

Starting a new regional plate is one command, and what it writes already
carries the furniture a plate owes a reader:

```bash
make-map situation-new --country Moldova --out moldova.yaml
make-map situation_map --config moldova.yaml --out moldova.svg
make-map audit moldova.svg          # clean, as written
```

The output format follows the extension of `--out`: `.svg`, `.png`, `.jpg`,
`.pdf`, `.eps`, or `.html` (the SVG inside a minimal page). Without `--out`
(or `out=` in Python), `choropleth`, `density` and `situation-map` write
`choropleth.svg`, `density.svg` or `situation_map.svg` in the current
directory; they never write over the package's own examples.
`make-map -V` (or `--version`) prints the installed version.

## Five ways in

One engine, reached five ways. All five install with the package, and every
one of them calls the same library functions.

### 1. The Python library

`import sprezzature_maps` exports:

| Name | What it does |
|---|---|
| `make_choropleth`, `make_situation_map`, `make_density` | Render one plate and return the path written |
| `classification_methods()` | The class-break methods a choropleth accepts: `quantile`, `equal`, `jenks`, `headtail` |
| `acled_events`, `ucdp_events` | Turn an ACLED or UCDP GED export into a situation-map config fragment |
| `article_sidecar(svg)` | Read back the title, alt text, description, zones, markers and numbered callouts of a finished plate |
| `plate_provenance(svg)`, `replay_report(svg, cfg, files)` | Read a plate's provenance stamp, and check whether a config and files are what drew it |
| `KINDS`, `MapKind`, `kind`, `kind_names` | The registry of the three map kinds that every surface reads |

### 2. The command line

Built with Click, a Python library for command-line tools with
sub-commands. It answers to two names, `sprezzature-maps` and `make-map`,
which point at the same function. Two sub-commands also take two
spellings: `situation-map` or `situation_map`, and `situation-new` or
`situation_new`. Until 2026-10-25 there were two separate commands, an
argparse one and a richer Click twin behind a `[cli]` extra, which is why
older notes count differently.

| Sub-command | What it does | Main options |
|---|---|---|
| `list` | Print the three map kinds | none |
| `choropleth` | Render a world choropleth | `--data` (CSV, TSV, JSON or JSONL; `-` reads CSV from stdin), `--map id=COL --map value=COL`, `--classes 2..12`, `--method`, `--diverging/--no-diverging`, `--relief/--no-relief`, `--simplify`, `--title`, `--out` |
| `situation-map` | Render a situation map from a YAML config | `--config`, `--title`, `--out` |
| `situation-new` | Write a starter config for a new situation plate | `--country` or `--bbox west,south,east,north`, `--title`, `--subtitle`, `--as-of YYYY-MM-DD`, `--out` |
| `density` | Render an accumulation map | `--points` (JSON list of `[lon, lat]`), `--bins`, `--title`, `--out` |
| `audit` | Check that a finished plate says how it was made | `TARGET` (a file or a folder), `--format text\|json` |
| `improve` | Render a map, read it with a vision model, apply only the safe repairs | `--kind`, `--data` / `--config` / `--points`, `--map`, `--out` (a `.png`), `--title`, `--rounds` |

`improve` needs a local vision model. It never changes the classification
method, the number of classes or the frame on its own: it prints those for
a person to decide.

The library and the HTTP API take options the command line does not
expose, such as `breaks`, `cities`, `rivers`, `width` and `height` for a
choropleth, or `bbox`, `width` and `caption` for a density map.

### 3. The HTTP API, with Docker and compose

FastAPI, a Python web framework, serves the generators over HTTP:

```bash
uvicorn sprezzature_maps.api:app --host 127.0.0.1 --port 8000
```

| Route | operation_id | What it does |
|---|---|---|
| `GET /health` | `health` | Liveness probe, returns `{"status": "ok"}` |
| `GET /v1/kinds` | `list_kinds` | `["choropleth", "density", "situation_map"]` |
| `POST /v1/choropleth` | `render_choropleth` | Render a choropleth from JSON rows `{"id", "value"}`, or the demo |
| `POST /v1/situation-map` | `render_situation_map` | Render a situation map from a config object, or the Europe demo |
| `POST /v1/density` | `render_density` | Render an accumulation map from `[lon, lat]` points, or the demo |
| `GET /` | none | The gallery page |
| `GET /docs`, `GET /redoc` | none | Interactive documentation generated from the OpenAPI schema |

Every body field is optional, and `format` picks `svg`, `png`, `pdf` or
`jpg`. The repository carries a `Dockerfile` and a `docker-compose.yml`.
`docker compose up -d` builds the image and serves the same app on port
8000, with `./work` mounted at `/work` for files going in and out. The
container runs `sprezzature-maps-mcp`, so the same port also answers the
MCP endpoint at `/mcp` (section 4).

### 4. The MCP server

MCP, the Model Context Protocol, is the standard that lets an AI assistant
call a tool directly. `sprezzature-maps-mcp` serves the HTTP app with an
MCP endpoint mounted at `/mcp`, on `127.0.0.1:8000` by default (`--host`,
`--port`, or the `SPREZZATURE_MAPS_HOST` and `SPREZZATURE_MAPS_PORT`
variables). Its tools are the five API routes above, named by their
`operation_id`: `health`, `list_kinds`, `render_choropleth`,
`render_situation_map` and `render_density`. The audit, the starter config
and `improve` have no MCP tool, because they work on files on the caller's
disk. The Docker image and the compose file run this server on `0.0.0.0:8000`,
so one container serves both the `/v1/...` routes and `/mcp`.

### 5. The skill

The agent skill `sprezzature-maps` ships with the
[sprezzature](https://github.com/warith-harchaoui/sprezzature) hub
repository, not with this one. It routes an agent to the calls above.
[`TRIGGERS.md`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/TRIGGERS.md)
holds the routing rules it follows.

### And the Studio, for a person

`sprezzature-maps-studio` opens an editor on `http://127.0.0.1:8010/`
(`--host`, `--port`, `--reload`). Paste rows, a config or points, render,
and optionally run the same look-and-repair loop as `improve`. It is a page
a person opens rather than a surface a program calls. Why it exists apart
from the figures Studio is explained [below](#why-a-separate-repo-not-a-chart-type-in-sprezzature-figures).

## Recipes

### What moved between two dates

The question a researcher actually brings, and the one a single frame
cannot answer. The package's previous answer was an arrow, and an arrow is
the wrong answer: it asserts intent, momentum and success at once while
evidencing none of the three — the early maps of the 2022 invasion used
big ones and read as a blitzkrieg that was not happening.

A difference layer asserts nothing. Two extents, subtracted:

```yaml
change:
  before: 2022-april.geojson   # the earlier extent
  after:  2024-december.geojson  # defaults to areas_of_control.source
  actor: "Russian forces"      # whose ground; filters BOTH sides
  from: "April 2022"
  to:   "December 2024"
```

`actor` is the part that is easy to leave out and impossible to leave out
safely. A difference is about *somebody's* ground, and `after` defaults to
the whole control source — every camp's zones at once. The camps of a
control layer tile the same theatre at both dates, so their union barely
moves: subtracted from itself it reports that nothing happened while the
line between them walked across the map. Measured on a two-camp theatre
where one side took half a unit of ground, the layer returned **`taken` =
0.0** and gave `held` the entire rectangle. So a side spelling more than
one camp is now refused until `actor` says which one is meant, matched
against the property `areas_of_control.category_field` already names, and
applied to both sides by the one call that filters either.

Held, taken and lost in three colours, the interval printed in the footer
with the actor named — "Taken" states a direction and cannot state a camp —
and **each class keyed with the share of contested ground it covers** —
"Held throughout — 46%", "Taken — under 1%", "Lost — 54%". The share is
taken over the union of both extents, not over the plate, because the
question is asked of the ground either side ever held and not of a frame
that is mostly ocean. It is also what stops a sliver from taking a silent
row a reader then hunts the map for.

### A number per administrative unit

A choropleth of the world keys on ISO-3166-1 numeric. An analysis usually
does not: it is a rate by French region, a count by US state, a score by
German Kreis. Those atlases were vendored here all along and read only by
the layers that draw the *lines*, so `values` fills what is inside them:

```yaml
values:
  by: us-states          # or fr-regions, admin1, admin2, countries
  data: density.csv      # or inline rows; a path is relative to the config
  key: name              # the column holding the unit's name
  field: value           # the column holding the number
  classes: 6
  method: jenks          # quantile · equal · jenks · headtail, or `breaks:`
  label: "PEOPLE PER SQUARE MILE"
```

Names are matched through case, accents and punctuation, because a
spreadsheet spells Provence-Alpes-Côte d'Azur its own way. A table that
matches **nothing** stops the plate rather than drawing a confident grey map
of a column-name typo, and a cell that is not a number stops it rather than
being dropped as if the unit had no data. The key prints the breaks and names
the method, so the plate satisfies the audit by construction — and it counts
the classes the data **supported**, not the ones the config asked for. Ties
collapse boundaries, which is ordinary: `classes: 6` over counts with a long
run of zeros is not six classes, and a key saying so over six swatches would
be a key to nothing.

Living inside the situation map rather than in a generator of its own is the
point: it inherits the conic projection, the texture-shaded relief, the
frontier conventions, the labels that dodge each other, the scale bar, the
locator, the footer and the disclaimers.

### Then read the plate back

```bash
make-map audit world.svg            # exit 1 on any finding
```

Eleven static rules over a rendered plate, because a map is read the way a
text is. Six apply to any plate. Did it **name the classification method**
(`method-unnamed`: the same numbers in quantiles and in natural breaks tell
two different stories)? Does it print its class breaks (`breaks-missing`)?
Does it name the no-data fill, so absent does not read as low
(`no-data-hidden`)? Does it say when it was true, or that it is a schematic
(`no-provenance`)? Does it have a title (`untitled`) and an accessible name
(`unlabelled`)? A plate that passes is not thereby a good map. It is one a
reader can argue with.

A seventh, `text-unreadable`, applies to every plate too and is described
below: it measures whether every word can be read.

Four more only apply to a **regional** plate (`no-locator`,
`undated-control`, `evidence-unclassed`, `disputed-unflagged`), and come from the
standards such a plate gets read against — the UNHCR Mapping Guidelines for
the furniture, the Institute for the Study of War for the evidence model.
Does it carry a **locator**, so a reader who does not know where this is can
place it. Does a control map say **as of when** — looser is not enough here,
because a publication year in a source citation is not the date a front was
true. Are its zones **graded by evidence**, or does a belligerent's claim
look exactly like a geolocated observation. And does it carry the
**disclaimer** its extent owes, for the three boundaries that have a standard
sentence attached. The generator now supplies the first and the last of those
on its own; the other two are sentences only an author can write.

### From a conflict dataset, in one call

The two datasets peace-and-conflict research runs on — [ACLED](https://acleddata.com/methodology/acled-codebook)
and the [UCDP Georeferenced Event Dataset](https://ucdp.uu.se/downloads/) —
each record, beside every coordinate, **how well that coordinate is known**:
ACLED's `geo_precision` 1–3, UCDP's `where_prec` 1–7. ACLED's 3 means a
provincial capital standing in for a whole province; UCDP's 6 means only the
country is known. Tools that plot this data draw all of them as the same dot,
which asserts a street corner the source never gave, once per row.

This generator's markers already draw that distinction — a solid cased disc
for a named location, a hollow ring for an approximate one, a broken ring for
a region pinned to its capital, a drawn radius where the dataset states one.
The loaders are the step between the file and the mark:

```python
from sprezzature_maps import acled_events, make_situation_map

cfg = {"title": "Sudan: recorded political violence, 2024"}
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
make_situation_map(config=cfg, out="sudan.svg")
```

A plate is also a navigable document: its claim polygons, its event marks and
its legend controls are keyboard-reachable and each one names itself to a
screen reader — including **how well a mark's position is known**, so a reader
who cannot see a broken ring is told in words what the ring means. Set
`print_width: "90mm"` and the file lands at a journal's column width, and the
plate says in points how small its smallest label will actually print.

`ucdp_events` does the same for GED, maps its seven-step precision onto the
three in a table written out in `scripts/_conflict.py`, and **refuses to place
the country-level rows at all** — counting them on the plate's own method line
rather than dropping them in silence. See [`EXAMPLES.md`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/EXAMPLES.md#conflict-event-data-acled-and-ucdp-ged).

### One panel per window of time

A plate is a snapshot; most of what research says about a conflict is a
change. `small_multiples` cuts the same config into one panel per year,
quarter, month, week or day:

```python
cfg = {"title": "Recorded political violence, by quarter"}
cfg.update(acled_events("export.csv", derive_region=True, size_by="fatalities"))
cfg["small_multiples"] = {"by": "quarter", "columns": 4}
make_situation_map(config=cfg, out="by-quarter.svg")
```

Every panel comes from that one config, so the extent, the projection and the
marker scale cannot drift apart between frames the way they do when you export
a plate per window — and the sheet draws the title, the key, the ruler and the
credits once. Two rules it will not bend: **a window with nothing in it is
still a panel** (dropping it closes the gap, and the neighbouring panels then
read as consecutive), and **a mark is placed only where its own
`time_precision` allows** — a row dated *month of March* goes in a March panel
and in no week panel, and what fits in no single window is counted on the
sheet rather than binned anyway.

A word on how long that takes, because nothing on screen will tell you. A
choropleth is about a second. A situation map depends on how much world is
in the frame: the bundled Europe demo is about 10 s from a cold start, a
regional plate like eastern DRC about 3 s once the process is warm. Of the
demo's time, roughly 2 s is terrain shading, about 2 s is loading the
vendored atlases and importing — paid once per process, so a server renders
its second plate faster than its first — and the rest is real geometry.
`basemap: {relief: false}` removes the terrain cost if you do not need it.

### Proving which inputs drew a plate

A plate already prints `method`, `source` and `as_of` — what it was drawn
from, in prose, for a reader. None of that answers the question review
actually asks of a published figure: *is this the picture these inputs
produce?* The drawing is a function of three things — the code, the config,
and the file a loader read on the way in — so `provenance` fingerprints each
of them into `<metadata>`, which draws no pixels:

```python
cfg = {"title": "Recorded political violence", "provenance": True}
cfg.update(acled_events("export.csv", derive_region=True))
make_situation_map(config=cfg, out="plate.svg")
```

```python
from sprezzature_maps import plate_provenance, replay_report

plate_provenance(svg)   # {"version", "config_sha256", "inputs": [...]}

report = replay_report(svg, cfg, ["export.csv"])
report["replays"]       # True only if everything the stamp names matched
report["differences"]   # ["export.csv differs: 3f2a91c0d4e8 on the plate, …"]
```

Three things about that stamp are each the opposite of the obvious choice.
**It records digests, not the inputs**: an `areas_of_control` config carries
coordinates and a `source` carries a path that names somebody's machine, so
embedding either would publish it, while a digest publishes nothing and still
lets anyone holding the inputs prove the match. **It carries no clock**, since
a render time would make two renders of the same inputs differ and so destroy
the property the field exists to record. And **it is off by default**, because
it carries the package version: switching it on for everyone would change
every committed plate at every release.

A stamped input nobody hands over comes back under `unchecked`, not as a
match — the plate is then unrefuted, which is not the same as reproduced. The
conflict loaders fill the input list for you: by the time `make_situation_map`
sees the config the rows are inline and the CSV is gone, and the loader is the
only point in the chain that still knows which export it was.

See [`EXAMPLES.md`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/EXAMPLES.md) for more recipes, including the HTTP API.
See [`doc/CARTOGRAPHY.tex`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/doc/CARTOGRAPHY.tex) for the full method
behind every projection, colour scale, and relief (shaded-terrain)
technique this repo uses: the underlying maths, TikZ diagrams, citations,
and print-resolution figures, compiled with `xelatex`/`biber` (LaTeX's
Unicode-aware typesetter and its bibliography tool) into
[`doc/CARTOGRAPHY.pdf`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/doc/CARTOGRAPHY.pdf).

## Why a separate repo, not a chart type in sprezzature-figures

`choropleth` and `situation_map` used to sit inside `sprezzature-figures`'
catalogue, 126 chart kinds at the time (`density` was born here, after the
split).
Splitting them out was a deliberate product decision:
Sprezzature Studio, the conversational chart editor that ships with
`sprezzature-figures`, will not grow map support. Maps got their own,
separate Studio instead, and it ships here:

```sh
sprezzature-maps-studio          # http://127.0.0.1:8010/
```

The reason the two are separate is the data, not the branding. A chart Studio
can assume a table and ask which column plays which role. These three kinds
take three different things — rows per territory for a choropleth, a region
*configuration* with no table in it for a situation map, and a bare list of
`[lon, lat]` positions for a density map — and teaching one input panel all
three would have made the chart Studio worse at charts to make it mediocre at
maps.

It is FastAPI and server-rendered HTML rather than NiceGUI, which the figures
Studio uses. Measured before deciding: NiceGUI costs **20 packages** nothing
else in this graph brings, a websocket stack for one surface's view, while
FastAPI and uvicorn are already base dependencies here. And the figures
Studio's own numbers say the view is the cheap half to choose — 117 of its
5397 lines touch NiceGUI, and its ingest, recommendation, export and Ralph
subpackages touch it in **0 of 34 files**. That separation is what is worth
copying, so everything in `sprezzature_maps.studio` that *decides* anything
is importable and testable without a server.

## Status

Published on PyPI ([`sprezzature-maps`](https://pypi.org/project/sprezzature-maps/)),
with a green CI workflow (lint, type checks, tests and doctests on every
push and pull request to `main`, plus an install-and-import check on Python
3.10; see `.github/workflows/ci.yml`): `pytest` passes, all
three kinds render from their bundled demo data, and the command line
renders them to real SVG files. There is no FIGURES.md-style catalogue page
(with three kinds, this README is the catalogue).

Fifteen worked situation maps live in `scripts/build_situation_examples.py`,
regenerated into `assets/situation-maps/` with
`python scripts/build_situation_examples.py` (or one by name, such as
`python scripts/build_situation_examples.py sudan`). Six are thematic:
Ukraine, the lower Dnieper (the plate that goes with an article, with its
numbered marks), Syria and Libya as historical snapshots, and Sudan and
eastern DRC drawn from open-source reporting to late September 2026. Each
of those is schematic by construction, says so on the plate, and keeps its
claim lines in readable Python rather than an opaque data file, so a reader
who disagrees can see exactly which coordinates to argue with. The other
nine are reference plates with no thematic layer: Switzerland, Iberia,
western Europe, the Himalaya, the Caribbean, the Andes, the Sahel, the
Strait of Hormuz, and the South China Sea, drawn with no claim line on it.

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
outline, it having drained after the dam breach of 6 June 2023, and
`lakes.historic` for the other half of that problem, a lake that still
exists at a fraction of the polygon on file (Lake Urmia is drawn that way
by default: faded fill, dashed edge, name suffixed "historic extent" —
`lakes.historic: []` restores the basemap's own extents); and
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

### Saying how sure you are

A map that cannot say "probably" says "certainly" by default. Two of the
options above exist only to let a plate be less confident than its ink
would otherwise make it look.

**How sure the assessment is**, on a control zone. The vocabulary is
[ISW](https://www.understandingwar.org)'s: their control-of-terrain maps
keep three things apart that one fill runs together — ground a force is
assessed to hold, ground where movement has been *reported* but not
assessed as held, and ground a belligerent *claims* and nobody has
verified. That separation is what lets a reader hold the map up against a
ministry's communiqué. Any zone may carry a `confidence` property:

```yaml
areas_of_control:
  confidence_field: confidence     # the default
  palette: { "Government": "#9cc3d5", "Opposition": "#d98880" }
  source: zones.geojson            # features carry: confidence: claimed
```

`assessed` is the default and draws as a solid fill. `reported` keeps the
class colour, lowered, under a diagonal hatch — still plainly the same
actor, plainly less certain. `claimed` gets no solid fill at all, only a
dotted texture inside a dashed outline, because painting a claim the
colour of held ground asserts the one thing nobody has verified. An
unreadable value is refused rather than quietly rounded down to
`assessed`.

**How well the location is known**, on a marker. The codes are
[ACLED](https://acleddata.com)'s `geo_precision`, which that project
records next to every event "to reflect the fact that the precise location
of the incident may not be known" — precision 3 meaning a provincial
capital standing in for a whole province. Drawing all three as the same
hard dot asserts a street corner the source never gave:

```yaml
events:
  - lon: 38.0008
    lat: 48.5947
    precision: 2             # a named place standing in for a general area
    radius_km: 25            # optional: drawn to the map's own scale
    date: "March 2026"
    time_precision: 3        # the tooltip reads "month of March 2026"
    source: "https://example.org/report"   # provenance for this one mark
```

Precision 1 is the solid dot and means what it always meant. An
approximate position gives up its solid centre rather than inventing an
area for itself — a hollow ring, the old cartographic signal for "about
here" — and precision 3 breaks the ring as well. A radius is drawn only if
you state one: the generator will not guess an uncertainty from the event
type, because the buffers published for that measure how far an effect
reached, not how badly a position is known.

### When the map illustrates an article

The article is the deliverable; the map is subordinate to it. That changes
a few defaults.

**It has to fit the column.** A one-column chart at The Economist is 595
pixels wide, Datawrapper defaults to 600, and a phone column is about 375.
The legend card is a fixed 262 pixels, which is fine at 1000 and covers the
map at 375, so `legend_position` takes `below` (a full-width band under the
map) and `auto`, which chooses from the plate's own width:

```yaml
canvas_width: 375
legend_position: auto     # keeps the floating card while the card is small
```

**The note is the point.** Newsroom practice is unanimous that the
annotation is what makes a news map, and the other layers exist to support
it. `annotations:` takes a point, a sentence, and optionally a radius in
kilometres on the ground:

```yaml
annotations:
  - at: [30.5, 51.3]
    text: "Columns withdrew north of Kyiv in April 2022."
    place: left
    color: "#2f5d92"
    circle_km: 90
```

A circle rather than an arrow, because an arrowhead points at a pixel and
claims a precision a note about a region does not have. The note takes the
colour of the thing it describes, so it sits back onto the map instead of
jumping off it.

**The direction can be measured rather than guessed.** `place` takes the
four sides and the four diagonals — so every leader falls on 90 or 45
degrees, which is Datawrapper's rule after Beck — and `place: auto` tries
them in that order and takes the first whose every line clears the names
already on the plate. `annotations` was the one text layer here that never
consulted the ink ledger, and a hand that guessed wrong set a sentence
through a toponym, at its most visible, because the note is drawn above
every map layer. A note with nowhere to go is refused by name rather than
drawn in the least-bad direction.

**A numbered mark is half of a reference whose other half is a
paragraph.**

```yaml
annotations:
  - at: [32.6250, 46.6425]
    number: 1
    text: "Kherson, retaken in November 2022."
    place: auto
```

The numbers have to run 1..n with no gap and no repeat, because a plate
showing 1, 2 and 4 sends a reader hunting the map for a 3 that was cut
from the article. And they come back out of the finished plate, so the
page prints the list it is given rather than one somebody typed again
beside it:

```python
from sprezzature_maps import article_sidecar
for note in article_sidecar(svg)["callouts"]:
    print(f"{note['number']}. {note['text']}")
```

The badge is focusable and announces the note's words, not its digit: a
reference is useless to a reader who reaches it by keyboard and hears "3".

**And a rectangle says where the story is.** The extent has to stay wide
enough to place itself — that is what the locator argues — and the piece
is usually happening in a tenth of it:

```yaml
detail_area:
  bbox: [32.1, 46.3, 34.2, 47.4]
  label: "Lower Dnieper"
```

An outline and a label, nothing else. Dimming the context outside it was
tried and refused: a wash over the relief, the control fills and the
water changes every colour the legend keys, so the key would show hues
the plate no longer draws.

The examples all three of these were chosen from — eight named New York
Times situation maps, read through their own text layer — are in
[`references/situation-map-annotation.md`](https://github.com/warith-harchaoui/sprezzature-maps/blob/main/references/situation-map-annotation.md),
together with the reason this package still refuses movement arrows when
the desk that invented the modern form of these plates spent 2022
abandoning them.

**It says where on Earth it is, without being asked.** *"Zoom out for
perspective, zoom in for detail"* is the locator map's one rule, and a plate
that only ever zooms in answers half of it. So a regional plate draws a
locator by default — the mapped area in red on a wider view, in a fifth of
the plate's width. A plate already wide enough to place itself gets none,
and a caller can always decline:

```yaml
inset:
  position: top-right     # or any corner; omitted, it takes one the
                          # legend and the scale bar have not
  zoom: 6                 # how far out, when no bbox is given
  show: false             # no locator on this plate
```

**Its date is stamped under the title, not only at the foot.** The
guidelines put "as of DD Month YYYY" directly beneath the strapline,
because it is the single most important fact on a control plate and the
one a reader needs before anything else. The footer keeps the whole line
— the copy that travels with a screenshot; the stamp is the one a reader
sees while deciding whether to believe the map.

**Every word on it can be read, and that is measured.** A map is mostly
type, and this package already placed *labels* with real font metrics. It
did not place the furniture that way: the scale bar, the legend card, the
break values under a colour strip and the provenance footer were each
positioned by arithmetic that was right on the plate it was tuned on.
`make-map audit` now rebuilds every `<text>`'s ink rectangle and reports
the ones that collide, run off the plate, or are set too small — which is
how the ruler printing through a colour strip, a footer running eleven
words off the eastern-DRC plate, and four town names buried under that
footer were all found at once.

**It carries the disclaimer its extent owes.** Three boundaries have a
standard sentence attached to them — Jammu and Kashmir, Sudan and South
Sudan, Abyei. Drawing one of those lines and saying nothing is a position
taken by omission, so the sentence is added to the provenance footer
whenever the plate's region reaches the boundary, on the same principle as
the automatic OpenStreetMap credit: an obligation a caller has to remember
is an obligation the plates will not meet. Declining the footer does not
decline the sentence.

**The page around it needs words and numbers.** `article_sidecar(svg)` reads
them back out of the finished file, so a caption typed into a CMS cannot
drift from the plate above it:

```python
from sprezzature_maps import article_sidecar
card = article_sidecar(svg)
card["alt"]      # description + a computed takeaway
card["zones"]    # [{"category", "confidence", "area_share"}, ...]
card["markers"]  # [{"lon", "lat", "precision", "radius_km"}, ...]
```

The `alt` string carries a takeaway, which the accessible description did
not — "Ukrainian government control covers the largest mapped share, 81%",
computed from what was drawn rather than asserted, and spoken as *"is
claimed to cover"* when the largest share is only a claim.

**And it has to leave as vector.** `--out figure-1.pdf` (or `.eps`) writes a
drawn page at exactly the width `print_width` asked for, via `rsvg-convert`
from librsvg — an optional system package. Without it you still get a page at
the right size, plus a warning that it is a raster, because a raster PDF
satisfies the extension and nothing a journal wants.

**It has to be light enough to ship.** Geometry is thinned to the render's
own resolution after projection (`simplify: 0` switches it off), and the
shaded-relief raster is written as an exact indexed palette rather than
32-bit colour. Together these roughly halve a plate — Ukraine from 2094 KB
to 1006 KB — with no visible change.

Like the other two kinds, the plate now opens with an accessible root
(`role="img"` wired to a `<title>`/`<desc>` pair), and its description
names the classes drawn, names any confidence tier below assessed, and
repeats the caveat the caption carries: the map draws the assessment it
was given and does not verify it. Each control zone and each marker also
carries its own `data-*` attributes (`data-confidence`, `data-precision`,
`data-area-share`), so the assessment can be read back out of the finished
file rather than only looked at.

The five ways to reach all of this are listed under
[Five ways in](#five-ways-in).

## Roadmap

`situation_map` already shades real elevation onto its Lambert conformal
conic projection, on by default (`scripts/make_situation_map.py`'s
`_relief_layer`), the same terrain-shading technique `choropleth` uses
for the whole-world Equal Earth view, reworked for the region-scale
projection's own analytic inverse. A few lower-priority items from the
full cartography plan are tracked but not scheduled yet: relief built
from the ETOPO global elevation dataset, alternate projections better
suited to editorial maps (Robinson, Mollweide). The shared reader for the
TopoJSON format (a compact way of storing map boundaries that records each
shared border only once, instead of once per neighbouring country) was the
third item here and is now `scripts/_topojson.py`.

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
