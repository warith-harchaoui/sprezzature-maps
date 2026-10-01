"""
The demo SVGs the docs embed must be what the generators currently produce.

``EXAMPLES.md`` tells the reader those images "can never silently drift from
what the code in this repo actually produces". Nothing enforced it. The
situation-map demo was a month and three releases stale — from before lakes,
axes of advance, the accessible root and the confidence tiers — while the
choropleth one stayed current purely because ``make_choropleth``'s doctest
writes it as a side effect. One file was fresh by coincidence, the other by
nothing, and the page asserted a process that did not exist.

A promise in prose is not a mechanism. This is the mechanism.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Generator module, the demo file it owns, and the zero-argument call the
#: docs quote for it. Kept in step with ``scripts/build_demo_examples.py``.
_DEMOS = [
    ("make_choropleth", "choropleth.svg"),
    ("make_situation_map", "situation_map.svg"),
    ("make_density", "density.svg"),
]


def _render(module_name: str, destination: Path) -> str:
    """Return the generator's zero-argument demo, rendered to ``destination``.

    Through the public ``make_<kind>()`` entry point, not ``build_svg`` /
    ``build_map``: the shipped file is written by ``write_svg``, which also
    embeds the fonts, and comparing against the bare builder's output would
    compare two different things and fail for the wrong reason. (It did, on
    the first run of this test.)
    """
    scripts = REPO_ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, scripts / f"{module_name}.py"
        )
        assert spec and spec.loader
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        getattr(module, module_name)(out=destination)
        return destination.read_text(encoding="utf-8")
    finally:
        if sys.path and sys.path[0] == str(scripts):
            sys.path.pop(0)


def _fingerprint(svg: str) -> str:
    """Return what "the same plate" means, across machines.

    Byte equality is the obvious comparison and the wrong one. Verified by
    rendering the situation demo inside the project's own Docker image and
    against this checkout: with decimal numbers normalised the two are
    **identical**, and raw they are not — the projection's floating-point
    arithmetic differs by ulps between macOS and Linux, which moves
    coordinates in the last printed digit without moving anything a reader
    could see. A byte-equality gate would therefore have failed on CI for a
    reason that has nothing to do with staleness, every time.

    So the fingerprint drops two things and keeps everything else:

    * **embedded rasters**, because the relief encoder's input is the same
      floating-point terrain and its output is a different-sized PNG;
    * **decimal numbers**, for the reason above.

    What survives is the document's whole structure and all of its text:
    element names and order, ids, classes, layer groups, every label,
    title, legend row and caption. Any real drift — a layer added or
    renamed, a label changed, a legend row gained, a title edited — moves
    this. Sub-pixel noise does not.
    """
    without_rasters = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "RASTER", svg)
    return re.sub(r"-?\d+\.\d+", "N", without_rasters)


@pytest.mark.parametrize(("module_name", "filename"), _DEMOS)
def test_the_embedded_demo_is_what_the_generator_produces_now(
    module_name: str, filename: str, tmp_path: Path
) -> None:
    """
    Every image the docs show is the output of the call they say it is.

    When this fails the fix is not to edit the test: it is to run
    ``python scripts/build_demo_examples.py`` and commit the result, which
    is also the moment to look at the new plate before shipping it.
    """
    shipped = REPO_ROOT / "assets" / "svg-examples" / filename
    assert shipped.exists(), (
        f"{filename} is missing. Run: python scripts/build_demo_examples.py"
    )
    fresh = _render(module_name, tmp_path / filename)
    if _fingerprint(shipped.read_text(encoding="utf-8")) != _fingerprint(fresh):
        pytest.fail(
            f"{filename} is stale: the docs embed it as the live output of "
            f"{module_name}, and it no longer is. "
            "Run: python scripts/build_demo_examples.py"
        )
