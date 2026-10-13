# Triggers

When someone wants a map, and what to call.

This file is written for an agent — a Claude Code / OpenCode skill, an MCP
host, anything choosing a tool on someone's behalf. Humans are welcome, but
the routing rules below are the point.

---

## The generalisation, stated once

> **Data attached to *places* is the trigger.** Not the word "map": "which
> countries are worst affected", "break this down by région", "where is this
> happening", "show me the spread across Europe", « par département », "who
> holds the east". A column of country names, region codes, states or
> départements is a map waiting to be drawn, and the question is only which
> kind.

---

## Three kinds here, and five schematic ones elsewhere

This repo draws **real geography** — actual coastlines, a real projection.
That is the whole scope, and the first routing decision is whether you need
it at all.

| The user wants… | Call | Example phrasings |
|---|---|---|
| **territories shaded by a value** | `render_choropleth` | "map this by country", "colour the regions by score", "which country is highest", « une carte par département » |
| **who holds which ground** | `render_situation_map` | "areas of control", "front line", "contested zones", "who controls what", « carte de situation » |
| **where events fell, not what a territory scores** | `render_density` | "accumulation map", "where did the strikes land", "heat map of incidents", "point density", « carte de densité » |
| **a conflict dataset, as exported** | `acled_events` / `ucdp_events`, then `render_situation_map` | "I have an ACLED export", "map this UCDP GED file", "plot these events", "conflict event map", « j'ai un fichier ACLED » |
| **place-shaped data without real coastlines** | → **sprezzature-figures** | "hex map", "dot density", "spike map", "binned grid" — schematic maps that plot points or cells |

Three rows are easy to get wrong.

The **ACLED / UCDP row** is a routing rule, not a convenience. Both datasets
record, beside every coordinate, how well that coordinate is known — ACLED's
`geo_precision` 1–3, UCDP's `where_prec` 1–7 — and the weak codes mean a
provincial capital standing in for a province, or, at UCDP's 6, only the
country. `acled_events` and `ucdp_events` carry those codes onto the marks;
reading the file yourself and emitting plain `events` throws them away, and
the plate then asserts a street corner the source never gave, once per row.
Both return a config fragment, so the call is
`cfg.update(acled_events(path))` and everything else about the config is
unchanged. **UCDP `where_prec` 6 rows are not drawn** and the count goes on
the plate; do not "fix" that by passing `country_level="keep"` unless the
user asked for it and knows what it asserts.

The other two:

The **last** one: a hexmap of US states is not a choropleth and does not live
here; `list_kinds` on the figures package has those five kinds. Ask whether
the shape of the land matters — if it does, this repo; if it is a layout
convention, that one.

The **density row against the choropleth row**: both answer "where is there
more of this", and the difference is what the data is. A choropleth needs one
value per named territory and colours that territory. Density needs raw point
events and bins them, so the answer can be finer than any boundary and does
not stop at one. If the user has a table of countries, choropleth; if they
have a list of things that happened at coordinates, density.

---

## What to call, on every surface

| Job | CLI | MCP tool |
|---|---|---|
| Choropleth | `make-map choropleth --out world.svg` | `render_choropleth` |
| Situation map | `make-map situation_map --config region.yaml --out r.svg` | `render_situation_map` |
| Density | `make-map density --out where.svg` | `render_density` |
| Which kinds exist | `make-map --help` | `list_kinds` |

A conflict export has no CLI of its own: the loaders are a Python call that
builds the config the situation map then renders.

```python
from sprezzature_maps import acled_events, make_situation_map

cfg = {"title": "Sudan: recorded political violence, 2024"}
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
make_situation_map(config=cfg, out="sudan.svg")
```

Both render tools take every field as optional: send nothing and you get the
demo map, which is the quick way to show someone the format before committing
real data to it. The situation map is configured by a YAML region file, so
the CLI is usually the better surface for it.

---

## One contract an agent must not break

**A situation map draws exactly what you send it.** It has no view on whether
a claim of control is true, and a plate that looks like a professional
intelligence product gets read as one. When you pass such a map on, say where
the underlying assessment came from. That is not a disclaimer to append — it
is part of the map's meaning.

---

## File patterns

`*.svg` under `assets/svg-examples/`, and any YAML region config, route here
when a real geographic basemap is wanted rather than a schematic point or
grid map.
