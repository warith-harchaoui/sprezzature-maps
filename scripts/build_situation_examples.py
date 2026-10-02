#!/usr/bin/env python3
"""One builder for every shipped situation-map example, so there is a single source of truth.

Author: Warith HARCHAOUI

Generates every example configuration for ``make_situation_map.py`` the
same consistent way, so the shipped example gallery looks uniform and can
be regenerated in one command:

- ``ukraine``: a schematic split of the country's real outline into
  government-held, occupied, and contested territory, drawn along an
  approximate front line (the boundary between opposing forces) as
  reported in open-source geopolitical literature (for instance ISW, the
  Institute for the Study of War, a think tank that publishes daily
  conflict maps). An illustrative snapshot from partway through the war,
  not a claim of exact, current accuracy.
- ``syria``: a schematic four-way split (government, opposition, the
  Kurdish-led SDF, Syrian Democratic Forces, and Turkish-backed forces)
  based on open-source literature, an illustrative snapshot from around
  2018.
- ``libya``: a schematic split between loyalist, rebel, and contested
  territory during the First Libyan Civil War (the 2011 uprising against
  Muammar Gaddafi's government), based on open-source literature, an
  illustrative snapshot from around spring 2011.
- ``sudan``: the war's east-west partition in five classes -- the army, the
  RSF, SPLM-N in the Nuba mountains and southern Blue Nile, the Jebel Marra
  holdout, and the contested Kordofan front -- with an assessed and a
  reported axis of advance drawn differently. Open-source reporting to late
  September 2026.
- ``drc``: who holds North and South Kivu, on the Albertine Rift. The plate
  that could not be drawn honestly until the generator had lake polygons:
  Goma and Bukavu face each other across Lake Kivu, and on a land-versus-
  ocean basemap the water between them was painted as ground.

Every one of these non-neutral maps is deliberately coarse, and says so
directly on the map itself. The schematic control lines and territory
polygons are not hidden inside some opaque data file: they live here, in
the open, in this script's own source, sourced in the code comments right
next to each one (Wikipedia, ISW, DeepStateMap, a crowd-sourced tracker
of the war in Ukraine). An expert reader can see exactly how each map was
drawn, line by line, and correct or refine any part of it, rather than
having to trust a black box. Running this script writes the tracked
``assets/situation-maps/<name>.{yaml,svg,png}`` files plus the gallery's
raster (pixel-grid) image.

    python scripts/build_situation_examples.py             # every example
    python scripts/build_situation_examples.py sudan drc   # just these
    python scripts/build_situation_examples.py --layers    # + the layer views

``--layers`` also writes the a-posteriori per-layer decomposition of each
plate (basemap / areas-of-control / markers / labels, as SVG and PNG). It is
off by default because it is about 12 MB of derived files per example and
most runs only want the plates.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from make_situation_map import (  # noqa: E402
    build_map,
    load_country,
    load_lakes,
    load_land,
    validate_config,
)
from shapely.geometry import (  # noqa: E402
    LineString,
    Polygon,
    box,
    mapping,
)
from shapely.ops import unary_union  # noqa: E402

# These examples used to be generated *into* sprezzature-figures, back when the
# situation map lived there. Both paths still pointed at a sibling checkout
# after the split, so this script could only run on a machine that happened to
# have one -- and then wrote this repo's own examples into the other repo.
SHIP = REPO / "assets" / "situation-maps"


def _feat(name: str, geom: Any) -> dict[str, Any]:
    return {"type": "Feature", "properties": {"actor": name}, "geometry": mapping(geom)}


def _partition_by_claims(
    country: Any, base_name: str, claims: list[tuple[str, list]]
) -> list[dict[str, Any]]:
    """Greedily assign land to the first actor that claims it; remainder -> base.

    Parameters
    ----------
    country : shapely geometry
        The national outline to divide.
    base_name : str
        Actor that holds everything unclaimed (e.g. the government).
    claims : list of (name, polygon-coords)
        Ordered actor claims; earlier claims win overlaps.

    Returns
    -------
    list of GeoJSON features, base actor first.
    """
    assigned = None
    features: list[dict[str, Any]] = []
    zones: list[tuple[str, Any]] = []
    for name, coords in claims:
        poly = Polygon(coords)
        piece = country.intersection(poly)
        if assigned is not None:
            piece = piece.difference(assigned)
        if not piece.is_empty:
            zones.append((name, piece))
            assigned = piece if assigned is None else unary_union([assigned, piece])
    base = country if assigned is None else country.difference(assigned)
    features.append(_feat(base_name, base))
    features.extend(_feat(n, g) for n, g in zones)
    return features


def _smooth(geom: Any, km: float = 18.0) -> Any:
    """Round a hand-typed claim polygon so it reads as ground, not as typing.

    A control zone entered as six coordinates comes out with six straight
    edges and six sharp corners, and a straight edge on a control map is a
    claim: it says someone surveyed that line. Opening then closing the shape
    by the same radius rounds convex and concave corners alike and leaves the
    area essentially unchanged, which is what a coarse assessment should look
    like.
    """
    deg = km / 111.0
    return geom.buffer(deg).buffer(-2 * deg).buffer(deg)


def _contested_band(line_pts: list, country: Any, km: float) -> Any:
    """Return a buffered band along a contact line, clipped to the country."""
    deg = km / 111.0  # crude deg-per-km; fine for a schematic hatch band
    band = LineString(line_pts).buffer(deg)
    return country.intersection(band)


# --------------------------------------------------------------------------- #
# Sardinia: neutral synthetic                                                 #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Ukraine: schematic, per open-source literature                              #
# --------------------------------------------------------------------------- #

# Approximate 2024 contact line north->south, hugging the reported flashpoints
# (Kupiansk, Bakhmut, Avdiivka, Vuhledar, Robotyne) down to the Dnipro / Kherson.
FRONT = [
    (37.55, 49.75),
    (38.00, 49.00),
    (38.05, 48.60),
    (37.75, 48.15),
    (37.20, 47.90),
    (36.40, 47.60),
    (35.85, 47.44),
    (34.70, 47.05),
    (33.00, 46.72),
    (32.55, 46.50),
]
ENVELOPE = FRONT + [(32.55, 43.8), (41.5, 43.8), (41.5, 50.6), (37.55, 49.75)]
CRIMEA_BBOX = [32.4, 44.28, 36.75, 46.25]
# Shallow NE Kharkiv-oblast salient reached in the May 2024 cross-border push.
VOVCHANSK_BBOX = [36.8, 50.15, 37.7, 50.62]


def build_ukraine() -> dict[str, Any]:
    ukr = load_country("Ukraine")
    occupied = unary_union(
        [
            ukr.intersection(Polygon(ENVELOPE)),
            load_land().intersection(box(*CRIMEA_BBOX)),  # Crimea (occupied 2014)
            ukr.intersection(box(*VOVCHANSK_BBOX)),  # Vovchansk salient (2024)
        ]
    )
    government = ukr.difference(occupied)
    contested = _contested_band(FRONT, ukr, km=22)
    government = government.difference(contested)
    occupied = occupied.difference(contested)
    # Slightly deeper, more saturated pastels so the three classes separate
    # cleanly at fill_opacity ~0.78 (Ukrainian cool blue / occupied warm red /
    # contested ochre) while staying inside the paper-and-ink house palette.
    palette = {
        "Ukrainian government control": "#bcd4ec",
        "Russian-occupied (approx.)": "#e0a89e",
        "Contested (approx. front line)": "#e4cf9c",
    }
    features = [
        _feat("Ukrainian government control", government),
        _feat("Russian-occupied (approx.)", occupied),
        _feat("Contested (approx. front line)", contested),
    ]
    b = ukr.bounds
    bbox = [b[0] - 0.6, b[1] - 1.2, b[2] + 0.6, b[3] + 0.6]
    return {
        "title": "Ukraine: Areas of Control",
        "subtitle": (
            "Schematic, approximate open-source positions circa 2024 · "
            "roughly 18% of the country occupied · illustrative, not operational intelligence"
        ),
        "region": {"bbox": bbox},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "sea_color": "#a8bccb",
            "land_color": "#f6f1df",
            "coast_color": "#7993a6",
            "bathymetry": {"rings": 7, "color": "#ffffff", "opacity": 0.4},
        },
        "frontiers": {"focus": "Ukraine"},
        "legend_position": "right",
        "rivers": {"always_label": ["Dnieper"], "color": "#5d86a6", "label_color": "#3f6a8c"},
        # Natural Earth still carries the Kakhovka Reservoir at its full
        # ~2 150 km2 extent. It drained within two weeks of the dam breach of
        # 6 June 2023, and by 2026 the bed is willow and poplar scrub over sand
        # and marsh -- ground infantry has been infiltrating through, which
        # makes it a feature of this plate rather than a footnote to it.
        # Drawn as former (dashed outline, no fill) rather than skipped: on a
        # map of this front the absence of the reservoir is itself information,
        # and a reader who knows the geography will come looking for it.
        "lakes": {
            "former": ["Kakhovka Reservoir"],
            "always_label": ["Kakhovka Reservoir"],
        },
        # The approximate contact line, drawn as an emphasised front (north->south).
        "front": {
            "line": [[p[0], p[1]] for p in FRONT],
            "color": "#3a4149",
            "legend_label": "Approx. contact line",
        },
        "legend_footer": "As of ~2024 · schematic, open-source geography",
        "caption": "full",
        "method": "Schematic polygons drawn by hand from open-source reporting, not a geocoded dataset",
        "source": (
            "Natural Earth basemap; the Kakhovka Reservoir is drawn as former "
            "(drained after the dam breach of 6 June 2023)"
        ),
        "as_of": "Positions as of ~2024 · illustrative, not operational intelligence",
        "areas_of_control": {
            "category_field": "actor",
            "palette": palette,
            "contested": ["Contested (approx. front line)"],
            "fill_opacity": 0.78,
            "hatch_color": "#b34a3a",
            "source": {"type": "FeatureCollection", "features": features},
        },
        # Reported 2023-24 flashpoints (lon, lat). Each is a town name standing
        # in for a sector of front around it, which is ACLED's geo-precision 2
        # exactly: a named place chosen to represent a general area. The mark
        # says so itself -- a hollow ring, not a dot -- so the "(approx.)" that
        # used to sit in the legend's wording is now carried by the ink.
        "events": [
            {"lon": 38.0008, "lat": 48.5947, "color": "#c0392b", "r": 5, "precision": 2},  # Bakhmut
            {"lon": 37.7450, "lat": 48.1453, "color": "#c0392b", "r": 5, "precision": 2},  # Avdiivka
            {"lon": 37.1828, "lat": 48.2828, "color": "#c0392b", "r": 5, "precision": 2},  # Pokrovsk
            {"lon": 37.2483, "lat": 47.7792, "color": "#c0392b", "r": 5, "precision": 2},  # Vuhledar
            {"lon": 35.8261, "lat": 47.4431, "color": "#c0392b", "r": 5, "precision": 2},  # Robotyne
            {"lon": 36.9428, "lat": 50.2878, "color": "#c0392b", "r": 5, "precision": 2},
        ],  # Vovchansk
        "marker_legend": [
            {"color": "#c0392b", "label": "Contested flashpoint", "precision": 2}
        ],
        "labels": {
            "waters": [
                {"lon": 31.3, "lat": 43.15, "text": "Black Sea", "size": 19, "tracking": 7},
                {"lon": 37.0, "lat": 46.35, "text": "Sea of Azov", "size": 11, "tracking": 2.4},
            ],
            "places": [
                {"lon": 30.5233, "lat": 50.4500, "text": "Kyiv", "size": 16, "capital": True},
                {"lon": 36.2311, "lat": 49.9925, "text": "Kharkiv"},
                {"lon": 30.7434, "lat": 46.4857, "text": "Odesa", "anchor": "below"},
                {"lon": 35.0400, "lat": 48.4675, "text": "Dnipro"},
                {
                    "lon": 37.98,
                    "lat": 47.88,
                    "text": "Donetsk",
                    "anchor": "end",
                },  # clear of Avdiivka marker
                {"lon": 39.3031, "lat": 48.5678, "text": "Luhansk"},
                {"lon": 37.5494, "lat": 47.0958, "text": "Mariupol", "anchor": "above"},
                {"lon": 32.6250, "lat": 46.6425, "text": "Kherson", "anchor": "above"},
                {"lon": 35.1175, "lat": 47.8500, "text": "Zaporizhzhia", "anchor": "end"},
                {"lon": 33.5225, "lat": 44.6050, "text": "Sevastopol", "anchor": "above"},
                {"lon": 24.0322, "lat": 49.8425, "text": "Lviv"},
                {"lon": 31.9950, "lat": 46.9750, "text": "Mykolaiv", "size": 11, "anchor": "end"},
                {"lon": 28.4833, "lat": 49.2333, "text": "Vinnytsia", "size": 11},
                {"lon": 34.5514, "lat": 49.5894, "text": "Poltava", "size": 11},
                {"lon": 34.8028, "lat": 50.9119, "text": "Sumy", "size": 11},
                {"lon": 31.2947, "lat": 51.4939, "text": "Chernihiv", "size": 11},
                {"lon": 37.30, "lat": 48.98, "text": "Kramatorsk", "size": 11, "anchor": "above"},
                {"lon": 34.90, "lat": 46.70, "text": "Melitopol", "size": 11, "anchor": "above"},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Syria: schematic four-actor, per open-source literature (~2018)             #
# --------------------------------------------------------------------------- #


def build_syria() -> dict[str, Any]:
    syr = load_country("Syria")
    # Ordered claims (earlier wins overlaps), per open-source reporting ~2018:
    #  - Turkish-backed: the northern border strip (Afrin + Euphrates Shield),
    #    west of the Euphrates, above Aleppo (which stayed government).
    #  - SDF / AANES: north-east of the Euphrates. Its south-west edge follows the
    #    river so Deir ez-Zor city and al-Bukamal (west/south bank) stay government.
    #  - Opposition / HTS: the Idlib pocket in the north-west.
    claims = [
        ("Turkish-backed", [(36.35, 37.45), (38.15, 37.45), (38.15, 36.35), (36.35, 36.35)]),
        (
            "SDF / AANES (approx.)",
            [
                (38.15, 37.45),
                (42.5, 37.45),
                (42.5, 34.35),
                (41.15, 34.75),
                (40.5, 35.1),
                (40.0, 35.5),
                (39.1, 35.75),
                (38.15, 36.5),
            ],
        ),
        ("Opposition (Idlib)", [(35.6, 36.4), (37.0, 36.4), (37.2, 35.5), (35.9, 35.45)]),
    ]
    features = _partition_by_claims(syr, "Syrian government", claims)
    palette = {
        "Syrian government": "#e3b0aa",
        "Turkish-backed": "#bcd0e6",
        "SDF / AANES (approx.)": "#f2d99a",
        "Opposition (Idlib)": "#cdddb0",
    }
    # Order palette to match legend priority government-first.
    b = syr.bounds
    bbox = [b[0] - 0.6, b[1] - 0.6, b[2] + 0.6, b[3] + 0.6]
    return {
        "title": "Syria: Areas of Control",
        "subtitle": (
            "Schematic / approximate, per open-source geopolitical literature · "
            "illustrative ~2018 snapshot, not an operational assessment"
        ),
        "region": {"bbox": bbox},
        "projection": "auto",
        "canvas_width": 1180,
        "basemap": {
            "sea_color": "#9fb2c0",
            "land_color": "#f4efdd",
            "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.45},
        },
        "frontiers": {"focus": "Syria"},
        "rivers": {"always_label": ["Euphrates", "Tigris"]},
        "areas_of_control": {
            "category_field": "actor",
            "palette": palette,
            "source": {"type": "FeatureCollection", "features": features},
        },
        "events": [
            {"lon": 37.13, "lat": 36.20, "color": "#c0392b", "r": 5},  # Aleppo
            {"lon": 40.14, "lat": 35.34, "color": "#c0392b", "r": 5},  # Deir ez-Zor
            {"lon": 38.99, "lat": 35.95, "color": "#c0392b", "r": 5},
        ],  # Raqqa
        "marker_legend": [{"color": "#c0392b", "label": "Contested city (approx.)"}],
        "labels": {
            "water": {
                "lon": 35.55,
                "lat": 35.95,
                "text": "Mediterranean Sea",
                "size": 12,
                "tracking": 2,
            },
            "places": [
                {"lon": 36.292, "lat": 33.513, "text": "Damascus", "size": 15},
                # Flashpoint cities: the red event dot is the marker (dot:false),
                # name offset with `clear` sized to that dot.
                {
                    "lon": 37.134,
                    "lat": 36.202,
                    "text": "Aleppo",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "above",
                },
                {"lon": 36.723, "lat": 34.733, "text": "Homs"},
                {"lon": 36.750, "lat": 35.132, "text": "Hama"},
                {"lon": 35.791, "lat": 35.531, "text": "Latakia"},
                {"lon": 35.886, "lat": 34.889, "text": "Tartus", "size": 11},
                {"lon": 36.634, "lat": 35.931, "text": "Idlib", "anchor": "end"},
                {
                    "lon": 39.017,
                    "lat": 35.950,
                    "text": "Raqqa",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "below",
                },
                {
                    "lon": 40.140,
                    "lat": 35.336,
                    "text": "Deir ez-Zor",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "below",
                },
                {"lon": 40.750, "lat": 36.500, "text": "Al-Hasakah", "size": 11},
                {"lon": 41.231, "lat": 37.053, "text": "Qamishli", "size": 11, "anchor": "end"},
                {"lon": 38.354, "lat": 36.891, "text": "Kobani", "size": 11, "anchor": "above"},
                {"lon": 36.869, "lat": 36.512, "text": "Afrin", "size": 11, "anchor": "end"},
                {"lon": 37.516, "lat": 36.371, "text": "Al-Bab", "size": 11},
                {"lon": 36.106, "lat": 32.618, "text": "Deraa", "size": 11},
                {"lon": 38.284, "lat": 34.560, "text": "Palmyra", "size": 11},
                {"lon": 40.919, "lat": 34.453, "text": "Al-Bukamal", "size": 11, "anchor": "end"},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Libya: schematic First Libyan Civil War, ~spring 2011                        #
# --------------------------------------------------------------------------- #

# Oil-crescent front, Ajdabiya -> Brega -> Ras Lanuf -> Bin Jawad -> toward Sirte.
LIBYA_FRONT = [(20.20, 30.72), (19.58, 30.41), (18.54, 30.50), (17.70, 30.90), (16.90, 31.05)]


def build_libya() -> dict[str, Any]:
    lby = load_country("Libya")
    # East/west divide ran around the Gulf of Sidra / Brega (~19 E): rebels (NTC)
    # held Cyrenaica in the east; Gaddafi held Tripolitania (west) + Fezzan (south).
    rebel_east = lby.intersection(Polygon([(18.9, 33.6), (25.8, 33.6), (25.8, 18.8), (18.9, 18.8)]))
    # Besieged rebel enclaves inside the loyalist west.
    misrata = load_land().intersection(box(14.85, 32.20, 15.40, 32.58))
    nafusa = lby.intersection(box(10.30, 31.45, 12.85, 32.20))  # Berber mountains
    rebel = unary_union([rebel_east, misrata, nafusa])
    gaddafi = lby.difference(rebel)
    contested = _contested_band(LIBYA_FRONT, lby, km=28)
    gaddafi = gaddafi.difference(contested)
    rebel = rebel.difference(contested)
    palette = {
        "Gaddafi loyalists": "#c9d8a6",
        "Rebels / NTC": "#e3b0aa",
        "Contested (oil crescent)": "#e6d5b8",
    }
    features = [
        _feat("Gaddafi loyalists", gaddafi),
        _feat("Rebels / NTC", rebel),
        _feat("Contested (oil crescent)", contested),
    ]
    b = lby.bounds
    bbox = [b[0] - 0.6, b[1] - 0.6, b[2] + 0.6, b[3] + 1.0]
    return {
        "title": "Libya: Areas of Control",
        "subtitle": (
            "Schematic · approximate, First Libyan Civil War ~spring 2011 "
            "(after UNSCR 1973) · open-source reporting, not operational intelligence"
        ),
        "region": {"bbox": bbox},
        "projection": "auto",
        "canvas_width": 1180,
        "basemap": {
            "sea_color": "#9fb2c0",
            "land_color": "#f4efdd",
            "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.45},
        },
        "frontiers": {"focus": "Libya"},
        "areas_of_control": {
            "category_field": "actor",
            "palette": palette,
            "contested": ["Contested (oil crescent)"],
            "source": {"type": "FeatureCollection", "features": features},
        },
        "events": [
            {"lon": 19.576, "lat": 30.408, "color": "#c0392b", "r": 5},  # Brega
            {"lon": 18.542, "lat": 30.500, "color": "#c0392b", "r": 5},  # Ras Lanuf
            {"lon": 15.092, "lat": 32.378, "color": "#c0392b", "r": 5},
        ],  # Misrata siege
        "marker_legend": [{"color": "#c0392b", "label": "Contested / besieged (approx.)"}],
        "labels": {
            "water": {
                "lon": 18.4,
                "lat": 33.5,
                "text": "Mediterranean Sea",
                "size": 15,
                "tracking": 4,
            },
            "places": [
                {"lon": 13.191, "lat": 32.887, "text": "Tripoli", "size": 15, "anchor": "above"},
                {"lon": 20.068, "lat": 32.119, "text": "Benghazi", "size": 14},
                {
                    "lon": 15.092,
                    "lat": 32.378,
                    "text": "Misrata",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "above",
                },
                {"lon": 16.588, "lat": 31.205, "text": "Sirte"},
                {"lon": 14.429, "lat": 27.038, "text": "Sabha"},
                {"lon": 23.964, "lat": 32.084, "text": "Tobruk", "anchor": "end"},
                {"lon": 20.227, "lat": 30.755, "text": "Ajdabiya", "size": 11},
                {"lon": 21.755, "lat": 32.763, "text": "Al Bayda", "size": 11, "anchor": "end"},
                {"lon": 22.640, "lat": 32.767, "text": "Derna", "size": 11, "anchor": "above"},
                {
                    "lon": 19.576,
                    "lat": 30.408,
                    "text": "Brega",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "below",
                    "size": 11,
                },
                {
                    "lon": 18.542,
                    "lat": 30.500,
                    "text": "Ras Lanuf",
                    "dot": False,
                    "clear": 5.5,
                    "anchor": "end",
                    "size": 11,
                },
                {"lon": 12.728, "lat": 32.752, "text": "Zawiya", "size": 11, "anchor": "end"},
                {"lon": 12.253, "lat": 31.930, "text": "Zintan", "size": 11, "anchor": "end"},
                {"lon": 10.980, "lat": 31.869, "text": "Nalut", "size": 11, "anchor": "end"},
                {"lon": 23.313, "lat": 24.179, "text": "Al Kufra", "size": 11, "anchor": "end"},
                {"lon": 10.180, "lat": 24.964, "text": "Ghat", "size": 11},
            ],
        },
    }



# --------------------------------------------------------------------------- #
# Sudan: schematic, per open-source reporting                                  #
# --------------------------------------------------------------------------- #

# The east-west divide the war settled into: SAF holds the Nile corridor, the
# centre and the east; the RSF holds Darfur and the west; the fighting is in
# Kordofan, in between. Drawn north -> south roughly along the Kordofan front,
# and reused as both the RSF claim's eastern edge and the drawn contact line so
# the hatched band straddles exactly the boundary the fills meet at.
SUDAN_FRONT = [
    (27.70, 16.30),
    (28.15, 14.20),
    (28.80, 12.60),
    (28.85, 11.50),
    (28.50, 10.20),
    (28.10, 9.65),
]
# The claim polygon runs past both ends of the drawn line, so the difference
# covers the whole country; the line itself stops at the border, because a
# contact line drawn across South Sudan claims a front that is not there.
SUDAN_RSF_CLAIM = (
    [(21.0, 23.0), (27.70, 23.0)] + SUDAN_FRONT + [(27.95, 8.0), (21.0, 8.0)]
)
# Jebel Marra + Tawila: the Sudan Liberation Movement (Abdel Wahid al-Nur) has
# held the massif throughout, a third zone belonging to neither belligerent.
# The west edge stops short of Zalingei, which is RSF-held.
SUDAN_JEBEL_MARRA = [
    (23.70, 12.30),
    (24.30, 11.95),
    (25.10, 12.60),
    (25.25, 13.45),
    (24.60, 13.95),
    (24.00, 13.60),
    (23.70, 13.00),
]
# Dar Zaghawa, the far north-west: Zaghawa-aligned former Darfur rebels kept a
# foothold around Tina and Kornoi after the rest of Darfur fell.
# A ragged foothold, not a survey rectangle: a box drawn on a control map
# reads as a claim of straight borders, which is never what is meant.
SUDAN_DAR_ZAGHAWA = [
    (21.85, 15.05),
    (22.70, 14.85),
    (23.25, 15.20),
    (23.10, 15.95),
    (22.40, 16.30),
    (21.85, 16.05),
]
# SPLM-N (al-Hilu) holds the Nuba Mountains east of Kadugli and south-east of
# Dilling -- both towns stay SAF -- and the southern Blue Nile.
SUDAN_NUBA = [(29.95, 10.35), (31.30, 10.35), (31.50, 11.60), (30.20, 12.10), (29.85, 11.50)]
SUDAN_BLUE_NILE = [(33.60, 9.50), (35.00, 9.50), (35.10, 11.00), (34.20, 11.30), (33.70, 10.60)]


def build_sudan() -> dict[str, Any]:
    """Sudan's east-west partition: SAF, RSF, SPLM-N and the Jebel Marra holdout.

    The most complex plate in this gallery -- five classes rather than three --
    because the war genuinely has five answers to "who holds this", and
    collapsing the two non-belligerent zones into "other" would misdescribe
    both. Schematic, from open-source reporting to late September 2026; the
    claim lines above are coarse by construction and the map says so.
    """
    sdn = load_country("Sudan")
    jebel_marra = sdn.intersection(_smooth(Polygon(SUDAN_JEBEL_MARRA), km=14))
    zaghawa = sdn.intersection(_smooth(Polygon(SUDAN_DAR_ZAGHAWA), km=14))
    splm_n = sdn.intersection(
        _smooth(unary_union([Polygon(SUDAN_NUBA), Polygon(SUDAN_BLUE_NILE)]), km=16)
    )
    # Earlier claims win: the two holdout zones are carved out of Darfur before
    # the RSF takes the rest of it.
    carved = unary_union([jebel_marra, zaghawa])
    rsf = sdn.intersection(Polygon(SUDAN_RSF_CLAIM)).difference(carved)
    saf = sdn.difference(unary_union([rsf, carved, splm_n]))
    # The Kordofan fighting, as a band straddling the divide rather than a line
    # through it: that is what "the front is in Kordofan" actually looks like.
    contested = _contested_band(SUDAN_FRONT, sdn, km=55)
    saf = saf.difference(contested)
    rsf = rsf.difference(contested)
    splm_n = splm_n.difference(contested)
    contested = unary_union([contested, zaghawa])

    palette = {
        "Sudanese Armed Forces": "#bcd4ec",
        "Rapid Support Forces": "#e0a89e",
        "SPLM-N (al-Hilu)": "#cdddb0",
        "SLM-AW (Jebel Marra)": "#cfc0d8",
        "Contested (approx.)": "#e4cf9c",
    }
    features = [
        _feat("Sudanese Armed Forces", saf),
        _feat("Rapid Support Forces", rsf),
        _feat("SPLM-N (al-Hilu)", splm_n),
        _feat("SLM-AW (Jebel Marra)", jebel_marra),
        _feat("Contested (approx.)", contested),
    ]
    b = sdn.bounds
    bbox = [b[0] - 0.8, b[1] - 0.8, b[2] + 0.8, b[3] + 0.8]
    return {
        "title": "Sudan: Areas of Control",
        "subtitle": (
            "Schematic · the war's east-west partition, with the fighting in Kordofan"
        ),
        "method": "Schematic polygons drawn by hand from the sources below, not a geocoded dataset",
        "source": "Open-source reporting (ACLED, Sudans Post territorial-control tracking)",
        "as_of": "As of ~25 September 2026 · illustrative, not an operational assessment",
        "caption": "full",
        "region": {"bbox": bbox},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "sea_color": "#a8bccb",
            "land_color": "#f4efdd",
            "coast_color": "#7993a6",
            "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.4},
        },
        "frontiers": {"focus": "Sudan"},
        "legend_position": "right",
        "legend_footer": "Five classes · boundaries approximate",
        "rivers": {"always_label": ["Nile", "White Nile", "Blue Nile"]},
        "front": {
            "line": [list(p) for p in SUDAN_FRONT],
            "color": "#3a4149",
            "legend_label": "Approx. Kordofan front",
        },
        # Two movements, drawn differently because they are two different
        # claims. The SAF push through North Kordofan is assessed (Sodari
        # taken 25 September) and drawn solid; the SPLM-N advance in Blue Nile
        # is a single reported garrison capture, and is drawn as an outline.
        "arrows": [
            {
                "line": [[30.45, 13.05], [30.05, 13.65], [29.55, 14.05], [29.05, 14.45]],
                "color": "#2f5d92",
                "width": 6.5,
                "label": "SAF advance",
                "label_side": "right",
                "legend_label": "Assessed advance",
            },
            {
                "line": [[34.02, 10.00], [34.18, 10.45], [34.12, 10.95]],
                "color": "#3f5a2e",
                "width": 6.5,
                "style": "dashed",
                "label": "SPLM-N (reported)",
                "label_side": "right",
                "legend_label": "Reported advance",
            },
        ],
        "areas_of_control": {
            "category_field": "actor",
            "palette": palette,
            "contested": ["Contested (approx.)"],
            "fill_opacity": 0.78,
            "hatch_color": "#b34a3a",
            "source": {"type": "FeatureCollection", "features": features},
        },
        "events": [
            {"lon": 25.350, "lat": 13.631, "color": "#c0392b", "r": 5},  # El Fasher
            {"lon": 30.217, "lat": 13.183, "color": "#c0392b", "r": 5},  # El Obeid
            {"lon": 29.717, "lat": 11.017, "color": "#c0392b", "r": 5},  # Kadugli
            {"lon": 34.350, "lat": 11.767, "color": "#c0392b", "r": 5},  # Ad-Damazin
        ],
        "marker_legend": [{"color": "#c0392b", "label": "Contested town (approx.)"}],
        "labels": {
            "places": [
                {"lon": 32.532, "lat": 15.590, "text": "Khartoum", "size": 15},
                {"lon": 37.216, "lat": 19.616, "text": "Port Sudan", "anchor": "end"},
                {"lon": 24.883, "lat": 12.050, "text": "Nyala"},
                {
                    "lon": 25.350, "lat": 13.631, "text": "El Fasher",
                    "dot": False, "clear": 5.5, "anchor": "above",
                },
                {
                    "lon": 30.217, "lat": 13.183, "text": "El Obeid",
                    "dot": False, "clear": 5.5, "anchor": "above",
                },
                {
                    "lon": 29.717, "lat": 11.017, "text": "Kadugli",
                    "dot": False, "clear": 5.5, "anchor": "below",
                },
                {
                    "lon": 34.350, "lat": 11.767, "text": "Ad-Damazin",
                    "dot": False, "clear": 5.5, "anchor": "below",
                },
                {"lon": 22.435, "lat": 13.434, "text": "El Geneina", "size": 11, "anchor": "end"},
                {"lon": 23.477, "lat": 12.900, "text": "Zalingei", "size": 11, "anchor": "end"},
                {"lon": 24.861, "lat": 13.514, "text": "Tawila", "size": 11, "anchor": "end"},
                {"lon": 30.483, "lat": 19.167, "text": "Dongola", "size": 11},
                {"lon": 31.817, "lat": 18.483, "text": "Merowe", "size": 11},
                {"lon": 33.978, "lat": 17.697, "text": "Atbara", "size": 11},
                {"lon": 36.390, "lat": 15.450, "text": "Kassala", "size": 11},
                {"lon": 35.383, "lat": 14.033, "text": "Gedaref", "size": 11},
                {"lon": 33.517, "lat": 14.400, "text": "Wad Madani", "size": 11},
                {"lon": 33.583, "lat": 13.550, "text": "Sennar", "size": 11},
                {"lon": 28.343, "lat": 11.717, "text": "Al-Fulah", "size": 11, "anchor": "end"},
                {"lon": 28.423, "lat": 12.693, "text": "En Nahud", "size": 11, "anchor": "end"},
                {"lon": 29.656, "lat": 12.053, "text": "Dilling", "size": 11, "anchor": "end"},
                {"lon": 31.208, "lat": 12.904, "text": "Umm Ruwaba", "size": 11},
                {"lon": 26.688, "lat": 13.596, "text": "Umm Keddada", "size": 11},
            ],
        },
    }



# --------------------------------------------------------------------------- #
# Eastern DRC: schematic, per open-source reporting                            #
# --------------------------------------------------------------------------- #

# M23/AFC holds a band along the Rwandan and Burundian border taking in both
# provincial capitals -- Goma since January 2025, Bukavu weeks after it --
# and has been widening it westward through Masisi.
DRC_M23_CLAIM = [
    (29.78, -0.72),
    (29.10, -0.82),
    (28.52, -1.18),
    (28.02, -1.58),
    (27.92, -2.12),
    (28.18, -2.58),
    (28.52, -2.98),
    (29.02, -3.18),
    (29.42, -2.88),
    (29.82, -2.32),
    (29.88, -1.38),
]
# Two places the fighting is, rather than two places anyone holds: the
# south-western Masisi approaches toward Walikale, and the South Kivu
# highlands on the line of advance to Minembwe. Drawn as irregular ground
# rather than as a buffer around a line -- a buffered line comes out a
# perfect stadium, and a control map with a rounded rectangle on it says
# someone surveyed a rounded rectangle.
DRC_WALIKALE_ZONE = [
    (28.38, -1.30),
    (28.05, -1.16),
    (27.72, -1.22),
    (27.52, -1.48),
    (27.63, -1.78),
    (27.98, -1.88),
    (28.32, -1.72),
    (28.46, -1.50),
]
DRC_MINEMBWE_ZONE = [
    (29.18, -3.38),
    (28.86, -3.42),
    (28.58, -3.62),
    (28.52, -3.95),
    (28.72, -4.18),
    (29.02, -4.12),
    (29.20, -3.86),
]


def build_drc() -> dict[str, Any]:
    """Eastern DRC: who holds the Kivus, on a basemap where the lakes exist.

    The plate this generator could not draw honestly until it had lake
    polygons: Goma and Bukavu are 100 km apart at opposite ends of Lake Kivu,
    and on a land-versus-ocean basemap the water between them was painted as
    ground. Schematic, from open-source reporting to late September 2026.
    """
    drc = load_country("Dem. Rep. Congo")
    # No actor "holds" open water, and a control fill laid across Lake Kivu
    # says one does. The lakes come out of every zone before anything is
    # drawn, which is only possible now that the generator has them at all.
    water = unary_union([g for g, _n, _r in load_lakes()])
    land = drc.difference(water)
    m23 = land.intersection(_smooth(Polygon(DRC_M23_CLAIM), km=12))
    contested = land.intersection(
        _smooth(
            unary_union([Polygon(DRC_WALIKALE_ZONE), Polygon(DRC_MINEMBWE_ZONE)]),
            km=15,
        )
    )
    m23 = m23.difference(contested)
    government = land.difference(unary_union([m23, contested]))

    # Government is *not* blue on this plate. Every other map in this gallery
    # is a country with a coast, so a pale blue government fill reads as
    # government; here the DRC fills the frame and the same blue read as
    # ocean -- two thirds of the plate looked like water. A sage green is the
    # nearest house pastel that can never be mistaken for the sea.
    palette = {
        "Government (FARDC)": "#c3d6b4",
        "M23 / AFC": "#e0a89e",
        "Contested (approx.)": "#e4cf9c",
    }
    features = [
        _feat("Government (FARDC)", government),
        _feat("M23 / AFC", m23),
        _feat("Contested (approx.)", contested),
    ]
    return {
        "title": "Eastern DRC: Areas of Control",
        "subtitle": "Schematic · North and South Kivu, along the Albertine Rift",
        "method": "Schematic polygons drawn by hand from the sources below, not a geocoded dataset",
        "source": "Open-source reporting (Critical Threats Congo Security Review, IPIS, Al Jazeera)",
        "as_of": "As of ~25 September 2026 · illustrative, not an operational assessment",
        "caption": "full",
        "region": {"bbox": [27.10, -4.70, 30.30, 0.90]},
        "projection": "auto",
        "canvas_width": 900,
        "padding": 26,
        "basemap": {
            "sea_color": "#a8bccb",
            "land_color": "#f4efdd",
            "coast_color": "#7993a6",
        },
        "frontiers": {"focus": "Dem. Rep. Congo"},
        "legend_position": "bottom-left",
        "legend_footer": "Boundaries approximate",
        "lakes": {"always_label": ["Lake Kivu", "Lake Edward", "Lake Tanganyika", "Lake Albert"]},
        "rivers": {"width": "ranked", "always_label": ["Congo"]},
        "areas_of_control": {
            "category_field": "actor",
            "palette": palette,
            "contested": ["Contested (approx.)"],
            "fill_opacity": 0.78,
            "hatch_color": "#b34a3a",
            "source": {"type": "FeatureCollection", "features": features},
        },
        # Both movements are reported rather than assessed, and are drawn as
        # outlines for that reason: an expansion into ground nobody contested
        # before, and a line of advance that is being fought over, not held.
        "arrows": [
            {
                "line": [[28.82, -1.44], [28.52, -1.42], [28.22, -1.45]],
                "color": "#9c3b2e",
                "width": 6.0,
                "style": "dashed",
                "label": "toward Walikale",
                "label_side": "left",
            },
            {
                "line": [[29.28, -3.10], [29.14, -3.40], [28.98, -3.68]],
                "color": "#9c3b2e",
                "width": 5.5,
                "style": "dashed",
                "label": "toward Minembwe",
                "label_side": "right",
            },
        ],
        "events": [
            {"lon": 29.2336, "lat": -1.6794, "color": "#c0392b", "r": 5},  # Goma
            {"lon": 28.8608, "lat": -2.5061, "color": "#c0392b", "r": 5},  # Bukavu
            {"lon": 29.4667, "lat": 0.5000, "color": "#c0392b", "r": 5},  # Beni
        ],
        "marker_legend": [{"color": "#c0392b", "label": "Contested city (approx.)"}],
        "labels": {
            "places": [
                {
                    "lon": 29.2336, "lat": -1.6794, "text": "Goma",
                    "dot": False, "clear": 5.5, "anchor": "above", "size": 14,
                },
                {
                    "lon": 28.8608, "lat": -2.5061, "text": "Bukavu",
                    "dot": False, "clear": 5.5, "anchor": "end", "size": 14,
                },
                {
                    "lon": 29.4667, "lat": 0.5000, "text": "Beni",
                    "dot": False, "clear": 5.5, "anchor": "above",
                },
                {"lon": 29.2800, "lat": 0.1300, "text": "Butembo", "size": 11},
                {"lon": 29.4494, "lat": -1.1858, "text": "Rutshuru", "size": 11},
                {"lon": 28.8000, "lat": -1.4000, "text": "Masisi", "size": 11, "anchor": "end"},
                {"lon": 28.0700, "lat": -1.4261, "text": "Walikale", "size": 11, "anchor": "end"},
                {"lon": 29.1500, "lat": -3.4000, "text": "Uvira", "size": 11},
                {"lon": 28.7301, "lat": -3.9344, "text": "Minembwe", "size": 11, "anchor": "end"},
                {"lon": 29.0940, "lat": -4.1041, "text": "Baraka", "size": 11},
                {"lon": 29.1906, "lat": -5.9128, "text": "Kalemie", "size": 11},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Reference plates: the natural layers, with nothing competing for attention   #
# --------------------------------------------------------------------------- #
#
# These four carry no areas of control. They exist because the conflict plates
# are a bad place to judge terrain, water and labels: a reader looking at
# Ukraine is looking at the front line, and the relief under it only has to
# not get in the way. Here there is nothing else to look at, so the basemap
# has to stand on its own.
#
# They were in the website's gallery for months with no generator at all --
# rendered once in August, before this package was split out of the monorepo,
# and carried along as files ever since. That is output without a recipe, and
# it showed: opened today, those files have neither a ``<title>`` nor a
# ``<desc>``. They predate the accessibility work entirely. So these are not
# the old configs recovered -- they are the same four subjects, redrawn by the
# current generator. Recovering the originals byte-for-byte would have
# faithfully reproduced four inaccessible maps.


def build_switzerland() -> dict[str, Any]:
    """The Alpine relief, at the scale where a lake is a place and not a dot.

    Switzerland is the hardest small test this generator has. The relief
    carries almost all the information; the lakes are large enough to need
    labelling and close enough together to collide; and the country's own
    outline is so indented that a frontier drawn too thick eats the terrain
    behind it. It is also the one plate where a reader is likely to know the
    ground well enough to catch a mistake.
    """
    return {
        "title": "Switzerland: Relief and Water",
        "subtitle": (
            "A reference plate: terrain, lakes and rivers with no thematic "
            "layer over them"
        ),
        "region": {"bbox": [5.7, 45.6, 10.7, 48.0]},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "relief": True,
            "sea_color": "#a8bccb",
            "land_color": "#f6f1df",
            "coast_color": "#7993a6",
        },
        "frontiers": {"focus": "Switzerland", "label_neighbours": True},
        "internal_borders": {"show": True, "label_names": True},
        # Lake Geneva and Lake Constance are shared borders as much as they are
        # water, and both carry a frontier down the middle. Labelling them is
        # not decoration here: an unlabelled lake on a border plate reads as a
        # gap in the land.
        "lakes": {
            "always_label": ["Lake Geneva", "Bodensee"],
            "depth_rings": True,
        },
        "rivers": {"always_label": ["Rhine", "Rhône"]},
        "cities": {"show": True, "max_rank": 8},
        "legend_position": "right",
        "caption": "full",
        "method": "Natural Earth physical geography; no thematic layer",
        "source": "Natural Earth 1:50m physical and cultural vectors; SRTM-derived shaded relief",
        "labels": {
            "places": [
                {"lon": 7.4474, "lat": 46.9480, "text": "Bern", "capital": True},
                {"lon": 8.5417, "lat": 47.3769, "text": "Zurich"},
                {"lon": 6.1432, "lat": 46.2044, "text": "Geneva", "anchor": "end"},
                {"lon": 7.5886, "lat": 47.5596, "text": "Basel", "anchor": "above"},
                {"lon": 8.9511, "lat": 46.0037, "text": "Lugano", "size": 11},
                {"lon": 9.5215, "lat": 46.8508, "text": "Chur", "size": 11},
                {"lon": 7.9904, "lat": 46.5333, "text": "Interlaken", "size": 11},
                {"lon": 7.3604, "lat": 46.2331, "text": "Sion", "size": 11, "anchor": "below"},
            ],
        },
    }


def build_iberia() -> dict[str, Any]:
    """Two countries, one peninsula, and the rivers that cross between them.

    The point of this one is the river network. Iberia's great rivers -- the
    Tagus, the Douro, the Ebro, the Guadalquivir -- run most of their length
    in one country and reach the sea in another, which is exactly the case
    where labelling a river once, at the right place, is hard.
    """
    return {
        "title": "The Iberian Peninsula",
        "subtitle": "A reference plate: relief, the great rivers, and the Meseta",
        "region": {"bbox": [-10.0, 35.6, 4.6, 44.2]},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "relief": True,
            "sea_color": "#a8bccb",
            "land_color": "#f6f1df",
            "coast_color": "#7993a6",
            "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.35},
        },
        "frontiers": {"focus": "Spain", "label_neighbours": True},
        "rivers": {
            "always_label": ["Tagus", "Duero", "Ebro"],
            # Natural Earth carries the Tagus twice, once under each
            # country's name for it, and the auto-labeller cannot know they
            # are one river -- so the plate printed "Tagus" and "Tajo" on the
            # same water, forty millimetres apart.
            "skip": ["Tajo"],
            "label_max_scalerank": 7,
        },
        "lakes": {"depth_rings": True},
        "cities": {"show": True, "max_rank": 8},
        "legend_position": "right",
        "caption": "full",
        "method": "Natural Earth physical geography; no thematic layer",
        "source": "Natural Earth 1:50m physical and cultural vectors; SRTM-derived shaded relief",
        "labels": {
            "waters": [
                {"lon": -8.6, "lat": 40.6, "text": "ATLANTIC OCEAN", "size": 14, "tracking": 5},
                {"lon": 0.5, "lat": 39.6, "text": "Mediterranean Sea", "size": 12, "tracking": 2.4},
                {"lon": -5.4, "lat": 36.25, "text": "Strait of Gibraltar", "size": 9},
            ],
            "places": [
                {"lon": -3.7038, "lat": 40.4168, "text": "Madrid", "capital": True},
                {"lon": -9.1393, "lat": 38.7223, "text": "Lisbon", "capital": True, "anchor": "end"},
                {"lon": 2.1734, "lat": 41.3851, "text": "Barcelona"},
                {"lon": -5.9845, "lat": 37.3891, "text": "Seville", "anchor": "below"},
                {"lon": -0.3763, "lat": 39.4699, "text": "Valencia"},
                {"lon": -8.6110, "lat": 41.1496, "text": "Porto", "size": 11, "anchor": "end"},
                {"lon": -2.9350, "lat": 43.2630, "text": "Bilbao", "size": 11},
                {"lon": -4.4214, "lat": 36.7213, "text": "Malaga", "size": 11, "anchor": "below"},
                {"lon": -5.6635, "lat": 40.9701, "text": "Salamanca", "size": 11},
                {"lon": -0.8891, "lat": 41.6488, "text": "Zaragoza", "size": 11},
            ],
            "territories": [
                {"lon": -3.9, "lat": 41.3, "text": "MESETA CENTRAL", "size": 11, "tracking": 3},
                {"lon": -3.2, "lat": 37.1, "text": "SIERRA NEVADA", "size": 9, "tracking": 2},
                {"lon": 0.5, "lat": 42.7, "text": "PYRENEES", "size": 10, "tracking": 2.5},
            ],
        },
    }


def build_western_europe() -> dict[str, Any]:
    """The plate the skill documentation points at, at last reproducible.

    ``SKILL.md`` cites this map as the worked example of what the generator
    produces, which made it the single most-referenced artifact in the
    package -- and it was the one nothing could rebuild.

    At this scale every one of the generator's label heuristics is under
    pressure at once: a dozen countries, three seas, the Alps, and a
    coastline that runs from Gibraltar to Denmark. It is the plate where a
    regression in label placement shows up first.
    """
    return {
        "title": "Western Europe",
        "subtitle": "A reference plate: the physical base the thematic maps are drawn on",
        "region": {"bbox": [-10.5, 35.5, 19.5, 55.5]},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "relief": True,
            "sea_color": "#a8bccb",
            "land_color": "#f6f1df",
            "coast_color": "#7993a6",
            "bathymetry": {"rings": 7, "color": "#ffffff", "opacity": 0.35},
        },
        "frontiers": {"show": True, "label_neighbours": True},
        "rivers": {
            "always_label": ["Rhine", "Danube", "Rhône", "Loire", "Elbe", "Po"],
            "label_max_scalerank": 6,
        },
        "lakes": {"depth_rings": True, "label_min_area_frac": 0.0012},
        "cities": {"show": True, "max_rank": 7},
        "legend_position": "right",
        "caption": "full",
        "method": "Natural Earth physical geography; no thematic layer",
        "source": "Natural Earth 1:50m physical and cultural vectors; SRTM-derived shaded relief",
        "labels": {
            "waters": [
                {"lon": -8.0, "lat": 47.0, "text": "ATLANTIC OCEAN", "size": 16, "tracking": 7},
                {"lon": 5.0, "lat": 42.0, "text": "Mediterranean Sea", "size": 13, "tracking": 3},
                {"lon": 3.5, "lat": 54.3, "text": "North Sea", "size": 12, "tracking": 2.4},
                {"lon": 14.5, "lat": 41.0, "text": "Tyrrhenian Sea", "size": 10, "tracking": 2},
                {"lon": -3.0, "lat": 50.0, "text": "English Channel", "size": 9, "tracking": 1.8},
            ],
            "places": [
                {"lon": 2.3522, "lat": 48.8566, "text": "Paris", "capital": True},
                {"lon": 13.4050, "lat": 52.5200, "text": "Berlin", "capital": True},
                {"lon": -3.7038, "lat": 40.4168, "text": "Madrid", "capital": True},
                {"lon": 12.4964, "lat": 41.9028, "text": "Rome", "capital": True},
                {"lon": -0.1276, "lat": 51.5074, "text": "London", "capital": True, "anchor": "above"},
                {"lon": 4.3517, "lat": 50.8503, "text": "Brussels", "size": 11, "anchor": "end"},
                {"lon": 8.5417, "lat": 47.3769, "text": "Zurich", "size": 11},
                {"lon": 9.1900, "lat": 45.4642, "text": "Milan", "size": 11},
                {"lon": 5.3698, "lat": 43.2965, "text": "Marseille", "size": 11, "anchor": "below"},
                {"lon": 9.9937, "lat": 53.5511, "text": "Hamburg", "size": 11},
                {"lon": 16.3738, "lat": 48.2082, "text": "Vienna", "size": 11},
                {"lon": -9.1393, "lat": 38.7223, "text": "Lisbon", "size": 11, "anchor": "end"},
            ],
            "territories": [
                {"lon": 10.0, "lat": 46.6, "text": "ALPS", "size": 12, "tracking": 4},
                {"lon": 0.5, "lat": 42.7, "text": "PYRENEES", "size": 10, "tracking": 2.5},
            ],
        },
    }


def build_himalaya() -> dict[str, Any]:
    """The hardest relief on the planet, which is the point.

    Everywhere else the shaded relief is a background. Here it is the
    subject: eight kilometres of elevation inside a few degrees of longitude,
    which is where a hillshade either holds up or turns into mud. The plate
    is kept deliberately bare -- no control zones, few labels -- so that any
    failure in the terrain rendering has nowhere to hide.

    It is also where the river layer earns its keep: the Indus, the Ganges
    and the Brahmaputra all rise within this frame, on the far side of the
    range from the plains they define.
    """
    return {
        "title": "The Himalaya and the Tibetan Plateau",
        "subtitle": "A reference plate: eight kilometres of relief, and the rivers that leave it",
        "region": {"bbox": [71.5, 24.5, 93.5, 37.5]},
        "projection": "auto",
        "canvas_width": 1320,
        "padding": 30,
        "basemap": {
            "relief": True,
            "sea_color": "#a8bccb",
            "land_color": "#f6f1df",
            "coast_color": "#7993a6",
        },
        "frontiers": {"show": True, "label_neighbours": True},
        "rivers": {
            "always_label": ["Indus", "Ganges", "Brahmaputra", "Sutlej"],
            "label_max_scalerank": 6,
        },
        "lakes": {"depth_rings": True},
        "cities": {"show": True, "max_rank": 7},
        "legend_position": "right",
        "caption": "full",
        "method": "Natural Earth physical geography; no thematic layer",
        "source": "Natural Earth 1:50m physical and cultural vectors; SRTM-derived shaded relief",
        "labels": {
            "places": [
                {"lon": 77.2090, "lat": 28.6139, "text": "Delhi", "capital": True},
                {"lon": 85.3240, "lat": 27.7172, "text": "Kathmandu", "capital": True},
                {"lon": 91.1162, "lat": 29.6500, "text": "Lhasa", "size": 12},
                {"lon": 74.3587, "lat": 31.5204, "text": "Lahore", "size": 11},
                {"lon": 88.3639, "lat": 22.5726, "text": "Kolkata", "size": 11},
                {"lon": 74.7973, "lat": 34.0837, "text": "Srinagar", "size": 11},
                {"lon": 77.5946, "lat": 29.9680, "text": "Dehradun", "size": 10, "anchor": "end"},
            ],
            "territories": [
                {"lon": 84.0, "lat": 32.5, "text": "TIBETAN PLATEAU", "size": 13, "tracking": 5},
                {"lon": 82.5, "lat": 28.6, "text": "H I M A L A Y A", "size": 13, "tracking": 4},
                {"lon": 75.5, "lat": 35.6, "text": "KARAKORAM", "size": 10, "tracking": 2.5},
                {"lon": 79.5, "lat": 26.6, "text": "GANGETIC PLAIN", "size": 10, "tracking": 2.5},
            ],
        },
    }


BUILDERS = {
    "ukraine": build_ukraine,
    "syria": build_syria,
    "libya": build_libya,
    "sudan": build_sudan,
    "drc": build_drc,
    "switzerland": build_switzerland,
    "iberia": build_iberia,
    "western-europe": build_western_europe,
    "himalaya": build_himalaya,
}

PNG_WIDTH = 1300  # export raster width, px


def _render_png(svg: Path, png: Path, *, width: int = PNG_WIDTH) -> bool:
    """Rasterise ``svg`` to ``png``; return whether a raster was written.

    ``resvg-py`` is a declared dependency of this package, so it is here on any
    machine that can run the generator at all. ``rsvg-convert`` -- which this
    used to require, and silently skipped every PNG without -- stays as a
    fallback for the one thing resvg occasionally trips on, a system font the
    SVG names but does not embed.

    ``width`` is a parameter rather than the module constant because the
    gallery publisher renders a world choropleth narrower than a regional
    plate, and a second copy of this fallback logic is the last thing this
    repository needs.
    """
    try:
        import resvg_py

        png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg.read_text(), width=width)))
        return True
    except Exception as exc:  # pragma: no cover - fallback path
        rsvg = shutil.which("rsvg-convert")
        if not rsvg:
            print(f"  (skipped PNG for {png.name}: resvg failed [{exc}], no rsvg-convert)")
            return False
        subprocess.run([rsvg, "-w", str(width), str(svg), "-o", str(png)], check=True)
        return True


# Every named layer the generator emits, bottom -> top.
ALL_LAYERS = (
    "basemap-sea",
    "basemap-bathymetry",
    "basemap-land",
    "lakes",
    "frontiers",
    "areas-of-control",
    "coastline",
    "infrastructure",
    "rivers",
    "cities",
    "front-line",
    "arrows",
    "forces",
    "events",
    "annotation-labels",
    "annotation-furniture",
    "legend",
    "frame",
)
# The physical basemap + furniture kept as a constant backdrop under each view,
# so a single thematic layer is read *in geographic context*, not in a void.
# Frontiers, coastline and rivers are base geography, so they ride the backdrop.
_BACKDROP = {
    "basemap-sea",
    "basemap-bathymetry",
    "basemap-land",
    "lakes",
    "frontiers",
    "coastline",
    "rivers",
    "annotation-furniture",
    "frame",
}
# The a-posteriori decompositions a geopolitics analyst actually reads a plate in.
LAYER_VIEWS = {
    "basemap": _BACKDROP,
    "areas-of-control": _BACKDROP | {"areas-of-control", "front-line", "arrows", "legend"},
    "markers": _BACKDROP | {"forces", "events", "legend"},
    "labels": _BACKDROP | {"annotation-labels"},
}


def _export_layers(name: str, svg_text: str) -> None:
    """Emit a-posteriori per-layer SVG+PNG views by hiding the other layers.

    The generator writes each semantic layer as ``<g id="...">``; a view keeps a
    chosen subset visible and sets ``display:none`` on the rest: a decomposition
    of the finished plate into the strata an analyst toggles between.
    """
    out_dir = SHIP / "layers"
    out_dir.mkdir(parents=True, exist_ok=True)
    for view, keep in LAYER_VIEWS.items():
        text = svg_text
        for layer in ALL_LAYERS:
            if layer not in keep:
                text = text.replace(f'<g id="{layer}">', f'<g id="{layer}" style="display:none">')
        svg_out = out_dir / f"{name}.a-posteriori.{view}.svg"
        png_out = out_dir / f"{name}.a-posteriori.{view}.png"
        svg_out.write_text(text)
        _render_png(svg_out, png_out)
    print(f"  layers: {name}.a-posteriori.{{{', '.join(LAYER_VIEWS)}}}.svg/.png")


def main(argv: list[str]) -> None:
    want_layers = "--layers" in argv
    names = [a for a in argv if not a.startswith("-")] or list(BUILDERS)
    unknown = [n for n in names if n not in BUILDERS]
    if unknown:
        raise SystemExit(f"unknown example(s) {unknown}; known: {', '.join(BUILDERS)}")
    SHIP.mkdir(parents=True, exist_ok=True)
    for name in names:
        cfg = BUILDERS[name]()
        # Validate before writing anything. These configs ship as the worked
        # examples of what the generator accepts, so a dead option in one is
        # not a private mistake -- it is documentation that lies. Three of
        # them carried ``areas_of_control.hatch_color`` past a validator that
        # refuses it, for as long as this script has existed, because this
        # script never asked.
        validate_config(cfg)
        yaml_path = SHIP / f"{name}.yaml"
        yaml_path.write_text(json.dumps(cfg, indent=2))
        # The generator is imported, not shelled out to: the subprocess call
        # named a path in a sibling checkout, and this way a config that the
        # generator refuses fails here with its own error message.
        svg_path = SHIP / f"{name}.svg"
        svg_path.write_text(build_map(cfg))
        _render_png(svg_path, SHIP / f"{name}.png")
        print(f"wrote {name}.yaml / .svg / .png  ({yaml_path.stat().st_size // 1024} KB config)")
        # A-posteriori layer decomposition: the final stage, once the plate is
        # set, and only when asked -- it is an order of magnitude more output
        # than the plate itself.
        if want_layers:
            _export_layers(name, svg_path.read_text())


if __name__ == "__main__":
    main(sys.argv[1:])
