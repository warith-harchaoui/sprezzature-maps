"""The regional choropleth: a value per administrative unit.

The gap this closes. ``areas_of_control`` colours a unit by *who holds
it*, which is categorical. ``make_choropleth`` colours by *how much*, and
only for the whole world, keyed on ISO-3166-1 numeric. Between the two sat
every ordinary analysis a data scientist actually brings — a rate by
French region, a count by US state, a score by German Kreis — with the
geometry already vendored in this repository, already read by the border
layers that draw the lines and say nothing about what is inside them.

What the layer has to get right is not the filling. It is the matching and
the key: a row that lines up with no unit, a value that is not a number,
a classification nobody can name, a no-data grey nothing explains. Each
one of those is a way to produce a confident picture of nothing, and each
has a test here.

Author: Warith HARCHAOUI
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")

#: Four states and a slice of the west, small enough to render quickly.
_WEST = {
    "title": "A values plate",
    "region": {"bbox": [-125.0, 32.0, -108.0, 46.0]},
    "canvas_width": 700,
    "basemap": {"relief": False},
    "cities": {"show": False},
    "rivers": {"show": False},
}


def _with_values(**spec: object) -> dict:
    return {**_WEST, "values": {"by": "us-states", **spec}}


# ── matching ─────────────────────────────────────────────────────────────


def test_a_name_matches_through_case_accents_and_punctuation() -> None:
    """A spreadsheet spells a place its way and the atlas spells it another.

    "Provence-Alpes-Cote d'Azur" against "Provence-Alpes-Côte d'Azur" is
    not a disagreement about which region is meant. A match that failed on
    it would drop a real row into the no-data grey without a word, which
    is indistinguishable from the region genuinely having no value.
    """
    fold = msm._fold
    assert fold("Provence-Alpes-Côte d'Azur") == fold("provence alpes cote dazur")
    assert fold("New York") == fold("new-york")
    assert fold("Baden-Württemberg") == fold("BADEN WURTTEMBERG")
    assert fold("Ohio") != fold("Iowa")


def test_a_table_that_matches_nothing_raises() -> None:
    """A spelling problem must not render as an empty grey map.

    This is the failure that looks most like success. Every unit comes out
    in the no-data fill, the legend explains the no-data fill, the plate
    is internally consistent and says nothing — and the cause is one
    column name.
    """
    cfg = _with_values(data=[{"name": "Californie", "value": 1.0}])
    with pytest.raises(ValueError, match="not one of the 1 values rows"):
        msm._values_layer(cfg, msm.build_projection(cfg["region"]["bbox"], "auto"),
                          _viewport(cfg))


def test_a_value_that_is_not_a_number_stops_the_plate() -> None:
    """Dropping it would be indistinguishable from the unit having no data.

    The reading and the refusing are deliberately two steps: the table
    collects what it could not parse, the layer decides that a plate
    cannot be drawn over it. Keeping the decision out of the parser is
    what lets the message name every bad cell at once instead of the
    first.
    """
    table, unreadable = msm._value_table(
        {"data": [{"name": "Oregon", "value": "n/a"}]}, Path(".")
    )
    assert table == {}
    assert unreadable == ["Oregon='n/a'"]

    cfg = _with_values(data=[{"name": "Oregon", "value": "n/a"}])
    with pytest.raises(ValueError, match="not a number"):
        msm._values_layer(
            cfg, msm.build_projection(cfg["region"]["bbox"], "auto"), _viewport(cfg)
        )


def test_an_empty_value_is_no_data_and_not_an_error() -> None:
    """A blank cell is a real answer: this unit has no value.

    The distinction from the test above is the whole point. ``""`` means
    "we have no figure here"; ``"n/a"`` means somebody wrote something the
    reader can see and the parser cannot, and quietly treating the second
    as the first is how a typo becomes a grey state.
    """
    table, unreadable = msm._value_table(
        {"data": [{"name": "Oregon", "value": ""}, {"name": "Utah", "value": 3}]},
        Path("."),
    )
    assert unreadable == []
    assert set(table) == {msm._fold("Utah")}


def test_a_row_with_no_key_column_raises_naming_the_option() -> None:
    with pytest.raises(ValueError, match="values.key"):
        msm._value_table({"data": [{"state": "Oregon", "value": 1}]}, Path("."))


# ── the key ──────────────────────────────────────────────────────────────


def test_the_classification_names_its_own_method() -> None:
    """Quantiles and natural breaks tell different stories from one dataset.

    A plate that does not say which it used cannot be argued with, which
    is why ``audit`` reports one that does not. Here the generator prints
    it rather than the author remembering to.
    """
    breaks, method, classes = msm._value_classes(
        {"classes": 4, "method": "quantile"}, [1.0, 2.0, 3.0, 9.0, 20.0, 50.0]
    )
    assert method == "quantile"
    assert classes == 4
    assert len(breaks) == 3


def test_given_breaks_are_labelled_as_given() -> None:
    """Editorial boundaries are provenance, and the legend has to say so."""
    breaks, method, classes = msm._value_classes({"breaks": [10, 20, 30]}, [1.0, 50.0])
    assert (breaks, method, classes) == ([10.0, 20.0, 30.0], "given", 4)


def test_an_unknown_method_raises_with_the_list() -> None:
    with pytest.raises(ValueError, match="natural|jenks|quantile"):
        msm._value_classes({"method": "vibes"}, [1.0, 2.0])


def test_an_unknown_layer_raises_with_the_list() -> None:
    cfg = _with_values(by="martian-provinces", data=[{"name": "x", "value": 1}])
    with pytest.raises(ValueError, match="unknown values.by"):
        msm._values_layer(cfg, msm.build_projection(cfg["region"]["bbox"], "auto"),
                          _viewport(cfg))


def test_a_mistyped_option_is_refused_like_every_other_section() -> None:
    """The repository's standing rule: a key nothing reads is refused."""
    cfg = _with_values(data=[{"name": "Oregon", "value": 1}], classses=5)
    with pytest.raises(ValueError, match="classses"):
        msm.validate_config(cfg)


# ── the drawing ──────────────────────────────────────────────────────────


def _viewport(cfg: dict) -> dict:
    bbox = cfg["region"]["bbox"]
    return msm.make_viewport(
        msm.build_projection(bbox, "auto"), bbox, float(cfg["canvas_width"]), 30.0
    )


def test_the_layer_fills_the_units_it_matched() -> None:
    cfg = _with_values(
        data=[
            {"name": "Oregon", "value": 44.1},
            {"name": "Nevada", "value": 28.3},
            {"name": "Utah", "value": 39.9},
            {"name": "Idaho", "value": 22.3},
        ],
        classes=3,
        method="equal",
        label="PEOPLE PER SQUARE MILE",
    )
    vp = _viewport(cfg)
    markup = msm._values_layer(cfg, msm.build_projection(cfg["region"]["bbox"], "auto"), vp)
    assert markup.startswith('<g id="values">')
    assert "<title>Oregon: 44.1</title>" in markup
    key = cfg["_value_key"]
    assert key["method"] == "equal"
    assert key["classes"] == 3

    legend = msm._value_legend(cfg, vp)
    assert "3 classes, equal intervals" in legend, legend
    for cut in key["breaks"]:
        assert msm._fmt_num(cut) in legend, f"break {cut} is not printed"
    assert "PEOPLE PER SQUARE MILE" in legend


def test_the_no_data_chip_appears_only_when_a_unit_got_no_data() -> None:
    """A key that explains a colour the plate never used makes a reader check."""
    cfg = _with_values(data=[{"name": "Oregon", "value": 1.0}], classes=2)
    vp = _viewport(cfg)
    msm._values_layer(cfg, msm.build_projection(cfg["region"]["bbox"], "auto"), vp)
    assert cfg["_value_key"]["no_data"], (
        "the plate draws several western states and only one has a value, "
        "so the chip is owed"
    )
    assert "No data" in msm._value_legend(cfg, vp)

    everything = {msm._fold(name) for name, _g in msm.load_us_states(cfg["region"]["bbox"])}
    full = _with_values(
        data=[{"name": n, "value": float(i)} for i, n in enumerate(sorted(everything))],
        classes=2,
    )
    vp2 = _viewport(full)
    msm._values_layer(full, msm.build_projection(full["region"]["bbox"], "auto"), vp2)
    assert full["_value_key"]["no_data"] == ""
    assert "No data" not in msm._value_legend(full, vp2)


def test_the_scale_bar_yields_to_the_graded_key() -> None:
    """Both want the bottom-left corner, and the first plate drawn put the
    ruler straight through the colour strip and its break values.
    """
    plain_x, _y = msm._scale_bar_origin(_WEST, {"ts": 1.0, "width": 1000.0, "height": 700.0})
    with_key_x, _y2 = msm._scale_bar_origin(
        _with_values(data=[{"name": "Oregon", "value": 1}]),
        {"ts": 1.0, "width": 1000.0, "height": 700.0},
    )
    assert plain_x < 500.0, "the bar's home is bottom-left"
    assert with_key_x > 500.0, "the bar did not move out of the key's corner"
