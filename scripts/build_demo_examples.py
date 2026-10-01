#!/usr/bin/env python3
"""Regenerate the demo SVG every doc page shows, one per generator.

``EXAMPLES.md`` claims the images it embeds "are the actual output of
``make_choropleth()`` and ``make_situation_map()`` called with no arguments
[…] so they can never silently drift from what the code in this repo
actually produces". That claim was false when it was written and stayed
false for three releases: nothing regenerated them. ``choropleth.svg``
happened to stay current because ``make_choropleth``'s own doctest writes
it as a side effect on every test run; ``situation_map.svg`` was a month and
three releases out of date, from before lakes, axes of advance, the
accessible root and the confidence tiers; and ``density.svg`` did not exist
at all, because the third generator was never added to the page.

A promise in prose is not a mechanism. This script is the mechanism, and
``tests/test_demo_examples_are_current.py`` is the enforcement: it renders
each generator afresh and fails if the shipped file differs, naming this
script in the failure message.

    python scripts/build_demo_examples.py

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: The generator module and the demo stem it writes, in the order the docs
#: present them. Each is rendered by the exact no-argument call the docs
#: quote, so the file on disk is that call's output and nothing else.
_DEMOS: tuple[tuple[str, str], ...] = (
    ("make_choropleth", "choropleth"),
    ("make_situation_map", "situation_map"),
    ("make_density", "density"),
)


def _build_one(module_name: str, stem: str) -> Path:
    """Render one generator's zero-argument demo and return where it landed."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        module_name, Path(__file__).resolve().parent / f"{module_name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    # Every generator exposes ``make_<stem>()``; calling it with no arguments
    # is both the documented quick start and what the embedded image must be.
    return getattr(module, module_name)()


def main() -> int:
    """Regenerate every demo SVG. ``write_svg`` reports each path as it lands."""
    for module_name, stem in _DEMOS:
        path = _build_one(module_name, stem)
        print(f"  {path.name:20s} {path.stat().st_size / 1024:7.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
