"""Every third-party module this repository imports is declared as a dependency.

Ported from `sprezzature-figures`, which is what ``CODING.md`` means by "a
pattern proven on one side is the default for the other". It found a real
defect here on its first run, which is the only reason worth porting a test.

What it found
-------------
``sprezzature_maps/api.py`` does an unguarded ``from pydantic import BaseModel,
Field`` at module level, and ``pydantic`` appeared in **no**
``pyproject.toml`` table. It resolved anyway, because ``fastapi`` requires it —
so three readers all had nothing to say:

* **pip** never had to resolve it: it arrives by transitivity, so a clean venv
  installs it and the gap is invisible.
* **mypy** reads an installed package as installed; nothing about the import
  is wrong.
* **CI** imports ``api.py`` and it works, for the same transitive reason.

And the exposure is real, measured on the index rather than argued: **fastapi
0.115.0, which this package's ``fastapi>=0.115`` floor permits, requires
``pydantic>=1.7.4,<3.0.0``**. A resolver may therefore hand this package
pydantic 1.x, where ``BaseModel`` and ``Field`` both exist and the API around
them does not. The import would succeed and the behaviour would differ, which
is the worst shape a dependency defect takes — louder is better.

So: walk every ``import`` in the hand-written code and assert each
third-party top-level name resolves to something the manifest declares, in any
table.

What it deliberately does not check
-----------------------------------
The converse. A distribution declared and imported nowhere is a different
question — it may be there for a generator that lives elsewhere, or for a
transitive floor this package wants to pin — and asserting that direction
would be a decision rather than a defect. ``sprezzature-figures`` says the
same thing in its own copy, with the five it measured.

``tests/`` is out of scope: a test may import something only the developer lane
has, and ``[dev]`` is where that is declared.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# `tomllib` is stdlib only from 3.11 and this package supports 3.10, where a
# bare import fails collection of the whole file. `tomli` is the same parser
# under its pre-stdlib name.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The directories of hand-written code. ``tests/`` is deliberately out, for
#: the reason the module docstring gives.
_CODE_DIRS = ("sprezzature_maps", "scripts")

#: Import names that differ from the distribution providing them. Each entry
#: is a fact about PyPI, not a preference, and leaving one out makes this test
#: fail rather than pass -- the safe direction. The rest normalise
#: mechanically: ``resvg_py`` -> ``resvg-py``, ``fastapi_mcp`` ->
#: ``fastapi-mcp``, ``sprezzature_figures`` -> ``sprezzature-figures``.
_IMPORT_TO_DISTRIBUTION = {
    "PIL": "pillow",
    "yaml": "pyyaml",
}


def _normalise(name: str) -> str:
    """PEP 503 normalisation: lowercase, and any run of ``-_.`` to a hyphen."""
    out: list[str] = []
    for char in name.lower():
        if char in "-_.":
            if out and out[-1] == "-":
                continue
            out.append("-")
        else:
            out.append(char)
    return "".join(out)


def _declared_distributions() -> set[str]:
    """Every distribution name ``pyproject.toml`` declares, from every table."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle).get("project", {})
    requirements = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        requirements.extend(extra)
    names = set()
    for requirement in requirements:
        # "uvicorn[standard]>=0.30" -> "uvicorn"; "tomli; python_version < …" -> "tomli"
        head = requirement.split(";")[0].strip()
        for separator in ("[", "<", ">", "=", "!", "~", " "):
            head = head.split(separator)[0]
        if head:
            names.add(_normalise(head))
    return names


def _local_module_names() -> set[str]:
    """Names that resolve inside this repository rather than to a distribution.

    The generators put their own directory on ``sys.path`` and import siblings
    by bare name (``from _render import ...``), so every file stem under the
    scanned directories is a local name — as is each directory, and the three
    package names the wheel publishes them under.
    """
    names = {
        "sprezzature_maps",
        "sprezzature_maps_scripts",
        "sprezzature_maps_geo",
        "tests",
    }
    for directory in _CODE_DIRS:
        names.add(directory)
        for path in (REPO_ROOT / directory).rglob("*.py"):
            names.add(path.stem)
    return names


def _third_party_imports() -> dict[str, list[str]]:
    """Map every third-party top-level import name to the files importing it."""
    local = _local_module_names()
    found: dict[str, list[str]] = {}
    for directory in _CODE_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    # A relative import resolves inside the package by definition.
                    roots = [] if node.level or not node.module else [node.module.split(".")[0]]
                else:
                    continue
                for root in roots:
                    if root in sys.stdlib_module_names or root in local:
                        continue
                    found.setdefault(root, []).append(str(path.relative_to(REPO_ROOT)))
    return found


def test_the_scan_finds_the_imports_it_is_supposed_to_check() -> None:
    """The walk reaches real code, so a green result is not an empty one.

    A scanner that silently matches nothing is the failure mode this whole
    file exists to prevent in the dependency table; it would be absurd for the
    guard to have it too. The floors are low enough to survive ordinary
    refactoring and high enough that a broken walk cannot pass.
    """
    scanned = sum(1 for directory in _CODE_DIRS for _ in (REPO_ROOT / directory).rglob("*.py"))
    assert scanned > 25, f"only {scanned} Python files found in {_CODE_DIRS}"
    imports = _third_party_imports()
    assert len(imports) > 8, f"only {len(imports)} third-party imports found: {sorted(imports)}"
    assert "numpy" in imports, "numpy is imported by the generators; the walk missed it"
    assert "pyproj" in imports, "pyproj is what makes these real projections; the walk missed it"
    assert _declared_distributions() >= {"numpy", "pyproj", "shapely", "click"}, (
        "the pyproject table did not parse into the base dependencies"
    )


def test_no_module_is_imported_without_being_declared() -> None:
    """Every third-party import maps to a distribution ``pyproject.toml`` asks for."""
    declared = _declared_distributions()
    undeclared: list[str] = []
    for name, files in sorted(_third_party_imports().items()):
        distribution = _IMPORT_TO_DISTRIBUTION.get(name, _normalise(name))
        if distribution not in declared:
            where = ", ".join(sorted(set(files))[:3])
            undeclared.append(f"{name} (as {distribution!r}) imported by {where}")
    assert not undeclared, (
        "imported but declared in no pyproject.toml table, so the manifest does not "
        "say what the code needs and a resolver decides it instead:\n  "
        + "\n  ".join(undeclared)
    )
