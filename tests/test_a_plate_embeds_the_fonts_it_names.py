"""
A plate may only name a font it carries, and may only carry one it can get.

Two failures, facing each other, and this package shipped both at once.

**Naming what you do not carry.** The density plate's ``<text>`` asked for
``Georgia, 'Times New Roman', serif`` and a bare ``ui-monospace`` while
``write_svg`` spliced in Roboto and Roboto Mono: 427 KB of base64 in a 525 KB
file, for families nothing referenced. The plate therefore drew in whatever
each reader's machine happened to own -- the same non-determinism that turned
CI red over the export canary.

**Carrying what you cannot get.** The obvious repair was to name Roboto Serif
and embed it. It passed here and failed on CI with ``FileNotFoundError:
RobotoSerif-Variable.woff2``, because ``sprezzature-figures`` deliberately
leaves that family out of its wheel -- 12.2 MB of 18.6 MB, documented in its
``pyproject.toml`` -- while ``available_faces()`` still lists ``serif`` among
the faces it offers. Locally ``sprezzature_figures`` resolves to a source
checkout that has every font; installed, it does not. Works-on-my-machine,
exactly.

So this checks both directions, and it is the second one that needs CI to be
useful: the face keys a generator embeds must resolve to a file that actually
exists in the installed distribution.

Author
------
Project maintainers.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_every_face_the_density_plate_embeds_is_actually_installed() -> None:
    """
    The one that only CI can fail, and the one that matters.

    ``available_faces()`` advertises more than the wheel ships. A generator
    that trusts the advertisement renders fine from a source checkout and
    raises ``FileNotFoundError`` for everybody who installed the package.
    """
    from sprezzature_figures.fonts import font_path

    density = _load("make_density")
    missing = []
    for key in density._EMBED_FACES:
        for woff2 in (True, False):
            try:
                path = font_path(key, woff2=woff2)
            except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                missing.append(f"{key} (woff2={woff2}): {exc}")
                continue
            if not Path(path).is_file():
                missing.append(f"{key} (woff2={woff2}): {path} does not exist")

    assert not missing, (
        "make_density embeds font faces that are not present in the installed "
        "sprezzature-figures:\n  " + "\n  ".join(missing)
        + "\n\nEither the family has to be added to that package's "
        "`[tool.setuptools.package-data]` font globs, or this plate has to "
        "name a family that ships."
    )


def test_the_density_plate_names_only_families_it_embeds(tmp_path: Path) -> None:
    """
    The other direction: a family in the markup with no `@font-face` behind it.

    Rendered through ``make_density`` rather than ``build_svg``, because the
    `@font-face` block is spliced in by ``write_svg`` at the end -- reading the
    builder's output asks the question before the answer exists. (It did, on
    the first run of this test.) The primary family of each stack, the entry
    before the fallbacks, has to be one the plate carries.
    """
    density = _load("make_density")
    out = tmp_path / "density.svg"
    density.make_density(out=out)
    svg = out.read_text(encoding="utf-8")

    embedded = {
        m.strip("'\"")
        for m in re.findall(r"@font-face\{[^}]*?font-family:\s*([^;}]+)", svg)
    }
    assert embedded, "the plate carries no @font-face block at all"

    named = {
        stack.split(",")[0].strip().strip("'\"")
        for stack in re.findall(r'font-family="([^"]+)"', svg)
    }
    unbacked = sorted(named - embedded)
    assert not unbacked, (
        f"these families are named by the markup but not embedded: {unbacked}. "
        f"Embedded: {sorted(embedded)}. A named family with no face behind it "
        "renders from whatever the reader happens to have installed."
    )


def test_nothing_is_embedded_that_nothing_names() -> None:
    """Weight is a cost too: 290 KB of a family the plate never draws."""
    demo = REPO / "assets" / "svg-examples" / "density.svg"
    if not demo.is_file():
        pytest.skip("no rendered density plate to read")
    svg = demo.read_text(encoding="utf-8")

    embedded = {
        m.strip("'\"")
        for m in re.findall(r"@font-face\{[^}]*?font-family:\s*([^;}]+)", svg)
    }
    named = {
        stack.split(",")[0].strip().strip("'\"")
        for stack in re.findall(r'font-family="([^"]+)"', svg)
    }
    unused = sorted(embedded - named)
    assert not unused, (
        f"these families are embedded but never named: {unused}. Each one is "
        "base64 in every copy of the plate, for nothing."
    )
