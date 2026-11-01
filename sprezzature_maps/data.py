"""
sprezzature-maps: reading the three shapes of input the three kinds take.

Module summary
--------------
A chart library can assume one shape — a table, and a question about which
column plays which role. The three kinds here take three different things, and
:attr:`sprezzature_maps.kinds.MapKind.data_shape` is where each one says which:

``rows``
    A **choropleth** takes per-territory values, bound through the ``id`` and
    ``value`` roles. ``.csv``, ``.tsv``, ``.json``, ``.jsonl``, or CSV on
    standard input.
``config``
    A **situation map** takes a region *configuration* — zones, fronts,
    labels, a projection. There is no table in it.
``points``
    A **density** map takes a bare list of ``[lon, lat]`` positions, and draws
    no coastline at all.

Why this module exists rather than a second reader
--------------------------------------------------
``read_choropleth_rows`` and :func:`parse_mapping` were ``cli.py``'s private
``_load_choropleth_rows`` and ``_parse_mapping``. Moved, not copied: the
Studio needs exactly the same reading, and a second implementation of "what
counts as a usable choropleth file" is two answers to one question — the day
one gains a format or an error message, the other quietly stays behind.

What *did* change in the move is the exception. The originals raised
``click.ClickException``, which is the command line's vocabulary: it prints
``Error: ...`` and exits 2. A library function that can only be called from a
Click command is not a library function, so these raise :class:`ValueError`
and ``cli.py`` wraps them. The messages are unchanged, because they were
already written for a reader rather than for a traceback.

Standard input is passed in rather than read
--------------------------------------------
``_load_choropleth_rows`` reached for ``sys.stdin`` itself when handed
``"-"``. That is untestable without replacing a global, so the stream is a
parameter here, defaulting to ``sys.stdin`` for the command line that wants
exactly that.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, TextIO

import yaml

#: The roles a choropleth binds, in the order ``--map`` documents them. A
#: territory identifier and the number that colours it; nothing else is
#: required, and nothing else is read.
CHOROPLETH_ROLES: tuple[str, ...] = ("id", "value")

#: Extensions :func:`read_choropleth_rows` accepts, and how to read each.
#: Stated as data so the error message can list them rather than repeat a
#: literal that drifts from the branches below.
ROW_SUFFIXES: tuple[str, ...] = (".csv", ".tsv", ".json", ".jsonl")


def parse_mapping(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated ``role=column`` strings into a dict.

    Parameters
    ----------
    pairs : tuple of str
        Each ``"<role>=<column>"``, as ``--map`` is repeated on the command
        line.

    Returns
    -------
    dict of str to str
        ``{role: column}``.

    Raises
    ------
    ValueError
        When a pair carries no ``=``, or names a role this kind does not bind.

        The second check is new in the move, and it closes a measured defect.
        The original accepted any role name and stored it; ``id_col`` then
        fell back to ``"id"``. So ``--map country=Code`` was **accepted and
        silently ignored** whenever the file happened to carry the default
        ``id`` and ``value`` columns — demonstrated on a three-column file,
        where the rows came back keyed from ``id`` and the reader who asked
        for ``Code`` got no complaint at all. Where the default column was
        *absent* the old code did fail, with "missing column", which is why
        this went unnoticed: it failed in the case where the mistake did not
        matter and passed in the case where it did.

    Examples
    --------
    >>> parse_mapping(("id=Code", "value=Score"))
    {'id': 'Code', 'value': 'Score'}
    """
    mapping: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--map expects role=column (e.g. --map id=Code), got: {pair!r}")
        # Split on the FIRST "=" only: a column header could itself contain
        # "=" (unusual, but not impossible for a hand-edited CSV), and the
        # role name never does. Carried over from the original.
        role, column = pair.split("=", 1)
        role, column = role.strip(), column.strip()
        if role not in CHOROPLETH_ROLES:
            raise ValueError(
                f"--map names the role {role!r}, which a choropleth does not bind; "
                f"it binds {', '.join(CHOROPLETH_ROLES)}"
            )
        if not column:
            raise ValueError(f"--map {role}= names no column")
        mapping[role] = column
    return mapping


def read_choropleth_rows(
    data_path: str | Path,
    mapping: dict[str, str] | None = None,
    *,
    stdin: TextIO | None = None,
) -> list[dict[str, Any]]:
    """Read per-territory rows for a choropleth, applying a role mapping.

    Parameters
    ----------
    data_path : str or pathlib.Path
        A ``.csv``/``.tsv``/``.json``/``.jsonl`` file, or ``"-"`` to read CSV
        from *stdin*.
    mapping : dict of str to str, optional
        ``{"id": <column>, "value": <column>}``, from :func:`parse_mapping`.
        Empty or ``None`` means the file's own columns are already named
        ``id`` and ``value``.
    stdin : typing.TextIO, optional
        The stream ``"-"`` reads from. Defaults to :data:`sys.stdin`.

    Returns
    -------
    list of dict
        Rows shaped ``[{"id": str, "value": float}, ...]``, which is what
        :func:`sprezzature_maps.make_choropleth` expects.

    Raises
    ------
    ValueError
        If the file is missing, carries an unsupported extension, holds JSON
        that is not a list, or is missing a required column after mapping.

    Examples
    --------
    >>> import io
    >>> read_choropleth_rows("-", stdin=io.StringIO("id,value\\n840,12.5\\n"))
    [{'id': '840', 'value': 12.5}]
    """
    mapping = mapping or {}
    id_col = mapping.get("id", "id")
    value_col = mapping.get("value", "value")

    if str(data_path) == "-":
        # CSV only. JSON piped in would need its own flag to tell it from
        # CSV, so the stdin path stays single-purpose rather than guessing.
        raw_rows: list[dict[str, Any]] = list(csv.DictReader(stdin or sys.stdin))
    else:
        path = Path(data_path)
        if not path.is_file():
            raise ValueError(f"--data file not found: {data_path}")
        suffix = path.suffix.lower()
        if suffix in (".csv", ".tsv"):
            delimiter = "\t" if suffix == ".tsv" else ","
            with path.open(newline="", encoding="utf-8") as handle:
                raw_rows = list(csv.DictReader(handle, delimiter=delimiter))
        elif suffix == ".json":
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                raise ValueError(
                    f"--data JSON must be a list of rows, got {type(loaded).__name__}"
                )
            raw_rows = loaded
        elif suffix == ".jsonl":
            raw_rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            raise ValueError(
                f"Unsupported --data extension: {suffix!r} "
                f"(expected {'/'.join(ROW_SUFFIXES)})"
            )

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        if id_col not in raw or value_col not in raw:
            raise ValueError(
                f"Row {index}: missing column {id_col!r} or {value_col!r} "
                f"(available: {sorted(raw.keys())}). Use --map id=<col> --map value=<col> "
                "if your file names them differently."
            )
        rows.append({"id": str(raw[id_col]), "value": float(raw[value_col])})
    return rows


def read_density_points(points_path: str | Path) -> list[list[float]]:
    """Read ``[[lon, lat], ...]`` event positions for a density map.

    Parameters
    ----------
    points_path : str or pathlib.Path
        A ``.json`` file holding a list of two-number sequences.

    Returns
    -------
    list of list of float
        ``[[lon, lat], ...]``, in file order.

    Raises
    ------
    ValueError
        If the file is missing, is not a list, or holds an entry that is not
        a pair of numbers. The per-entry check names the index: a single bad
        row in a long export is otherwise reported as a ``TypeError`` from
        inside the renderer, which says nothing about which row.

    Examples
    --------
    >>> import json, tempfile, os
    >>> fd, path = tempfile.mkstemp(suffix=".json")
    >>> _ = os.write(fd, b"[[2.35, 48.86], [-0.13, 51.51]]")
    >>> os.close(fd)
    >>> read_density_points(path)
    [[2.35, 48.86], [-0.13, 51.51]]
    >>> os.unlink(path)
    """
    path = Path(points_path)
    if not path.is_file():
        raise ValueError(f"--points file not found: {points_path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"--points JSON must be a list, got {type(loaded).__name__}")
    points: list[list[float]] = []
    for index, entry in enumerate(loaded):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError(
                f"Point {index} is {entry!r}; every entry must be a [lon, lat] pair"
            )
        try:
            points.append([float(entry[0]), float(entry[1])])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Point {index} is not a pair of numbers: {entry!r}") from exc
    return points


def read_situation_config(config_path: str | Path) -> dict[str, Any]:
    """Read a region configuration for a situation map.

    Parameters
    ----------
    config_path : str or pathlib.Path
        A ``.yaml``/``.yml`` or ``.json`` file, shaped the way ``--config``
        documents.

    Returns
    -------
    dict
        The configuration as a mapping.

    Raises
    ------
    ValueError
        If the file is missing, carries an unsupported extension, or does not
        hold a mapping at the top level. A list here is the likely mistake —
        the zones are a list *inside* the config — and saying so is more use
        than a ``KeyError`` from the renderer.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ValueError(f"--config file not found: {config_path}")
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        loaded = yaml.safe_load(text)
    elif suffix == ".json":
        loaded = json.loads(text)
    else:
        raise ValueError(
            f"Unsupported --config extension: {suffix!r} (expected .yaml/.yml/.json)"
        )
    if not isinstance(loaded, dict):
        raise ValueError(
            f"--config must hold a mapping at the top level, got "
            f"{type(loaded).__name__}. The zones are a list inside it, not the whole file."
        )
    return loaded
