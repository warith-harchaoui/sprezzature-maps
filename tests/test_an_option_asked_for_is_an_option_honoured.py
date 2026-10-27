"""
An option this package offers either works or says it does not apply.

``--language`` sat in every map generator's ``--help`` and was honoured by
none of them. The parser accepted ``fr``, ``render_cli`` passed the argument
only to generators whose ``build_svg`` declared it, no generator declared it,
and the option fell on the floor. The exit code was 0 and the file was
English.

That is the worst of the three possible behaviours. A flag that errors sends
you to read; a flag that works gives you French; a flag that is accepted and
dropped gives you an English map you believe is French, and ships it into a
French page. Nothing anywhere said no.

The dropping was deliberate and the reasoning was sound: passing an option
only to the generators that declare it lets a package adopt one generator at
a time without breaking the rest. The error is doing that when somebody
**asked**. Silence is right for a default and wrong for a request.

Two halves, both checked here, because they fail apart. The guard without the
feature means `--language fr` always errors and French is unreachable. The
feature without the guard means the next generator to not adopt it goes
quietly back to lying.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _generators() -> list[Path]:
    return sorted(p for p in SCRIPTS.glob("make_*.py")
                  if "def build_svg" in p.read_text(encoding="utf-8"))


def _build_svg(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module.build_svg


@pytest.mark.parametrize("generator", _generators(), ids=lambda p: p.name)
def test_an_unhonoured_language_is_refused_not_dropped(generator: Path, tmp_path: Path) -> None:
    """Either the generator speaks French, or asking for it fails loudly."""
    out = tmp_path / "x.svg"
    done = subprocess.run(
        [sys.executable, str(generator), "--language", "fr", "--out", str(out)],
        capture_output=True, text=True, cwd=REPO, timeout=600,
    )
    speaks = "language" in inspect.signature(_build_svg(generator)).parameters
    if speaks:
        assert done.returncode == 0, done.stderr[-400:]
        return
    assert done.returncode != 0, (
        f"{generator.name} accepted --language fr and does not implement it. "
        f"That produces an English file somebody believes is French."
    )
    assert "does not accept it" in done.stderr, done.stderr[-400:]


def test_the_density_plate_actually_speaks_french(tmp_path: Path) -> None:
    """The half that makes the answer yes rather than a better no."""
    build_svg = _build_svg(SCRIPTS / "make_density.py")
    if "language" not in inspect.signature(build_svg).parameters:
        pytest.skip("make_density has not adopted --language")

    english = build_svg(bins=12, width=400)
    french = build_svg(bins=12, width=400, language="fr")

    assert english != french, "the language argument changed nothing"
    assert "Où la foudre est tombée" in french
    assert "Where the lightning fell" in english
    # The legend is the piece most easily left behind: it is assembled from
    # fragments rather than taken from one string.
    assert "moins" in french and "par cellule" in french
    assert "peak" not in french, "an English word survived in the French plate"


def test_an_unknown_language_is_refused_rather_than_guessed() -> None:
    build_svg = _build_svg(SCRIPTS / "make_density.py")
    if "language" not in inspect.signature(build_svg).parameters:
        pytest.skip("make_density has not adopted --language")
    with pytest.raises(ValueError, match="no chrome for"):
        build_svg(bins=8, width=300, language="es")


def test_a_caller_can_still_override_any_single_string() -> None:
    """Translating the defaults must not take the arguments away.

    The chrome words are defaults, not a wall: a caller drawing a map of
    something other than lightning passes its own title and keeps the
    translated legend underneath.
    """
    build_svg = _build_svg(SCRIPTS / "make_density.py")
    if "language" not in inspect.signature(build_svg).parameters:
        pytest.skip("make_density has not adopted --language")
    svg = build_svg(bins=8, width=300, language="fr", title="Les séismes de 2026")
    assert "Les séismes de 2026" in svg
    assert "par cellule" in svg
