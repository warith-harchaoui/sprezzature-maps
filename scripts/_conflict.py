"""
_conflict: turn a conflict-event export into the config a plate is drawn from.

The two datasets peace-and-conflict research actually runs on are ACLED and
the UCDP Georeferenced Event Dataset. Both ship a row per event with
coordinates, a date, an actor pair and a death count -- and, the part
everything else throws away, **a code saying how well the location and the
date are known**. ACLED records ``geo_precision`` 1-3 and
``time_precision`` 1-3; UCDP records ``where_prec`` 1-7 and ``date_prec``
1-5. Those codes are not metadata about the file. They are the dataset
telling you which of its own rows are a street address and which are a
provincial capital standing in for a province the size of Bavaria.

Every map of this data that this author has seen draws all of them as the
same dot. ``make_situation_map`` already does not: a marker carries
``precision`` and ``time_precision`` and draws a ring, a dash pattern and a
spoken date accordingly (see ``_GEO_PRECISION`` there, whose wording comes
from ACLED's own codebook). What was missing was the twenty lines between a
researcher's CSV and that marker, and twenty missing lines is the difference
between a feature that exists and a feature anyone uses.

So: one call, from the file they already have.

>>> rows = [{"event_date": "2024-03-05", "latitude": "15.5", "longitude": "32.5",
...          "event_type": "Battles", "geo_precision": "1", "time_precision": "1",
...          "fatalities": "4", "source": "Radio Dabanga", "location": "Omdurman",
...          "notes": "", "admin1": "Khartoum"}]
>>> fragment = acled_events(rows)
>>> fragment["events"][0]["lon"], fragment["events"][0]["precision"]
(32.5, 1)
>>> fragment["marker_legend"]
[{'color': '#0072B2', 'label': 'Battles', 'precision': 1}]

The return value is a *config fragment*, not a finished map: the keys it
carries are keys ``build_map`` already reads, so it composes with a config
written by hand rather than replacing one.

>>> cfg = {"title": "Sudan", "region": {"bbox": [21.8, 8.6, 38.6, 22.2]}}
>>> cfg.update(fragment)
>>> sorted(cfg)
['events', 'marker_legend', 'method', 'region', 'title']

What it will not do
-------------------
It will not invent a position. UCDP ``where_prec`` 6 means *only the country
is known*; the row still carries coordinates, because every row must, and
they are a representative point for a whole state. Drawing them is how a map
comes to assert that a massacre happened at a particular bend in a river
because that is where the country's centroid fell. Those rows are dropped by
default and **counted in the plate's own method line**, because a silent drop
is the other half of the same dishonesty.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import json
import math
import warnings
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

#: A categorical palette for event classes, published values, ordered by
#: how well a *prefix* of it survives colour-vision deficiency.
#:
#: Okabe-Ito, the eight-colour set designed to stay distinguishable to
#: readers with the three common colour-vision deficiencies. Taken at its
#: published values and not retuned, for a reason worth recording, because
#: the obvious improvement is the wrong one.
#:
#: The obvious improvement is to darken the pale members until every disc
#: clears 3:1 against this project's cream land (``#f4efdd``), where
#: Okabe-Ito's orange manages 1.96:1. Doing it was measured, and it makes
#: the palette *worse*: forcing six colours to the same luminance removes
#: the lightness differences, and lightness is the one channel all three
#: deficiencies leave intact. The worst pair falls from 0.076 to 0.019 in
#: OKLab distance under simulation -- four times less separable -- in
#: exchange for contrast the disc does not need, because a marker is drawn
#: with a white casing and a shadow. **The casing makes the mark visible;
#: the fill says which category it is.** Loading both jobs onto the fill is
#: what breaks it.
#:
#: The order is not the published one. The palette is consumed as a prefix
#: -- three classes take the first three -- so the order was chosen by
#: searching all 720 permutations for the one whose every prefix has the
#: largest minimum pairwise distance under protanopia, deuteranopia and
#: tritanopia at once. At three classes that raises the floor from 0.084 to
#: 0.189. ``tests/test_conflict_loaders.py`` pins each prefix floor, so a
#: reordering that quietly costs separation fails rather than ships.
#:
#: Black and yellow are last and outside that search: black is the one
#: colour that never reads as a category beside five hues, and a small
#: yellow disc on cream is a disc a reader hunts for. Neither is reached by
#: the bundled vocabularies (six ACLED types, three UCDP ones).
OKABE_ITO: tuple[str, ...] = (
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#009E73",  # bluish green
    "#000000",  # black
    "#F0E442",  # yellow
)

#: How many categorical colours a dot map can carry before colour stops
#: being the thing that separates them.
#:
#: Not a limit -- the sixth colour is drawn, and the vocabulary can be
#: extended past it. It is the point past which the measurement says the
#: claim gets thin: the palette's worst pair under simulation falls from
#: 0.131 at four classes to 0.086 at five and 0.076 at six. A reader is
#: told once, with the column that would fix it.
_CROWDED_LEGEND = 5

#: ACLED's six event types, in the codebook's own hierarchical order.
#:
#: Fixed rather than discovered, so the same type is the same colour on two
#: plates drawn from two different country files -- a legend that reshuffles
#: between figures in one paper is a legend the reader has to re-learn.
ACLED_EVENT_TYPES: tuple[str, ...] = (
    "Battles",
    "Explosions/Remote violence",
    "Violence against civilians",
    "Protests",
    "Riots",
    "Strategic developments",
)

#: UCDP's ``type_of_violence``, from the GED codebook.
UCDP_VIOLENCE_TYPES: dict[int, str] = {
    1: "State-based conflict",
    2: "Non-state conflict",
    3: "One-sided violence",
}

#: ``where_prec`` (UCDP, 1-7) onto this generator's ``precision`` (1-3).
#:
#: The two scales were built for different purposes and the mapping is a
#: judgement, so it is written down rather than buried in an ``if``. UCDP's
#: wording, verbatim from the GED 25.1 codebook, against what this
#: generator's own table means:
#:
#: * 1 "exact location of the event known and coded" -> 1, named location.
#: * 2 "within at maximum a ca. 25 km radius around a known point" -> 2,
#:   and the 25 km is kept as an explicit ``radius_km`` rather than thrown
#:   away: the dataset states the radius, so the plate can draw it.
#: * 3 "only the second order administrative division ... coded with a point
#:   representing it (typically the centroid)" -> 2, a place standing in for
#:   a general area.
#: * 4 the same for the *first* order division -> 3, a place standing in for
#:   a whole region.
#: * 5 "neither a known point nor a known formal administrative division,
#:   but rather a linear feature ... or a fuzzy polygon" -> 3.
#: * 6 "only the country where the event took place in is known" -> no
#:   honest point exists; see :func:`ucdp_events`.
#: * 7 "event in international waters or airspace" -> 3. The coordinates are
#:   real but the feature is not a place.
UCDP_WHERE_PREC: dict[int, int | None] = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: None, 7: 3}

#: ``date_prec`` (UCDP, 1-5) onto ``time_precision``.
#:
#: The generator's scale was ACLED's three steps -- day, week, month. UCDP
#: has a fifth step this project had no word for, "known only within a range
#: longer than one month but not more than one calendar year", so
#: ``make_situation_map`` grew a fourth level rather than rounding a year
#: down to a month and overstating it.
UCDP_DATE_PREC: dict[int, int] = {1: 1, 2: 2, 3: 2, 4: 3, 5: 4}


def _rows(source: Any) -> list[dict[str, Any]]:
    """Return a list of row dicts from a path, an open file, or an iterable.

    A researcher has the data in whichever of three shapes their last step
    left it: a downloaded ``.csv``, a ``.json`` body from the API, or a list
    of dicts already in memory (including ``DataFrame.to_dict("records")``,
    which is how this accepts pandas without depending on it).
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() in (".json", ".jsonl"):
            if path.suffix.lower() == ".jsonl":
                return [json.loads(line) for line in text.splitlines() if line.strip()]
            body = json.loads(text)
            # The ACLED API answers {"status":200,"data":[...]}; a hand-saved
            # file is usually the bare list. Take either.
            if isinstance(body, Mapping):
                for key in ("data", "results", "events", "features"):
                    if isinstance(body.get(key), list):
                        return list(body[key])
                raise ValueError(
                    f"{path} is a JSON object with no 'data', 'results' or 'events' list; "
                    "pass the list of event records, or the API body that contains one."
                )
            return list(body)
        return list(csv.DictReader(text.splitlines()))
    if isinstance(source, Iterable):
        return [dict(r) for r in source]
    raise TypeError(f"expected a path or an iterable of rows, got {type(source).__name__}")


def _number(raw: Any, field: str, row: int) -> float:
    """Return ``raw`` as a float, naming the row and column when it is not one."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"row {row}: {field} is {raw!r}, which is not a number. "
            "A conflict export with an unparseable coordinate is a file worth "
            "looking at rather than a row worth skipping."
        ) from None


def _code(raw: Any, field: str, row: int, allowed: Iterable[int]) -> int:
    """Return ``raw`` as one of ``allowed``, refusing anything else.

    Deliberately strict. Treating an unreadable precision code as "exact" is
    the one direction this whole feature exists to prevent, and a dataset
    that has changed its codes under you is worth an error, not a shrug.
    """
    allowed = tuple(allowed)
    try:
        code = int(str(raw).strip())
    except (TypeError, ValueError):
        code = -1
    if code not in allowed:
        raise ValueError(
            f"row {row}: {field} is {raw!r}; this loader knows "
            f"{', '.join(str(a) for a in allowed)}. If the dataset has changed its "
            "codes, the mapping in scripts/_conflict.py needs changing with it."
        )
    return code


def _magnitude(raw: Any) -> float:
    """Return ``raw`` as a non-negative magnitude, or zero."""
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def _radii(values: list[float], base: float, biggest: float) -> list[float]:
    """Return one radius per value: area-true, and bounded by the page.

    Two rules, and the second is the one a square root alone gets wrong.

    *Area-true*: a disc is read by its area, so the radius goes as the square
    root of the value. Scaling the radius directly would quadruple the ink
    for twice the deaths and quadruple the number the reader takes away.

    *Bounded*: the scale is set by the largest value **in this file**, not by
    an absolute constant, because conflict magnitudes span four orders and no
    constant survives both a protest and a massacre. An earlier version used
    ``base * sqrt(1 + value)`` with no ceiling; on ten synthetic rows the
    120-fatality mark came out at radius 33 -- a disc wider than Darfur, and,
    because the generator scales an approximate ring's stroke with its radius,
    one drawn as a 15-unit-thick cogwheel. That was found by rendering it and
    looking, which is the only way that kind of defect is ever found.
    """
    top = max(values) if values else 0.0
    if top <= 0.0:
        return [base for _ in values]
    span = biggest - base
    return [round(base + span * math.sqrt(v / top), 2) for v in values]


def _legend(
    classes: list[str], palette: Iterable[str], precision: int = 1
) -> list[dict[str, Any]]:
    """Return one legend row per class met, in the order the vocabulary lists them.

    ``precision`` is the symbol the key draws, and it has to be the symbol the
    plate draws. Aggregated marks come out at precision 3 -- hollow, broken --
    and a key that kept showing a solid disc beside them would be teaching the
    reader the wrong symbol on the same page it teaches them the colour. Found
    by rendering an aggregated plate and looking at its legend.
    """
    palette = tuple(palette)
    if len(classes) > len(palette):
        raise ValueError(
            f"{len(classes)} event classes but only {len(palette)} colours in the "
            "palette. Pass a longer `palette=`, or group the classes first: a "
            "legend with nine categorical colours is a legend nobody reads."
        )
    return [
        {"color": palette[i], "label": label, "precision": precision}
        for i, label in enumerate(classes)
    ]


def _bbox(events: list[dict[str, Any]], pad: float) -> list[float]:
    """Return ``[west, south, east, north]`` around ``events``, padded in degrees."""
    lons = [e["lon"] for e in events]
    lats = [e["lat"] for e in events]
    return [min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad]


def _method_line(kept: int, dropped: dict[str, int], dataset: str, window: str) -> str:
    """Return the sentence the plate prints about its own evidence base.

    Every number a reviewer would ask for, on the map rather than in a
    console the reader never saw: how many events are drawn, over what
    window, and -- the one that matters -- how many the loader refused to
    draw and why. ``publish_gallery``'s lesson, applied to data: a count
    nobody can reconstruct is a count nobody should believe.
    """
    parts = [f"{kept:,} {dataset} event{'s' if kept != 1 else ''} drawn"]
    if window:
        parts.append(window)
    line = "; ".join(parts) + "."
    if dropped:
        why = "; ".join(f"{n:,} {reason}" for reason, n in sorted(dropped.items()) if n)
        if why:
            line += f" Not drawn: {why}."
    return line


def _window(dates: list[str]) -> str:
    """Return ``"2024-01-03 to 2024-12-29"`` from the dates actually kept."""
    real = sorted(d for d in dates if d)
    if not real:
        return ""
    return real[0] if real[0] == real[-1] else f"{real[0]} to {real[-1]}"


#: The columns each dataset names its administrative units in.
#:
#: Both publish them, and both spell them differently: ACLED's ``admin1`` is
#: UCDP's ``adm_1``. A caller who asks to aggregate by first-order unit should
#: not have to know which file they are holding.
_UNIT_COLUMNS: dict[str, dict[str, str]] = {
    "ACLED": {"admin1": "admin1", "admin2": "admin2"},
    "UCDP": {"admin1": "adm_1", "admin2": "adm_2"},
}


def _aggregate(
    events: list[dict[str, Any]], unit_of: Callable[[dict[str, Any]], str]
) -> tuple[list[dict[str, Any]], int]:
    """Collapse one mark per event into one mark per (class, administrative unit).

    The reason is not cartographic tidiness. OCHA's data-responsibility
    guidance is blunt about it: a map that plots where vulnerable people are
    can be the thing that finds them, and location data is hard to anonymise
    precisely because coordinates are identifying. A dot map of four thousand
    events over a displacement crisis is a dot map of four thousand places
    somebody could go.

    Aggregating is the usual answer, and the usual answer is usually done
    dishonestly: the aggregate is drawn as a confident dot at a centroid, as
    though the pile of events happened there. Here it cannot be, because the
    mark that comes out **declares what it is**. A unit's aggregate is
    ``precision`` 3 -- *a place standing in for a whole region* -- which is
    the generator's existing wording for exactly this situation, so it draws
    as a hollow broken ring and its tooltip and its accessible name both say
    so. The symbology was already right; it only had to be told the truth.

    The position is the mean of the member coordinates. That is a
    representative point and not a centroid of the unit, and on a crescent-
    shaped region it can fall outside the unit it represents -- which is a
    real caveat and the reason the mark is drawn at the weakest precision
    rather than a strong one.

    Returns
    -------
    tuple
        The aggregated marks, and how many units they cover.
    """
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mark in events:
        key = (str(mark["_class"]), unit_of(mark))
        buckets.setdefault(key, []).append(mark)

    out: list[dict[str, Any]] = []
    for (cls, unit), members in buckets.items():
        n = len(members)
        dates = sorted(str(m.get("date") or "") for m in members if m.get("date"))
        window = ""
        if dates:
            window = dates[0] if dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}"
        agg: dict[str, Any] = {
            "lon": round(sum(m["lon"] for m in members) / n, 4),
            "lat": round(sum(m["lat"] for m in members) / n, 4),
            # Not a choice: an aggregate *is* a place standing in for a whole
            # region, and that is what code 3 means.
            "precision": 3,
            "time_precision": 1,
            "_class": cls,
            "label": f"{unit}: {n} event{'s' if n != 1 else ''}" if unit else
                     f"{n} event{'s' if n != 1 else ''}",
            "color": None,
        }
        if window:
            agg["date"] = window
        if "_magnitude" in members[0]:
            agg["_magnitude"] = sum(float(m.get("_magnitude", 0.0)) for m in members)
        out.append(agg)
    return out, len({unit for _, unit in buckets})


def _common(
    rows: list[dict[str, Any]],
    *,
    vocabulary: list[str],
    class_of: Callable[[dict[str, Any], int], str],
    place: Callable[[dict[str, Any], int], dict[str, Any] | str],
    dataset: str,
    palette: Iterable[str],
    size_by: str | None,
    base_radius: float,
    max_radius: float,
    tooltip_from: str | None,
    aggregate: str | None,
    derive_region: bool,
    region_pad: float,
    limit: int | None,
) -> dict[str, Any]:
    """Shared body of :func:`acled_events` and :func:`ucdp_events`.

    The two loaders differ only in their column names and their precision
    tables; everything after that -- colouring, legend, sizing, the method
    line, the derived region -- is one piece of code so the two datasets
    cannot drift into drawing differently.
    """
    events: list[dict[str, Any]] = []
    dropped: dict[str, int] = {}
    met: list[str] = []
    dates: list[str] = []

    for n, row in enumerate(rows, start=1):
        mark = place(row, n)
        if isinstance(mark, str):  # a reason, not a marker
            dropped[mark] = dropped.get(mark, 0) + 1
            continue
        label = class_of(row, n)
        if vocabulary and label not in vocabulary:
            raise ValueError(
                f"row {n}: {dataset} class {label!r} is not one this loader knows "
                f"({', '.join(vocabulary)}). Pass `vocabulary=` to extend it."
            )
        if label not in met:
            met.append(label)
        mark["color"] = None  # filled once the legend order is settled
        mark["_class"] = label
        if size_by:
            mark["_magnitude"] = _magnitude(row.get(size_by))
        if tooltip_from and row.get(tooltip_from):
            mark["label"] = str(row[tooltip_from])
        if aggregate:
            column = _UNIT_COLUMNS[dataset].get(aggregate, aggregate)
            if column not in row:
                raise ValueError(
                    f"aggregate={aggregate!r} needs a {column!r} column and this "
                    f"{dataset} export has none. Known shorthands: "
                    f"{', '.join(sorted(_UNIT_COLUMNS[dataset]))}; anything else is "
                    "taken as a column name."
                )
            mark["_unit"] = str(row.get(column) or "")
        events.append(mark)
        dates.append(str(mark.get("date") or ""))

    units = 0
    if aggregate:
        # Before the radii: an aggregate's magnitude is the sum of its members,
        # so scaling the members first would set the scale by a single event.
        before = len(events)
        events, units = _aggregate(events, lambda m: str(m.pop("_unit", "")))
        aggregated = f"{before:,} events aggregated to {units:,} {aggregate} units"
    if size_by:
        # Set after the loop, not inside it: the scale is relative to the
        # largest value in this file, which is not known until the last row.
        for mark, r in zip(
            events,
            _radii([m.pop("_magnitude") for m in events], base_radius, max_radius),
            strict=True,
        ):
            mark["r"] = r

    classes = [c for c in vocabulary if c in met] if vocabulary else met
    if len(classes) > _CROWDED_LEGEND:
        warnings.warn(
            f"{len(classes)} categorical colours on one plate: past {_CROWDED_LEGEND} "
            "the palette's worst pair stops being reliably separable under "
            "colour-vision deficiency, and colour is no longer doing the work. "
            "Colouring by a coarser column -- ACLED's 'disorder_type' has three "
            "values, UCDP's type_of_violence three -- or drawing one plate per "
            "class reads better than a sixth hue.",
            RuntimeWarning,
            stacklevel=3,
        )
    legend = _legend(classes, palette, precision=3 if aggregate else 1)
    colour = {row["label"]: row["color"] for row in legend}
    for mark in events:
        mark["color"] = colour[mark.pop("_class")]

    if limit is not None and len(events) > limit:
        dropped[f"beyond the {limit:,}-event limit"] = len(events) - limit
        events = events[:limit]

    method = _method_line(len(events), dropped, dataset, _window(dates))
    if aggregate:
        # The reader is looking at 18 marks drawn from 1,284 events and has no
        # way to know that unless the plate says it. An aggregate that does
        # not announce itself is a map claiming 18 things happened.
        method = (
            f"{aggregated}; each mark is a representative point for its unit, "
            f"not a location. " + method.split("; ", 1)[-1]
            if "; " in method
            else f"{aggregated}. " + method
        )
    fragment: dict[str, Any] = {
        "events": events,
        "marker_legend": legend,
        "method": method,
    }
    if derive_region:
        if not events:
            raise ValueError(
                "derive_region=True but no event survived the filters, so there is "
                "no region to derive. Pass region= explicitly, or widen the filters."
            )
        fragment["region"] = {"bbox": _bbox(events, region_pad)}
    for reason, n in sorted(dropped.items()):
        if n:
            warnings.warn(
                f"{dataset}: {n:,} row(s) not drawn ({reason}). "
                "The count is on the plate's method line as well.",
                RuntimeWarning,
                stacklevel=3,
            )
    return fragment


def acled_events(
    source: Any,
    *,
    colour_by: str = "event_type",
    vocabulary: Iterable[str] | None = None,
    palette: Iterable[str] = OKABE_ITO,
    size_by: str | None = None,
    base_radius: float = 3.0,
    max_radius: float = 11.0,
    tooltip_from: str | None = None,
    aggregate: str | None = None,
    derive_region: bool = False,
    region_pad: float = 0.6,
    limit: int | None = None,
) -> dict[str, Any]:
    """Return the plate config for an ACLED export.

    Parameters
    ----------
    source : path, str, or iterable of dict
        An ACLED ``.csv``, an API ``.json`` body, or rows already in memory
        (``DataFrame.to_dict("records")`` included).
    colour_by : str, optional
        The column whose values become the legend. ``"event_type"`` by
        default; ``"disorder_type"`` and ``"sub_event_type"`` are the other
        two the codebook offers.
    vocabulary : iterable of str, optional
        The classes to expect, in legend order. Defaults to
        :data:`ACLED_EVENT_TYPES` when colouring by ``event_type``, and
        otherwise to the order the classes are met. Fixing it is what keeps
        two plates in one paper on the same legend.
    palette : iterable of str, optional
        Colours, one per class. :data:`OKABE_ITO` by default.
    size_by : str, optional
        A column to scale the disc by, area-true -- the radius goes as the
        square root, so four times the value is twice the radius and the
        *ink* is what reads. ``"fatalities"`` is the column that makes
        sense. Off by default: a dot map of *where* is a different claim
        from a bubble map of *how many*, and the caller should have to say
        which one they are making.
    base_radius, max_radius : float, optional
        The smallest and largest disc, in plate units. The scale between
        them is set by the largest value in *this file*: conflict magnitudes
        span four orders and no absolute constant survives both a protest
        and a massacre.
    tooltip_from : str, optional
        A column to name each mark in its hover tooltip (``"location"``,
        ``"admin1"``). It is **not drawn on the plate**: a static figure
        with two hundred names on it is not a map, and the few places worth
        naming are worth naming by hand in ``labels.places``. Without it the
        tooltip falls back to the event's class.
    aggregate : str, optional
        Draw one mark per administrative unit instead of one per event:
        ``"admin1"``, ``"admin2"``, or any column name. Off by default.

        This is the answer to a question that is not cartographic. OCHA's
        data-responsibility guidance is blunt that a map plotting where
        vulnerable people are can be the thing that finds them, and that
        coordinates resist anonymisation. Aggregating is the usual remedy and
        is usually done dishonestly -- the pile is drawn as a confident dot at
        a centroid. Here it cannot be: an aggregate comes out at
        ``precision`` 3, *a place standing in for a whole region*, so it draws
        as a hollow broken ring, says so in its tooltip and in its accessible
        name, and the plate's method line says how many events became how many
        marks.
    derive_region : bool, optional
        Set ``region.bbox`` from the events themselves rather than taking
        it from the caller's config.
    region_pad : float, optional
        Degrees of margin around the derived region.
    limit : int, optional
        Keep at most this many events. The remainder is counted on the
        plate, never silently dropped.

    Returns
    -------
    dict
        ``events``, ``marker_legend``, ``method``, and ``region`` when
        ``derive_region``. Every key is one ``build_map`` already reads, so
        ``cfg.update(acled_events(...))`` is the whole integration.

    Raises
    ------
    ValueError
        On an unreadable coordinate, an unknown precision code, or a class
        outside the vocabulary. See :func:`_code` for why none of those is
        skipped quietly.

    Examples
    --------
    >>> rows = [{"event_date": "2024-07-01", "latitude": "12.0", "longitude": "30.0",
    ...          "event_type": "Protests", "geo_precision": "2", "time_precision": "3",
    ...          "fatalities": "0", "source": "Sudan Tribune"}]
    >>> frag = acled_events(rows)
    >>> frag["events"][0]["precision"], frag["events"][0]["time_precision"]
    (2, 3)
    >>> frag["method"]
    '1 ACLED event drawn; 2024-07-01.'
    """
    rows = _rows(source)
    vocab = list(vocabulary) if vocabulary is not None else (
        list(ACLED_EVENT_TYPES) if colour_by == "event_type" else []
    )

    def place(row: dict[str, Any], n: int) -> dict[str, Any] | str:
        mark: dict[str, Any] = {
            "lon": _number(row.get("longitude"), "longitude", n),
            "lat": _number(row.get("latitude"), "latitude", n),
            "precision": _code(row.get("geo_precision", 1), "geo_precision", n, (1, 2, 3)),
            "time_precision": _code(
                row.get("time_precision", 1), "time_precision", n, (1, 2, 3)
            ),
        }
        if row.get("event_date"):
            mark["date"] = str(row["event_date"])
        if row.get("source"):
            mark["source"] = str(row["source"])
        return mark

    def class_of(row: dict[str, Any], n: int) -> str:
        value = row.get(colour_by)
        if not value:
            raise ValueError(f"row {n}: no {colour_by!r} to colour by")
        return str(value)

    return _common(
        rows,
        vocabulary=vocab,
        class_of=class_of,
        place=place,
        dataset="ACLED",
        palette=palette,
        size_by=size_by,
        base_radius=base_radius,
        max_radius=max_radius,
        tooltip_from=tooltip_from,
        aggregate=aggregate,
        derive_region=derive_region,
        region_pad=region_pad,
        limit=limit,
    )


def ucdp_events(
    source: Any,
    *,
    vocabulary: Iterable[str] | None = None,
    palette: Iterable[str] = OKABE_ITO,
    size_by: str | None = None,
    base_radius: float = 3.0,
    max_radius: float = 11.0,
    tooltip_from: str | None = None,
    aggregate: str | None = None,
    country_level: str = "drop",
    derive_region: bool = False,
    region_pad: float = 0.6,
    limit: int | None = None,
) -> dict[str, Any]:
    """Return the plate config for a UCDP Georeferenced Event Dataset export.

    Parameters
    ----------
    source : path, str, or iterable of dict
        A GED ``.csv``, a GED API ``.json`` body, or rows in memory.
    vocabulary : iterable of str, optional
        Legend order. Defaults to UCDP's three types of violence.
    palette : iterable of str, optional
        Colours, one per class. :data:`OKABE_ITO` by default.
    size_by : str, optional
        ``"best"`` is UCDP's own best estimate of total fatalities, and the
        column this is for. Area-true, like ACLED's.
    base_radius, max_radius : float, optional
        The smallest and largest disc, as :func:`acled_events`.
    tooltip_from : str, optional
        A column to name each mark in its hover tooltip, e.g.
        ``"where_coordinates"``. Not drawn on the plate; see
        :func:`acled_events`.
    aggregate : str, optional
        One mark per administrative unit rather than per event; ``"admin1"``
        and ``"admin2"`` resolve to UCDP's ``adm_1`` and ``adm_2``. See
        :func:`acled_events` for why, and for what the resulting mark claims.
    country_level : {"drop", "keep"}, optional
        What to do with ``where_prec`` 6, where only the country is known
        and the coordinates are a representative point for the whole state.
        ``"drop"`` is the default and the honest answer; ``"keep"`` places
        them at precision 3 for a caller who has a reason and knows what
        they are asserting. Either way the count reaches the plate.
    derive_region, region_pad, limit
        As :func:`acled_events`.

    Returns
    -------
    dict
        ``events``, ``marker_legend``, ``method``, and ``region`` when
        ``derive_region``.

    Examples
    --------
    ``where_prec`` 2 is the one case where the dataset states a radius, and
    it survives as a drawn radius rather than being flattened to a code:

    >>> rows = [{"latitude": "9.0", "longitude": "31.0", "where_prec": "2",
    ...          "date_prec": "1", "date_start": "2023-04-15",
    ...          "type_of_violence": "1", "best": "12"}]
    >>> frag = ucdp_events(rows)
    >>> frag["events"][0]["precision"], frag["events"][0]["radius_km"]
    (2, 25)

    A country-level row is refused a position, and said so:

    >>> import warnings
    >>> rows = [{"latitude": "9.0", "longitude": "31.0", "where_prec": "6",
    ...          "date_prec": "1", "date_start": "2023-04-15",
    ...          "type_of_violence": "1"}]
    >>> with warnings.catch_warnings():
    ...     warnings.simplefilter("ignore")
    ...     frag = ucdp_events(rows)
    >>> frag["events"]
    []
    >>> frag["method"]
    '0 UCDP events drawn. Not drawn: 1 located only to the country.'
    """
    if country_level not in ("drop", "keep"):
        raise ValueError(f"country_level must be 'drop' or 'keep'; got {country_level!r}")
    rows = _rows(source)
    vocab = list(vocabulary) if vocabulary is not None else list(UCDP_VIOLENCE_TYPES.values())

    def place(row: dict[str, Any], n: int) -> dict[str, Any] | str:
        where = _code(row.get("where_prec", 1), "where_prec", n, tuple(UCDP_WHERE_PREC))
        precision = UCDP_WHERE_PREC[where]
        if precision is None:
            if country_level == "drop":
                return "located only to the country"
            precision = 3
        mark: dict[str, Any] = {
            "lon": _number(row.get("longitude"), "longitude", n),
            "lat": _number(row.get("latitude"), "latitude", n),
            "precision": precision,
            "time_precision": UCDP_DATE_PREC[
                _code(row.get("date_prec", 1), "date_prec", n, tuple(UCDP_DATE_PREC))
            ],
        }
        if where == 2:
            # The codebook states the radius; drawing it is strictly more
            # information than drawing the code that stands for it.
            mark["radius_km"] = 25
        date = str(row.get("date_start") or "")
        if date:
            # date_prec 5 means the year and no more. Printing "in 2023-04-15"
            # would dress a year up as a day; print the year.
            mark["date"] = date[:4] if mark["time_precision"] == 4 else date
        if row.get("source_article"):
            mark["source"] = str(row["source_article"])
        return mark

    def class_of(row: dict[str, Any], n: int) -> str:
        code = _code(
            row.get("type_of_violence", 1), "type_of_violence", n, tuple(UCDP_VIOLENCE_TYPES)
        )
        return UCDP_VIOLENCE_TYPES[code]

    return _common(
        rows,
        vocabulary=vocab,
        class_of=class_of,
        place=place,
        dataset="UCDP",
        palette=palette,
        size_by=size_by,
        base_radius=base_radius,
        max_radius=max_radius,
        tooltip_from=tooltip_from,
        aggregate=aggregate,
        derive_region=derive_region,
        region_pad=region_pad,
        limit=limit,
    )
