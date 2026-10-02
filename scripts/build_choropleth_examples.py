#!/usr/bin/env python3
"""One builder for every shipped choropleth example, so the gallery has a recipe.

Author: Warith HARCHAOUI

The website's gallery carried three choropleth variants --
``choropleth-sequential``, ``choropleth-diverging`` and ``choropleth-large``
-- for months with no script in either repository that produced them. They
were rendered once, by hand, before this package was split out of the
monorepo, and carried along as files ever since.

That is output without a recipe, and the cost is not hypothetical: when the
``0.10.1`` fix went out, the five plates that *did* have builders were
regenerated in one command and these three were not, because nobody could.
A file nobody can rebuild is a file nobody can correct.

The three differ in exactly one decision each, which is the point -- they
exist to show what the same data looks like under a different reading:

- ``sequential``: one indicator, low to high, on the house blue ramp. The
  default, and the right choice whenever the data has no meaningful middle.
- ``diverging``: the same countries against a reference value, so the
  question becomes "above or below", and the ramp has to carry a direction
  as well as a magnitude.
- ``large``: the sequential reading at poster size. It is here because
  scale changes which decisions are wrong -- simplification tolerance, label
  density and stroke weight that look right at 745px do not at 2000px.

    python scripts/build_choropleth_examples.py                 # all three
    python scripts/build_choropleth_examples.py diverging       # just one
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from make_choropleth import DEMO_DATA, build_svg  # noqa: E402

SHIP = REPO / "assets" / "choropleths"

#: The value the diverging reading measures against.
#:
#: The original artifact's data ran -40.0 to 39.4 and the transform that
#: produced it is lost, so this does not try to reproduce it byte for byte --
#: it states a rule instead. Centring the synthetic index on 50 turns "how
#: exposed is this country" into "more or less exposed than the midpoint",
#: which is the question a diverging ramp exists to answer, and the scaling
#: keeps the result in the same rough range the old file used so the figure
#: stays recognisably the one the documentation describes.
_DIVERGING_CENTRE: float = 50.0
_DIVERGING_SCALE: float = 0.8


def _diverging_rows() -> list[dict[str, Any]]:
    """Recentre the synthetic index so it reads as a signed departure."""
    return [
        {"id": row["id"], "value": round((row["value"] - _DIVERGING_CENTRE) * _DIVERGING_SCALE, 1)}
        for row in DEMO_DATA
    ]


def build_sequential() -> str:
    """One indicator, low to high: the default reading."""
    return build_svg(
        title="Global Exposure Index, by Country",
        subtitle="Synthetic illustrative values; sequential reading, low to high",
    )


def build_diverging() -> str:
    """The same countries as a signed departure from the midpoint."""
    return build_svg(
        data=_diverging_rows(),
        title="Illustrative Growth Rate, by Country",
        subtitle="Synthetic illustrative values; diverging reading about zero",
        diverging=True,
    )


def build_large() -> str:
    """The sequential reading at poster size.

    Not simply the same call with bigger numbers: at this width the default
    simplification tolerance -- which is measured in *screen* pixels -- would
    throw away detail the extra resolution exists to show, so it tightens
    with the canvas.
    """
    return build_svg(
        title="Global Exposure Index, by Country",
        subtitle="Synthetic illustrative values; sequential reading at poster scale",
        width=2000,
        height=1128,
        simplify=0.1,
    )


BUILDERS = {
    "sequential": build_sequential,
    "diverging": build_diverging,
    "large": build_large,
}


def main(argv: list[str]) -> int:
    names = argv or list(BUILDERS)
    unknown = [n for n in names if n not in BUILDERS]
    if unknown:
        raise SystemExit(f"unknown example(s) {unknown}; known: {', '.join(BUILDERS)}")
    SHIP.mkdir(parents=True, exist_ok=True)
    for name in names:
        svg = BUILDERS[name]()
        path = SHIP / f"choropleth-{name}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path.name}  ({len(svg) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
