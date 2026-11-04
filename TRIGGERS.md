# Triggers

When someone wants a map, and what to call.

This file is written for an agent: a Claude Code or OpenCode skill, an MCP
(Model Context Protocol) host, anything choosing a tool on someone's behalf.
Humans are welcome, but the routing rules below are the point.

---

## The generalisation, stated once

> **Data attached to *places* is the trigger.** Not the word "map". A column
> of country names, ISO codes, regions, states or départements is a map
> waiting to be drawn, and so is a list of coordinates where something
> happened. The only question is which kind.

Route on what the caller **holds**, not on how they phrase it. A list of
phrasings is never complete; the shapes of map data are. There are three,
and they are the registry's own `data_shape` values
(`sprezzature_maps.kinds`), which every surface reads. A fourth thing a
caller can hold is a plate that already exists.

| The caller holds | Shape | Kind | Call |
|---|---|---|---|
| one value per named territory | `rows` | `choropleth` | `render_choropleth` |
| zones, fronts and markers for a region | `config` | `situation_map` | `render_situation_map` |
| a place or a bounding box, and no config yet | none yet | the start of a `situation_map` | `make-map situation_new` |
| positions of events, `[lon, lat]` | `points` | `density` | `render_density` |
| an ACLED or UCDP GED export | events with precision codes | `situation_map` | `acled_events` / `ucdp_events`, then `render_situation_map` |
| the same ground at several moments | a config with dated marks | `situation_map` | `small_multiples` in the config, then `render_situation_map` |
| a finished plate (an SVG) | none | none | `make-map audit`, `make-map improve`, `article_sidecar`, `replay_report` (see below) |
| place-shaped data where the shape of the land does not matter | none | none | **sprezzature-figures** (hex maps, dot density, spike maps, binned grids) |

Phrasings confirm a route; they do not decide it. "Map this by country",
"which country is highest", « une carte par département » are `rows`.
"Areas of control", "front line", "who holds what", « carte de situation »
are `config`. "Where did the strikes land", "heat map of incidents",
« carte de densité » are `points`. "I have an ACLED export", « j'ai un
fichier ACLED » is the loader row.

Three rows are easy to get wrong.

The **ACLED / UCDP row** is a routing rule, not a convenience. Both datasets
record, beside every coordinate, how well that coordinate is known: ACLED's
`geo_precision` 1 to 3, UCDP's `where_prec` 1 to 7. The weak codes mean a
provincial capital standing in for a province, or, at UCDP's 6, only the
country. `acled_events` and `ucdp_events` carry those codes onto the marks.
Reading the file yourself and emitting plain `events` throws them away, and
the plate then asserts a street corner the source never gave, once per row.
Both return a config fragment, so the call is
`cfg.update(acled_events(path))` and everything else about the config is
unchanged. **UCDP `where_prec` 6 rows are not drawn** and the count goes on
the plate. Do not "fix" that by passing `country_level="keep"` unless the
user asked for it and knows what it asserts.

The **density row against the choropleth row**: both answer "where is there
more of this", and the difference is what the data is. A choropleth needs one
value per named territory and colours that territory. Density needs raw point
events and bins them, so the answer can be finer than any boundary and does
not stop at one. If the user has a table of countries, choropleth. If they
have a list of things that happened at coordinates, density. A choropleth of
raw counts draws population, not the phenomenon.

The **sprezzature-figures row**: a hexmap of US states is not a choropleth
and does not live here. `list_kinds` on the figures package lists those
schematic kinds. Ask whether the shape of the land matters. If it does, this
repository; if it is a layout convention, that one.

---

## Every tool, and the request it answers

| Tool | The request it answers |
|---|---|
| `make_choropleth` / `render_choropleth` | Shade real countries by one value each (rows keyed on ISO-3166-1 numeric codes), on an Equal Earth world projection |
| `make_situation_map` / `render_situation_map` | Draw a region's zones of control, fronts, markers, values per administrative unit or a change between two dates, on a Lambert conformal conic projection |
| `make_density` / `render_density` | Bin point events into a field with no coastline drawn |
| `make-map situation_new` | Write a starter region config, already furnished, from a country name or a bounding box |
| `acled_events`, `ucdp_events` | Turn a conflict export into the marker layer of a situation map, keeping precision codes |
| `classification_methods` | List the class-break methods a choropleth accepts: `quantile`, `equal`, `jenks`, `headtail` |
| `make-map audit` | Say whether a finished plate states how it was made (eleven static rules) |
| `make-map improve` | Render a map, read it with a vision model, apply only the repairs that cannot change what it says |
| `article_sidecar` | Give the page around a plate its alt text, caption, zones, markers and numbered callouts, read from the SVG |
| `plate_provenance`, `replay_report` | Say whether a stamped plate was drawn from a given config and files |
| `list_kinds` / `make-map list` | Name the three kinds this package draws |
| `health` | Check that the HTTP or MCP server is up. Call it only to diagnose a connection |
| `sprezzature-maps` | A person wants to paste data and edit a map in a browser. Not an agent call |

---

## What to call, on every surface

The command line answers to `make-map` and to `sprezzature-maps`, which are
the same Click group. `situation_map` and `situation_new` also accept the
hyphenated spellings `situation-map` and `situation-new`. MCP tool names are
the FastAPI `operation_id` of each route.

| Job | Library | CLI | MCP tool | HTTP route |
|---|---|---|---|---|
| Choropleth | `make_choropleth` | `make-map choropleth --data rows.csv --out world.svg` | `render_choropleth` | `POST /v1/choropleth` |
| Situation map | `make_situation_map` | `make-map situation_map --config region.yaml --out r.svg` | `render_situation_map` | `POST /v1/situation-map` |
| A region config to start one from | none | `make-map situation_new --country Sudan --out sudan.yaml` | none | none |
| Density | `make_density` | `make-map density --points e.json --out where.svg` | `render_density` | `POST /v1/density` |
| Audit a finished plate | `sprezzature_maps.audit.audit` (reads SVG text) | `make-map audit plate.svg` | none | none |
| Render it, look at it, repair what is safe | none | `make-map improve --kind density --points e.json --out m.png` | none | none |
| Which kinds exist | `kind_names` | `make-map list` | `list_kinds` | `GET /v1/kinds` |
| Is the server up | none | none | `health` | `GET /health` |
| A conflict export | `acled_events`, `ucdp_events` | none | none | none |
| Read a plate back | `article_sidecar`, `plate_provenance`, `replay_report` | none | none | none |

The servers: `sprezzature-maps-mcp` serves the HTTP routes with the MCP
endpoint at `/mcp` (default `127.0.0.1:8000`). `uvicorn
sprezzature_maps.api:app`, the Docker image and `docker compose up` serve the
HTTP routes without `/mcp`.

A conflict export has no CLI of its own: the loaders are a Python call that
builds the config the situation map then renders.

```python
from sprezzature_maps import acled_events, make_situation_map

cfg = {"title": "Sudan: recorded political violence, 2024"}
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
make_situation_map(config=cfg, out="sudan.svg")
```

All three render tools take every field as optional: send nothing and you
get the demo map, which is the quick way to show someone the format before
committing real data to it. `format` picks `svg`, `png`, `pdf` or `jpg`. The
situation map is configured by a YAML region file, so the CLI is usually the
better surface for it.

The audit, the starter and `improve` have no MCP tool. The MCP surface is
this repository's HTTP routes, and those render into a response, while these
three work on files sitting on the caller's disk, which an HTTP renderer
never sees.

---

## Asked whether the map is any good, not for another map

> **A judgement about a rendered map is the trigger**, not a request to draw
> one: "is this readable", "the legend is too small", "can you make this
> clearer", "fix the colours", « la légende est illisible », « rends ça plus
> lisible ». The caller already has a map, or is about to, and what they want
> is for someone to *look at it*.

`make-map improve` renders a PNG, hands it to a vision model, and changes
one keyword at a time from a ladder that ends. It needs a vision model
reachable on the machine, which is one reason it has no MCP tool: an agent
calling it would be an agent calling a model through a tool, and the agent
can look at the PNG itself. `--rounds` lowers the ceiling on rounds; it
cannot raise it.

What it will not do on its own is the part worth knowing before routing to
it. It never changes anything that can alter what the map *says about the
data*: the classification method, the number of classes, the frame. Those it
prints for a person to decide. So "make it legible" is a job for it, and
"re-cut the classes so my country looks worse" is not.

---

## Asked for a situation map, with no region config in hand

> **A place named, and no YAML to render: that is the trigger.** The
> situation map is the only kind here that is configured by a file, so
> every request for one starts at the same fork: either the caller already
> has a region config, or the first call is `make-map situation_new` to
> write one.

The vocabulary is the domain's own, and it is short: the config's sections
are **region**, **basemap**, **frontiers**, **cities**, **areas of
control**, **legend**, **provenance**. A question naming one of them, or
naming a country or a bounding box and no file, is this call: "where do I
start a plate of Mali", "I need a region config for the Sahel", "what goes
in the YAML", « une carte de situation du Mali, je pars de quoi ». So is
any request to change the plate's *furniture* rather than its subject: the
starter writes all of it already furnished.

```
make-map situation_new --country Sudan --out sudan.yaml
make-map situation_new --bbox 21.8,8.7,27.6,16.4 --title "Darfur" --out darfur.yaml
```

Exactly one of `--country` and `--bbox`. The country name is resolved
against the vendored Natural Earth atlas, so it is the Natural Earth
spelling or nothing: an unknown name is refused rather than guessed at.
`--as-of` stamps the vintage (default: today); without `--out` the config
goes to stdout.

What comes out renders as it stands (basemap, frontiers, towns, scale,
locator, provenance footer), and the thematic block is present but
commented, with `confidence` on every zone. That field is the one most
often left out, and leaving it out is itself a claim: it says the author is
certain. Do not delete the comment and the field together.

---

## Asked whether a finished plate can be published

"Can we publish this map?", "does it say where the numbers came from?",
"check this before it goes out": a plate that already exists is not a
rendering request, and this one has a command, `make-map audit plate.svg`,
or a folder to take the whole set at once (`--format json` for a machine).
It is static: it reads the markup the generator wrote, with no rendering and
no network. It exits 1 on any finding, 0 when clean, 2 when the target holds
no SVG.

Eleven rules, each a thing a map gets wrong that a chart auditor has no way
to ask.

- On any plate: a classed legend that never names its method
  (`method-unnamed`), class breaks missing from the key (`breaks-missing`),
  no-data drawn and never named so absent reads as low (`no-data-hidden`),
  no vintage **and** no statement that the plate is a schematic
  (`no-provenance`), no title (`untitled`), no accessible name
  (`unlabelled`), and a label that collides, runs off the plate or is set
  too small (`text-unreadable`).
- On a regional plate only: no locator inset (`no-locator`), areas of
  control with no "as of" date (`undated-control`), every zone at one
  confidence (`evidence-unclassed`), and a disputed boundary drawn without
  its standard disclaimer (`disputed-unflagged`).

A plate announcing "synthetic illustrative values" is placed well enough,
better than a date would place it, since stamping a vintage on invented data
would be a fabrication. So do not "fix" a demo plate by dating it.

What the audit does not do is judge the cartography: whether the right
classification was chosen, whether the projection suits the latitudes,
whether the data is any good. A clean run therefore is not an endorsement of
the map, and reporting it as one is the failure this section exists to
prevent. It means the reader has been given enough to argue with the plate,
which is all anyone can check by parsing.

---

## Asked whether a figure replays

"Is this the map that CSV produces?" is not a rendering request, and there is
no CLI or MCP tool for it. It is two Python calls on the finished file:

```python
from sprezzature_maps import plate_provenance, replay_report

plate_provenance(svg)  # {} if it was never stamped
replay_report(svg, cfg, ["sudan-2024.csv"])["replays"]
```

A plate only carries a stamp if it was rendered with `provenance: true` in its
config (or `provenance=True` for a choropleth or a density map), which is
**not** the default. So the honest answer to "does this published figure
replay?" is often "it recorded nothing, and nothing can be said". Do not
report a match for an unstamped plate; `replay_report` refuses one rather
than letting an agent paraphrase silence as agreement.

---

## One contract an agent must not break

**A situation map draws exactly what you send it.** It has no view on whether
a claim of control is true, and a plate that looks like a professional
intelligence product gets read as one. When you pass such a map on, say where
the underlying assessment came from. That is not a disclaimer to append: it
is part of the map's meaning.

---

## File patterns

`*.svg` under `assets/svg-examples/` or `assets/situation-maps/`, and any
YAML region config, route here when a real geographic basemap is wanted
rather than a schematic point or grid map.
