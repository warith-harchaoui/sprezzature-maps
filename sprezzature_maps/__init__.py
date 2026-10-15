"""sprezzature-maps: hand-authored SVG world maps — choropleth, situation map, accumulation map.

A focused sibling of `sprezzature-figures <https://github.com/warith-harchaoui/sprezzature-figures>`_,
carrying its "real basemap" geospatial generators: `choropleth` (each
country filled with a colour encoding a number), `situation_map` (a layered
"who controls what" plate for any region) and `density` (point events binned
to a field, where the events draw the geography and no coastline is), as
an independent product with its own release schedule and, eventually,
its own visual editor. Depends on ``sprezzature-figures`` for the
rendering primitives the two products share (embedding fonts inside the
SVG file, and choosing between a self-contained SVG and one that links to
external files) rather than keeping a second copy of that code.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

__version__ = "0.18.0"

# In the source tree the generators live in scripts/; once installed they
# ship (collision-free) as the sibling package sprezzature_maps_scripts/,
# same pattern as sprezzature-figures. Check the dedicated installed name
# FIRST: a bare scripts/ at the root of site-packages is a generic name an
# unrelated package can also claim.
_SCRIPTS_DIR = next(
    (
        Path(__file__).resolve().parent.parent / name
        for name in ("sprezzature_maps_scripts", "scripts")
        if (Path(__file__).resolve().parent.parent / name).is_dir()
    ),
    Path(__file__).resolve().parent.parent / "scripts",
)


def _load_script(name: str) -> Any:
    """Load (and cache) a ``scripts/<name>.py`` module, matching
    sprezzature-figures' own loader.

    The generator scripts import sibling helpers by bare name (``from
    _render import ...``), so ``scripts/`` must be on ``sys.path`` before
    ``exec_module`` runs.

    Parameters
    ----------
    name : str
        Module stem under ``scripts/`` (e.g. ``"make_choropleth"``).

    Returns
    -------
    module
        The loaded module, from ``sys.modules`` on every call after the
        first. This is the application-service layer every CLI/API/MCP/GUI
        surface calls through (see CODING.md Sec 19.1) -- once those
        surfaces exist, a FastAPI worker handling many requests would
        otherwise re-parse and re-``exec`` this file (plus its numpy/PIL
        imports) on *every single call*, which the earlier unconditional
        ``exec_module`` did. Checking ``sys.modules`` first makes this a
        cheap dict lookup after the first load, same as a normal
        ``import``.
    """
    scripts_dir = str(_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    # A second call for the same generator is the common case once any
    # long-lived surface (API, MCP) calls into this repeatedly -- reuse
    # the already-executed module instead of re-loading it from disk.
    if name in sys.modules:
        return sys.modules[name]
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load script: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def make_choropleth(*args: Any, **kwargs: Any) -> Path:
    """Render a world choropleth map. See ``scripts/make_choropleth.py`` for the full signature."""
    return _load_script("make_choropleth").make_choropleth(*args, **kwargs)


def make_situation_map(*args: Any, **kwargs: Any) -> Path:
    """Render a layered areas-of-control situation map. See ``scripts/make_situation_map.py`` for the full signature."""
    return _load_script("make_situation_map").make_situation_map(*args, **kwargs)


def make_density(*args: Any, **kwargs: Any) -> Path:
    """Render an accumulation map, where the events draw the geography. See ``scripts/make_density.py``."""
    return _load_script("make_density").make_density(*args, **kwargs)


def acled_events(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return the plate config for an ACLED export. See ``scripts/_conflict.py``.

    The bridge between the file a conflict researcher already has and the
    marker layer that already knows what ACLED's precision codes mean. The
    result is a config fragment: ``cfg.update(acled_events("sudan.csv"))``.
    """
    return _load_script("_conflict").acled_events(*args, **kwargs)


def ucdp_events(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return the plate config for a UCDP Georeferenced Event Dataset export.

    Same bridge for UCDP, whose seven-step ``where_prec`` is mapped onto this
    generator's three in a table written out in ``scripts/_conflict.py``
    rather than hidden in a branch -- including the step that has no honest
    answer, ``where_prec`` 6, where only the country is known.
    """
    return _load_script("_conflict").ucdp_events(*args, **kwargs)


def article_sidecar(svg: str) -> dict[str, Any]:
    """Return the metadata a page needs around a finished plate.

    An article that a map illustrates still needs an ``alt`` string, a
    caption and the numbers the map asserts, and today each of those is
    retyped into a CMS by looking at the picture -- which is how a caption
    comes to disagree with the plate above it. This reads them back out of
    the SVG itself, so the two cannot drift apart.

    Parameters
    ----------
    svg : str
        A finished plate, as returned by the generators.

    Returns
    -------
    dict
        ``title``, ``alt`` (the accessible description plus a computed
        takeaway), ``description``, ``zones`` and ``markers``.
    """
    return _load_script("_sidecar").article_sidecar(svg)


def plate_provenance(svg: str) -> dict[str, Any]:
    """Return the provenance stamp a finished plate carries, if any.

    Parameters
    ----------
    svg : str
        A finished plate.

    Returns
    -------
    dict
        ``generator``, ``version``, ``config_sha256`` and ``inputs``
        (``{name, sha256, bytes}`` per file). Empty for a plate rendered
        without ``provenance``, which is the default.
    """
    return _load_script("_sidecar").plate_provenance(svg)


def replay_report(svg: str, cfg: Any, files: Any = ()) -> dict[str, Any]:
    """Say whether a config and a set of files are what drew a plate.

    The question a reviewer asks of a published figure and that no caption
    can settle. The plate's stamp holds a digest of the code, of the config
    and of each file a loader read; this compares them against what is in
    front of you and names whichever one moved.

    Parameters
    ----------
    svg : str
        A plate carrying a provenance stamp.
    cfg : dict
        The config believed to have produced it.
    files : iterable of path, optional
        The files believed to have fed it. They have to be handed over: the
        stamp keeps basenames and digests, never directories.

    Returns
    -------
    dict
        ``replays``, ``differences``, ``unchecked`` and ``provenance``.
        ``replays`` is true only when everything the stamp names was
        checked and matched -- a stamped input nobody supplied leaves the
        plate unrefuted, not reproduced.

    Raises
    ------
    ValueError
        If the plate carries no stamp, since answering at all would mean
        answering about nothing.
    """
    return _load_script("_sidecar").replay_report(svg, cfg, files)


__all__ = [
    "acled_events",
    "article_sidecar",
    "make_choropleth",
    "make_density",
    "make_situation_map",
    "plate_provenance",
    "replay_report",
    "ucdp_events",
]
