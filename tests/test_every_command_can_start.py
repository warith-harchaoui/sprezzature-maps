"""
A command this package installs has to be able to start.

``pip install`` puts three commands on ``$PATH``. Each is a one-line wrapper
generated from ``[project.scripts]``: it imports a module and calls a function.
Three things can break that before any argument is parsed —

* an import at module load that needs an extra the user did not install;
* an entry point naming a function that moved or was renamed;
* a ``prog=`` naming the module instead of the command, so the help a reader
  gets back is about a file they cannot run.

None of them shows up in a unit test of the code underneath, because the code
underneath is fine. All three show up the first time somebody types the command
with ``--help``, which is why this runs exactly that.

Why it arrived late
-------------------
The monorepo asked, from the one place that sees all nine bricks, whether each
one's suite ever runs a command it installs. Four did not, this among them, and
the comment in the monorepo had been asserting the opposite — "its own suite
checks their --help there". It is this suite's job and it was not being done.

Both outcomes are accepted. Exit 0 with a help text that names the command,
which is the case for all three once the package is installed — ``make-map``
and its Click twin and the MCP server. Or a clean refusal naming the extra to
install, which is what a front door must do when its own library is the extra
that is missing. What is refused is everything else: a traceback, silence, or a
usage line about a module.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "sprezzature-maps"

#: ``name = "module:function"`` under ``[project.scripts]``. Read from the
#: manifest rather than from the installed metadata: the manifest is what a
#: release will ship, and it is readable from a checkout that was never
#: installed.
_ENTRY_POINT = re.compile(r'^([\w.-]+)\s*=\s*"([\w.]+):(\w+)"', re.M)


def _commands() -> list[tuple[str, str, str]]:
    """Every (command, module, function) this package declares."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if block is None:
        return []
    return _ENTRY_POINT.findall(block.group(1))


def _run(command: str, module: str, function: str) -> subprocess.CompletedProcess:
    """`command --help`, through the wrapper if installed, as it would be if not.

    On ``$PATH`` the real wrapper runs, which is the thing being tested. In a
    checkout where the package is importable but its scripts directory is not
    on the path, the same three lines the wrapper would contain are run instead,
    so the test says the same thing in both places.
    """
    found = shutil.which(command)
    if found is not None:
        return subprocess.run([found, "--help"], capture_output=True, text=True)
    code = (
        "import sys\n"
        f"sys.argv = [{command!r}, '--help']\n"
        f"from {module} import {function}\n"
        f"raise SystemExit({function}())\n"
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)


def test_the_manifest_declares_commands() -> None:
    """An empty table would make every case below vacuous."""
    found = _commands()
    assert found, (
        f"{PACKAGE}/pyproject.toml declares no [project.scripts]. Either the "
        f"table moved or this package stopped installing commands; both make "
        f"the cases below collect nothing, which pytest reports as a skip and "
        f"a reader takes for a pass."
    )


@pytest.mark.parametrize("command,module,function", _commands(), ids=lambda v: v)
def test_the_command_starts_and_names_itself(
    command: str, module: str, function: str
) -> None:
    """``--help`` is the cheapest proof that a command is callable at all."""
    proc = _run(command, module, function)
    output = proc.stdout + proc.stderr

    # "This package is not installed in this environment" is the one condition
    # that is about the machine rather than the code. Read off the outcome
    # rather than asked in advance: ``find_spec`` raises ValueError for a
    # package whose ``__spec__`` is None, which is the case for the ``scripts/``
    # directory this project maps to an importable name at build time.
    top = module.split(".")[0]
    if f"No module named '{top}'" in output:
        pytest.skip(f"{PACKAGE} is not installed here: pip install -e '.[dev]'")

    assert "Traceback" not in output, (
        f"{command} --help raised:\n{output}"
    )
    assert output.strip(), f"{command} --help printed nothing (exit {proc.returncode})"

    if proc.returncode != 0:
        # The one legitimate refusal: a front door whose own library is an
        # extra. It has to say which one, or the reader is stuck holding a
        # command that will not run and no way to find out why.
        assert "pip install" in output, (
            f"{command} --help exited {proc.returncode} without naming an "
            f"install that would fix it:\n{output}"
        )

    assert command in output, (
        f"{command} --help does not name {command}. A usage line that names "
        f"the module instead sends the reader to a file they cannot run:\n"
        f"{output.splitlines()[0] if output.splitlines() else ''}"
    )
