"""
The editorial annotation layer: numbered marks, measured placement, a detail area.

A control plate shows an assessment. A plate that runs beside an article
has to do something else as well — it has to carry the argument's own
marks, so a reader's eye moves between a numbered paragraph and a
numbered badge. The New York Times desk's own term for that work is the
annotation layer, and Amanda Cox's line about it is the whole brief:
"otherwise it's a case of here it is, you go figure it out".

This package had the layer and used it on none of its fourteen plates.
What it did not have is in ``references/situation-map-annotation.md``,
with the examples each item came from. Three of them are tested here.

**The numbered callout.** The map's half of a reference whose other half
is a paragraph. Two things make it more than decoration: the numbers run
1..n, because a plate showing 1, 2 and 4 sends a reader hunting for a 3
that was cut from the prose; and they are readable back out of the
finished plate, so the page's list is generated from the artefact that
drew the map rather than typed again beside it.

**Measured placement.** ``annotations`` was the only text layer in the
generator that never consulted the ink ledger: a note went where the
``place`` key said, and a hand that guessed wrong set a sentence through
a toponym — at its most visible, because the note is drawn above every
map layer. ``place: auto`` asks the ledger instead.

**The detail area.** A labelled rectangle around the ground the piece is
about, so the plate can stay wide enough to place itself and still say
where the story is.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from _plates import plate

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")
sidecar = _load_script("_sidecar")

#: A quiet plate with room on every side of the annotated point, so a
#: placement that moves has moved for a reason the test put there.
_BBOX = [29.0, 45.5, 40.5, 51.0]


def _config(**extra: object) -> dict:
    return {
        "title": "Annotation",
        "region": {"bbox": list(_BBOX)},
        "canvas_width": 1100,
        "basemap": {"relief": False},
        **extra,
    }


def _viewport(cfg: dict) -> tuple:
    proj = msm.build_projection(cfg["region"]["bbox"], "auto")
    vp = msm.make_viewport(proj, cfg["region"]["bbox"], float(cfg["canvas_width"]), 30.0)
    vp.setdefault("ink", [])
    return proj, vp


def _leader(markup: str) -> tuple[float, float]:
    """Return one leader line's (dx, dy), rounded to the unit."""
    x1, y1, x2, y2 = (
        float(v)
        for v in re.search(
            r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', markup
        ).groups()
    )
    return round(x2 - x1), round(y2 - y1)


# ── the numbered callout ─────────────────────────────────────────────────


def test_the_numbered_list_comes_back_out_of_the_plate() -> None:
    """The one half of "accompanying an article" a generator can guarantee.

    The map's badge and the article's paragraph are two halves of one
    reference, and nothing but a shared source stops them drifting: a
    note cut from the prose leaves its badge behind, and a renumbered
    badge leaves the prose pointing somewhere else. Read back out of the
    finished SVG, the plate *is* the shared source.
    """
    cfg = _config(
        annotations=[
            {"at": [37.0, 48.1], "number": 2, "text": "The second thing."},
            {"at": [33.5, 46.6], "number": 1, "text": "The first thing."},
        ]
    )
    card = sidecar.article_sidecar(plate(cfg))
    assert [c["number"] for c in card["callouts"]] == [1, 2]
    assert [c["text"] for c in card["callouts"]] == ["The first thing.", "The second thing."]
    # The coordinates come back too, so a page can place the badge's twin
    # in a photo caption or an interactive without re-reading the config.
    assert card["callouts"][0]["lon"] == pytest.approx(33.5)


def test_a_number_the_article_cannot_follow_is_refused() -> None:
    """1, 2 and 4 is a reader hunting the map for a 3 nobody drew.

    The realistic cause is editorial rather than typographic: a note gets
    cut from the article and its number goes with it.
    """
    with pytest.raises(ValueError, match="1..n with no gap"):
        msm._callout_numbers([{"number": 1}, {"number": 2}, {"number": 4}])
    with pytest.raises(ValueError, match="1..n with no gap"):
        msm._callout_numbers([{"number": 1}, {"number": 1}])


def test_the_order_the_notes_are_written_in_is_free() -> None:
    """A config is ordered by geography and an article by argument."""
    assert msm._callout_numbers([{"number": 3}, {"number": 1}, {"number": 2}]) == [3, 1, 2]


def test_a_numbered_mark_needs_no_sentence_beside_it() -> None:
    """The pure form of the device: the badge refers, the article explains.

    A leader drawn to an empty note would be a line pointing at nothing,
    so a numbered mark with no text gets a badge and stops there.
    """
    cfg = _config(annotations=[{"at": [34.0, 48.0], "number": 1}])
    proj, vp = _viewport(cfg)
    markup = msm._annotations_layer(cfg, proj, vp)
    assert 'data-callout="1"' in markup
    assert "<line" not in markup, "a note with no words was given a leader"


def test_every_note_that_has_words_gets_them_drawn() -> None:
    """A note dropped in silence is the quietest way to lose an argument.

    The layer runs in two passes -- marks, then sentences -- and a pass
    that stopped early would leave a plate with all its badges and some
    of its notes, which looks finished.
    """
    notes = [
        {"at": [32.0, 47.0], "number": 1, "text": "First.", "place": "left"},
        {"at": [34.5, 48.3], "number": 2, "text": "Second.", "place": "above"},
        {"at": [37.0, 49.0], "number": 3, "text": "Third.", "place": "right"},
        {"at": [38.5, 46.5], "number": 4},
    ]
    cfg = _config(annotations=notes)
    proj, vp = _viewport(cfg)
    markup = msm._annotations_layer(cfg, proj, vp)
    assert markup.count("<line") == 3, "a note with words was drawn without its leader"
    for said in ("First.", "Second.", "Third."):
        assert f">{said}<" in markup, f"{said!r} never reached the plate"


def test_a_badge_announces_the_note_and_not_only_its_digit() -> None:
    """A reader who arrives by keyboard has only what the badge says."""
    cfg = _config(annotations=[{"at": [34.0, 48.0], "number": 1, "text": "The dam."}])
    proj, vp = _viewport(cfg)
    markup = msm._annotations_layer(cfg, proj, vp)
    assert 'aria-label="Note 1. The dam."' in markup
    assert 'tabindex="0"' in markup


# ── measured placement ───────────────────────────────────────────────────


def test_an_auto_placed_note_steps_around_ink_already_on_the_plate() -> None:
    """The class guard: a note is placed by measurement or not at all.

    Park a long hand-placed name where the note would go, and the note
    has to be somewhere else — and, the part that matters, somewhere its
    own box does not touch. Asserting only that the *direction* changed
    would pass for a note that moved and still overlapped.
    """
    note = {"at": [34.5, 48.3], "text": "A note that has to find room.", "place": "auto"}
    clear = _config(annotations=[note])
    blocked = _config(
        annotations=[note],
        labels={"places": [{"lon": 36.4, "lat": 48.3, "text": "AAAAAAAAAAAAAAAAAAAA", "size": 16}]},
    )
    proj, vp = _viewport(clear)
    assert _leader(msm._annotations_layer(clear, proj, vp)) == (29, 0)

    proj, vp = _viewport(blocked)
    before = len(vp["ink"])
    msm._labels_layer(blocked, proj, vp)
    assert len(vp["ink"]) > before, "the blocker never reached the ledger"
    taken = list(vp["ink"])
    msm._annotations_layer(blocked, proj, vp)
    placed = vp["ink"][len(taken):]
    assert placed, "the note left no box in the ledger"
    for box_ in placed:
        for other in taken:
            assert not msm.boxes_overlap(box_, other), (
                f"an auto-placed note landed on ink already on the plate: {box_} vs {other}"
            )


def test_a_note_with_nowhere_to_go_is_refused_rather_than_drawn() -> None:
    """An annotation over a place name is worse than no annotation.

    Drawing it in the least-bad direction would be the generator deciding
    which name to spoil. The author is told, and can shorten the note,
    move its point, or overrule the measurement with an explicit place.
    """
    cfg = _config(annotations=[{"at": [34.5, 48.3], "text": "Nowhere to go.", "place": "auto"}])
    proj, vp = _viewport(cfg)
    # Every square unit of the plate already inked. Stated as one box
    # rather than built out of eight blocking names: the assertion is
    # about what the measurement does when it finds no room, and a test
    # that first has to arrange no room out of font metrics is testing
    # the font metrics.
    vp["ink"] = [(0.0, 0.0, float(vp["width"]), float(vp["height"]))]
    with pytest.raises(ValueError, match="not one of the 8 directions clears"):
        msm._annotations_layer(cfg, proj, vp)


def test_every_leader_lies_on_a_right_angle_or_a_diagonal() -> None:
    """Datawrapper's rule, after Beck: 90 or 45 degrees, never 89.

    And every leader the same length, so eight notes around one point
    read as a ring of notes rather than a star with long arms.
    """
    lengths = set()
    for place in msm._ANNOTATION_PLACES:
        cfg = _config(annotations=[{"at": [34.5, 48.3], "text": "Note.", "place": place}])
        proj, vp = _viewport(cfg)
        dx, dy = _leader(msm._annotations_layer(cfg, proj, vp))
        assert dx == 0 or dy == 0 or abs(abs(dx) - abs(dy)) <= 1, (
            f"{place} draws a leader at neither 90 nor 45 degrees: {(dx, dy)}"
        )
        lengths.add(round((dx * dx + dy * dy) ** 0.5))
    # One unit of slop: the markup rounds every coordinate to a tenth,
    # and a diagonal pays that twice.
    assert max(lengths) - min(lengths) <= 1, (
        f"the eight leaders are not one length: {sorted(lengths)}"
    )


def test_an_explicit_place_is_not_second_guessed() -> None:
    """A direction the author named is the author's argument.

    The same standing a hand-placed name has, and the reason the
    measurement is opt-in rather than the default: an editor who has
    looked at the plate knows something the ledger does not.
    """
    cfg = _config(
        annotations=[{"at": [34.5, 48.3], "text": "Set here on purpose.", "place": "left"}],
        labels={"places": [{"lon": 32.6, "lat": 48.3, "text": "AAAAAAAAAAAAAAAA", "size": 16}]},
    )
    proj, vp = _viewport(cfg)
    msm._labels_layer(cfg, proj, vp)
    dx, dy = _leader(msm._annotations_layer(cfg, proj, vp))
    assert (dx, dy) == (-29, 0)


def test_a_place_the_generator_cannot_draw_is_refused() -> None:
    """``place: above_right`` drew to the right and said nothing.

    Any unknown value fell through the lookup to the default, so a typo
    in a direction was a note set somewhere the author did not ask for.
    """
    cfg = _config(annotations=[{"at": [34.5, 48.3], "text": "Note.", "place": "above_right"}])
    proj, vp = _viewport(cfg)
    with pytest.raises(ValueError, match="place: 'above_right'"):
        msm._annotations_layer(cfg, proj, vp)


def test_a_note_is_placed_against_every_mark_and_not_only_the_earlier_ones() -> None:
    """Found by rendering, which is the only way this one shows up.

    The notes used to be placed one at a time: note 1 took the paper to
    its right, which was free when it was asked, and note 2's badge then
    landed in the middle of a word. Both notes were placed correctly
    against a plate that was not finished. Every mark is down before any
    sentence is.
    """
    cfg = _config(
        annotations=[
            {"at": [34.0, 48.3], "number": 1, "text": "The first note, set to its right.",
             "place": "auto"},
            # Close enough to the east that the first note's text would
            # have been drawn straight through this badge.
            {"at": [35.6, 48.3], "number": 2, "text": "The second.", "place": "auto"},
        ]
    )
    proj, vp = _viewport(cfg)
    markup = msm._annotations_layer(cfg, proj, vp)
    badges = [
        (float(cx), float(cy))
        for cx, cy in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="#', markup)
    ]
    assert len(badges) == 2
    r = msm._CALLOUT_BADGE_R * vp["ts"]
    for bx, by in badges:
        badge_box = (bx - r, by - r, bx + r, by + r)
        for box_ in vp["ink"]:
            # The badge's own entry, which the markup rounds to a tenth
            # and the ledger does not.
            if abs(box_[0] - badge_box[0]) < 0.2 and abs(box_[1] - badge_box[1]) < 0.2:
                continue
            assert not msm.boxes_overlap(badge_box, box_), (
                f"a badge at {(bx, by)} sits on ink at {box_}"
            )


# ── the detail area ──────────────────────────────────────────────────────


def test_the_rectangle_surrounds_the_ground_it_names() -> None:
    """Both diagonal corners through the projection, not degrees scaled.

    Under a conic a box of degrees is not a box of plate units, and the
    rectangle has to end up around the ground the bbox names.
    """
    cfg = _config(detail_area={"bbox": [33.0, 47.0, 36.0, 49.0]})
    proj, vp = _viewport(cfg)
    markup = msm._detail_area_layer(cfg, proj, vp)
    x, y, w, h = (
        float(v)
        for v in re.search(
            r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', markup
        ).groups()
    )
    for lon, lat in ((33.0, 47.0), (36.0, 49.0), (33.0, 49.0), (36.0, 47.0)):
        px, py = vp["to_svg"](*proj.transform(lon, lat))
        assert x - 0.1 <= px <= x + w + 0.1 and y - 0.1 <= py <= y + h + 0.1, (lon, lat)


def test_a_label_with_no_room_above_it_goes_below() -> None:
    """A box near the top of the plate has no paper over it.

    A label that silently went missing there is the failure the whole
    ledger exists to stop, so the other side is tried before anything is
    given up.
    """
    cfg = _config(detail_area={"bbox": [33.0, 47.0, 36.0, 49.0], "label": "Detail area"})
    proj, vp = _viewport(cfg)
    # Ink the band of paper the label would take above the rectangle. On
    # a real plate that band is a river name or a neighbour's capitals;
    # here it is stated outright so the fallback is what is measured.
    top_left = vp["to_svg"](*proj.transform(33.0, 49.0))
    vp["ink"] = [(top_left[0] - 200.0, top_left[1] - 40.0, top_left[0] + 400.0, top_left[1])]
    markup = msm._detail_area_layer(cfg, proj, vp)
    rect_y = float(re.search(r'<rect x="[\d.]+" y="([\d.]+)"', markup).group(1))
    rect_h = float(re.search(r'height="([\d.]+)" rx=', markup).group(1))
    label_y = float(re.search(r'<text[^>]*\by="([\d.]+)"', markup).group(1))
    assert label_y > rect_y + rect_h, "the label stayed above a box with no room above it"


def test_a_rectangle_that_encloses_no_ground_is_refused() -> None:
    cfg = _config(detail_area={"bbox": [36.0, 47.0, 33.0, 49.0]})
    proj, vp = _viewport(cfg)
    with pytest.raises(ValueError, match="encloses no ground"):
        msm._detail_area_layer(cfg, proj, vp)


def test_a_rectangle_needs_four_numbers() -> None:
    cfg = _config(detail_area={"bbox": [33.0, 47.0, 36.0]})
    proj, vp = _viewport(cfg)
    with pytest.raises(ValueError, match="four numbers"):
        msm._detail_area_layer(cfg, proj, vp)


def test_the_label_can_be_turned_off_and_the_box_kept() -> None:
    """A plate whose caption is in the prose still wants the rectangle."""
    cfg = _config(detail_area={"bbox": [33.0, 47.0, 36.0, 49.0], "label": ""})
    proj, vp = _viewport(cfg)
    markup = msm._detail_area_layer(cfg, proj, vp)
    assert "<rect" in markup and "<text" not in markup


# ── the schema ───────────────────────────────────────────────────────────


def test_both_new_sections_are_options_the_validator_accepts() -> None:
    """An option the validator rejects is an option nobody can set."""
    msm.validate_config(
        _config(
            detail_area={"bbox": [33.0, 47.0, 36.0, 49.0]},
            annotations=[{"at": [34.0, 48.0], "number": 1, "text": "x", "place": "auto"}],
        )
    )


def test_a_typo_one_level_down_is_refused() -> None:
    with pytest.raises(ValueError, match="bbbox"):
        msm.validate_config(_config(detail_area={"bbbox": [33.0, 47.0, 36.0, 49.0]}))


def test_an_annotation_key_nothing_reads_is_refused() -> None:
    cfg = _config(annotations=[{"at": [34.0, 48.0], "text": "x", "numbre": 1}])
    proj, vp = _viewport(cfg)
    with pytest.raises(ValueError, match="numbre"):
        msm._annotations_layer(cfg, proj, vp)


def test_the_example_plate_uses_every_device() -> None:
    """The gap this work exists to close, held shut.

    The annotation layer was written, documented, validated -- and called
    by none of the fourteen bundled plates, which is this repository's
    dominant failure mode: the tool exists and nothing calls it. A
    capability nobody switches on is a capability the package does not
    have, so one shipped plate has to use all three.
    """
    builders = _load_script("build_situation_examples").BUILDERS
    cfg = builders["dnieper"]()
    assert cfg.get("detail_area", {}).get("bbox"), "the example plate declares no detail area"
    notes = cfg.get("annotations") or []
    assert [n.get("number") for n in notes] == [1, 2, 3, 4]
    assert all(n.get("place") == "auto" for n in notes), (
        "the example plate hand-places its notes, so it demonstrates nothing"
    )


def test_the_example_plate_hands_an_article_its_numbered_list() -> None:
    """End to end: the page's prose is generated from the plate.

    Not from the config. A config is what somebody meant; the plate is
    what was drawn, and the drift this guards against happens between
    the two.
    """
    builders = _load_script("build_situation_examples").BUILDERS
    svg = plate(builders["dnieper"]())
    callouts = sidecar.article_sidecar(svg)["callouts"]
    assert [c["number"] for c in callouts] == [1, 2, 3, 4]
    assert all(c["text"] for c in callouts)
    assert "Kherson" in callouts[0]["text"]


def test_the_reference_document_is_in_the_repository() -> None:
    """The study the devices were chosen from, kept where it can be read.

    A design decision argued in a commit message is a decision nobody
    finds. These three were chosen against named examples, and the
    examples are what makes them arguable rather than taste.
    """
    doc = Path(__file__).resolve().parent.parent / "references" / "situation-map-annotation.md"
    text = doc.read_text(encoding="utf-8")
    for named in ("Mosul", "Westerveld", "Cheshire", "Tim Wallace", "Datawrapper"):
        assert named in text, f"the study names no {named} example"
    assert "detail_area" in text and "place: auto" in text
