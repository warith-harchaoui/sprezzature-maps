"""
A plate built for a 90 mm column came out of ``--out plate.pdf`` 333 mm wide.

Nothing here had a single test. ``print_width`` shipped, the export path
shipped, and the two had never met: the rasteriser refuses a document whose
root is measured in millimetres -- *"SVG has an invalid size"*, on a
one-rectangle document as readily as on a plate -- so a plate built for a
journal could be written as ``.svg`` and **crashed** as ``.png``. Past that,
Pillow laid the PDF page out at the pixel count over 72 dpi, so asking for
90 mm got a 333 mm page: the exact opposite of what asking for a print width
means, in the one output format that can carry the intent rather than merely
record it.

And the page was a picture of the plate. Every journal that asks for PDF or
EPS is asking for vector; a PNG in a PDF wrapper satisfies the extension and
nothing else.

Three converters were measured against this project's own plates before one
was chosen, and the measuring is in here with them, because choosing an
engine by looking at a render once is an anecdote and an anecdote keeps being
true only until somebody upgrades something.

``cairosvg`` -- on the same cairo build librsvg uses, so this is its SVG
parser and not the renderer underneath -- **ignores ``paint-order``**. Every
place name on a plate is one ``<text>`` carrying a fat white halo and
``paint-order="stroke"`` to put the halo under the glyph; read in document
order instead, the halo paints over the glyph and the map comes back with its
toponyms erased. Headless Chromium printed the plate's interactive layer
panel into the figure and fell back to Times for part of the type.
``rsvg-convert`` got page size, typography and layers all right, so it is the
one the writer looks for -- and when it is absent the page is still written,
still at the right physical size, and says in a warning that it is a raster.

The canary at the foot of this file is that reasoning turned into a check,
and it ships with its own negative control: the same canary with
``paint-order`` removed, which the house rasteriser draws blank, so the
sensitivity of the measurement is demonstrated rather than asserted.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _plates import plate  # noqa: E402


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


render = _load("_render")
msm = _load("make_situation_map")

#: True when the optional vector renderer is installed here.
HAS_RSVG = shutil.which(render._VECTOR_RENDERER) is not None

needs_rsvg = pytest.mark.skipif(not HAS_RSVG, reason=f"{render._VECTOR_RENDERER} is not installed")

needs_poppler = pytest.mark.skipif(
    shutil.which("pdftoppm") is None, reason="poppler's pdftoppm is not installed"
)


def _plate(**over: Any) -> str:
    cfg: dict[str, Any] = {
        "title": "Format under test",
        "region": {"bbox": [29.0, 11.0, 33.5, 15.5]},
        "canvas_width": 900,
        # Terrain is a raster by nature and irrelevant to every question here,
        # and it costs minutes.
        "basemap": {"relief": False},
        "cities": {"show": False},
        "areas_of_control": {"palette": {"RSF": "#c0392b", "SAF": "#2f5d92"}},
    }
    cfg.update(over)
    # A screen-width plate at 90 mm warns about its own type size, which is
    # the feature working and is not what any of these tests are about.
    with pytest.warns(RuntimeWarning, match="smallest label"):
        return str(msm.build_map(cfg))


def _write(svg: str, out: Path) -> Path:
    return Path(render.write_svg(out, svg))


def _page_mm(pdf: Path) -> tuple[float, float]:
    """The page size a reader would get, in millimetres."""
    pypdf = pytest.importorskip("pypdf")
    box = pypdf.PdfReader(str(pdf)).pages[0].mediabox
    return float(box.width) / 72 * 25.4, float(box.height) / 72 * 25.4


def _page_content(pdf: Path) -> tuple[int, int]:
    """Return ``(bytes of drawing operators, raster images)`` on page one.

    The discriminator the whole feature turns on. A vector page keeps its
    drawing in a form XObject -- tens of kilobytes of path operators -- and
    rasterises only what genuinely is a raster. The fallback page is one
    image and nothing else.
    """
    pypdf = pytest.importorskip("pypdf")
    page = pypdf.PdfReader(str(pdf)).pages[0]
    xobjects = page["/Resources"].get("/XObject", {})
    drawn, images = 0, 0
    for ref in xobjects.values():
        obj = ref.get_object()
        if obj.get("/Subtype") == "/Image":
            images += 1
            continue
        drawn += len(obj.get_data())
        for inner in obj.get("/Resources", {}).get("/XObject", {}).values():
            if inner.get_object().get("/Subtype") == "/Image":
                images += 1
    return drawn, images


# --------------------------------------------------------------------------- #
# The crash: two shipped features that had never met                           #
# --------------------------------------------------------------------------- #


def test_a_plate_built_for_a_column_can_still_be_rasterised(tmp_path: Path) -> None:
    """
    This raised ``SVG has an invalid size`` and wrote nothing.

    The rasteriser will not read a root measured in millimetres, so the one
    kind of plate most likely to be exported -- the one built for a page --
    was the one kind that could not be.
    """
    out = _write(_plate(print_width="90mm"), tmp_path / "plate.png")
    assert out.stat().st_size > 0


def test_the_svg_keeps_the_physical_size_it_was_built_with(tmp_path: Path) -> None:
    """
    The substitution happens on the way into the rasteriser and nowhere else.

    A ``.svg`` is the format where the physical size is the whole point: it
    is what makes the file land at 90 mm in InDesign.
    """
    out = _write(_plate(print_width="90mm"), tmp_path / "plate.svg")
    head = out.read_text(encoding="utf-8")[:400]
    assert 'width="90mm"' in head


def test_the_raster_is_sized_by_the_drawing_and_not_by_the_millimetres(
    tmp_path: Path,
) -> None:
    """A plate is the same picture whether or not it declares a print size."""
    png = pytest.importorskip("PIL.Image")
    plain = _write(str(plate(_cfg_plain())), tmp_path / "a.png")
    sized = _write(_plate(print_width="90mm"), tmp_path / "b.png")
    assert png.open(plain).size == png.open(sized).size


def _cfg_plain() -> dict[str, Any]:
    return {
        "title": "Format under test",
        "region": {"bbox": [29.0, 11.0, 33.5, 15.5]},
        "canvas_width": 900,
        "basemap": {"relief": False},
        "cities": {"show": False},
        "areas_of_control": {"palette": {"RSF": "#c0392b", "SAF": "#2f5d92"}},
    }


@pytest.mark.parametrize(
    ("declared", "expected_mm"),
    [("90mm", 90.0), ("180mm", 180.0), ("9cm", 90.0), ("3.5in", 88.9)],
)
def test_the_page_is_the_width_the_plate_asked_to_print_at(
    tmp_path: Path, declared: str, expected_mm: float
) -> None:
    """
    A PDF has a page size, so it is the format that can carry the intent.

    Pillow's default of 72 dpi made every one of these 333 mm, which is not a
    rounding error -- it is a different figure.
    """
    out = _write(_plate(print_width=declared), tmp_path / "plate.pdf")
    assert _page_mm(out)[0] == pytest.approx(expected_mm, abs=0.2)


def test_a_plate_with_no_print_width_keeps_the_page_it_always_had(
    tmp_path: Path,
) -> None:
    """Nothing changes for a plate that never claimed to be going to a page."""
    out = _write(str(plate(_cfg_plain())), tmp_path / "plate.pdf")
    assert _page_mm(out)[0] > 200.0


# --------------------------------------------------------------------------- #
# Vector, or an honest raster                                                  #
# --------------------------------------------------------------------------- #


@needs_rsvg
def test_a_pdf_is_a_drawing_and_not_a_picture_of_one(tmp_path: Path) -> None:
    out = _write(_plate(print_width="90mm"), tmp_path / "plate.pdf")
    drawn, _images = _page_content(out)
    assert drawn > 10_000, f"only {drawn} bytes of drawing on the page"


@needs_rsvg
def test_an_eps_is_postscript_and_not_a_wrapped_bitmap(tmp_path: Path) -> None:
    """Elsevier and Science still ask for EPS; the header is what they read."""
    out = _write(_plate(print_width="90mm"), tmp_path / "plate.eps")
    assert out.read_bytes()[:14] == b"%!PS-Adobe-3.0"
    # A rasterised EPS of this plate is megabytes; a drawn one is tens of KB.
    assert out.stat().st_size < 1_000_000


@pytest.mark.parametrize("suffix", [".pdf", ".eps"])
def test_without_the_renderer_the_page_says_it_is_a_raster(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    """
    Silence here would be the whole defect, restored.

    A raster page satisfies the extension and nothing a journal wants, and it
    is indistinguishable from a vector one until somebody zooms in -- by which
    point the figure is in review.
    """
    real = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name, *a, **k: None if name == render._VECTOR_RENDERER else real(name),
    )
    with pytest.warns(RuntimeWarning, match="raster page"):
        out = _write(_plate(print_width="90mm"), tmp_path / f"plate{suffix}")
    assert out.stat().st_size > 0


def test_the_warning_names_what_to_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A complaint nobody can act on changes nothing."""
    real = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name, *a, **k: None if name == render._VECTOR_RENDERER else real(name),
    )
    with pytest.warns(RuntimeWarning) as caught:
        _write(_plate(print_width="90mm"), tmp_path / "plate.pdf")
    said = [str(w.message) for w in caught]
    assert any(render._VECTOR_RENDERER in line and "librsvg" in line for line in said)


def test_the_fallback_page_is_still_the_right_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    The honest raster is still a 90 mm raster.

    Degrading is not the same as giving up: a reviewer who cannot install
    librsvg should still get a figure that drops into the column.
    """
    real = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name, *a, **k: None if name == render._VECTOR_RENDERER else real(name),
    )
    with pytest.warns(RuntimeWarning):
        out = _write(_plate(print_width="90mm"), tmp_path / "plate.pdf")
    assert _page_mm(out)[0] == pytest.approx(90.0, abs=0.2)
    drawn, images = _page_content(out)
    assert (drawn, images) == (0, 1), "the fallback should be one image and no drawing"


# --------------------------------------------------------------------------- #
# Everything the refactor could have broken on its way past                    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".html", ".svg", ".txt"])
def test_every_other_extension_still_writes_what_it_always_did(tmp_path: Path, suffix: str) -> None:
    out = _write(str(plate(_cfg_plain())), tmp_path / f"plate{suffix}")
    assert out.stat().st_size > 0


def test_an_unknown_extension_writes_the_svg_rather_than_guessing(
    tmp_path: Path,
) -> None:
    """A mislabelled binary is worse than a correctly-labelled surprise."""
    out = _write(str(plate(_cfg_plain())), tmp_path / "plate.json")
    assert out.read_text(encoding="utf-8").startswith("<svg")


@pytest.mark.parametrize(
    ("root", "expected"),
    [
        ('<svg viewBox="0 0 100 50" width="90mm" height="45mm"/>', "100"),
        ('<svg viewBox="0 0 100 50" width="9cm" height="4.5cm"/>', "100"),
        ('<svg viewBox="0 0 100 50" width="100" height="50"/>', "100"),
    ],
)
def test_a_physical_root_is_swapped_for_the_coordinate_system(root: str, expected: str) -> None:
    out = render._size_in_pixels(root)
    assert re.search(r'width="([\d.]+)"', out).group(1) == expected  # type: ignore[union-attr]
    assert "mm" not in out and "cm" not in out


# --------------------------------------------------------------------------- #
# The canary: does the page still have the map's words on it?                  #
# --------------------------------------------------------------------------- #

#: Exactly how a plate draws a place name: one ``<text>``, a fat white halo,
#: and ``paint-order="stroke"`` so the halo goes *under* the glyph.
#:
#: Written out here rather than lifted from a rendered plate, because what is
#: under test is this construct and nothing else. A converter that reads the
#: attribute draws dark letters on cream; one that ignores it paints the
#: 7.3-unit white stroke over a 26-unit glyph and leaves the page blank.
_HALO_CANARY = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" '
    'width="400" height="120">'
    '<rect width="400" height="120" fill="#f7f3e3"/>'
    '<text x="200" y="50" text-anchor="middle" font-family="Roboto, \'Helvetica Neue\', Arial, sans-serif" '
    'font-size="26" font-weight="600" fill="#1a1a1a" paint-order="stroke" '
    'stroke="#ffffff" stroke-width="7.3">AL-UBAYYID</text>'
    '<text x="200" y="95" text-anchor="middle" font-family="Roboto, \'Helvetica Neue\', Arial, sans-serif" '
    'font-size="26" font-weight="600" fill="#1a1a1a" paint-order="stroke" '
    'stroke="#ffffff" stroke-width="7.3">WHITE NILE</text>'
    "</svg>"
)


def _ink(png: bytes) -> float:
    """The fraction of the image that is dark enough to read as a letter."""
    from PIL import Image

    grey = Image.open(io.BytesIO(png)).convert("L")
    pixels = list(grey.getdata())
    return sum(1 for value in pixels if value < 128) / len(pixels)


def _house_ink(svg: str) -> float:
    """What the plate looks like, measured by the rasteriser this project ships."""
    import resvg_py

    return _ink(bytes(resvg_py.svg_to_bytes(svg_string=svg)))


def _fresh(tmp_path: Path, name: str) -> Path:
    """A directory of its own, because ``_pdf_ink`` writes fixed filenames."""
    out = tmp_path / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def _pdf_ink(page: bytes, tmp_path: Path) -> float:
    pdf = tmp_path / "canary.pdf"
    pdf.write_bytes(page)
    subprocess.run(
        ["pdftoppm", "-r", "96", "-png", "-singlefile", str(pdf), str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )
    return _ink((tmp_path / "out.png").read_bytes())


def test_the_canary_would_notice_a_converter_that_ignored_paint_order() -> None:
    """
    The test that tests the test, and it needs nothing installed to run.

    Dropping ``paint-order`` is not a hypothetical: it is precisely what
    ``cairosvg`` does to these plates, and the reason a map came back from it
    with every toponym erased -- a failure invisible at thumbnail size and
    fatal at print size. Reproduced here with the house rasteriser, so the
    sensitivity of the measurement below is demonstrated rather than claimed.
    """
    legible = _house_ink(_HALO_CANARY)
    erased = _house_ink(_HALO_CANARY.replace('paint-order="stroke" ', ""))
    assert legible > 0.02, "the canary has to be legible before it can go missing"
    assert erased < legible * 0.05, (
        f"the halo did not cover the glyphs: {erased:.4f} against {legible:.4f}"
    )


@needs_rsvg
@needs_poppler
def test_the_exported_page_still_carries_the_words(tmp_path: Path) -> None:
    """
    A converter is trusted with every place name on the map. This checks it.

    The engine was chosen by looking at renders, once, on one machine --
    which is an anecdote, and an anecdote is not a mechanism. This is the
    mechanism: export the canary, rasterise what came back, and check the
    words are still on the page.

    It asks the converter about *itself* rather than comparing it to the
    house rasteriser, and that is the whole design. The first version did
    compare the two (``_pdf_ink(...) == approx(_house_ink(...), rel=0.3)``)
    and it was wrong in a way that only showed up off this laptop: the canary
    asked for ``Helvetica, sans-serif``, macOS has Helvetica and Ubuntu does
    not, so on CI librsvg fell back to DejaVu -- wider and heavier -- while
    resvg resolved its own fallback. Same drawing, two font stacks, 39% more
    ink, and a red build about fontconfig rather than about paint-order.

    The canary now names the stack a place name actually uses
    (``make_situation_map._DEFAULT_FONT``) rather than a typeface this project
    never draws with. That does not fix the cross-platform problem on its own
    -- Roboto is no likelier to exist on a runner than Helvetica -- but a
    canary should be drawn the way the thing it stands for is drawn.

    So the measurement is taken twice through the *same* converter, on the
    same machine, with the same fonts: once as the canary is drawn, once with
    ``paint-order`` removed. Whatever font either engine picks cancels out,
    because it is on both sides of the comparison. What cannot cancel out is
    the failure being hunted -- a halo painted over its own glyphs, which is
    exactly what ``cairosvg`` does to these plates and why a map came back
    from it with every toponym erased.
    """
    page = render._vector_bytes(_HALO_CANARY, "pdf")
    assert page is not None
    legible = _pdf_ink(page, _fresh(tmp_path, "legible"))

    blanked = render._vector_bytes(_HALO_CANARY.replace('paint-order="stroke" ', ""), "pdf")
    assert blanked is not None
    erased = _pdf_ink(blanked, _fresh(tmp_path, "erased"))

    assert legible > 0.02, (
        f"the exported page carries almost no ink ({legible:.4f}): the words did "
        "not survive the conversion at all"
    )
    assert erased < legible * 0.05, (
        f"the halo did not cover the glyphs on the exported page: {erased:.4f} "
        f"against {legible:.4f} -- this converter ignores paint-order"
    )


# --------------------------------------------------------------------------- #
# A plate bound for a page does not draw screen shadows                        #
# --------------------------------------------------------------------------- #


def test_a_screen_plate_keeps_every_shadow_it_ever_had() -> None:
    """The default is untouched: a plate that never mentioned print is as it was."""
    assert 'filter="url(#panel-shadow)"' in plate(_cfg_plain())


def test_a_plate_bound_for_a_page_draws_no_filter_at_all() -> None:
    """
    An SVG filter is the one construct a vector exporter cannot express.

    It rasterises the region instead -- and the cost is per *mark*, not per
    plate, because every event marker carries a shadow too.
    """
    assert 'filter="url(#' not in _plate(print_width="90mm")


def test_a_dense_print_plate_exports_without_a_single_raster(tmp_path: Path) -> None:
    """
    The measurement this is here to keep true.

    Before: 120 events at 90 mm came out as a PDF holding 122 embedded
    rasters, one per shadow, at 126 KB. A figure made of bitmap patches,
    inside a format a journal asked for because it is not made of those.
    """
    events = [
        {
            "lon": 29.5 + (n % 20) * 0.2,
            "lat": 11.5 + (n // 20) * 0.2,
            "color": "#c0392b",
            "r": 4,
            "label": f"event {n}",
            "precision": 1,
        }
        for n in range(60)
    ]
    svg = _plate(
        print_width="90mm",
        events=events,
        marker_legend=[{"color": "#c0392b", "label": "Event", "precision": 1}],
    )
    out = _write(svg, tmp_path / "dense.pdf")
    _drawn, images = _page_content(out)
    if HAS_RSVG:
        assert images == 0, f"{images} rasters on a page that should have none"


def test_a_panel_of_a_printed_sheet_is_printed_too() -> None:
    """
    A panel drops ``print_width`` -- the sheet is what has a page size.

    Which is exactly how it would have kept its shadows: eight panels of
    screen chrome inside a figure built for a column.
    """
    events = [
        {
            "lon": 30.0,
            "lat": 12.0,
            "color": "#c0392b",
            "r": 4,
            "label": "a",
            "precision": 1,
            "date": "2023-05-02",
            "time_precision": 1,
        },
        {
            "lon": 31.0,
            "lat": 13.0,
            "color": "#c0392b",
            "r": 4,
            "label": "b",
            "precision": 1,
            "date": "2024-05-02",
            "time_precision": 1,
        },
    ]
    sheet = _plate(
        print_width="180mm",
        events=events,
        marker_legend=[{"color": "#c0392b", "label": "Event", "precision": 1}],
        small_multiples={"by": "year"},
    )
    assert 'filter="url(#' not in sheet
