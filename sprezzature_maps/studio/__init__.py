"""
sprezzature-maps Studio: a conversational editor for the three map kinds.

Module summary
--------------
What `sprezzature-figures`' Studio is for charts, this is for maps — and it is
a **separate** Studio on purpose. ``CODING.md`` and ``LISEZMOI.md`` both
recorded that decision before a line of this existed: "the conversational
editor ships with the figures package; maps get their own when there is one",
and "Les cartes auront leur propre Studio séparé, une fois construit." This is
that one.

Why separate, restated now that it is being built
--------------------------------------------------
Because the data does not have one shape. A chart Studio can assume a table
and ask which column plays which role. The three kinds here consume three
different things, and the registry says so in
:attr:`~sprezzature_maps.kinds.MapKind.data_shape`:

* a **choropleth** takes rows of per-territory values, bound through the
  ``id`` and ``value`` roles — the only shape a chart Studio would recognise;
* a **situation map** takes a region *configuration*: zones, fronts, labels,
  a projection. There is no table in it;
* a **density** map takes a bare list of ``[lon, lat]`` positions, and draws
  no coastline at all.

Teaching one input panel all three would have made the chart Studio worse at
charts to make it mediocre at maps.

No NiceGUI here, and the measurement that decided it
----------------------------------------------------
`sprezzature-figures`' Studio is a NiceGUI application. This one is FastAPI
plus server-rendered HTML, which is what :mod:`sprezzature_maps.gui` already
does for the gallery, for the reason that module already states: a build
pipeline for a small page "would cost more in tooling than it would ever pay
back".

Measured before deciding, rather than assumed:

* **NiceGUI costs 20 packages** that nothing else in the graph brings —
  ``python-socketio``, ``python-engineio``, ``aiohttp``, ``bidict``,
  ``wsproto``, ``simple-websocket``, ``orjson``, ``markdown2``, ``docutils``,
  ``tinycss2`` and the rest. On a 162-package install of
  `sprezzature-figures`, that is a websocket stack for one surface's view.
* **FastAPI and uvicorn are already base dependencies here**, so the view
  layer below adds nothing to the install.
* And the figures Studio's own numbers say the view layer is the cheap half to
  choose: 117 lines of 5397 touch NiceGUI — **2.2%** — and its ``assistant``,
  ``export``, ``ingest``, ``ralph`` and ``recommendation`` subpackages are at
  **0 of 34 files**. The engine was already interface-free. So the pattern
  worth copying from over there is not the toolkit; it is that separation.

This package follows it deliberately from the first commit: everything under
this subpackage that *decides* anything is importable and testable without a
server, and the view is a thin layer over it.

Models go through best-engine-ai-helper, and only there
-------------------------------------------------------
Exactly as `sprezzature-figures`' Studio does: ``best_engine_ai_helper``
resolves which model and which backend answers, and nothing here calls Ollama
or any provider directly. One place decides, so a machine with a different
model available does not need this package changed.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

__all__: list[str] = []
