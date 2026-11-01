"""
Describe a dataset without carrying any of it.

What leaves this module is headers, shapes and counts — never a cell value.
That is a privacy property and also a cost one: the whole description of a
hundred-thousand-row file fits in a short prompt, so choosing a map does not
depend on how big the file is.

The column classifier below is coarse on purpose. It answers only the
distinctions that change *which map can be drawn*: is there something that
names a territory, is there something numeric to colour by, is there a pair of
coordinates. Everything else is ``text``, and a wrong guess there changes
nothing.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .schemas import ColumnProfile, DataProfile

_ISO3 = re.compile(r"^[A-Z]{3}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?")

#: Headers that name a coordinate, lowercased.
#:
#: ``x`` and ``y`` were in these sets until they were measured: two columns of
#: ordinary scores headed ``x`` and ``y``, with values in the tens, came back
#: as longitude and latitude — which is precisely the false positive this
#: module's prose claimed to prevent, and would have had the Studio offer a
#: density map of somebody's survey. The names that stayed are the ones that
#: mean a coordinate and nothing else. A real file headed ``x,y`` is now
#: classified ``number``, which is the harmless direction to be wrong in.
_LATITUDE_HEADERS = frozenset({"lat", "latitude", "lat_deg"})
_LONGITUDE_HEADERS = frozenset({"lon", "lng", "long", "longitude", "lon_deg"})


def _numeric(values: Sequence[str]) -> bool:
    for value in values:
        try:
            float(value)
        except ValueError:
            return False
    return bool(values)


def classify(header: str, values: Sequence[str]) -> str:
    """One of :data:`sprezzature_maps.studio.assistant.schemas.COLUMN_LOOKS`.

    A coordinate is called one only when the header names a coordinate *and*
    the numbers stay in range. Both halves are needed and neither is
    sufficient: a column of numbers between -90 and 90 is usually a
    measurement, and a header can lie. The header vocabulary is kept narrow for
    the same reason — see :data:`_LATITUDE_HEADERS`, where ``x`` and ``y`` were
    removed after being measured wrong on exactly this case.

    Parameters
    ----------
    header : str
        The column name.
    values : sequence of str
        Its non-empty values, as text.

    Returns
    -------
    str

    Examples
    --------
    >>> classify("iso3", ["FRA", "DEU"])
    'country_code'
    >>> classify("lat", ["48.85", "52.52"])
    'latitude'
    >>> classify("lat", ["1", "2", "3"])
    'latitude'
    >>> classify("score", ["48.85", "52.52"])
    'number'
    >>> classify("x", ["12", "15"])   # a header too weak to trust
    'number'
    >>> classify("Tool", ["svgis", "D3 + d3-geo"])
    'text'
    """
    name = header.strip().lower()
    if _numeric(values):
        numbers = [float(v) for v in values]
        if name in _LATITUDE_HEADERS and all(-90.0 <= n <= 90.0 for n in numbers):
            return "latitude"
        if name in _LONGITUDE_HEADERS and all(-180.0 <= n <= 180.0 for n in numbers):
            return "longitude"
        return "number"
    if values and all(_ISO3.match(v) for v in values):
        return "country_code"
    if values and all(_ISO_DATE.match(v) for v in values):
        return "date"
    distinct = len(set(values))
    if values and distinct > 1 and all(v.replace(" ", "").replace("-", "").isalpha() for v in values):
        return "country_name" if distinct <= 300 else "text"
    return "text"


def profile_rows(rows: Sequence[dict[str, Any]], *, source: str = "") -> DataProfile:
    """Profile tabular rows, as :func:`sprezzature_maps.data.read_choropleth_rows` returns them.

    Parameters
    ----------
    rows : sequence of dict
        The rows. Column order follows the first row's keys.
    source : str
        A bare file name, for the model's benefit. A path is reduced to its
        name: the directories carry a user name and help nothing.

    Returns
    -------
    DataProfile
    """
    columns: list[ColumnProfile] = []
    headers: list[str] = []
    for row in rows:
        for header in row:
            if header not in headers:
                headers.append(header)
    for header in headers:
        raw = [row.get(header) for row in rows]
        present = [str(v) for v in raw if v is not None and str(v).strip() != ""]
        columns.append(
            ColumnProfile(
                name=header,
                looks_like=classify(header, present),
                distinct=len(set(present)),
                nulls=len(raw) - len(present),
            )
        )
    return DataProfile(rows=len(rows), columns=columns, source=Path(source).name if source else "")


def profile_points(points: Sequence[Sequence[float]], *, source: str = "") -> DataProfile:
    """Profile a bare list of positions, as :func:`sprezzature_maps.data.read_density_points` returns them.

    Parameters
    ----------
    points : sequence of sequence of float
        ``[[lon, lat], ...]`` or ``[[lon, lat, weight], ...]``.
    source : str
        A bare file name.

    Returns
    -------
    DataProfile
    """
    width = max((len(p) for p in points), default=0)
    names = ["longitude", "latitude", "weight"][:width] or []
    columns = [
        ColumnProfile(
            name=name,
            looks_like={"longitude": "longitude", "latitude": "latitude"}.get(name, "number"),
            distinct=len({p[i] for p in points if len(p) > i}),
            nulls=sum(1 for p in points if len(p) <= i),
        )
        for i, name in enumerate(names)
    ]
    return DataProfile(
        rows=len(points), columns=columns, source=Path(source).name if source else ""
    )
