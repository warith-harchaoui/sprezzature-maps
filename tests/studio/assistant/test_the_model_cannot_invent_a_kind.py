"""
The schemas are the fence, and the registry is what they are made of.

A model asked which map to draw will answer ``heatmap``, or ``bubble_map``, or
``flow_map`` — plausible names for things this package does not render. The
failure is quiet: the JSON validates as text, the Studio passes the name to a
renderer, and the error surfaces three layers from the cause. So the kind name
is checked against :func:`sprezzature_maps.kinds.kind_names` at validation
time, and the same goes for the role bindings.

What these tests pin down is not that validation happens — Pydantic does that —
but that it is wired to the *registry* rather than to a list typed into
``schemas.py``. A fourth kind must become answerable without anyone editing a
schema, and must not be answerable before it exists.

Author
------
Project maintainers.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import sprezzature_maps.kinds as kinds
from sprezzature_maps.data import CHOROPLETH_ROLES
from sprezzature_maps.kinds import MapKind, kind_names
from sprezzature_maps.studio.assistant import KindChoice, MapReading


@pytest.mark.parametrize("name", kind_names())
def test_every_registered_kind_is_answerable(name: str) -> None:
    """Whatever the registry holds, a model may answer."""
    assert KindChoice(kind=name).kind == name


@pytest.mark.parametrize("invented", ["heatmap", "bubble_map", "flow_map", "choropleth_map", ""])
def test_an_invented_kind_is_refused(invented: str) -> None:
    """The plausible-sounding names, which are the dangerous ones."""
    assert invented not in kind_names()
    with pytest.raises(ValidationError):
        KindChoice(kind=invented)


def test_a_new_kind_becomes_answerable_with_no_schema_edit(monkeypatch) -> None:
    """The anti-drift property, checked by actually adding one.

    If ``schemas.py`` ever grows its own list of names, this test fails — which
    is the point. The alternative failure is silent: a fourth kind ships, the
    Studio renders it, and the assistant can never suggest it.
    """
    added = MapKind(
        name="flow_map",
        label="Flow map",
        description="Lines between places.",
        command="flow-map",
        endpoint="/v1/flow-map",
        renderer="make_flow_map",
        data_shape="rows",
        data_option="--data",
        payload_keyword="data",
    )
    with pytest.raises(ValidationError):
        KindChoice(kind="flow_map")
    monkeypatch.setattr(kinds, "KINDS", (*kinds.KINDS, added))
    assert KindChoice(kind="flow_map").kind == "flow_map"
    assert MapReading(kind_seen="flow_map").kind_seen == "flow_map"


def test_alternatives_are_held_to_the_same_registry() -> None:
    """A real kind beside an invented one must not pass on the real one's name."""
    with pytest.raises(ValidationError):
        KindChoice(kind="choropleth", alternatives=["density", "bubble_map"])
    assert KindChoice(kind="choropleth", alternatives=["density"]).alternatives == ["density"]


@pytest.mark.parametrize("role", CHOROPLETH_ROLES)
def test_every_bindable_role_binds(role: str) -> None:
    assert KindChoice(kind="choropleth", roles={role: "col"}).roles == {role: "col"}


@pytest.mark.parametrize("role", ["colour", "color", "size", "label", "weight"])
def test_a_role_no_kind_binds_is_refused(role: str) -> None:
    """``--map colour=x`` was silently ignored by the CLI until it was fixed;
    the same invention must not reach a renderer through the assistant."""
    assert role not in CHOROPLETH_ROLES
    with pytest.raises(ValidationError):
        KindChoice(kind="choropleth", roles={role: "col"})


def test_kind_seen_may_be_empty_but_not_invented() -> None:
    """"I cannot tell" is a finding; "it is a heatmap" is a lie the schema stops."""
    assert MapReading(kind_seen="").kind_seen == ""
    with pytest.raises(ValidationError):
        MapReading(kind_seen="heatmap")
