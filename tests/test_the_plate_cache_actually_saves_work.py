"""
The cache in ``tests/_plates.py`` is an optimisation, and an optimisation that
quietly stops working is worse than none: the suite still passes, so nothing
says the fifteen minutes came back.

Two ways it can stop working without failing. A call site drifts back to
``build_map`` directly -- the obvious one, and the one a rebase does by
accident. Or the cache keeps missing: a config that should match stops
matching, every lookup falls through to a real render, and the only symptom is
that CI is slow again.

So these check the saving itself rather than the mechanism.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import ast
import re
import time
from pathlib import Path

import pytest
from _plates import cached_plate_count, plate

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent

#: Tests that must keep calling ``build_map`` directly, with the reason. A
#: cache would hand the first group the same string twice and make their
#: assertion vacuous; it would skip the render the second group is listening
#: to; and the third asks whether the plate changes when the *code* changes,
#: which a config-keyed cache cannot know.
MUST_RENDER_FOR_REAL = {
    # Two renders compared against each other. A cache returns the same string
    # object twice and the assertion stops asserting anything.
    "test_the_drawing_is_untouched_by_the_print_width": "compares two renders",
    "test_attribution_layer_only_credits_osm_when_in_view": "compares two renders",
    "test_the_plate_names_the_states_of_its_own_year": "compares two renders",
    "test_vertices_below_the_output_resolution_are_not_written": "compares three renders",
    # Listening for a warning the render emits on its way. A cache hit does no
    # render, so it emits nothing, and the test fails with "DID NOT WARN" --
    # which is how this whole category was discovered.
    "test_a_named_plate_overrides_config_colours_audibly": "listens for a warning",
    "test_a_screen_plate_is_told_it_cannot_be_printed": "listens for a warning",
    "test_the_warning_names_the_canvas_width_that_would_fix_it": "listens for a warning",
    "test_the_warning_is_a_warning_and_not_a_refusal": "asserts on warnings raised",
    "test_a_plate_built_for_the_page_says_nothing": "asserts no warning is raised",
    "test_the_root_carries_the_physical_width": "asserts no warning is raised",
    "test_the_aspect_ratio_survives_the_conversion": "asserts no warning is raised",
    # A helper, not a test: it wraps the render in `pytest.warns` for the
    # callers below it, so it is the real renderer for all of them.
    "_plate": "helper that renders inside pytest.warns",
}

#: Files exempt wholesale, with the reason. ``test_a_plate_can_prove_what_drew_it``
#: exists to show that a plate is a function of its config *and the code and the
#: data behind it*; a cache keyed on the config alone cannot see the other two
#: change, so it is wrong there by the file's own thesis rather than by accident.
EXEMPT_FILES = {"test_a_plate_can_prove_what_drew_it.py"}

_DIRECT_CALL = re.compile(r"\b\w+\.build_map\(")


def _functions_calling_build_map_directly() -> dict[str, str]:
    """``{test name: file}`` for every test still rendering without the cache."""
    found: dict[str, str] = {}
    for path in sorted(TESTS.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        if "build_map(" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef):
                continue
            body = ast.get_source_segment(source, node) or ""
            if _DIRECT_CALL.search(body):
                found[node.name] = path.name
    return found


def test_only_the_tests_that_must_render_for_real_still_do() -> None:
    """Both directions.

    A new direct call is a call site that drifted back and costs three seconds
    every run. A name on the list that no longer renders directly is a test
    that quietly started trusting the cache -- and the list says why each one
    must not.
    """
    direct = _functions_calling_build_map_directly()
    direct = {name: where for name, where in direct.items() if where not in EXEMPT_FILES}
    unexpected = sorted(set(direct) - set(MUST_RENDER_FOR_REAL))
    assert not unexpected, (
        "these render without the cache and are not on the list; either use "
        f"`plate(...)` or say why here: {[(n, direct[n]) for n in unexpected]}"
    )
    stale = sorted(set(MUST_RENDER_FOR_REAL) - set(direct))
    assert not stale, f"listed as needing a real render, but no longer doing one: {stale}"


def test_the_same_config_is_drawn_once_and_then_handed_back() -> None:
    """The saving, measured rather than assumed.

    The config carries a marker nothing else uses, so the first call is a miss
    whatever ran before it. The first draft asked for a pristine ``iberia``
    and was **flaky under xdist**: if another test in the same worker had
    already drawn that plate, the "first" call was a hit and the count never
    moved. A guard that passes or fails on test ordering is not a guard.

    The time threshold is deliberately coarse -- a render is seconds, a dict
    comparison is microseconds -- so this cannot fail for being on a slow
    machine, only for actually re-rendering.
    """
    marker = "cache probe: drawn once"
    config = _builders()["iberia"]()
    config["title"] = marker

    before = cached_plate_count()
    first = plate(config)
    assert cached_plate_count() == before + 1, "the first draw was not recorded"

    again = _builders()["iberia"]()
    again["title"] = marker
    start = time.perf_counter()
    second = plate(again)
    elapsed = time.perf_counter() - start

    assert second == first
    assert cached_plate_count() == before + 1, "an identical config was drawn a second time"
    assert elapsed < 0.5, f"the second lookup took {elapsed:.2f}s -- it re-rendered"


def test_a_config_that_differs_is_not_served_from_the_cache() -> None:
    """The other half: sharing too much is a wrong answer, not a slow one.

    Several tests change a config and render it, and handing one of those the
    unmodified plate would make it pass while testing nothing.
    """
    examples = _builders()
    config = examples["iberia"]()
    plate(config)

    modified = examples["iberia"]()
    modified["title"] = "a different title entirely"
    before = cached_plate_count()
    other = plate(modified)
    assert cached_plate_count() == before + 1, "a changed config was served from the cache"
    assert "a different title entirely" in other


def _builders() -> dict:
    import importlib.util
    import sys

    scripts = REPO / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "build_situation_examples", scripts / "build_situation_examples.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("build_situation_examples", module)
    spec.loader.exec_module(module)
    return module.BUILDERS


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
