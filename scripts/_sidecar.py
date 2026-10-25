"""
_sidecar: what a content management system needs next to the map file.

A map that illustrates an article is not the deliverable; the article is.
Around the image a page still needs an ``alt`` string, a caption, a credit
line and, if the piece is doing its job, the numbers the map asserts. Today
every one of those is typed a second time into the CMS, by hand, from
looking at the picture -- which is how a caption ends up disagreeing with
the plate above it after one of them is corrected and the other is not.

So this does not read the config. It reads **the finished SVG**: the
``<title>``/``<desc>`` the accessibility work already writes, and the
``data-*`` attributes the zones and markers already carry (svgis's
``--data-fields`` idea, which is what made this possible at all). A sidecar
derived from the artifact cannot drift from the artifact.

The ``alt`` string follows the formula accessibility practice has settled
on for charts -- *what kind of thing it is, what is in it, and what it
shows* -- because the third part is the one a generated description almost
always omits and the one a reader actually needs. Here the takeaway is
computed from the areas the plate really drew, not asserted.

The second half of this module answers the other question a page asks of a
figure -- the one review asks and a caption cannot settle: **is this picture
the one these inputs produce?** A plate already prints ``method``, ``source``
and ``as_of``: what it was drawn *from*, in prose, for a reader. None of that
is enough to redraw it. The drawing is a function of three things -- the
code, the config, and the file a loader read on the way in -- and the
optional provenance stamp fingerprints each, so that a mismatch later says
*which one moved*.

Three decisions in that stamp are each the opposite of the obvious one:

*It records digests, not the inputs.* Embedding the config would make the
file self-describing, and would also publish it: an ``areas_of_control``
config carries coordinates, a ``source`` carries a path that names someone's
machine, and this codebase has already once refused to draw a precise
location it was handed. A digest publishes nothing and lets anyone holding
the inputs prove the match, which is the direction a reviewer needs.

*It carries no clock.* A render time would make two renders of the same
inputs differ -- the field would destroy the property it exists to record.

*It is opt-in.* Not because it costs pixels (``<metadata>`` draws nothing)
but because it carries the package version, so switching it on by default
would change every committed plate at every release.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

#: ``data-*`` on a control zone, written by ``_areas_of_control_layer``.
_ZONE_RE = re.compile(
    r'data-category="([^"]*)" data-confidence="([^"]*)" data-area-share="([\d.]+)"'
)

#: ``data-*`` on a marker, written by ``_markers_layer``. The radius is
#: optional, so it is captured as its own group that may be absent.
_MARKER_RE = re.compile(
    r'data-precision="(\d)" data-lon="(-?[\d.]+)" data-lat="(-?[\d.]+)"'
    r'(?: data-radius-km="([\d.]+)")?'
)

#: The root ``<title>``/``<desc>``, whichever kind wrote them. Matched on the
#: element rather than on an id: the situation map stamps ``sm-title`` and the
#: choropleth ``cx-title``, and keying on one of them made this return a
#: hollow record for the other kinds -- an empty title, an empty alt string
#: and no error, which is the quietest way to be useless.
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.S)
_DESC_RE = re.compile(r"<desc\b[^>]*>(.*?)</desc>", re.S)


#: The provenance stamp's opening tag. Keyed on ``data-generator`` rather
#: than on an id, for the reason written above :data:`_TITLE_RE`: the three
#: generators prefix their ids differently, and a reader keyed on one of
#: them comes back empty for the other two and says nothing about it. The
#: trailing ``/?`` takes both the self-closing form (no inputs) and the
#: paired one.
_PROVENANCE_RE = re.compile(r'<metadata\b([^>]*?\bdata-generator="sprezzature-maps"[^>]*?)/?>')

#: One recorded input file. Scanned over the whole document rather than
#: inside the matched ``<metadata>``: the element name exists nowhere else,
#: so the narrower search would only be a second thing to keep in step.
_PROV_INPUT_RE = re.compile(r"<provenance-input\b([^>]*?)/>")

#: Any ``data-*`` pair, for reading a stamp's attributes back as a dict.
_ATTR_RE = re.compile(r'data-([a-z0-9-]+)="([^"]*)"')


def _unescape(text: str) -> str:
    """Undo the XML escape the generators apply on the way out.

    ``&amp;`` is undone last: doing it first would turn a literal
    ``&amp;lt;`` back into a ``<``.
    """
    return (
        text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")
    )


def _esc_attr(text: str) -> str:
    """Escape ``text`` for an XML attribute value.

    The inverse of :func:`_unescape`, and the ``"`` matters here in a way it
    does not for element text: a file named with a quote in it would
    otherwise close the attribute and silently truncate the record.
    """
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def article_sidecar(svg: str) -> dict[str, Any]:
    """Return the metadata a page needs around ``svg``, read back out of it.

    Parameters
    ----------
    svg : str
        A finished plate, as returned by a generator's ``build_map`` /
        ``build_svg``.

    Returns
    -------
    dict
        ``title``, ``alt``, ``description``, ``zones`` and ``markers``.
        ``zones`` and ``markers`` are empty lists for a plate that draws
        neither, which is the normal case for a locator map.

    Examples
    --------
    >>> svg = (
    ...     '<svg><title id="sm-title">Who holds what</title>'
    ...     '<desc id="sm-desc">Situation map covering 1.0°E to 2.0°E.</desc>'
    ...     '<path data-category="Blue" data-confidence="assessed" data-area-share="0.7000"/>'
    ...     '<path data-category="Red" data-confidence="claimed" data-area-share="0.3000"/>'
    ...     "</svg>"
    ... )
    >>> card = article_sidecar(svg)
    >>> card["title"]
    'Who holds what'
    >>> [z["category"] for z in card["zones"]]
    ['Blue', 'Red']
    >>> card["alt"]
    'Situation map covering 1.0°E to 2.0°E. Blue covers the largest mapped share, 70%.'

    A plate whose largest zone is only claimed says so, because "covers" and
    "is claimed to cover" are different sentences:

    >>> swapped = svg.replace('data-area-share="0.7000"', 'data-area-share="0.2000"')
    >>> article_sidecar(swapped)["alt"].endswith(
    ...     'Red is claimed to cover the largest mapped share, 30%.')
    True
    """
    title_match = _TITLE_RE.search(svg)
    desc_match = _DESC_RE.search(svg)
    title = _unescape(title_match.group(1)) if title_match else ""
    description = _unescape(desc_match.group(1)) if desc_match else ""

    zones = [
        {"category": _unescape(cat), "confidence": conf, "area_share": float(share)}
        for cat, conf, share in _ZONE_RE.findall(svg)
    ]
    markers = [
        {
            "precision": int(precision),
            "lon": float(lon),
            "lat": float(lat),
            **({"radius_km": float(radius)} if radius else {}),
        }
        for precision, lon, lat, radius in _MARKER_RE.findall(svg)
    ]
    return {
        "title": title,
        "description": description,
        "alt": _alt_text(description, zones),
        "zones": zones,
        "markers": markers,
    }


def _alt_text(description: str, zones: list[dict[str, Any]]) -> str:
    """Return the description with a takeaway appended, when one can be computed.

    The accessible ``<desc>`` on the plate says what kind of map it is and
    what is on it, which is two thirds of what alt text is supposed to do.
    The missing third is what it *shows*, and that is the part a reader who
    cannot see the plate has no other way to get.

    The takeaway here is deliberately the narrowest true statement
    available -- which class covers the most ground, and how much -- rather
    than a summary of the conflict. Anything larger would be the generator
    inventing an editorial line, and a plate's job is to draw the assessment
    it was given.

    A merely *claimed* largest share gets different wording, because a claim
    and a holding are not the same sentence and this is exactly the
    distinction the confidence tiers exist to preserve.
    """
    if not zones:
        return description
    # Several zones may share a class; the reader's question is about the
    # class, so sum them before ranking.
    by_class: dict[tuple[str, str], float] = {}
    for zone in zones:
        key = (str(zone["category"]), str(zone["confidence"]))
        by_class[key] = by_class.get(key, 0.0) + float(zone["area_share"])
    (category, confidence), share = max(by_class.items(), key=lambda kv: kv[1])
    verb = "is claimed to cover" if confidence == "claimed" else "covers"
    if confidence == "reported":
        verb = "is reported to cover"
    takeaway = f"{category} {verb} the largest mapped share, {share * 100:.0f}%."
    return f"{description} {takeaway}".strip()


# --------------------------------------------------------------------------- #
# Provenance: can this plate be redrawn from these inputs?                      #
# --------------------------------------------------------------------------- #


def _package_version() -> str:
    """Return the running ``sprezzature-maps`` version.

    Read from the package rather than from installed distribution metadata
    (``importlib.metadata``): an editable install's metadata goes stale the
    moment the source bumps, and this repository has already lost an
    afternoon to exactly that staleness on a sibling package. The version in
    ``__init__.py`` is the one ``test_release_consistency`` holds to
    ``pyproject.toml``, so it is the one that is true.

    Falls back to reading that file directly, for the case where the
    generators are used straight out of ``scripts/`` with the package not
    importable at all.
    """
    try:
        from sprezzature_maps import __version__

        return str(__version__)
    except Exception:  # pragma: no cover - only without the package on the path
        init = Path(__file__).resolve().parent.parent / "sprezzature_maps" / "__init__.py"
        if init.exists():
            found = re.search(r'^__version__ = "([^"]+)"', init.read_text(), re.M)
            if found:
                return found.group(1)
        # Stamped as-is rather than guessed. A reader comparing against it
        # gets a reported mismatch, which is the honest outcome; a plausible
        # wrong number would get a reported match.
        return "unknown"


def _canonical(value: Any) -> Any:
    """Make ``value`` JSON-serialisable for the digest, or refuse it.

    ``default=str`` would be the one-liner here and it is a trap: a numpy
    array's ``str`` elides its middle with ``...``, so two different arrays
    can stringify identically and two different configs would then digest
    identically. A fingerprint that can collide on purpose is worse than no
    fingerprint, so anything this does not know how to read honestly is
    refused by name.
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        # No order of its own, so the digest has to impose one.
        return sorted(str(item) for item in value)
    # numpy scalars and arrays, and anything else offering the same contract:
    # a lossless conversion to built-ins, which is what the digest needs.
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    raise TypeError(
        f"a {type(value).__name__} in the config cannot be fingerprinted: "
        "the digest only reads JSON values, dates, paths, sets and anything "
        "with .tolist(). Convert it before rendering, or leave provenance off."
    )


def config_digest(cfg: Mapping[str, Any]) -> str:
    """Return the sha256 of ``cfg``, serialised canonically.

    Keys the generators write into the config for their own use (the
    leading-underscore ones: the resolved plate palette, the relief cache,
    the directory the YAML was read from) are left out. They are outputs of
    the render, not inputs to it, and including them would make the digest
    depend on where the file happened to live.

    Parameters
    ----------
    cfg : mapping
        The config a generator was called with.

    Returns
    -------
    str
        Sixty-four lowercase hex digits.

    Examples
    --------
    Key order does not change it; a value does:

    >>> config_digest({"a": 1, "b": 2}) == config_digest({"b": 2, "a": 1})
    True
    >>> config_digest({"a": 1}) == config_digest({"a": 2})
    False

    Neither does the directory the config was loaded from:

    >>> config_digest({"a": 1, "_config_dir": "/home/x"}) == config_digest({"a": 1})
    True
    """
    public = {k: v for k, v in cfg.items() if not str(k).startswith("_")}
    body = json.dumps(public, sort_keys=True, separators=(",", ":"), default=_canonical)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def file_fingerprint(path: str | Path) -> dict[str, Any]:
    """Return ``{name, sha256, bytes}`` for the file at ``path``.

    The *basename* only, never the directory. A full path names a machine,
    sometimes a user and occasionally an operation, and none of that belongs
    in a figure that gets published; the digest already identifies the file
    to anyone who holds it, which is the only identification that can be
    checked anyway.

    Parameters
    ----------
    path : str or Path
        A file that fed the plate.

    Returns
    -------
    dict
        ``name`` (basename), ``sha256`` of the bytes, and ``bytes`` (size).

    Notes
    -----
    Read in chunks rather than with ``read_bytes``. The files this exists for
    are conflict-dataset exports, and a full ACLED download runs to hundreds
    of megabytes: the one-liner would hold all of it at once to compute a
    sixty-four-character answer.
    """
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return {"name": Path(path).name, "sha256": digest.hexdigest(), "bytes": size}


def _declared_inputs(raw: Any, base: str | Path | None) -> list[dict[str, Any]]:
    """Return the input records a ``provenance`` config section asks for.

    Two shapes are accepted because two kinds of caller write this. A
    loader has already read the file and contributes a finished record; a
    person writing YAML has only the path, so a string is fingerprinted
    here, resolved against the config's own directory.
    """
    records: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, Mapping):
            missing = {"name", "sha256", "bytes"} - set(item)
            if missing:
                raise ValueError(
                    f"a provenance input record is missing {', '.join(sorted(missing))}; "
                    "pass a path instead and it will be fingerprinted here."
                )
            records.append(dict(item))
            continue
        candidate = Path(item)
        if not candidate.is_absolute() and base is not None:
            candidate = Path(base) / candidate
        records.append(file_fingerprint(candidate))
    return records


def _with_loader_input(
    cfg: Mapping[str, Any], declared: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Put the loader's own file at the head of ``declared``.

    A loader is the only place in the chain that still knows which export a
    plate came from: by the time a generator sees the config, the rows are
    inline and the path is gone. It leaves the record under ``_source_file``
    rather than switching the stamp on, so the default stays opt-in -- and so
    a caller who wrote ``provenance: false`` before ``cfg.update(loader(...))``
    is not quietly overruled by the loader that ran after them.

    A caller who also named the same file by hand gets it recorded once.
    """
    found = cfg.get("_source_file")
    if not isinstance(found, Mapping):
        return list(declared)
    already = {(rec.get("name"), rec.get("sha256")) for rec in declared}
    if (found.get("name"), found.get("sha256")) in already:
        return list(declared)
    return [dict(found), *declared]


def provenance_metadata(cfg: Mapping[str, Any], base: str | Path | None = None) -> str:
    """Return the ``<metadata>`` stamp for ``cfg``, or ``""`` when it is off.

    Parameters
    ----------
    cfg : mapping
        The config the plate is being drawn from. ``provenance`` switches
        this on: ``true`` for the code-and-config fingerprint, or a mapping
        with ``inputs`` (paths, or records a loader already built) to also
        record files that fed it and that the config no longer names. A
        ``_source_file`` left by a loader is picked up either way, since a
        config that asked for a stamp should not also have to re-name the
        export the loader already dissolved into ``events``.
    base : str or Path, optional
        Directory a relative input path is resolved against -- the config's
        own directory, as everywhere else in these generators.

    Returns
    -------
    str
        SVG markup drawing nothing, or the empty string. Empty rather than
        an empty element: a plate that did not ask for a stamp has to come
        out byte-for-byte as it did before.

    Examples
    --------
    >>> provenance_metadata({"region": {"bbox": [0, 0, 1, 1]}})
    ''
    >>> stamp = provenance_metadata({"region": {"bbox": [0, 0, 1, 1]}, "provenance": True})
    >>> stamp.startswith('<metadata id="provenance" data-generator="sprezzature-maps"')
    True
    >>> "data-config-sha256=" in stamp
    True
    """
    raw = cfg.get("provenance")
    if raw is None or raw is False:
        return ""
    if raw is True:
        declared: list[dict[str, Any]] = []
    elif isinstance(raw, Mapping):
        unknown = sorted(set(raw) - {"inputs"})
        if unknown:
            raise ValueError(
                f"provenance has key(s) this generator never reads: {', '.join(unknown)}. "
                "Known provenance keys: inputs"
            )
        declared = _declared_inputs(raw.get("inputs"), base)
    else:
        raise ValueError(f"provenance is {raw!r}; write true, false, or a mapping with 'inputs'.")
    inputs = _with_loader_input(cfg, declared)

    head = (
        '<metadata id="provenance" data-generator="sprezzature-maps" '
        f'data-version="{_esc_attr(_package_version())}" '
        f'data-config-sha256="{config_digest(cfg)}"'
    )
    if not inputs:
        return head + "/>"
    body = "".join(
        f'<provenance-input data-name="{_esc_attr(str(rec["name"]))}" '
        f'data-sha256="{_esc_attr(str(rec["sha256"]))}" '
        f'data-bytes="{int(rec["bytes"])}"/>'
        for rec in inputs
    )
    return f"{head}>{body}</metadata>"


def plate_provenance(svg: str) -> dict[str, Any]:
    """Return the provenance stamp read back out of ``svg``.

    Parameters
    ----------
    svg : str
        A finished plate.

    Returns
    -------
    dict
        ``generator``, ``version``, ``config_sha256`` and ``inputs``
        (a list of ``{name, sha256, bytes}``). Empty for an unstamped
        plate, which is most of them: the stamp is opt-in.

    Examples
    --------
    >>> svg = "<svg>" + provenance_metadata({"region": "x", "provenance": True}) + "</svg>"
    >>> plate_provenance(svg)["generator"]
    'sprezzature-maps'
    >>> plate_provenance("<svg><title>no stamp</title></svg>")
    {}
    """
    found = _PROVENANCE_RE.search(svg)
    if not found:
        return {}
    attrs = dict(_ATTR_RE.findall(found.group(1)))
    inputs = []
    for chunk in _PROV_INPUT_RE.findall(svg):
        rec = dict(_ATTR_RE.findall(chunk))
        inputs.append(
            {
                "name": _unescape(rec.get("name", "")),
                "sha256": rec.get("sha256", ""),
                "bytes": int(rec.get("bytes", 0)),
            }
        )
    return {
        "generator": _unescape(attrs.get("generator", "")),
        "version": _unescape(attrs.get("version", "")),
        "config_sha256": attrs.get("config-sha256", ""),
        "inputs": inputs,
    }


def replay_report(
    svg: str,
    cfg: Mapping[str, Any],
    files: Iterable[str | Path] = (),
) -> dict[str, Any]:
    """Say whether ``cfg`` and ``files`` are what drew ``svg``.

    Parameters
    ----------
    svg : str
        A plate carrying a provenance stamp.
    cfg : mapping
        The config believed to have produced it -- the one a generator was
        called with, after any loader fragment was merged in.
    files : iterable of path, optional
        The files believed to have fed it. They have to be handed over:
        the stamp records basenames and digests, never directories, so
        nothing in the plate can go looking for them.

    Returns
    -------
    dict
        ``replays`` (bool), ``differences`` (a list of sentences, empty when
        there are none), ``unchecked`` (stamped inputs nobody supplied) and
        ``provenance`` (the stamp itself).

        ``replays`` is true only when everything the stamp names was checked
        and matched. An input that was not supplied makes it false, with the
        reason in ``unchecked``: a plate whose inputs nobody produced is not
        reproduced, it is merely unrefuted, and the two deserve different
        answers.

    Raises
    ------
    ValueError
        If ``svg`` carries no stamp. Refusing beats returning
        ``replays: True`` for a plate that recorded nothing -- a caller
        reading that would have been told the opposite of what is known.

    Examples
    --------
    >>> cfg = {"region": "Sudan", "provenance": True}
    >>> svg = "<svg>" + provenance_metadata(cfg) + "</svg>"
    >>> replay_report(svg, cfg)["replays"]
    True
    >>> report = replay_report(svg, {**cfg, "region": "Chad"})
    >>> report["replays"], len(report["differences"])
    (False, 1)
    """
    stamp = plate_provenance(svg)
    if not stamp:
        raise ValueError(
            "this plate carries no provenance stamp, so there is nothing to check "
            "it against. Re-render with `provenance: true` in the config."
        )

    differences: list[str] = []
    unchecked: list[str] = []

    running = _package_version()
    if stamp["version"] != running:
        differences.append(f"drawn by sprezzature-maps {stamp['version']}; {running} is installed")

    digest = config_digest(cfg)
    if stamp["config_sha256"] != digest:
        differences.append(
            f"the config differs: {stamp['config_sha256'][:12]} on the plate, {digest[:12]} here"
        )

    # Keyed by basename, which is all the stamp kept -- and a list per name,
    # because a caller can legitimately offer two candidates for one name.
    supplied: dict[str, list[dict[str, Any]]] = {}
    for path in files:
        record = file_fingerprint(path)
        supplied.setdefault(record["name"], []).append(record)

    for want in stamp["inputs"]:
        got = supplied.pop(want["name"], None)
        if not got:
            unchecked.append(want["name"])
            continue
        if not any(rec["sha256"] == want["sha256"] for rec in got):
            differences.append(
                f"{want['name']} differs: {want['sha256'][:12]} on the plate, "
                f"{got[0]['sha256'][:12]} on disk"
            )

    # Whatever is left was offered as an input and the plate never saw it.
    # That is the caller asserting something about this figure that is not
    # true of it, and the usual cause is handing over the wrong export.
    for name in sorted(supplied):
        differences.append(f"{name} was not an input to this plate")

    return {
        "replays": not differences and not unchecked,
        "differences": differences,
        "unchecked": unchecked,
        "provenance": stamp,
    }
