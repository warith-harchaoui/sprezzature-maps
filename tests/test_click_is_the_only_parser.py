"""
Every command this package installs is click, and nothing here imports argparse.

The suite decided on 2026-11-04 that its own command lines are click and only
click. The front door had moved on 2026-10-25, but two parsers survived it:
``sprezzature-maps audit`` ran an argparse parser behind its click
sub-command, and ``sprezzature-maps-mcp`` parsed its ``--host`` and
``--port`` with argparse. Two more lived in the packaged generators
(``scripts/_render.py`` and ``scripts/make_situation_map.py``). Each one
answered ``--help`` in a different dialect, lowercase ``usage:`` and all,
and nothing failed, because nothing asked.

Two checks, one per way it comes back:

* every ``[project.scripts]`` entry answers ``--help`` with exit 0 and a
  click usage line (``Usage:``, capitalised; argparse writes ``usage:``);
* no module of the package, nor of the packaged generators, imports
  argparse. An AST walk rather than a substring, so a docstring that tells
  the history of the old parser does not trip it.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The trees whose modules ship in the wheel and carry Python code.
_SHIPPED = (REPO_ROOT / "sprezzature_maps", REPO_ROOT / "scripts")

_ENTRY_POINT = re.compile(r'^([\w.-]+)\s*=\s*"([\w.]+):(\w+)"', re.M)


def _scripts() -> list[tuple[str, str, str]]:
    """Every (command, module, function) under ``[project.scripts]``."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S)
    assert block is not None, "pyproject.toml has no [project.scripts] table"
    return _ENTRY_POINT.findall(block.group(1))


def test_the_manifest_declares_commands() -> None:
    """A parametrised test over an empty list passes by having nothing to do."""
    assert len(_scripts()) >= 4


@pytest.mark.parametrize("command,module,func", _scripts(), ids=lambda v: str(v))
def test_every_command_answers_help_in_click(command: str, module: str, func: str) -> None:
    """``<command> --help`` exits 0 and prints click's ``Usage:`` line."""
    code = (
        "import sys\n"
        f"from {module} import {func} as entry\n"
        f"sys.argv = [{command!r}, '--help']\n"
        "sys.exit(entry(['--help']))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr[-600:]
    assert done.stdout.startswith("Usage:"), (
        f"{command} --help does not open on click's usage line:\n{done.stdout[:300]}"
    )


def _imports_argparse(path: Path) -> bool:
    """Whether ``path`` imports argparse anywhere, at any depth."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] == "argparse" for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "argparse":
            return True
    return False


def test_no_shipped_module_imports_argparse() -> None:
    """The package and its generators parse their arguments with click."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for root in _SHIPPED
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts and _imports_argparse(path)
    ]
    assert not offenders, f"argparse is imported by: {offenders}"


def test_the_walk_sees_an_argparse_import(tmp_path: Path) -> None:
    """Sabotage check: the detector is not a test that tests nothing."""
    planted = tmp_path / "planted.py"
    planted.write_text("def f():\n    import argparse\n    return argparse\n", encoding="utf-8")
    assert _imports_argparse(planted)
    clean = tmp_path / "clean.py"
    clean.write_text('"""argparse is gone."""\nimport click\n', encoding="utf-8")
    assert not _imports_argparse(clean)
