"""
What the assistant sends a model, and what it must never send.

A cloud backend is one of the things ``best-engine-ai-helper`` can resolve to.
So the description of a dataset that leaves this machine has to be a
description: headers, shapes, counts. Not one cell value — because the file
somebody hands it is, often enough, the reason they wanted a
local tool.

The property is enforced by the *shape* of :class:`DataProfile` rather than by
a filter: there is nowhere in it for a value to sit. These tests check that the
shape holds under data chosen to break it, and that the builders do not route
around it.

Author
------
Project maintainers.
"""

from __future__ import annotations

import csv
from pathlib import Path

from sprezzature_maps.assistant import DataProfile, profile_points, profile_rows
from sprezzature_maps.assistant.prompts import choose_prompt

ASSETS = Path(__file__).resolve().parents[2] / "assets"

SECRETS = [
    {"country": "FRA", "patients": "4117", "hospital": "Hôpital Saint-Louis"},
    {"country": "DEU", "patients": "2903", "hospital": "Charité"},
    {"country": "ESP", "patients": "881", "hospital": "Vall d'Hebron"},
]


def test_no_cell_value_reaches_the_prompt() -> None:
    """Every value in the table, searched for in the text that would be sent."""
    profile = profile_rows(SECRETS, source="patients.csv")
    prompt = choose_prompt("where are the patients", profile)
    leaked = [
        value
        for row in SECRETS
        for value in row.values()
        if value in prompt
    ]
    assert not leaked, f"these values would have been sent to a model: {leaked}"


def test_the_headers_do_reach_it() -> None:
    """The counterpart: a prompt with no headers in it would be useless, and
    this test is what says the one above is not passing for that reason."""
    profile = profile_rows(SECRETS, source="patients.csv")
    prompt = choose_prompt("where are the patients", profile)
    for header in ("country", "patients", "hospital"):
        assert header in prompt
    assert "3 rows" in prompt


def test_the_path_is_reduced_to_a_name() -> None:
    """A path carries a user name and a directory layout. Neither helps choose
    a map, and both are somebody's business."""
    profile = profile_rows(SECRETS, source="/Users/someone/Documents/trial-7/patients.csv")
    assert profile.source == "patients.csv"
    prompt = choose_prompt("", profile)
    assert "someone" not in prompt and "trial-7" not in prompt


def test_coordinates_are_counted_not_listed() -> None:
    """Positions are data too: a density profile must not carry the points."""
    points = [[2.3522, 48.8566], [13.405, 52.52], [-0.1276, 51.5072]]
    profile = profile_points(points, source="cells.jsonl")
    prompt = choose_prompt("density of the cells", profile)
    for point in points:
        for coordinate in point:
            assert str(coordinate) not in prompt
    assert "3 rows" in prompt


def test_the_repository_own_sample_profiles_sanely() -> None:
    """A known-good file, to check the classifier is not merely cautious.

    ``assets/landscape.csv`` is the feature comparison behind the README: one
    column of tool names and fourteen of scores. A classifier that called the
    scores "latitude" would offer a density map of them.
    """
    with (ASSETS / "landscape.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    profile = profile_rows(rows, source="landscape.csv")
    looks = [c.looks_like for c in profile.columns]
    assert looks[0] == "text", "the tool-name column"
    assert set(looks[1:]) == {"number"}, f"the scores classified as {set(looks[1:])}"
    assert "latitude" not in looks and "longitude" not in looks


def test_an_empty_profile_is_describable() -> None:
    """No rows is a state a caller meets before a file is pasted in."""
    prompt = choose_prompt("anything", DataProfile())
    assert "no columns" in prompt
