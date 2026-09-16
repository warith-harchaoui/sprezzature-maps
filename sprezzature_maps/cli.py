"""``make-map``: render a choropleth or situation map from the command line.

A thin dispatcher, built with argparse (Python's standard library for
parsing command-line arguments), that just hands off to the two
generators. Its shape deliberately mirrors the sister
`sprezzature-figures <https://github.com/warith-harchaoui/sprezzature-figures>`_
repository's own ``make-figure`` command, so a user already familiar with
one recognizes the other.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import make_choropleth, make_density, make_situation_map


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make-map", description=__doc__)
    sub = parser.add_subparsers(dest="kind", required=True)

    p_choro = sub.add_parser("choropleth", help="World choropleth map.")
    p_choro.add_argument("--data", help="JSON file of rows ({id, value}); defaults to demo data.")
    p_choro.add_argument("--out", help="Output SVG path.")
    p_choro.add_argument("--title", default=None)
    p_choro.add_argument(
        "--classes",
        type=int,
        default=None,
        metavar="K",
        help="Class the values into K colour classes instead of stretching the ramp "
        "linearly from min to max. On skewed data -- which most indicators are -- "
        "the linear default puts most territories in the bottom of the ramp. "
        "Omit for the unclassed ramp.",
    )
    p_choro.add_argument(
        "--no-cities",
        action="store_true",
        help="Do not name the major cities. They are drawn by default: a map with "
        "nobody on it gives a reader nowhere to stand, and the selection is by "
        "cartographic prominence, not by 'is it a capital'.",
    )
    p_choro.add_argument(
        "--no-rivers",
        action="store_true",
        help="Do not draw the major rivers. They are drawn by default, tapered by "
        "prominence so a trunk reads thick and a tributary thin.",
    )
    p_choro.add_argument(
        "--breaks",
        default=None,
        metavar="V,V,V",
        help="Class boundaries you choose yourself, comma-separated, e.g. '5,10,25'. "
        "Overrides --classes/--method: some bands have to mean something outside the "
        "data (a regulatory threshold, a figure already published) and no algorithm "
        "will land on them by luck. The legend then says the breaks were given.",
    )
    p_choro.add_argument(
        "--method",
        default="quantile",
        choices=["quantile", "equal", "jenks", "headtail"],
        help="How to place the class boundaries, when --classes is given. "
        "quantile: equal count per class, supports ranking. equal: equal width, "
        "poor on skewed data. jenks: natural breaks, shows the data's own groups. "
        "headtail: for heavy tails. The legend names whichever you pick.",
    )

    p_den = sub.add_parser(
        "density",
        help="Accumulation map: point events binned to a luminous field, no coastline.",
    )
    p_den.add_argument(
        "--points",
        help="JSON file of [[lon, lat], ...] event positions; defaults to demo points.",
    )
    p_den.add_argument("--out", help="Output SVG path.")
    p_den.add_argument("--title", default=None)
    p_den.add_argument(
        "--bins",
        type=int,
        default=None,
        help="Cells across the image. Past roughly 260 the field becomes grain, so the "
        "visual limit arrives before the size limit.",
    )

    p_sit = sub.add_parser("situation_map", help="Layered areas-of-control situation map.")
    p_sit.add_argument("--config", help="YAML config; defaults to the bundled demo.")
    p_sit.add_argument("--out", help="Output SVG path.")

    args = parser.parse_args(argv)

    if args.kind == "choropleth":
        kwargs = {}
        if args.data:
            kwargs["data"] = json.loads(Path(args.data).read_text())
        if args.title:
            kwargs["title"] = args.title
        if args.out:
            kwargs["out"] = args.out
        if args.no_cities:
            kwargs["cities"] = False
        if args.no_rivers:
            kwargs["rivers"] = False
        if args.breaks:
            kwargs["breaks"] = [float(v) for v in args.breaks.split(",") if v.strip()]
        elif args.classes:
            kwargs["classes"] = args.classes
            kwargs["method"] = args.method
        path = make_choropleth(**kwargs)
    elif args.kind == "density":
        kwargs = {}
        if args.points:
            kwargs["points"] = [tuple(p) for p in json.loads(Path(args.points).read_text())]
        if args.title:
            kwargs["title"] = args.title
        if args.out:
            kwargs["out"] = args.out
        if args.bins:
            kwargs["bins"] = args.bins
        path = make_density(**kwargs)
    else:
        kwargs = {}
        if args.config:
            import yaml

            kwargs["config"] = yaml.safe_load(Path(args.config).read_text())
        if args.out:
            kwargs["out"] = args.out
        path = make_situation_map(**kwargs)

    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
