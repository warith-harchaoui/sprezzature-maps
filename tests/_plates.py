"""
Render each distinct plate once per process, instead of once per assertion.

The suite is slow for one reason, and it is not the renderer. There are
**nine** distinct situation plates, a render costs about three seconds once
the elevation tier is decoded, and the tests draw them roughly a hundred
times -- every test that wants to look at a plate calls ``build_map`` again
from scratch. 525 tests, 982 seconds serially, and almost all of it redrawing
pictures that were already drawn.

That diagnosis is not new: the 0.18.0 notes name it exactly ("one core doing
the same nine plates a hundred times"). What happened then was that the run
was *scheduled* better -- ``pytest -n auto``, 15m43s to 2m32s -- which spends
the same work on more cores. This spends less work.

Why the cache is keyed on config equality, and not on a name or a hash
---------------------------------------------------------------------
A key has to be exact. Hashing a canonicalised config was the obvious choice
and is wrong here: five of the nine configs do not survive a strict JSON
round-trip (tuples come back as lists), so the serialisation is lossy, and a
lossy key can hand a test the wrong plate -- a failure that would look like a
renderer bug for as long as it took to find. Keying on the builder *name*
fails differently: several tests mutate the config after building it and
before rendering, and those must not share anything.

Plain ``==`` on the dicts is exact, costs nothing next to a three-second
render, and is automatically right in both cases: a mutated config simply
matches nothing and renders fresh, exactly as it does today.

Why the mutation is replayed
----------------------------
``build_map`` writes two internal keys back into the caller's config --
``_relief_tone`` and ``_plate``. A cache hit that skipped the render would
also skip that write, so a caller's dict would come back in a different state
depending on whether some earlier test happened to draw the same plate. That
is the kind of order-dependence a test suite must never acquire. The
post-render config is stored alongside the SVG and copied back on a hit, so
``plate(cfg)`` is indistinguishable from ``build_map(cfg)`` from the caller's
side.

What this is not for
--------------------
Tests that render the same config **twice on purpose** -- to prove the result
is deterministic, or that a stamp is the only difference an option makes --
must keep calling ``build_map`` directly. A cache would hand them the same
string twice and the assertion would pass without testing anything. There are
six such tests; they are left alone, and this note is the reason.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import copy
import functools
import hashlib
import importlib.util
import os
import pickle
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

#: Where plates drawn by one process are left for the others to find.
#:
#: The in-memory cache below is per process, and ``pytest -n`` means one
#: process per worker -- so on four workers the nine plates were drawn nearly
#: four times over, and the parallel run barely moved while the serial run
#: halved. Sharing them on disk is what makes the two compose: the first
#: worker to need a plate draws it, the rest read it, and a worker that needs
#: none never even decodes the 1.68 GB elevation tier.
#:
#: Under ``.pytest_cache/`` because that is already gitignored and already
#: understood to be disposable. CI starts with it empty, which is correct: the
#: sharing that matters is *within* a run.
_DISK_CACHE = REPO / ".pytest_cache" / "plates"


def _code_fingerprint() -> str:
    """A digest of every generator source file, as the cache's outer key.

    Without it this cache would be the exact trap ``test_a_plate_can_prove_
    what_drew_it`` exists to describe: a plate is a function of its config
    **and the code that drew it**, so a config-keyed file written before an
    edit would be served after it, and a test would assert against a drawing
    the current code cannot produce. Changing any file under ``scripts/``
    moves every key, which is blunt and right -- a stale plate is a wrong
    answer, a redundant render is only a slow one.
    """
    digest = hashlib.sha256()
    for path in sorted(SCRIPTS.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


@functools.cache
def _cache_dir() -> Path:
    directory = _DISK_CACHE / _code_fingerprint()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _config_key(config: dict[str, Any]) -> str:
    """An index into the cache directory -- not a proof of equality.

    ``repr`` is lossy enough that two different configs could, in principle,
    land on one key, so the file it points at carries the pristine config and
    is compared with ``==`` before its SVG is trusted. The hash only decides
    which file to open.
    """
    return hashlib.sha256(repr(_canonical(config)).encode()).hexdigest()[:24]


def _canonical(value: Any) -> Any:
    """Order-independent form, so two equal dicts always key the same."""
    if isinstance(value, dict):
        return sorted((str(k), _canonical(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def _read_from_disk(config: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    path = _cache_dir() / f"{_config_key(config)}.pickle"
    try:
        pristine, after, svg = pickle.loads(path.read_bytes())
    except (OSError, pickle.UnpicklingError, ValueError, EOFError):
        return None
    if pristine != config:  # a hash collision, or a half-written file
        return None
    return after, svg


def _write_to_disk(pristine: dict[str, Any], after: dict[str, Any], svg: str) -> None:
    """Written to a unique name and renamed into place.

    Workers race for the same plate, and a half-written file read by another
    worker would be a corrupt plate rather than a slow one. ``os.replace`` is
    atomic on every platform this runs on, so a reader sees either the old
    absence or the whole file.
    """
    directory = _cache_dir()
    final = directory / f"{_config_key(pristine)}.pickle"
    temporary = directory / f".{os.getpid()}-{final.name}"
    try:
        temporary.write_bytes(pickle.dumps((pristine, after, svg)))
        os.replace(temporary, final)
    except OSError:
        temporary.unlink(missing_ok=True)  # a cache is allowed to fail


#: ``(config as given, config as left by the render, svg)``, one row per
#: distinct config this process has drawn. A list rather than a dict because
#: the key is a dict: unhashable, and deliberately compared with ``==``.
_CACHE: list[tuple[dict[str, Any], dict[str, Any], str]] = []

_MODULE: Any = None


def _msm() -> Any:
    """The generator module, loaded once for the whole process.

    Each test file loads its own copy through its local ``_load`` helper,
    which re-executes the module and replaces ``sys.modules`` wholesale. That
    is harmless but it is also why the cache lives here rather than being
    attached to any one of those copies.
    """
    global _MODULE
    if _MODULE is None:
        spec = importlib.util.spec_from_file_location(
            "make_situation_map", SCRIPTS / "make_situation_map.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("make_situation_map", module)
        spec.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def plate(config: dict[str, Any]) -> str:
    """``build_map(config)``, drawn once per distinct config per process.

    Parameters
    ----------
    config : dict
        A situation-map config, typically ``BUILDERS[name]()``, optionally
        modified first. Mutated in place exactly as ``build_map`` mutates it,
        including on a cache hit.

    Returns
    -------
    str
        The SVG text. The *same* string object on a hit, which is safe
        because strings are immutable -- a test that parses it gets its own
        tree, and a test that slices it gets its own slice.
    """
    for pristine, after, svg in _CACHE:
        if pristine == config:
            config.clear()
            config.update(copy.deepcopy(after))
            return svg

    pristine = copy.deepcopy(config)

    found = _read_from_disk(pristine)
    if found is not None:
        after, svg = found
        _CACHE.append((pristine, after, svg))
        config.clear()
        config.update(copy.deepcopy(after))
        return svg

    svg = _msm().build_map(config)
    after = copy.deepcopy(config)
    _CACHE.append((pristine, after, svg))
    _write_to_disk(pristine, after, svg)
    return svg


def cached_plate_count() -> int:
    """How many distinct configs this process has drawn -- for the test that
    checks the cache is actually being hit rather than silently bypassed."""
    return len(_CACHE)
