"""
sprezzature-maps — Click CLI (``sprezzature-maps`` command).

Module summary
--------------
A richer twin of the always-installed argparse ``make-map`` CLI
(:mod:`sprezzature_maps.cli`), available with the ``[cli]`` extra. Both
CLIs call the same shared application-service functions
(:func:`sprezzature_maps.make_choropleth`,
:func:`sprezzature_maps.make_situation_map` -- CODING.md Sec 19.1), so
this file adds a *surface*, not a second implementation of the generators.

What this adds over ``make-map`` specifically: CSV ingestion (``make-map``
only reads a pre-shaped JSON file) plus ``--map role=column`` bindings for
a CSV whose columns are not already named ``id``/``value`` -- exactly the
gap between the two CLIs in the sister ``sprezzature-figures`` repo (its
argparse ``make-figure`` is JSON/demo-only too; ``sprezzature-figures``'
Click CLI is where CSV + column mapping lives). Deliberately does **not**
duplicate ``make-map``'s JSON-file path or add a second ``situation_map``
config-loading path -- both already work and a CSV story does not apply to
``situation_map`` (it is YAML-config-driven, not row-data-driven).

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
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

try:
    import click
except ImportError:
    # Click is optional; the argparse CLI in cli.py is always available.
    def main() -> None:  # type: ignore[misc]
        """Placeholder entry point when click is not installed.

        Prints an install hint to stderr and exits non-zero, rather than
        raising ImportError at console-script invocation time with an
        unhelpful traceback -- a user running the ``sprezzature-maps``
        command without the ``[cli]`` extra needs a one-line fix, not a
        stack trace.
        """
        print(
            "sprezzature-maps click CLI requires click. "
            "Install with: pip install 'sprezzature-maps[cli]'",
            file=sys.stderr,
        )
        sys.exit(1)
else:
    from . import make_choropleth, make_situation_map

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

    def _load_choropleth_rows(
        data_path: str, mapping: dict[str, str]
    ) -> list[dict[str, Any]]:
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
                    json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
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
    def main() -> None:  # type: ignore[misc]
        """sprezzature-maps: render hand-authored SVG world maps."""

    @main.command("list")
    def list_cmd() -> None:
        """Print the two map kinds this repo carries."""
        for kind in ("choropleth", "situation_map"):
            click.echo(kind)

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
        "--relief/--no-relief", default=True, show_default=True,
        help="Composite the vendored hillshade texture.",
    )
    def choropleth_cmd(
        data_path: str | None,
        mappings: tuple[str, ...],
        out: str | None,
        title: str | None,
        diverging: bool | None,
        relief: bool,
    ) -> None:
        """Render a world choropleth map."""
        kwargs: dict[str, Any] = {"diverging": diverging, "relief": relief}
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

    @main.command("situation-map")
    @click.option(
        "--config",
        "config_path",
        default=None,
        type=click.Path(exists=True, dir_okay=False),
        help="YAML region config. Omit for the bundled Western-Europe demo.",
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


if __name__ == "__main__":
    main()
