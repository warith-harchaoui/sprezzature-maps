#!/usr/bin/env python3
"""Regenerate the twelve maps the website's gallery vendors, in one command.

Author: Warith HARCHAOUI

The gallery lives in a different repository. It does not import this package;
it vendors finished ``.svg`` and ``.png`` files and serves them directly, and
each one is referenced twice -- once from the English page, once from the
French. That arrangement is right for a static site and it has one failure
mode, which this script exists to close.

For months, seven of the twelve had no generator anywhere. They were
rendered once, by hand, before this package was split out of the monorepo,
and carried along as files. When the ``0.10.1`` fix went out, the five with
builders were regenerated in one command and the other seven were not,
because nobody could. A file nobody can rebuild is a file nobody can
correct, and the gallery quietly drifted into showing two different vintages
of the same generator side by side.

So: every map the gallery carries is built here, from the same builders the
test suite checks, under the exact filenames the site's markup already
references. **Those names are a contract with another repository** -- the
pages link them by hand, in two languages -- so they are declared explicitly
below rather than derived, and a target directory holding a name this script
does not produce is reported rather than silently left stale.

    python scripts/publish_gallery.py                    # the default sibling path
    python scripts/publish_gallery.py path/to/web/img/maps
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_choropleth_examples import BUILDERS as CHOROPLETH_BUILDERS  # noqa: E402
from build_situation_examples import BUILDERS as PLATE_BUILDERS  # noqa: E402
from build_situation_examples import _render_png  # noqa: E402
from make_situation_map import build_map, validate_config  # noqa: E402

#: Raster width for a situation plate, in pixels. Matches the five plates
#: already in the gallery; the site caps its figure at about 1024 CSS pixels,
#: so this is a little over 1x on a retina display and sharp on both.
PLATE_PNG_WIDTH = 1300

#: Raster width for a choropleth. Narrower because a world map at gallery
#: size is read as a whole rather than inspected, and the extra pixels buy
#: nothing a reader will use.
CHOROPLETH_PNG_WIDTH = 900

#: Where the gallery lives when both repositories are checked out side by
#: side, which is the normal arrangement.
DEFAULT_TARGET = REPO.parent / "sprezzature" / "web" / "img" / "maps"


def _published_names() -> dict[str, str]:
    """Return ``published stem -> builder key`` for every map the gallery shows."""
    names = {f"situation-{key}": key for key in PLATE_BUILDERS}
    names.update({f"choropleth-{key}": key for key in CHOROPLETH_BUILDERS})
    return names


def main(argv: list[str]) -> int:
    target = Path(argv[0]).expanduser().resolve() if argv else DEFAULT_TARGET
    if not target.is_dir():
        raise SystemExit(
            f"no such directory: {target}\n"
            f"Usage: python {Path(__file__).name} [path/to/web/img/maps]"
        )

    written: list[str] = []
    for stem, key in sorted(_published_names().items()):
        svg_path = target / f"{stem}.svg"
        if stem.startswith("situation-"):
            cfg = PLATE_BUILDERS[key]()
            # The same validation the example builder runs. A config that the
            # generator would refuse must never reach another repository.
            validate_config(cfg)
            svg_path.write_text(build_map(cfg), encoding="utf-8")
            width = PLATE_PNG_WIDTH
        else:
            svg_path.write_text(CHOROPLETH_BUILDERS[key](), encoding="utf-8")
            width = CHOROPLETH_PNG_WIDTH
        png_path = target / f"{stem}.png"
        if not _render_png(svg_path, png_path, width=width):
            raise SystemExit(f"could not rasterise {stem}; the gallery needs both files")
        written.append(stem)
        print(f"  {stem:28s} {svg_path.stat().st_size // 1024:5d} KB svg  "
              f"{png_path.stat().st_size // 1024:5d} KB png")

    # A name sitting in the gallery that nothing here produces is the exact
    # situation this script was written to end, so say so rather than leave
    # it to be discovered again in six months.
    stale = sorted(
        p.stem for p in target.glob("*.svg") if p.stem not in _published_names()
    )
    if stale:
        print(
            f"\n{len(stale)} map(s) in {target} that no builder here produces, "
            f"left untouched: {', '.join(stale)}"
        )
    print(f"\nwrote {len(written)} maps to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
