"""
A caption says what a plate was drawn from. It cannot say whether it was.

``method``, ``source`` and ``as_of`` are prose, written for a reader, and a
reader has no way to act on them. The question review actually asks of a
published figure -- *is this the picture these inputs produce?* -- needs the
three things the drawing is a function of: the code, the config, and the file
a loader read on the way in. The optional ``provenance`` stamp fingerprints
each, in ``<metadata>``, drawing nothing, so that a mismatch later says
**which one moved** instead of leaving a reviewer to guess.

Three properties carry the whole feature, and each is the opposite of the
easy choice:

*Digests, never the inputs.* An ``areas_of_control`` config carries
coordinates and a ``source`` carries a path that names somebody's machine.
Embedding either would publish it. A digest publishes nothing and still lets
anyone holding the inputs prove the match.

*No clock.* A render time would make two renders of the same inputs differ,
destroying the one property the field exists to record.

*Opt-in.* The stamp carries the package version, so a plate that did not ask
for one has to come out byte-for-byte as it did before -- at this release and
at every release after it.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import importlib.util
import re
import sys
from datetime import date
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


sidecar = _load("_sidecar")
conflict = _load("_conflict")
msm = _load("make_situation_map")
density = _load("make_density")


# --------------------------------------------------------------------------- #
# The config digest                                                            #
# --------------------------------------------------------------------------- #


def test_the_same_config_written_differently_digests_the_same() -> None:
    """Key order is not a fact about a figure, so it must not be in the digest."""
    a = {"region": {"bbox": [1, 2, 3, 4]}, "title": "X", "cities": {"show": False}}
    b = {"cities": {"show": False}, "title": "X", "region": {"bbox": [1, 2, 3, 4]}}
    assert sidecar.config_digest(a) == sidecar.config_digest(b)


def test_a_value_one_level_down_still_moves_the_digest() -> None:
    """A digest that only read the top level would miss almost every real edit."""
    a = {"region": {"bbox": [1, 2, 3, 4]}}
    b = {"region": {"bbox": [1, 2, 3, 5]}}
    assert sidecar.config_digest(a) != sidecar.config_digest(b)


@pytest.mark.parametrize("private", ["_config_dir", "_relief_cache", "_plate"])
def test_what_the_generator_wrote_into_the_config_is_not_part_of_it(private: str) -> None:
    """
    These are outputs of the render, not inputs to it.

    ``_config_dir`` is the directory the YAML happened to sit in; digesting
    it would make the same config on two machines fail to replay itself for
    a reason that has nothing to do with the figure.
    """
    plain = {"region": "Sudan"}
    assert sidecar.config_digest({**plain, private: "anything"}) == sidecar.config_digest(plain)


def test_a_date_in_the_config_is_read() -> None:
    """``as_of`` arrives as a date when it came through ``parse_as_of``."""
    assert sidecar.config_digest({"as_of": date(1995, 7, 1)}) == sidecar.config_digest(
        {"as_of": "1995-07-01"}
    )


def test_a_set_digests_the_same_whichever_order_it_was_built_in() -> None:
    a = {"keys": {"b", "a", "c"}}
    b = {"keys": {"c", "b", "a"}}
    assert sidecar.config_digest(a) == sidecar.config_digest(b)


def test_a_value_the_digest_cannot_read_honestly_is_refused_by_name() -> None:
    """
    ``default=str`` would be the one-liner here, and it collides on purpose.

    A numpy array's ``str`` elides its middle with ``...``, so two different
    arrays stringify identically and two different configs would then digest
    identically -- a fingerprint reporting a match for two different
    pictures. Refusing is the only honest outcome.
    """

    class Opaque:
        pass

    with pytest.raises(TypeError, match="Opaque"):
        sidecar.config_digest({"thing": Opaque()})


def test_the_refusal_says_what_to_do_about_it() -> None:
    with pytest.raises(TypeError, match="Convert it before rendering"):
        sidecar.config_digest({"thing": object()})


# --------------------------------------------------------------------------- #
# The file fingerprint                                                         #
# --------------------------------------------------------------------------- #


def _csv(path: Path, rows: list[list[str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_date", "event_type", "latitude", "longitude", "geo_precision"])
        writer.writerows(rows)
    return path


_ROWS = [
    ["2024-03-01", "Battles", "12.5", "30.5", "1"],
    ["2024-03-02", "Protests", "13.0", "31.0", "2"],
]


def test_a_fingerprint_names_the_file_and_never_the_directory(tmp_path: Path) -> None:
    """
    A full path names a machine, sometimes a user, occasionally an operation.

    None of that belongs in a figure that gets published, and the digest
    already identifies the file to anyone holding it -- which is the only
    identification a reviewer can check anyway.
    """
    record = sidecar.file_fingerprint(_csv(tmp_path / "deep" / "sub" / "acled.csv", _ROWS))
    assert record["name"] == "acled.csv"
    assert str(tmp_path) not in str(record)
    assert len(record["sha256"]) == 64


def test_the_same_bytes_in_two_places_fingerprint_the_same(tmp_path: Path) -> None:
    here = sidecar.file_fingerprint(_csv(tmp_path / "a" / "acled.csv", _ROWS))
    there = sidecar.file_fingerprint(_csv(tmp_path / "b" / "acled.csv", _ROWS))
    assert here == there


def test_one_changed_row_changes_the_fingerprint(tmp_path: Path) -> None:
    first = sidecar.file_fingerprint(_csv(tmp_path / "a.csv", _ROWS))
    second = sidecar.file_fingerprint(
        _csv(tmp_path / "b.csv", [_ROWS[0], ["2024-03-02", "Protests", "13.0", "31.5", "2"]])
    )
    assert first["sha256"] != second["sha256"]


# --------------------------------------------------------------------------- #
# The stamp on the plate                                                       #
# --------------------------------------------------------------------------- #


def _cfg(**over: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "title": "Plate under test",
        "region": {"bbox": [29.0, 11.0, 33.0, 15.0]},
        "canvas_width": 700,
        # Terrain is irrelevant here and costs minutes; off so these run in
        # seconds, as every other situation-map test in this repo does.
        "basemap": {"relief": False},
        "cities": {"show": False},
    }
    cfg.update(over)
    return cfg


def test_a_plate_that_did_not_ask_for_a_stamp_has_none() -> None:
    """The default, and the one every config written before this release used."""
    assert "<metadata" not in msm.build_map(_cfg())


def test_the_stamp_is_the_only_difference_it_makes() -> None:
    """
    Switching it on must not move a single drawn unit.

    Byte-for-byte, with the stamp excised: anything else would mean the
    record of how a plate was drawn had changed the plate.
    """
    plain = msm.build_map(_cfg())
    stamped = msm.build_map(_cfg(provenance=True))
    found = re.search(r"<metadata\b.*?(?:/>|</metadata>)", stamped, re.S)
    assert found, "the plate asked for a stamp and did not get one"
    assert stamped.replace(found.group(0), "") == plain


def test_two_renders_of_one_config_stamp_identically() -> None:
    """
    No clock in the stamp.

    A render time would be the obvious thing to record and would destroy the
    property the field exists to record: two renders of the same inputs would
    differ, and a reviewer comparing them would be told they do not match.
    """
    assert msm.build_map(_cfg(provenance=True)) == msm.build_map(_cfg(provenance=True))


def test_the_stamp_carries_the_running_version() -> None:
    stamp = sidecar.plate_provenance(msm.build_map(_cfg(provenance=True)))
    from sprezzature_maps import __version__

    assert stamp["generator"] == "sprezzature-maps"
    assert stamp["version"] == __version__


def test_an_unstamped_plate_reads_back_as_nothing_rather_than_as_something() -> None:
    assert sidecar.plate_provenance(msm.build_map(_cfg())) == {}


@pytest.mark.parametrize("bad", ["yes", 1, [], "true"])
def test_an_unreadable_provenance_value_is_refused(bad: Any) -> None:
    """
    ``provenance: "true"`` out of hand-written YAML is the realistic typo.

    Taking it as truthy would stamp; taking it as a mapping would crash
    somewhere further down. Saying what to write instead is the only answer
    that helps.
    """
    with pytest.raises(ValueError, match="write true, false, or a mapping"):
        sidecar.provenance_metadata({"provenance": bad})


def test_a_provenance_key_the_generator_never_reads_is_refused() -> None:
    with pytest.raises(ValueError, match="Known provenance keys: inputs"):
        sidecar.provenance_metadata({"provenance": {"input": ["x.csv"]}})


def test_all_three_generators_can_stamp(tmp_path: Path) -> None:
    """One feature, not three: the same reader has to work on every plate."""
    plates = [
        msm.build_map(_cfg(provenance=True)),
        density.build_svg(provenance=True),
        _load("make_choropleth").build_svg(provenance=True),
    ]
    for plate in plates:
        stamp = sidecar.plate_provenance(plate)
        assert stamp["generator"] == "sprezzature-maps"
        assert len(stamp["config_sha256"]) == 64


def test_a_keyword_generator_replays_by_re_rendering() -> None:
    """
    `choropleth` and `density` take keywords, not a config dict.

    What gets digested there is the whole call, defaults included, so the
    check a reviewer performs on one of those plates is to render again and
    compare the two stamps rather than to hand-build the dict
    ``replay_report`` would want.
    """
    first = sidecar.plate_provenance(density.build_svg(provenance=True, title="A"))
    again = sidecar.plate_provenance(density.build_svg(provenance=True, title="A"))
    other = sidecar.plate_provenance(density.build_svg(provenance=True, title="A", bins=60))
    assert first["config_sha256"] == again["config_sha256"]
    assert first["config_sha256"] != other["config_sha256"]


def test_a_large_input_is_not_read_whole_into_memory(tmp_path: Path) -> None:
    """
    An ACLED export runs to hundreds of megabytes; the digest is 64 characters.

    Checked against the answer ``read_bytes`` would have given, so the
    chunking cannot drift from the thing it replaced.
    """
    import hashlib

    blob = b"event_date,latitude\n" * 200_000
    big = tmp_path / "big.csv"
    big.write_bytes(blob)
    record = sidecar.file_fingerprint(big)
    assert record["sha256"] == hashlib.sha256(blob).hexdigest()
    assert record["bytes"] == len(blob)


def test_a_filename_with_a_quote_in_it_does_not_truncate_the_record(
    tmp_path: Path,
) -> None:
    """
    An unescaped ``"`` would close the attribute and silently shorten the stamp.

    Silently is the part that matters: the plate would still render, still
    carry a stamp, and record a different file from the one it read.
    """
    odd = _csv(tmp_path / 'a"b.csv', _ROWS)
    stamp = sidecar.plate_provenance(
        "<svg>" + sidecar.provenance_metadata({"provenance": {"inputs": [str(odd)]}}) + "</svg>"
    )
    assert [rec["name"] for rec in stamp["inputs"]] == ['a"b.csv']


# --------------------------------------------------------------------------- #
# The loader knows the file nothing downstream can recover                     #
# --------------------------------------------------------------------------- #


def test_rows_in_memory_record_no_file() -> None:
    """
    They have no bytes anyone else can re-hash.

    Inventing a name for them would put something in a published figure that
    cannot be checked, which is worse than recording nothing.
    """
    fragment = conflict.acled_events(
        [
            {
                "event_date": "2024-03-01",
                "latitude": "12.5",
                "longitude": "30.5",
                "event_type": "Battles",
                "geo_precision": "1",
            }
        ]
    )
    assert "_source_file" not in fragment


def test_a_loader_reading_a_file_records_it(tmp_path: Path) -> None:
    source = _csv(tmp_path / "acled.csv", _ROWS)
    fragment = conflict.acled_events(str(source))
    assert fragment["_source_file"] == sidecar.file_fingerprint(source)


def test_the_loader_does_not_switch_the_stamp_on_by_itself(tmp_path: Path) -> None:
    """
    Opt-in has to survive the loader, or it is not opt-in.

    The stamp carries the package version. A loader that turned it on would
    make every plate drawn from a CSV change bytes at every release, which is
    exactly what the default exists to prevent.
    """
    cfg = _cfg()
    cfg.update(conflict.acled_events(str(_csv(tmp_path / "acled.csv", _ROWS))))
    assert "<metadata" not in msm.build_map(cfg)


def test_switching_it_on_picks_the_loader_s_file_up_without_naming_it(
    tmp_path: Path,
) -> None:
    """
    By the time ``build_map`` sees the config, the events are inline and the
    file is gone. The config's own digest proves the plate matches the
    config; only the loader can say which export the config came from.
    """
    cfg = _cfg(provenance=True)
    cfg.update(conflict.acled_events(str(_csv(tmp_path / "acled.csv", _ROWS))))
    stamp = sidecar.plate_provenance(msm.build_map(cfg))
    assert [rec["name"] for rec in stamp["inputs"]] == ["acled.csv"]


def test_provenance_false_wins_over_the_loader(tmp_path: Path) -> None:
    """
    The documented integration is ``cfg.update(loader(...))``, so a fragment
    writing ``provenance`` would overwrite a caller who had already said no.
    """
    cfg = _cfg(provenance=False)
    cfg.update(conflict.acled_events(str(_csv(tmp_path / "acled.csv", _ROWS))))
    assert "<metadata" not in msm.build_map(cfg)


def test_a_sheet_of_panels_carries_one_stamp_and_not_one_per_panel(
    tmp_path: Path,
) -> None:
    """
    A sheet is one figure. Eight panels inheriting the stamp would define
    ``id="provenance"`` eight times and list the one ACLED export eight
    times, and a reader counting inputs would count eight.
    """
    cfg = _cfg(provenance=True, small_multiples={"by": "year"})
    cfg.update(
        conflict.acled_events(
            str(
                _csv(
                    tmp_path / "acled.csv",
                    [
                        ["2023-03-01", "Battles", "12.5", "30.5", "1"],
                        ["2024-03-02", "Protests", "13.0", "31.0", "1"],
                    ],
                )
            )
        )
    )
    sheet = msm.build_map(cfg)
    assert sheet.count('data-generator="sprezzature-maps"') == 1
    assert sheet.count("<provenance-input") == 1


# --------------------------------------------------------------------------- #
# The question a reviewer asks                                                 #
# --------------------------------------------------------------------------- #


def test_the_config_that_drew_it_replays_it() -> None:
    cfg = _cfg(provenance=True)
    report = sidecar.replay_report(msm.build_map(cfg), cfg)
    assert report["replays"] is True
    assert report["differences"] == []


def test_a_changed_config_says_the_config_changed() -> None:
    cfg = _cfg(provenance=True)
    report = sidecar.replay_report(msm.build_map(cfg), _cfg(provenance=True, title="Other"))
    assert report["replays"] is False
    assert len(report["differences"]) == 1
    assert "config differs" in report["differences"][0]


def test_a_different_release_says_so_and_names_both(tmp_path: Path) -> None:
    """
    The code is one of the three things the drawing is a function of.

    A config that matches and a version that does not is the case where the
    picture can legitimately differ, and the reviewer has to be told which.
    """
    cfg = _cfg(provenance=True)
    plate = msm.build_map(cfg).replace('data-version="', 'data-version="0.0.1+', 1)
    report = sidecar.replay_report(plate, cfg)
    assert report["replays"] is False
    assert any("0.0.1+" in line and "is installed" in line for line in report["differences"])


def test_an_input_nobody_supplied_leaves_the_plate_unrefuted_not_reproduced(
    tmp_path: Path,
) -> None:
    """
    The distinction the whole report exists for.

    Nothing in the plate can go looking for the file -- it kept a basename
    and a digest, never a directory -- so a caller who hands over nothing has
    checked nothing, and a report saying ``replays: True`` would tell them
    the opposite of what is known.
    """
    cfg = _cfg(provenance=True)
    cfg.update(conflict.acled_events(str(_csv(tmp_path / "acled.csv", _ROWS))))
    report = sidecar.replay_report(msm.build_map(cfg), cfg)
    assert report["replays"] is False
    assert report["unchecked"] == ["acled.csv"]
    assert report["differences"] == []


def test_handing_the_file_over_settles_it(tmp_path: Path) -> None:
    source = _csv(tmp_path / "acled.csv", _ROWS)
    cfg = _cfg(provenance=True)
    cfg.update(conflict.acled_events(str(source)))
    report = sidecar.replay_report(msm.build_map(cfg), cfg, [source])
    assert report["replays"] is True
    assert report["unchecked"] == []


def test_the_same_name_with_other_bytes_is_named(tmp_path: Path) -> None:
    """The realistic failure: a re-exported CSV, same filename, more rows."""
    source = _csv(tmp_path / "acled.csv", _ROWS)
    cfg = _cfg(provenance=True)
    cfg.update(conflict.acled_events(str(source)))
    plate = msm.build_map(cfg)
    _csv(tmp_path / "acled.csv", [*_ROWS, ["2024-03-03", "Riots", "12.0", "30.0", "1"]])
    report = sidecar.replay_report(plate, cfg, [source])
    assert report["replays"] is False
    assert any(line.startswith("acled.csv differs") for line in report["differences"])


def test_a_file_the_plate_never_read_is_named_too(tmp_path: Path) -> None:
    """
    Offering it is an assertion about the figure, and it is not true of it.

    The usual cause is handing over the wrong export, which is precisely the
    mistake a silent pass would let through.
    """
    cfg = _cfg(provenance=True)
    other = _csv(tmp_path / "ucdp.csv", _ROWS)
    report = sidecar.replay_report(msm.build_map(cfg), cfg, [other])
    assert report["replays"] is False
    assert "ucdp.csv was not an input to this plate" in report["differences"]


def test_a_plate_with_no_stamp_is_refused_rather_than_passed() -> None:
    """
    ``replays: True`` for a plate that recorded nothing would be the one
    answer a caller must never get: the opposite of what is known.
    """
    with pytest.raises(ValueError, match="no provenance stamp"):
        sidecar.replay_report(msm.build_map(_cfg()), _cfg())


def test_the_refusal_says_how_to_get_one() -> None:
    with pytest.raises(ValueError, match="provenance: true"):
        sidecar.replay_report("<svg></svg>", {})
