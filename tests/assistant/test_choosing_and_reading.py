"""
The two operations, exercised with no model installed.

``FakeLLMClient`` is scripted with what a model would return, so these tests
cover the real validation and the real repair attempt — not a shortcut past
them. The one thing they cannot cover is whether a model answers well; that is
what the ``llm``/``vision`` marked tests are for, and they are excluded from
the default run.

Author
------
Project maintainers.
"""

from __future__ import annotations

import pytest

from sprezzature_maps.assistant import (
    DataProfile,
    FakeLLMClient,
    FakeLLMTimeout,
    KindChoice,
    LLMResponseError,
    MapIssue,
    MapReading,
    MapReadingError,
    choose_kind,
    kind_catalogue,
    profile_rows,
    read_map,
)
from sprezzature_maps.kinds import KINDS, kind_names

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
ROWS = [{"iso3": "FRA", "value": "68"}, {"iso3": "DEU", "value": "83"}]


def _profile() -> DataProfile:
    return profile_rows(ROWS, source="pop.csv")


def test_a_choice_comes_back_validated() -> None:
    answer = KindChoice(kind="choropleth", roles={"id": "iso3", "value": "value"}, why="per country")
    client = FakeLLMClient([answer])
    choice = choose_kind(client, "population by country", _profile())
    assert choice.kind == "choropleth"
    assert choice.roles == {"id": "iso3", "value": "value"}


def test_the_choice_is_renderable_without_rechecking() -> None:
    """What the schema buys the caller: ``choice.kind`` is a registry name."""
    client = FakeLLMClient([KindChoice(kind="density")])
    assert choose_kind(client, "where are they", _profile()).kind in kind_names()


def test_an_invented_kind_fails_after_one_repair() -> None:
    """A dict, not a model: it goes through validate-or-repair the way a real
    answer does, and the fake re-offers the same payload so the second
    validation fails deterministically."""
    client = FakeLLMClient([{"kind": "heatmap", "why": "looks hot"}])
    with pytest.raises(LLMResponseError) as caught:
        choose_kind(client, "anything", _profile())
    assert "heatmap" in caught.value.raw_response


def test_the_repair_attempt_is_made_exactly_once() -> None:
    client = FakeLLMClient([{"kind": "heatmap"}])
    with pytest.raises(LLMResponseError):
        choose_kind(client, "anything", _profile())
    assert len(client.calls) == 1, (
        "the repair round-trip is made by the real client inside its own `ask` "
        "closure; the fake answers from its queue, so one recorded call is right"
    )


def test_a_timeout_is_not_swallowed() -> None:
    client = FakeLLMClient([FakeLLMTimeout("no model answered")])
    with pytest.raises(FakeLLMTimeout):
        choose_kind(client, "anything", _profile())


def test_the_prompt_lists_every_kind_and_names_the_real_flags() -> None:
    """The catalogue is generated, so a kind cannot be missing from it. The
    options are named because a hint that invents a flag is worse than none."""
    catalogue = kind_catalogue()
    for kind in KINDS:
        assert kind.name in catalogue
        assert kind.data_option in catalogue
        assert kind.data_shape in catalogue


def test_a_reading_comes_back_with_its_issues() -> None:
    reading = MapReading(
        kind_seen="density",
        title_read="Cells per square kilometre",
        legend_present=True,
        legend_readable=False,
        issues=[MapIssue(severity="blocking", what="legend text is 4px", fix="raise it to 11px")],
    )
    client = FakeLLMClient([reading])
    out = read_map(client, PNG, asked_for="density")
    assert out.kind_seen == "density"
    assert [i.severity for i in out.blocking] == ["blocking"]


def test_the_image_is_what_was_handed_over() -> None:
    """The point of the vision path. Without this the call succeeds whether or
    not a picture was ever sent."""
    client = FakeLLMClient([MapReading()])
    read_map(client, PNG)
    assert client.calls[0]["image"] == PNG


def test_reading_an_svg_is_refused() -> None:
    """A vision model shown SVG source reads the markup and answers from the
    text in it — confidently, and without ever looking at a picture. That is
    the one failure this whole operation exists to catch, so it cannot be the
    way it is called."""
    client = FakeLLMClient([MapReading()])
    with pytest.raises(MapReadingError, match="SVG|svg"):
        read_map(client, b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>')
    assert not client.calls, "the model was called anyway"


def test_reading_an_svg_file_is_refused(tmp_path) -> None:
    path = tmp_path / "map.svg"
    path.write_text("<svg/>", encoding="utf-8")
    client = FakeLLMClient([MapReading()])
    with pytest.raises(MapReadingError, match="PNG"):
        read_map(client, path)
    assert not client.calls


@pytest.mark.parametrize("payload", [b"", bytearray()])
def test_an_empty_payload_is_refused(payload: bytes) -> None:
    client = FakeLLMClient([MapReading()])
    with pytest.raises(MapReadingError, match="empty"):
        read_map(client, bytes(payload))
    assert not client.calls


def test_a_missing_file_is_refused(tmp_path) -> None:
    client = FakeLLMClient([MapReading()])
    with pytest.raises(MapReadingError, match="no image"):
        read_map(client, tmp_path / "absent.png")
    assert not client.calls


def test_an_unprimed_reading_does_not_name_the_expected_kind() -> None:
    """Naming the answer in the question is how a reader comes to report it
    whether or not it is there, so ``asked_for`` is empty by default."""
    client = FakeLLMClient([MapReading()])
    read_map(client, PNG)
    prompt = client.calls[0]["prompt"]
    assert "this was rendered as" not in prompt
    read_map(client, PNG, asked_for="choropleth")
    assert "this was rendered as a choropleth" in client.calls[1]["prompt"]
