"""
sprezzature-maps: the Click command line (``sprezzature-maps`` and ``make-map``).

Module summary
--------------
Click is a Python library for building command-line tools with
subcommands. This module is the whole command line, reachable under two
names: ``[project.scripts]`` points both ``make-map`` and
``sprezzature-maps`` at :func:`main` here, so they resolve to one callable
and cannot differ. ``make-map`` is the older spelling and is kept because
it is what the skill, the README and years of notes tell people to type.
Every sub-command calls the library functions
(:func:`sprezzature_maps.make_choropleth`,
:func:`sprezzature_maps.make_situation_map`; see CODING.md §19.1), so this
file is a way to reach the generators, never a second implementation.

What this used to be, until 2026-10-25: a *richer twin* of an
argparse-based ``make-map`` that read only a JSON file already shaped the
way the generator expects, with Click bought through a ``[cli]`` extra.
The pair meant every sub-command written twice, and the extra meant a
reader could hold a command that would not run. argparse is gone, click is
a base dependency, the ``[cli]`` extra is gone with it, and the
distinction this docstring used to draw no longer exists — anything one
name does, the other does.

What that twin added is still here, now on both names: reading data
straight from a CSV/TSV/JSON/JSONL file, and ``--map role=column``
bindings for a file whose columns are not already named ``id``/``value``.
Both live on the sub-commands rather than on the group. There is still no
CSV story for ``situation_map``, which is driven by a YAML configuration
file describing zones and markers rather than by rows of tabular data.

Run it under either name::

    sprezzature-maps list
    sprezzature-maps choropleth --data my.csv --map id=Code --map value=Score --out world.svg
    sprezzature-maps choropleth --data my.csv --classes 5 --method jenks --out world.svg
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

import json
from pathlib import Path
from typing import Any

import click

from sprezzature_maps._skill import skill_command
from sprezzature_maps.data import parse_mapping, read_choropleth_rows
from sprezzature_maps.kinds import kind as kind_of
from sprezzature_maps.kinds import kind_names

from . import classification_methods, make_choropleth, make_density, make_situation_map


def _parse_mapping(pairs: tuple[str, ...]) -> dict[str, str]:
    """``--map role=column`` into a dict, in Click's vocabulary.

    The parsing moved to :func:`sprezzature_maps.data.parse_mapping` so the
    library reads files the same way this does; what stays here is the
    translation. A library function raises :class:`ValueError`; a command line
    prints ``Error: ...`` and exits 2, and the reader of a terminal should not
    be shown a traceback for a mistyped flag.
    """
    try:
        return parse_mapping(pairs)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _load_choropleth_rows(data_path: str, mapping: dict[str, str]) -> list[dict[str, Any]]:
    """Choropleth rows from a file, in Click's vocabulary.

    See :func:`sprezzature_maps.data.read_choropleth_rows`, which this wraps
    for the same reason as above. The messages are unchanged in the move:
    they were already written for a reader.
    """
    try:
        return read_choropleth_rows(data_path, mapping)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _render(generator: Any, **kwargs: Any) -> Any:
    """Call a generator, in Click's vocabulary.

    The generators refuse bad input with a :class:`ValueError` whose message is
    written for a reader: a mistyped config key, an empty window, a table that
    matches no territory. Left alone it reached the terminal under a traceback
    of the drawing code.
    """
    try:
        return generator(**kwargs)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


# `-V` / `--version` read the installed distribution's metadata rather than a
# constant, so the answer is the version pip resolved, whichever of the two
# names was typed.
@click.group()
@click.version_option(None, "-V", "--version", package_name="sprezzature-maps")
def main() -> None:
    """sprezzature-maps: render hand-authored SVG world maps."""


# Read from `sprezzature_maps.kinds.KINDS` rather than written here. It used
# to be a hard-coded ("choropleth", "situation_map"), and that is how this
# command came to answer two kinds of three: `density` was born in this
# repository after the other two were extracted from sprezzature-figures, and
# every list written before it had to be revisited by hand. The gallery, the
# HTTP routes and TRIGGERS.md were; this one, the one a reader asks directly,
# was not. The history lives here rather than in the docstring because Click
# prints the docstring as `--help`.
@main.command("list")
def list_cmd() -> None:
    """Print every map kind this package draws, one per line."""
    for name in kind_names():
        click.echo(name)


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

    TARGET is one SVG plate or a folder of them. Eleven static rules; exits 1
    on any finding, 0 when every plate is clean, 2 when TARGET holds no SVG.
    A brick that only makes is half a brick.
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
@click.option(
    "--out",
    default=None,
    help="Output path (.svg/.png/.jpg/.pdf/.eps/.html). Default: choropleth.svg in the "
    "current directory.",
)
@click.option("--title", default=None, help="Chart title.")
# The audit's `no-provenance` rule asks every plate to say when it was true,
# or that it is illustrative, and the subtitle is where a choropleth says it.
# Without this option a map made from the reader's own file could not pass
# the audit this same command group runs on it.
@click.option(
    "--subtitle",
    default=None,
    help=(
        "The line under the title: say when the data was true and where it "
        'comes from, e.g. "World Bank, 2024". The audit asks for it.'
    ),
)
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
# The most consequential decision on a choropleth, and until now the one
# decision this command could not express. `scripts/_classify.py` has held
# four classifications and an exact Fisher-Jenks solver since it was written;
# the HTTP request model offers both of these fields; the regional plate
# reads them out of its own YAML. Only the world choropleth -- the command
# the README shows first, and the one whose entire subject is numbers
# coloured by class -- had neither, so every map anybody made by typing got
# `classes=None`: the unclassed linear stretch, which that module's own
# docstring calls "the worst fit for the data choropleths are usually made
# of", because on skewed data it puts most territories in the bottom of the
# ramp and leaves numbers ten times apart looking identical.
#
# Reaching for `elbow-helper` to pick the number was measured and refused. Its
# floor sits above this question's ceiling: `robust_knee` wants 20 points on a
# curve (`min_samples = 20`) and the curve is residual within-class variance
# against k, which both surfaces here cap at 12. So it returns
# NoClearKnee(INSUFFICIENT_DATA) for every input the question can produce,
# including a control whose answer is unarguably three. The number of classes
# stays the caller's to state -- and now statable.
@click.option(
    "--classes",
    type=click.IntRange(2, 12),
    default=None,
    help=(
        "Class the values into this many colour classes instead of stretching "
        "the ramp linearly from min to max. Reach for it whenever the values "
        "are skewed — income, density, counts, GDP per head. Omit for the "
        "unclassed ramp."
    ),
)
@click.option(
    "--method",
    type=click.Choice(classification_methods()),
    default="quantile",
    show_default=True,
    help=(
        "Where to put the class boundaries, used only with --classes. "
        "quantile gives every class the same count; equal gives every class "
        "the same width; jenks finds the groupings the data itself suggests; "
        "headtail suits heavy tails. The legend prints whichever was used."
    ),
)
def choropleth_cmd(
    data_path: str | None,
    mappings: tuple[str, ...],
    out: str | None,
    title: str | None,
    subtitle: str | None,
    diverging: bool | None,
    relief: bool,
    simplify: float | None,
    classes: int | None,
    method: str,
) -> None:
    """Render a world choropleth map."""
    kwargs: dict[str, Any] = {"diverging": diverging, "relief": relief}
    if simplify is not None:
        kwargs["simplify"] = simplify
    # `method` without `classes` is not an error and not a silent drop: the
    # generator ignores it exactly as the HTTP surface does, because the
    # unclassed ramp has no boundaries to place. Passing it anyway would make
    # a reader who typed only --method believe a classification happened.
    if classes is not None:
        kwargs["classes"] = classes
        kwargs["method"] = method
    if data_path:
        kwargs["data"] = _load_choropleth_rows(data_path, _parse_mapping(mappings))
    elif mappings:
        raise click.ClickException("--map only applies with --data.")
    if title:
        kwargs["title"] = title
    if subtitle:
        kwargs["subtitle"] = subtitle
    if out:
        kwargs["out"] = out
    result = _render(make_choropleth, **kwargs)
    click.echo(result)


@main.command("density")
@click.option(
    "--points",
    "points_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file of [[lon, lat], ...] event positions; defaults to demo points.",
)
@click.option(
    "--out",
    default=None,
    help="Output path (.svg/.png/.jpg/.pdf/.eps/.html). Default: density.svg in the "
    "current directory.",
)
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
        from sprezzature_maps.render import infer_bbox

        kwargs["points"] = [tuple(point) for point in json.loads(Path(points_path).read_text())]
        # Framed on the events, as `render` does: this command has no
        # --bbox, and the generator's own default window is the contiguous
        # United States, so events anywhere else ended in "no point fell
        # inside the bbox" and events partly outside were cropped unsaid.
        try:
            kwargs["bbox"] = infer_bbox(kwargs["points"])
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
    if title:
        kwargs["title"] = title
    if out:
        kwargs["out"] = out
    if bins:
        kwargs["bins"] = bins
    click.echo(str(_render(make_density, **kwargs)))


@main.command("improve")
@click.option(
    "--kind",
    "kind_name",
    type=click.Choice(kind_names()),
    required=True,
    help="Which kind of map to render and then look at.",
)
@click.option(
    "--data",
    "data_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Per-territory rows, for a choropleth.",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Region configuration, for a situation map.",
)
@click.option(
    "--points",
    "points_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Event positions, for a density map.",
)
@click.option(
    "--map",
    "mapping",
    multiple=True,
    metavar="ROLE=COLUMN",
    help="Bind a column to a role. Repeatable.",
)
@click.option("--out", required=True, help="Where the map goes. Must be a .png.")
@click.option("--title", default=None, help="Your words. The loop never rewrites them.")
@click.option(
    "--rounds",
    type=int,
    default=None,
    help="Lower the ceiling on rounds. It cannot be raised: every round renders and reads a map.",
)
def improve_cmd(
    kind_name: str,
    data_path: str | None,
    config_path: str | None,
    points_path: str | None,
    mapping: tuple[str, ...],
    out: str,
    title: str | None,
    rounds: int | None,
) -> None:
    """Render a map, look at it, and repair what is safe to repair.

    The loop renders, hands the PNG to a vision model, matches what it read
    against a table of cues, and changes one keyword at a time from a ladder
    that ends. It never applies anything that can alter what the map says
    about the data -- the classification method, the number of classes, the
    frame -- and prints those for you to decide instead.

    Needs a model that `best-engine-ai-helper` can reach.
    """
    from sprezzature_maps.assistant import default_client
    from sprezzature_maps.data import read_density_points, read_situation_config
    from sprezzature_maps.ralph import improve

    kind = kind_of(kind_name)
    #: shape -> (the option the user passes, what they passed, how to read it)
    supplied = {
        "rows": ("--data", data_path),
        "config": ("--config", config_path),
        "points": ("--points", points_path),
    }
    wanted_flag, wanted_value = supplied[kind.data_shape]
    wrong = [
        flag for shape, (flag, value) in supplied.items() if value and shape != kind.data_shape
    ]
    if wrong:
        raise click.ClickException(
            f"a {kind.name} consumes {kind.data_shape}, so it takes {wanted_flag}, "
            f"not {', '.join(wrong)}"
        )
    if not wanted_value:
        raise click.ClickException(f"a {kind.name} needs {wanted_flag}")

    payload: Any
    try:
        if kind.data_shape == "rows":
            payload = read_choropleth_rows(wanted_value, _parse_mapping(mapping))
        elif kind.data_shape == "points":
            payload = read_density_points(wanted_value)
        else:
            payload = read_situation_config(wanted_value)
    except ValueError as bad:
        raise click.ClickException(str(bad)) from bad

    try:
        result = improve(
            default_client(),
            kind_name,
            payload,
            out=out,
            title=title,
            max_rounds=rounds,
        )
    except ValueError as bad:
        raise click.ClickException(str(bad)) from bad

    click.echo(str(result.image))
    for round_ in result.rounds:
        read = round_.reading
        seen = read.kind_seen or "could not tell"
        click.echo(f"round {round_.index}: read as {seen}, {len(round_.reading.issues)} issue(s)")
        for repair in round_.applied:
            click.echo(f"  applied {repair.option}={repair.value}  ({repair.because})")
    click.echo(f"stopped: {result.reason}")
    if not result.improved:
        click.echo("nothing was changed")
    for repair in result.for_a_person:
        click.echo(
            f"for you to decide: {repair.option}={repair.value}  ({repair.because}) "
            f"-- it can change what the map says about the data"
        )


@main.command("situation-new")
@click.option("--country", default=None, help="Read the region off the vendored atlas by name.")
@click.option(
    "--bbox",
    default=None,
    help="west,south,east,north in degrees. Use instead of --country.",
)
@click.option("--title", default=None, help="The plate's title. Defaults to the country.")
@click.option("--subtitle", default="", help="The editorial line under the title.")
@click.option(
    "--as-of",
    "as_of",
    default=None,
    help="Vintage stamped in the footer, as YYYY-MM-DD. Defaults to today.",
)
@click.option("--out", default=None, help="Where to write the config. Omit for stdout.")
def situation_new_cmd(
    country: str | None,
    bbox: str | None,
    title: str | None,
    subtitle: str,
    as_of: str | None,
    out: str | None,
) -> None:
    """Write a starter config for a new situation plate, already furnished.

    The plate it describes renders as it stands -- basemap, frontiers,
    towns, scale, locator, provenance footer -- so the work is adding the
    subject rather than remembering the furniture. The thematic block is
    there too, commented, with ``confidence`` on every zone, because that
    is the field most often left out and the one whose absence makes the
    strongest claim on the plate by default.
    """
    from datetime import date

    from sprezzature_maps.starter import country_bbox, situation_starter

    if (country is None) == (bbox is None):
        raise click.UsageError("give exactly one of --country or --bbox")
    if country is not None:
        try:
            region = country_bbox(country)
        except KeyError as exc:
            raise click.UsageError(
                f"no country named {country!r} in the vendored atlas; "
                "check the Natural Earth spelling, or pass --bbox"
            ) from exc
    else:
        parts = [p.strip() for p in str(bbox).split(",")]
        if len(parts) != 4:
            raise click.UsageError("--bbox needs four numbers: west,south,east,north")
        try:
            region = [float(v) for v in parts]
        except ValueError as exc:
            raise click.UsageError(f"--bbox must be four numbers; got {bbox!r}") from exc
    stamp = date.fromisoformat(as_of) if as_of else None
    text = situation_starter(
        title=title or country or "Untitled plate",
        bbox=region,
        subtitle=subtitle,
        as_of=stamp,
        focus=country,
    )
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(out)
    else:
        click.echo(text, nl=False)


@main.command("situation-map")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="YAML region config. Omit for the bundled Europe demo.",
)
@click.option(
    "--out",
    default=None,
    help="Output path (.svg/.png/.jpg/.pdf/.eps/.html). Default: situation_map.svg in the "
    "current directory.",
)
@click.option("--title", default=None, help="Overrides the config's own title if set.")
def situation_map_cmd(config_path: str | None, out: str | None, title: str | None) -> None:
    """Render a layered areas-of-control situation map."""
    kwargs: dict[str, Any] = {}
    if config_path:
        kwargs["config"] = _read_config(config_path)
    if title:
        kwargs["title"] = title
    if out:
        kwargs["out"] = out
    result = _render(make_situation_map, **kwargs)
    click.echo(result)


def _read_config(config_path: str) -> dict[str, Any]:
    """A plate config, anchored to its own directory.

    Without ``_config_dir`` every relative path in the YAML -- a zone's
    ``source:``, a ``layers:`` library -- resolved against wherever the
    command was typed, so a config that rendered from its own folder lost its
    layers from any other.
    """
    import yaml

    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    cfg["_config_dir"] = str(Path(config_path).resolve().parent)
    return cfg


@main.command("export")
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="The plate's YAML config.",
)
@click.option(
    "--out",
    required=True,
    help="Layer file to write: .geojson (QGIS, ArcGIS) or .kml (Google Earth).",
)
def export_cmd(config_path: str, out: str) -> None:
    """Write a plate's layers as GeoJSON or KML, for a GIS or the next plate.

    Every arrow, front, event, annotation, place and zone of control, in
    longitude and latitude with all its properties, plus the plate's title,
    date, source and method. Nothing depends on the projection or the frame,
    so the next plate -- another scale, another projection -- starts from it.
    """
    from sprezzature_maps.gis import export_layers, to_kml

    cfg = _read_config(config_path)
    collection = export_layers(cfg, cfg["_config_dir"])
    dest = Path(out)
    if dest.suffix.lower() == ".kml":
        dest.write_text(to_kml(collection), encoding="utf-8")
    elif dest.suffix.lower() in (".geojson", ".json"):
        dest.write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        raise click.ClickException("--out must end in .geojson, .json or .kml")
    click.echo(f"{dest}  ({len(collection['features'])} features)")


@main.command("import")
@click.argument("layer_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", default=None, help="Write the YAML blocks here. Omit for stdout.")
def import_cmd(layer_file: str, out: str | None) -> None:
    """Turn a GeoJSON or KML layer into the YAML blocks a plate reads.

    A file exported by `make-map export` goes back to its own blocks; a layer
    from elsewhere is placed by geometry (point -> events, line -> arrows,
    polygon -> areas_of_control). To reuse a layer across plates without
    copying it, name the file under `layers:` in each config instead.
    """
    import yaml

    from sprezzature_maps.gis import import_layers, read_features

    try:
        blocks = import_layers(read_features(layer_file))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    areas = (blocks.get("areas_of_control") or {}).get("source", {}).get("features", [])
    if any("confidence" not in (f.get("properties") or {}) for f in areas):
        click.echo(
            "note: some zones carry no `confidence`; the plate draws those as assessed, "
            "the strongest claim. Add assessed / reported / claimed before publishing.",
            err=True,
        )
    text = yaml.safe_dump(blocks, allow_unicode=True, sort_keys=False)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(out)
    else:
        click.echo(text, nl=False)


# The argparse front door spelled this sub-command `situation_map`, and
# TRIGGERS.md, SKILL.md and the hub's routing table all tell an agent to type
# that. Click's own idiom is the hyphen. Both are registered on the one
# callback rather than picking a winner: renaming would break every published
# instruction, and keeping only the underscore would read as a typo to anyone
# who knows click. Two spellings, one command -- the same bargain as
# `make-map` and `sprezzature-maps`.
main.add_command(main.commands["situation-map"], "situation_map")
main.add_command(main.commands["situation-new"], "situation_new")

# The skill this package ships, one sub-command away: `sprezzature-maps skill --install`.
main.add_command(skill_command)


if __name__ == "__main__":
    main()
