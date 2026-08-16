"""``make-map``: render a choropleth or situation map from the command line.

A thin dispatcher, built with argparse (Python's standard library for
parsing command-line arguments), that just hands off to the two
generators. Its shape deliberately mirrors the sister
`sprezzature-figures <https://github.com/warith-harchaoui/sprezzature-figures>`_
repository's own ``make-figure`` command, so a user already familiar with
one recognizes the other.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import make_choropleth, make_situation_map


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make-map", description=__doc__)
    sub = parser.add_subparsers(dest="kind", required=True)

    p_choro = sub.add_parser("choropleth", help="World choropleth map.")
    p_choro.add_argument("--data", help="JSON file of rows ({id, value}); defaults to demo data.")
    p_choro.add_argument("--out", help="Output SVG path.")
    p_choro.add_argument("--title", default=None)

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
        path = make_choropleth(**kwargs)
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
