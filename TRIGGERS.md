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
| **the same ground at several moments** | `small_multiples` in the config, then `render_situation_map` | "how did it change", "by year", "quarter by quarter", "over time", « évolution » |
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
| Audit a finished plate | `make-map audit plate.svg` | — |
| Which kinds exist | `make-map list` (or `--help`) | `list_kinds` |

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

The audit is the mirror image of the loaders: no MCP tool, because the MCP
surface is this repo's HTTP routes and those render into a response, while
the audit reads plates already sitting on the caller's disk — which an HTTP
renderer never sees. It is on both CLIs instead, `make-map audit` and
`sprezzature-maps audit`.

---

## Asked whether a finished plate can be published

"Can we publish this map?", "does it say where the numbers came from?",
"check this before it goes out" — a plate that already exists is not a
rendering request, and this one has a command: `make-map audit plate.svg`, or
a folder to take the whole set at once. It is static — it reads the markup
the generator wrote, no rendering and no network — and exits 1 on any finding.

Six rules, each of them a thing a map gets wrong that a chart auditor has no
way to ask: a classed legend that never names its method, the class breaks
missing from the key, no-data drawn and never named so absent reads as low,
no vintage **and** no statement that the plate is a schematic, no title, no
accessible name. A plate announcing "synthetic illustrative values" is placed
well enough — better than a date would place it, since stamping a vintage on
invented data would be a fabrication — so do not "fix" a demo plate by
dating it.

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
config, which is **not** the default — so the honest answer to "does this
published figure replay?" is often "it recorded nothing, and nothing can be
said". Do not report a match for an unstamped plate; `replay_report` refuses
one rather than letting an agent paraphrase silence as agreement.

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
