"""
The choropleth must not render something plausible out of data it cannot map.

Both defects here were found by a Ralph Loop pass that fed the generators the
inputs real callers actually produce — an empty result set, a spreadsheet
with one blank cell — rather than the tidy demo rows. Both rendered a
finished, publishable world map, which is the worst possible answer: a map
that looks right is trusted, and neither of these was.

The sibling generators already refused. ``make_density`` answers an empty
point list with "no point fell inside the bbox; nothing to draw", and
``make_situation_map`` will not render without a region. The choropleth was
the odd one out.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import pytest

from sprezzature_maps import _load_script

mc = _load_script("make_choropleth")


def test_an_empty_result_set_is_refused_not_silently_replaced_by_the_demo() -> None:
    """
    ``data=[]`` used to render the bundled synthetic demo.

    ``[]`` is falsy, so ``data if data else DEMO_DATA`` could not tell "I
    brought no data, show me the demo" apart from "my query returned
    nothing". The second is an ordinary thing for a dashboard to produce,
    and the result was 174 countries of invented values.
    """
    with pytest.raises(ValueError, match="empty list"):
        mc.build_svg([])


def test_the_empty_case_is_worst_under_the_caller_s_own_caption() -> None:
    """
    The demo subtitle is what kept this honest, and a caller who sets their
    own subtitle removes it.

    With ``title`` and ``subtitle`` supplied, the plate carried no warning
    anywhere: a world map of synthetic numbers under a real headline, and an
    accessible description announcing "174 countries with data ranging 0.9
    to 99.8" as though it were the caller's.
    """
    with pytest.raises(ValueError):
        mc.build_svg([], title="Q3 revenue by country", subtitle="Millions of euros")


def test_asking_for_the_demo_on_purpose_still_works() -> None:
    """``None`` means "show me the demo", and the plate says so on itself."""
    svg = mc.build_svg()
    assert "synthetic demo data" in svg


def test_a_single_nan_is_refused_rather_than_poisoning_the_scale() -> None:
    """
    One non-finite value made the whole map meaningless and still finished.

    ``min``/``max`` both came back ``nan``, so the ramp spanned nan, every
    class was garbage, the accessible description read "data ranging nan to
    nan" and the legend printed **nan** as its own axis labels. One empty
    cell in a spreadsheet is the ordinary way to arrive here.
    """
    rows = [
        {"id": "840", "value": float("nan")},
        {"id": "124", "value": 1},
        {"id": "076", "value": 9},
    ]
    with pytest.raises(ValueError, match="not a finite number"):
        mc.build_svg(rows)


def test_the_refusal_names_the_rows_at_fault() -> None:
    """A caller with a thousand rows needs to know which ones, not that some are."""
    rows = [
        {"id": "840", "value": float("inf")},
        {"id": "124", "value": 1},
        {"id": "076", "value": float("nan")},
    ]
    with pytest.raises(ValueError) as caught:
        mc.build_svg(rows)
    message = str(caught.value)
    assert "076" in message and "840" in message
    assert "124" not in message, "the rows that are fine must not be blamed"
    # And it teaches the state that already exists for "no value here".
    assert "no-data grey" in message


def test_clean_data_is_untouched_by_either_guard() -> None:
    svg = mc.build_svg([{"id": "840", "value": 5}, {"id": "124", "value": 9}])
    assert "<svg" in svg and "No data in grey" in svg
