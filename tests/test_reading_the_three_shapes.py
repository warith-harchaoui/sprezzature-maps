"""
Three kinds, three input shapes, one reader each — and a role typo that was ignored.

Why this file exists
--------------------
``sprezzature_maps.data`` holds what used to be ``cli.py``'s private
``_parse_mapping`` and ``_load_choropleth_rows``, plus readers for the other
two shapes. Moved rather than copied: the Studio needs exactly the same
reading, and a second implementation of "what counts as a usable choropleth
file" is two answers to one question.

The move changed one thing on purpose, and it closes a measured defect.

The defect, measured on the version in git
------------------------------------------
``_parse_mapping`` checked only that a pair carried an ``=``, then stored
whatever role name it found. ``_load_choropleth_rows`` read
``mapping.get("id", "id")``, so an unrecognised role fell back to the default
column. Demonstrated against the pre-move code on a file carrying
``id,value,Code``:

    >>> # _parse_mapping(("country=Code",))  ->  {'country': 'Code'}
    >>> # _load_choropleth_rows(path, that)  ->  rows keyed from `id`

``--map country=Code`` was **accepted, stored and silently ignored**: the map
came out drawn from ``id``, and the reader who asked for ``Code`` got no
complaint. And the reason it survived is worth stating — where the default
column was *absent*, the old code did fail with "missing column". It failed in
the case where the mistake did not matter and passed in the case where it did.

:func:`sprezzature_maps.data.parse_mapping` rejects a role the kind does not
bind, and names the ones it does.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from sprezzature_maps.data import (
    CHOROPLETH_ROLES,
    parse_mapping,
    read_choropleth_rows,
    read_density_points,
    read_situation_config,
)

# ── the role mapping, and the typo it used to swallow ──────────────────────


def test_a_well_formed_mapping_is_parsed() -> None:
    """The case that always worked, so the refusals below are not the whole story."""
    assert parse_mapping(("id=Code", "value=Score")) == {"id": "Code", "value": "Score"}


def test_a_column_name_may_contain_an_equals_sign() -> None:
    """Split on the first ``=`` only.

    Unusual for a header and not impossible for a hand-edited CSV, and the
    role name never contains one. Carried over from the original, which said
    so in a comment — the kind of reasoning a move loses if nobody writes it
    down again.
    """
    assert parse_mapping(("value=a=b",)) == {"value": "a=b"}


def test_a_pair_without_an_equals_sign_is_refused() -> None:
    """And the message shows the shape, rather than only naming the problem."""
    with pytest.raises(ValueError, match=r"role=column"):
        parse_mapping(("idCode",))


def test_a_role_this_kind_does_not_bind_is_refused() -> None:
    """The defect this file opens with.

    ``country`` is a plausible typing of ``id``, and the old code took it,
    dropped it, and drew the map from the default column.
    """
    with pytest.raises(ValueError, match=r"does not bind"):
        parse_mapping(("country=Code",))


def test_the_refusal_names_the_roles_that_do_exist() -> None:
    """Because "not a role" leaves the reader to guess which ones are."""
    with pytest.raises(ValueError) as caught:
        parse_mapping(("countrie=Code",))
    for role in CHOROPLETH_ROLES:
        assert role in str(caught.value), f"the refusal does not name {role!r}: {caught.value}"


def test_an_empty_column_is_refused() -> None:
    """``--map id=`` is a typo with a plausible shape; it binds nothing."""
    with pytest.raises(ValueError, match=r"names no column"):
        parse_mapping(("id=",))


# ── rows: the choropleth shape ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("suffix", "body"),
    [
        (".csv", "id,value\n840,12.5\n124,-3.2\n"),
        (".tsv", "id\tvalue\n840\t12.5\n124\t-3.2\n"),
        (".json", '[{"id": "840", "value": 12.5}, {"id": "124", "value": -3.2}]'),
        (".jsonl", '{"id": "840", "value": 12.5}\n\n{"id": "124", "value": -3.2}\n'),
    ],
)
def test_every_documented_row_format_reads_the_same(suffix: str, body: str, tmp_path: Path) -> None:
    """Four formats, one result. The ``--data`` help text promises exactly these.

    The ``.jsonl`` case carries a blank line on purpose: a trailing or stray
    newline in a generated export is ordinary, and a reader that raised on it
    would fail on files nothing is wrong with.
    """
    path = tmp_path / f"d{suffix}"
    path.write_text(body, encoding="utf-8")
    assert read_choropleth_rows(path) == [
        {"id": "840", "value": 12.5},
        {"id": "124", "value": -3.2},
    ]


def test_stdin_is_a_parameter_not_a_global(tmp_path: Path) -> None:
    """``"-"`` reads the stream it is handed.

    The original reached for ``sys.stdin`` itself, which cannot be tested
    without replacing a global — so the behaviour went unasserted. It is an
    argument now, defaulting to ``sys.stdin`` for the command line that wants
    exactly that.
    """
    rows = read_choropleth_rows("-", stdin=io.StringIO("id,value\n250,7\n"))
    assert rows == [{"id": "250", "value": 7.0}]


def test_a_mapping_renames_the_columns(tmp_path: Path) -> None:
    """The whole point of ``--map``: a file that names them differently."""
    path = tmp_path / "d.csv"
    path.write_text("Code,Score\n840,12.5\n", encoding="utf-8")
    assert read_choropleth_rows(path, {"id": "Code", "value": "Score"}) == [
        {"id": "840", "value": 12.5}
    ]


def test_a_missing_column_names_what_the_file_does_have(tmp_path: Path) -> None:
    """And says which flag fixes it.

    "KeyError: 'id'" is true and useless. This names the row, the column, the
    columns that are there, and the option.
    """
    path = tmp_path / "d.csv"
    path.write_text("Code,Score\n840,12.5\n", encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        read_choropleth_rows(path)
    message = str(caught.value)
    assert "Row 0" in message
    assert "Code" in message and "Score" in message, f"the real columns are not named: {message}"
    assert "--map" in message, f"the fix is not named: {message}"


def test_an_unsupported_extension_lists_the_supported_ones(tmp_path: Path) -> None:
    """Listed from the data, so the message cannot drift from the branches."""
    path = tmp_path / "d.parquet"
    path.write_text("not really parquet", encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        read_choropleth_rows(path)
    for suffix in (".csv", ".tsv", ".json", ".jsonl"):
        assert suffix in str(caught.value)


def test_json_that_is_not_a_list_says_what_it_got(tmp_path: Path) -> None:
    """A dict here is the likely mistake — one row, not a file of rows."""
    path = tmp_path / "d.json"
    path.write_text('{"id": "840", "value": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"list of rows, got dict"):
        read_choropleth_rows(path)


def test_a_missing_file_is_refused_before_anything_is_parsed(tmp_path: Path) -> None:
    """Naming the path, because a wrong path is the commonest mistake of all."""
    with pytest.raises(ValueError, match=r"not found"):
        read_choropleth_rows(tmp_path / "absent.csv")


# ── points: the density shape ─────────────────────────────────────────────


def test_points_read_as_pairs_of_floats(tmp_path: Path) -> None:
    """Integers in the file come back as floats, so the renderer sees one type."""
    path = tmp_path / "p.json"
    path.write_text("[[2.35, 48.86], [0, 51]]", encoding="utf-8")
    assert read_density_points(path) == [[2.35, 48.86], [0.0, 51.0]]


@pytest.mark.parametrize(
    "body", ['[[2.35, 48.86], [1, 2, 3]]', '[[2.35, 48.86], "Paris"]', '[[2.35, 48.86], [1]]']
)
def test_a_bad_point_names_its_index(body: str, tmp_path: Path) -> None:
    """One bad row in a long export, reported by index.

    Without this the renderer raises a ``TypeError`` from inside its own
    arithmetic, which says nothing about which of ten thousand rows is wrong.
    """
    path = tmp_path / "p.json"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=r"Point 1"):
        read_density_points(path)


def test_points_that_are_not_a_list_say_what_they_are(tmp_path: Path) -> None:
    """A GeoJSON feature collection is the likely mistake, and it is a dict."""
    path = tmp_path / "p.json"
    path.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"must be a list, got dict"):
        read_density_points(path)


# ── config: the situation-map shape ───────────────────────────────────────


def test_a_yaml_config_reads_as_a_mapping(tmp_path: Path) -> None:
    """The documented shape, in the format ``--config`` documents."""
    path = tmp_path / "c.yaml"
    path.write_text("title: Sahel\nzones:\n  - name: north\n", encoding="utf-8")
    config = read_situation_config(path)
    assert config["title"] == "Sahel"
    assert config["zones"] == [{"name": "north"}]


def test_a_json_config_reads_the_same(tmp_path: Path) -> None:
    """Both accepted, because a config generated by a tool is JSON."""
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"title": "Sahel", "zones": []}), encoding="utf-8")
    assert read_situation_config(path)["title"] == "Sahel"


def test_a_config_that_is_a_list_says_where_the_list_belongs(tmp_path: Path) -> None:
    """The likely mistake, and the one a ``KeyError`` would not explain.

    Someone writes the zones and saves *those* as the config. The message says
    the zones are a list inside it rather than the whole file.
    """
    path = tmp_path / "c.yaml"
    path.write_text("- name: north\n- name: south\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"zones are a list inside it"):
        read_situation_config(path)


def test_an_unsupported_config_extension_is_refused(tmp_path: Path) -> None:
    """A ``.toml`` config is a reasonable guess and is not accepted."""
    path = tmp_path / "c.toml"
    path.write_text('title = "Sahel"', encoding="utf-8")
    with pytest.raises(ValueError, match=r"expected \.yaml"):
        read_situation_config(path)
