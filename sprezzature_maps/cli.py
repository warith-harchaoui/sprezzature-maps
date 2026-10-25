"""
sprezzature-maps: the Click-based command line (the ``sprezzature-maps`` command).

Module summary
--------------
Click is a Python library for building command-line tools with
subcommands. This module uses it to provide a richer twin of the
always-installed, argparse-based ``make-map`` command
(:mod:`sprezzature_maps.cli`); it is available separately, through the
``[cli]`` extra. Both commands call the exact same underlying functions
(:func:`sprezzature_maps.make_choropleth`,
:func:`sprezzature_maps.make_situation_map`; see CODING.md §19.1), so this
file only adds a new way to reach the generators, not a second
implementation of them.

What this command adds over ``make-map``, specifically: it can read data
straight from a CSV file (``make-map`` only reads a JSON file already
shaped the way the generator expects), and it accepts ``--map
role=column`` bindings for a CSV whose columns are not already named
``id``/``value``. That is exactly the same gap that exists between the
two command lines in the sister ``sprezzature-figures`` repository (its
argparse-based command is JSON-and-demo-data only too; its Click command
is where CSV reading and column mapping live). This file deliberately does
not duplicate ``make-map``'s JSON-file path, and does not add a second way
to load a ``situation_map`` configuration: both already work, and a CSV
story simply does not apply to ``situation_map``, since it is driven by a
YAML configuration file describing zones and markers, not by rows of
tabular data.

Install the extra to pull in Click::

    pip install 'sprezzature-maps[cli]'

Then run the command::

    sprezzature-maps list
    sprezzature-maps choropleth --data my.csv --map id=Code --map value=Score --out world.svg
    sprezzature-maps situation-map --config my-region.yaml --out region.svg

Usage example
-------------
>>> # sprezzature-maps choropleth --out world.svg
>>> # world.svg

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import click

from . import make_choropleth, make_density, make_situation_map


def _parse_mapping(pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated ``--map role=column`` options into a dict.

    Parameters
    ----------
    pairs : tuple of str
        Each element is one ``--map`` option's raw value, expected in
        ``"role=column"`` form.

    Returns
    -------
    dict of str to str
        ``{role: column}``, e.g. ``{"id": "Code", "value": "Score"}``.

    Raises
    ------
    click.ClickException
        If any entry is missing the ``=`` separator.

    Examples
    --------
    >>> _parse_mapping(("id=Code", "value=Score"))
    {'id': 'Code', 'value': 'Score'}
    """
    mapping: dict[str, str] = {}
    for pair in pairs:
        # Split on the FIRST "=" only: a column header could itself
        # contain "=" (unusual, but not impossible for a hand-edited
        # CSV), and the role name never does.
        if "=" not in pair:
            raise click.ClickException(
                f"--map expects role=column (e.g. --map id=Code), got: {pair!r}"
            )
        role, _, column = pair.partition("=")
        mapping[role.strip()] = column.strip()
    return mapping


def _load_choropleth_rows(data_path: str, mapping: dict[str, str]) -> list[dict[str, Any]]:
    """Load choropleth rows from a CSV or JSON file, applying ``--map``.

    Parameters
    ----------
    data_path : str
        Path to a ``.csv``/``.tsv`` or ``.json``/``.jsonl`` file, or
        ``"-"`` to read CSV from stdin.
    mapping : dict of str to str
        ``{"id": <column name>, "value": <column name>}``, from
        :func:`_parse_mapping`. Empty means the file's own columns are
        already named ``id``/``value``.

    Returns
    -------
    list of dict
        Rows in the ``[{"id": str, "value": float}, ...]`` shape
        :func:`~sprezzature_maps.make_choropleth` expects.

    Raises
    ------
    click.ClickException
        If the file is missing, has an unsupported extension, or a
        required column is not present after mapping.

    Examples
    --------
    >>> import tempfile, os
    >>> fd, path = tempfile.mkstemp(suffix=".csv")
    >>> _ = os.write(fd, b"id,value\\n840,12.5\\n124,-3.2\\n")
    >>> os.close(fd)
    >>> rows = _load_choropleth_rows(path, {})
    >>> os.unlink(path)
    >>> rows
    [{'id': '840', 'value': 12.5}, {'id': '124', 'value': -3.2}]
    """
    id_col = mapping.get("id", "id")
    value_col = mapping.get("value", "value")

    if data_path == "-":
        # Reading from stdin only makes sense as CSV (JSON piped in
        # would need its own flag to disambiguate from CSV) -- keep
        # the stdin path single-purpose rather than guessing a format.
        reader = csv.DictReader(sys.stdin)
        raw_rows = list(reader)
    else:
        path = Path(data_path)
        if not path.is_file():
            raise click.ClickException(f"--data file not found: {data_path}")
        suffix = path.suffix.lower()
        if suffix in (".csv", ".tsv"):
            delimiter = "\t" if suffix == ".tsv" else ","
            with path.open(newline="", encoding="utf-8") as f:
                raw_rows = list(csv.DictReader(f, delimiter=delimiter))
        elif suffix == ".json":
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                raise click.ClickException(
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
            raise click.ClickException(
                f"Unsupported --data extension: {suffix!r} (expected .csv/.tsv/.json/.jsonl)"
            )

    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_rows):
        if id_col not in raw or value_col not in raw:
            raise click.ClickException(
                f"Row {i}: missing column {id_col!r} or {value_col!r} "
                f"(available: {sorted(raw.keys())}). Use --map id=<col> --map value=<col> "
                "if your file names them differently."
            )
        rows.append({"id": str(raw[id_col]), "value": float(raw[value_col])})
    return rows


@click.group()
def main() -> None:
    """sprezzature-maps: render hand-authored SVG world maps."""


@main.command("list")
def list_cmd() -> None:
    """Print the two map kinds this repo carries."""
    for kind in ("choropleth", "situation_map"):
        click.echo(kind)


@main.command("audit")
@click.argument("target", type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output shape.",
)
def audit_cmd(target: str, fmt: str) -> None:
    """Check that a rendered plate says how it was made.

    The twin of ``make-map audit``: same engine, the other parser. A
    brick that only makes is half a brick.
    """
    from sprezzature_maps.audit import main as audit_main

    raise SystemExit(audit_main([target, "--format", fmt]))


@main.command("choropleth")
@click.option(
    "--data",
    "data_path",
    default=None,
    type=click.Path(dir_okay=False, allow_dash=True),
    help="CSV/TSV/JSON/JSONL file of per-country rows. Omit for the built-in demo data. "
    "Use '-' to read CSV from stdin.",
)
@click.option(
    "--map",
    "mappings",
    multiple=True,
    metavar="ROLE=COLUMN",
    help="Bind a role (id, value) to a column when your file names them differently, "
    "e.g. --map id=CountryCode --map value=Score (repeatable). Only used with --data.",
)
@click.option("--out", default=None, help="Output path (.svg/.png/.pdf/.jpg).")
@click.option("--title", default=None, help="Chart title.")
@click.option(
    "--diverging/--no-diverging",
    default=None,
    help="Force the diverging ramp on/off. Default: auto-detect from the data's sign.",
)
@click.option(
    "--relief/--no-relief",
    default=True,
    show_default=True,
    help="Composite the vendored hillshade texture.",
)
@click.option(
    "--simplify",
    type=float,
    default=None,
    help=(
        "Vertex-thinning tolerance in output pixels. The default drops "
        "detail the canvas cannot resolve; pass 0 to keep every vertex."
    ),
)
def choropleth_cmd(
    data_path: str | None,
    mappings: tuple[str, ...],
    out: str | None,
    title: str | None,
    diverging: bool | None,
    relief: bool,
    simplify: float | None,
) -> None:
    """Render a world choropleth map."""
    kwargs: dict[str, Any] = {"diverging": diverging, "relief": relief}
    if simplify is not None:
        kwargs["simplify"] = simplify
    if data_path:
        kwargs["data"] = _load_choropleth_rows(data_path, _parse_mapping(mappings))
    elif mappings:
        raise click.ClickException("--map only applies with --data.")
    if title:
        kwargs["title"] = title
    if out:
        kwargs["out"] = out
    result = make_choropleth(**kwargs)
    click.echo(result)


@main.command("density")
@click.option(
    "--points",
    "points_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file of [[lon, lat], ...] event positions; defaults to demo points.",
)
@click.option("--out", default=None, help="Output SVG path.")
@click.option("--title", default=None)
@click.option(
    "--bins",
    type=int,
    default=None,
    help=(
        "Cells across the image. Past roughly 260 the field becomes grain, so the "
        "visual limit arrives before the size limit."
    ),
)
def density_cmd(
    points_path: str | None, out: str | None, title: str | None, bins: int | None
) -> None:
    """Accumulation map: point events binned to a luminous field, no coastline."""
    kwargs: dict[str, Any] = {}
    if points_path:
        kwargs["points"] = [tuple(point) for point in json.loads(Path(points_path).read_text())]
    if title:
        kwargs["title"] = title
    if out:
        kwargs["out"] = out
    if bins:
        kwargs["bins"] = bins
    click.echo(str(make_density(**kwargs)))


@main.command("situation-map")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="YAML region config. Omit for the bundled Europe demo.",
)
@click.option("--out", default=None, help="Output path (.svg/.png/.pdf/.jpg).")
@click.option("--title", default=None, help="Overrides the config's own title if set.")
def situation_map_cmd(config_path: str | None, out: str | None, title: str | None) -> None:
    """Render a layered areas-of-control situation map."""
    kwargs: dict[str, Any] = {}
    if config_path:
        import yaml

        kwargs["config"] = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if title:
        kwargs["title"] = title
    if out:
        kwargs["out"] = out
    result = make_situation_map(**kwargs)
    click.echo(result)


# The argparse front door spelled this sub-command `situation_map`, and
# TRIGGERS.md, SKILL.md and the hub's routing table all tell an agent to type
# that. Click's own idiom is the hyphen. Both are registered on the one
# callback rather than picking a winner: renaming would break every published
# instruction, and keeping only the underscore would read as a typo to anyone
# who knows click. Two spellings, one command -- the same bargain as
# `make-map` and `sprezzature-maps`.
main.add_command(main.commands["situation-map"], "situation_map")

if __name__ == "__main__":
    main()
