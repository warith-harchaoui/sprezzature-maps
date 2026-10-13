"""
The two conflict-dataset loaders, held to what the published codebooks say.

The loaders exist to carry one thing across the gap between a researcher's
CSV and a drawn plate: **how well each row's location and date are actually
known**. Everything here is a test of that. The column names, the code
ranges and the wording of each code are taken from the ACLED codebook
(October 2024) and the UCDP GED codebook (version 25.1), both read rather
than recalled, and the mapping between UCDP's seven-step geo-precision and
this generator's three is the judgement those documents leave open -- so it
is pinned here, where changing it means changing a test on purpose.

The palette is not asserted to be colour-vision safe. It is simulated, with
this repository's own ``simulate_cvd_hex``, and the result is measured. That
is the same rule the choropleth ramp is held to and it is the only kind of
accessibility claim worth making.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cf = _load("_conflict")
gc = _load("_geo_colors")
msm = _load("make_situation_map")


#: One ACLED row with every column this loader reads, spelled as the
#: codebook spells it.
ACLED_ROW: dict[str, str] = {
    "event_id_cnty": "SUD1234",
    "event_date": "2024-03-05",
    "year": "2024",
    "time_precision": "1",
    "disorder_type": "Political violence",
    "event_type": "Battles",
    "sub_event_type": "Armed clash",
    "actor1": "Military Forces of Sudan (2019-)",
    "actor2": "Rapid Support Forces",
    "country": "Sudan",
    "admin1": "Khartoum",
    "admin2": "Omdurman",
    "location": "Omdurman",
    "latitude": "15.6445",
    "longitude": "32.4777",
    "geo_precision": "1",
    "source": "Radio Dabanga",
    "source_scale": "National",
    "notes": "On 5 March 2024...",
    "fatalities": "9",
}

#: One UCDP GED row, likewise.
UCDP_ROW: dict[str, str] = {
    "id": "123456",
    "year": "2023",
    "type_of_violence": "1",
    "conflict_name": "Sudan: Government",
    "date_start": "2023-04-15",
    "date_end": "2023-04-15",
    "date_prec": "1",
    "where_coordinates": "Khartoum",
    "where_prec": "1",
    "adm_1": "Khartoum state",
    "adm_2": "Khartoum",
    "latitude": "15.588100",
    "longitude": "32.534200",
    "country": "Sudan",
    "best": "47",
    "low": "40",
    "high": "55",
    "source_article": "Reuters",
}


def _acled(**overrides: str) -> list[dict[str, str]]:
    return [ACLED_ROW | overrides]


def _ucdp(**overrides: str) -> list[dict[str, str]]:
    return [UCDP_ROW | overrides]


# ── what the loaders carry across ───────────────────────────────────────


@pytest.mark.parametrize("code", [1, 2, 3])
def test_acled_geo_precision_reaches_the_marker_unchanged(code: int) -> None:
    """
    ACLED's 1-3 is the scale the marker layer was built from; it passes through.

    This generator's ``_GEO_PRECISION`` wording was taken from this
    codebook, so any mapping here other than the identity would mean the two
    had drifted.
    """
    frag = cf.acled_events(_acled(geo_precision=str(code)))
    assert frag["events"][0]["precision"] == code


@pytest.mark.parametrize(
    ("where_prec", "precision", "radius_km"),
    [
        (1, 1, None),   # exact location known and coded
        (2, 2, 25),     # within ca. 25 km of a known point -- the radius is drawn
        (3, 2, None),   # an adm-2 centroid standing in for the division
        (4, 3, None),   # an adm-1 centroid standing in for the region
        (5, 3, None),   # a linear feature or a fuzzy polygon
        (7, 3, None),   # international waters or airspace
    ],
)
def test_ucdp_where_prec_maps_onto_the_three_step_scale(
    where_prec: int, precision: int, radius_km: int | None
) -> None:
    """
    UCDP's seven steps onto this generator's three, as the module documents them.

    The interesting row is ``where_prec`` 2: the codebook states a radius of
    about 25 km, and the loader keeps it as a drawn ``radius_km`` instead of
    flattening it into the code that stands for it.
    """
    frag = cf.ucdp_events(_ucdp(where_prec=str(where_prec)))
    mark = frag["events"][0]
    assert mark["precision"] == precision
    assert mark.get("radius_km") == radius_km


def test_a_country_level_ucdp_row_is_not_given_a_position() -> None:
    """
    ``where_prec`` 6 says only the country is known, so no dot is honest.

    The row still carries coordinates -- every GED row does -- and they are a
    representative point for a whole state. Drawing one asserts a place the
    source never gave. The row is dropped, and the drop is on the plate.
    """
    with pytest.warns(RuntimeWarning, match="located only to the country"):
        frag = cf.ucdp_events(_ucdp(where_prec="6"))
    assert frag["events"] == []
    assert "1 located only to the country" in frag["method"]


def test_a_country_level_row_can_be_kept_but_says_so() -> None:
    """A caller who wants them gets them at the weakest precision, still counted."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        frag = cf.ucdp_events(_ucdp(where_prec="6"), country_level="keep")
    assert frag["events"][0]["precision"] == 3


def test_a_year_only_date_is_printed_as_a_year() -> None:
    """
    ``date_prec`` 5 means the year and no more, and the plate now has a word for it.

    Before this, the scale stopped at "month of", and mapping a year onto it
    would have stated a month the source never gave -- an overstatement, which
    is the direction that matters. ``make_situation_map`` grew a fourth step.
    """
    frag = cf.ucdp_events(_ucdp(date_prec="5", date_start="2023-04-15"))
    mark = frag["events"][0]
    assert mark["time_precision"] == 4
    assert mark["date"] == "2023"
    assert msm._TIME_PRECISION[4].format("2023") == "in 2023"


def test_the_three_lower_precisions_still_mean_what_they_meant() -> None:
    """Adding a fourth step must not have moved the first three."""
    assert msm._TIME_PRECISION[1] == "{}"
    assert msm._TIME_PRECISION[2] == "week of {}"
    assert msm._TIME_PRECISION[3] == "month of {}"


# ── refusing rather than guessing ───────────────────────────────────────


@pytest.mark.parametrize("bad", ["", "4", "0", "exact", None])
def test_an_unreadable_precision_code_is_an_error_not_an_upgrade(bad: Any) -> None:
    """
    The one failure direction this feature exists to prevent.

    Treating a code it cannot read as "exact" would turn an approximate mark
    into a confident one on a plate that still looks finished.
    """
    with pytest.raises(ValueError, match="geo_precision"):
        cf.acled_events(_acled(geo_precision=bad))


def test_an_unparseable_coordinate_names_its_row() -> None:
    with pytest.raises(ValueError, match="row 1: longitude"):
        cf.acled_events(_acled(longitude="N/A"))


def test_a_class_outside_the_vocabulary_is_refused() -> None:
    """
    A new ACLED event type is news, not a row to colour arbitrarily.

    The fixed vocabulary is what keeps one colour meaning one thing across
    the figures in a paper; silently appending a seventh would break that
    without telling anyone.
    """
    with pytest.raises(ValueError, match="not one this loader knows"):
        cf.acled_events(_acled(event_type="Cyber operations"))


def test_the_vocabulary_can_be_extended_on_purpose() -> None:
    frag = cf.acled_events(
        _acled(event_type="Cyber operations"),
        vocabulary=[*cf.ACLED_EVENT_TYPES, "Cyber operations"],
    )
    assert frag["marker_legend"][0]["label"] == "Cyber operations"


def test_more_classes_than_colours_is_refused() -> None:
    """Only classes actually met take a colour, so this needs nine real ones."""
    vocab = [f"c{i}" for i in range(9)]
    rows = [ACLED_ROW | {"event_type": c} for c in vocab]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match=r"longer `palette="):
            cf.acled_events(rows, vocabulary=vocab, palette=("#000000",))


# ── the legend, the method line, the region ─────────────────────────────


def test_the_palette_is_not_asked_to_make_the_mark_visible() -> None:
    """
    The casing does that, which is why the fill is free to be a category.

    A precision-1 marker is a filled disc with a white stroke and a shadow;
    an approximate one is a white disc with a coloured ring. Either way the
    edge against the ground is white, not the fill, so the fill's contrast
    against the cream land is the wrong thing to measure. What has to hold
    is that no colour vanishes *into the casing*, which is a far lower bar
    and one every member clears.
    """
    for colour in cf.OKABE_ITO[:6]:
        ratio = gc.wcag_contrast_ratio(colour, "#ffffff")
        assert ratio >= 2.0, f"{colour} is {ratio:.2f}:1 against its own white casing"


def test_the_legend_follows_the_codebook_order_not_the_file_order() -> None:
    """
    Two plates from two country files must agree on what blue means.

    The file's own order is an accident of which event happened first; the
    codebook's order is a fact about the dataset.
    """
    rows = [
        ACLED_ROW | {"event_type": "Riots"},
        ACLED_ROW | {"event_type": "Battles"},
    ]
    frag = cf.acled_events(rows)
    assert [r["label"] for r in frag["marker_legend"]] == ["Battles", "Riots"]
    assert frag["events"][0]["color"] == frag["marker_legend"][1]["color"]  # the riot
    assert frag["events"][1]["color"] == frag["marker_legend"][0]["color"]  # the battle


def test_a_class_absent_from_the_file_is_absent_from_the_legend() -> None:
    """A legend row for a category with no marks is a row that teaches nothing."""
    frag = cf.acled_events(_acled(event_type="Protests"))
    assert [r["label"] for r in frag["marker_legend"]] == ["Protests"]


def test_the_method_line_carries_the_count_and_the_window() -> None:
    rows = [
        ACLED_ROW | {"event_date": "2024-01-03"},
        ACLED_ROW | {"event_date": "2024-12-29"},
    ]
    assert cf.acled_events(rows)["method"] == (
        "2 ACLED events drawn; 2024-01-03 to 2024-12-29."
    )


def test_a_limit_is_reported_rather_than_applied_in_silence() -> None:
    """
    Truncation that does not announce itself reads exactly like full coverage.

    The same rule this repository applies to a workflow that caps its own
    fan-out: say what was dropped.
    """
    rows = [ACLED_ROW] * 5
    with pytest.warns(RuntimeWarning, match="beyond the 2-event limit"):
        frag = cf.acled_events(rows, limit=2)
    assert len(frag["events"]) == 2
    assert "3 beyond the 2-event limit" in frag["method"]


def test_the_region_can_be_derived_from_the_events() -> None:
    rows = [
        ACLED_ROW | {"longitude": "30.0", "latitude": "10.0"},
        ACLED_ROW | {"longitude": "34.0", "latitude": "16.0"},
    ]
    bbox = cf.acled_events(rows, derive_region=True, region_pad=0.5)["region"]["bbox"]
    assert bbox == [29.5, 9.5, 34.5, 16.5]


def test_deriving_a_region_from_nothing_is_an_error() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="no event survived"):
            cf.ucdp_events(_ucdp(where_prec="6"), derive_region=True)


def test_sizing_by_fatalities_is_area_true() -> None:
    """
    A disc is read by its area, so the radius goes as the square root.

    With the span fixed by the file's own largest value, a row at a quarter
    of the maximum must sit a quarter of the way up the radius span -- the
    square root of 1/4 being 1/2 would put it halfway, which is the test.
    """
    rows = [
        ACLED_ROW | {"fatalities": "0"},
        ACLED_ROW | {"fatalities": "25"},
        ACLED_ROW | {"fatalities": "100"},
    ]
    r = [e["r"] for e in cf.acled_events(rows, size_by="fatalities",
                                         base_radius=4.0, max_radius=12.0)["events"]]
    assert r == [4.0, 8.0, 12.0]


def test_the_largest_disc_is_bounded_by_the_page_not_by_the_data() -> None:
    """
    Conflict magnitudes span four orders; an unbounded scale draws a county.

    The first version of this used ``base * sqrt(1 + value)`` with no
    ceiling and put a 120-fatality mark at radius 33 on a 1100-unit plate --
    found by rendering it and looking at it, not by any test.
    """
    rows = [ACLED_ROW | {"fatalities": f} for f in ("0", "100000")]
    r = [e["r"] for e in cf.acled_events(rows, size_by="fatalities")["events"]]
    assert max(r) == 11.0


def test_an_all_zero_column_draws_every_mark_the_same() -> None:
    """Nothing to scale is not a reason to divide by zero."""
    rows = [ACLED_ROW | {"fatalities": "0"}] * 3
    r = [e["r"] for e in cf.acled_events(rows, size_by="fatalities")["events"]]
    assert r == [3.0, 3.0, 3.0]


def test_no_sizing_unless_asked() -> None:
    """A dot map of *where* and a bubble map of *how many* are different claims."""
    assert "r" not in cf.acled_events(_acled())["events"][0]


# ── the shapes a researcher's data actually arrives in ──────────────────


def test_a_csv_on_disk(tmp_path: Path) -> None:
    import csv as _csv

    path = tmp_path / "acled.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(ACLED_ROW))
        w.writeheader()
        w.writerow(ACLED_ROW)
    assert cf.acled_events(path)["events"][0]["lat"] == 15.6445


def test_an_api_body_with_its_envelope(tmp_path: Path) -> None:
    """The ACLED API answers ``{"status": 200, "data": [...]}``; take either shape."""
    path = tmp_path / "acled.json"
    path.write_text(json.dumps({"status": 200, "count": 1, "data": [ACLED_ROW]}))
    assert len(cf.acled_events(path)["events"]) == 1


def test_a_json_object_with_no_event_list_says_so(tmp_path: Path) -> None:
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"status": 200, "message": "no key"}))
    with pytest.raises(ValueError, match="no 'data', 'results' or 'events' list"):
        cf.acled_events(path)


def test_rows_already_in_memory() -> None:
    """``DataFrame.to_dict("records")`` is this shape, which is how pandas works here."""
    assert len(cf.acled_events(iter([ACLED_ROW]))["events"]) == 1


# ── the palette, simulated rather than asserted ─────────────────────────


def _distance(a: str, b: str) -> float:
    """Perceptual distance between two hex colours, in OKLab."""
    la = gc._linear_to_oklab(gc._hex_to_linear(a))
    lb = gc._linear_to_oklab(gc._hex_to_linear(b))
    return sum((x - y) ** 2 for x, y in zip(la, lb, strict=True)) ** 0.5


CVD_TYPES = ("protanopia", "deuteranopia", "tritanopia")


def _cvd_floor(colours: tuple[str, ...]) -> tuple[float, str, str]:
    """The closest pair in ``colours``, over all three deficiencies at once."""
    worst = (float("inf"), "", "")
    for cvd in CVD_TYPES:
        seen = [gc.simulate_cvd_hex(c, cvd) for c in colours]
        for i in range(len(seen)):
            for j in range(i + 1, len(seen)):
                worst = min(worst, (_distance(seen[i], seen[j]), colours[i], colours[j]))
    return worst


#: The measured separation of each prefix of the palette, as shipped.
#:
#: Not a target someone hoped for -- the number the simulation returns today,
#: pinned so that a reordering, a substitution or a change to the simulation
#: has to be a decision rather than a side effect. The palette is consumed
#: as a prefix, so each length is its own promise: a plate with three
#: classes is held to the three-class floor, not to the six-class one.
PREFIX_FLOORS: dict[int, float] = {2: 0.290, 3: 0.189, 4: 0.131, 5: 0.086, 6: 0.075}


@pytest.mark.parametrize("n", sorted(PREFIX_FLOORS))
def test_every_prefix_of_the_palette_survives_colour_vision_deficiency(n: int) -> None:
    """
    Simulated, not asserted, and measured for the prefix actually used.

    A three-class plate takes the first three colours, so the promise that
    matters there is the three-class floor. The published Okabe-Ito order
    would give 0.084 at three; this order gives 0.189, which is why the
    order is searched rather than copied.
    """
    floor, a, b = _cvd_floor(cf.OKABE_ITO[:n])
    assert floor >= PREFIX_FLOORS[n] - 0.001, (
        f"with {n} classes the closest pair is {a} and {b} at {floor:.3f}, "
        f"below the {PREFIX_FLOORS[n]:.3f} this palette has been shipping"
    )


def test_the_order_is_the_one_that_was_searched_for() -> None:
    """
    Each prefix is at least as separable as the published Okabe-Ito order.

    The guard against someone "tidying" the palette back into its familiar
    order: that order is a fine set and a worse sequence.
    """
    published = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
    assert sorted(cf.OKABE_ITO[:6]) == sorted(published), "the colours themselves changed"
    for n in range(3, 7):
        assert _cvd_floor(cf.OKABE_ITO[:n])[0] >= _cvd_floor(published[:n])[0]


def test_equalising_contrast_would_cost_more_than_it_buys() -> None:
    """
    The measurement behind the decision not to darken the pale colours.

    Lightness is the one channel all three deficiencies leave intact, so
    pushing every colour to the same contrast ratio against the land is
    pushing out the cue those readers have left. This reproduces that: the
    darkened palette wins on contrast and loses badly on separation, and
    the comment in ``_conflict.py`` is checkable rather than a claim.
    """
    land = "#f4efdd"

    def darkened(hex_: str) -> str:
        lightness, chroma, hue = gc._oklab_to_oklch(gc._linear_to_oklab(gc._hex_to_linear(hex_)))
        for step in range(60):
            cand = gc._linear_to_hex(
                gc._oklab_to_linear(gc._oklch_to_oklab((max(0.0, lightness - step * 0.01),
                                                        chroma, hue)))
            )
            if gc.wcag_contrast_ratio(cand, land) >= 3.0:
                return cand
        return hex_

    flattened = tuple(darkened(c) for c in cf.OKABE_ITO[:6])
    assert all(gc.wcag_contrast_ratio(c, land) >= 3.0 for c in flattened)
    assert _cvd_floor(flattened)[0] < _cvd_floor(cf.OKABE_ITO[:6])[0] / 2


def test_a_crowded_legend_is_named_rather_than_drawn_in_silence() -> None:
    """Six hues on one dot map is the edge, and the reader is told once."""
    rows = [ACLED_ROW | {"event_type": t} for t in cf.ACLED_EVENT_TYPES]
    with pytest.warns(RuntimeWarning, match="categorical colours on one plate"):
        frag = cf.acled_events(rows)
    assert len(frag["marker_legend"]) == 6


def test_a_legend_within_the_limit_says_nothing() -> None:
    rows = [ACLED_ROW | {"event_type": t} for t in cf.ACLED_EVENT_TYPES[:4]]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert len(cf.acled_events(rows)["marker_legend"]) == 4


# ── and the whole way through to a drawn plate ──────────────────────────


def test_a_loaded_fragment_draws(tmp_path: Path) -> None:
    """
    The fragment's keys are keys the generator reads, end to end.

    A loader that produced a dict the validator rejects would be a loader
    that works only in its own tests.
    """
    rows = [
        ACLED_ROW | {"longitude": "32.5", "latitude": "15.6", "event_type": "Battles"},
        ACLED_ROW | {"longitude": "33.1", "latitude": "14.9", "event_type": "Protests",
                     "geo_precision": "3", "time_precision": "3"},
    ]
    cfg: dict[str, Any] = {
        "title": "Sudan: recorded political violence",
        "canvas_width": 900,
        "basemap": {"relief": False},
    }
    cfg.update(cf.acled_events(rows, derive_region=True, size_by="fatalities"))
    msm.validate_config(cfg)
    svg = msm.build_map(cfg)
    assert svg.startswith("<svg") or "<svg" in svg[:400]
    # The precision the loader read is the precision the markup carries.
    assert 'data-precision="3"' in svg
    assert 'data-precision="1"' in svg
