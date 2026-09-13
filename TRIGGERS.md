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

## Two kinds here, and a third elsewhere

This repo draws **real geography** — actual coastlines, a real projection.
That is the whole scope, and the first routing decision is whether you need
it at all.

| The user wants… | Call | Example phrasings |
|---|---|---|
| **territories shaded by a value** | `render_choropleth` | "map this by country", "colour the regions by score", "which country is highest", « une carte par département » |
| **who holds which ground** | `render_situation_map` | "areas of control", "front line", "contested zones", "who controls what", « carte de situation » |
| **place-shaped data without real coastlines** | → **sprezzature-figures** | "hex map", "dot density", "spike map", "binned grid" — schematic maps that plot points or cells |

The third row is the one an agent gets wrong. A hexmap of US states is not a
choropleth and does not live here; `list_kinds` on the figures package has
those five kinds. Ask whether the shape of the land matters: if it does, this
repo; if it is a layout convention, that one.

---

## What to call, on every surface

| Job | CLI | MCP tool |
|---|---|---|
| Choropleth | `make-map choropleth --out world.svg` | `render_choropleth` |
| Situation map | `make-map situation_map --config region.yaml --out r.svg` | `render_situation_map` |
| Which kinds exist | `make-map --help` | `list_kinds` |

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
