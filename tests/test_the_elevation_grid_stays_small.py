"""
The elevation cache is the single largest thing this package holds. Keep it so.

A render needs terrain, terrain comes from a vendored global grid, and the
finest tier is **902 million pixels**. How that grid is held decides whether a
test run fits in a CI runner: as float32 it is 3.61 GB, as int16 1.80 GB, and
the old loader briefly held *two* float32 copies at once because it wrote
``cache[path] = raw - OFFSET`` -- a second full array while the first was still
alive. Peak was ~9.5 GB and ``pytest -n 2`` was impossible on a 16 GB runner:
two workers wanted ~19 GB and the second was killed with SIGTERM.

So these are regression tests for a resource, which is unusual and deliberate.
Nothing about the drawing changes if they fail; what changes is whether CI can
run the suite at all, and that failure arrives as an OOM kill with no stack and
no test name -- the least diagnosable red build there is. Better to fail here,
by name.

The int16 choice is exact, not a tolerance: measured across all six tiers the
real range is -430..8625 m, nowhere near int16's +/-32767, and no NoData
sentinel. The round-trip assertion below is what keeps that true if a tier is
ever revendored.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _relief():
    name = "_relief"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: The coarsest tier: 1M pixels, so these tests cost megabytes, not gigabytes.
#: The property under test is the dtype and the arithmetic, and neither varies
#: with tier -- testing against the 902M-pixel one would make the guard itself
#: the memory problem it exists to prevent.
def _small_tier() -> Path:
    rel = _relief()
    for _arcsec, path in reversed(rel._ELEVATION_TIERS):
        if path.is_file():
            return path
    pytest.skip("no vendored elevation tier on disk")


def test_the_cache_holds_int16_not_float32() -> None:
    """float32 doubles the largest allocation in the process, for no precision."""
    rel = _relief()
    grid = rel._elevation_grid(_small_tier())
    assert grid.dtype == np.int16, (
        f"the elevation cache is {grid.dtype}, not int16. On the finest tier "
        "that is 3.61 GB instead of 1.80 GB, and it is what put the suite over "
        "a CI runner's memory."
    )


def test_the_offset_is_undone_exactly() -> None:
    """int16 is only safe because the data fits it; this is what proves it."""
    from PIL import Image

    rel = _relief()
    path = _small_tier()
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(path) as img:
            stored = np.asarray(img).astype(np.int64)
    finally:
        Image.MAX_IMAGE_PIXELS = previous

    expected = stored - int(rel._ELEVATION_OFFSET_M)
    assert expected.min() >= np.iinfo(np.int16).min, "a tier underflows int16"
    assert expected.max() <= np.iinfo(np.int16).max, (
        f"a tier reaches {expected.max()} m, past int16. Either the grid gained "
        "a NoData sentinel or the vendored data changed; the cache dtype has to "
        "widen with it."
    )

    grid = rel._elevation_grid(path)
    assert np.array_equal(grid.astype(np.int64), expected), (
        "the cached grid is not the stored values minus the offset"
    )


def test_a_window_hands_back_float32_without_widening_the_world() -> None:
    """
    The crop is float32 for the maths; the grid behind it stays int16.

    This is the split that matters: widening happens on the window a render
    asked for, not on the 902M-pixel world it was cut from.
    """
    rel = _relief()
    path = _small_tier()
    crop, _bounds = rel._elevation_window(-9.6, 35.9, 3.4, 43.9, path=path)
    assert crop.dtype == np.float32, "callers do real arithmetic on the window"
    assert rel._elevation_grid(path).dtype == np.int16, (
        "taking a window widened the cached grid -- the saving is gone"
    )


def test_a_window_does_not_alias_the_shared_cache() -> None:
    """
    A crop that is a *view* would let one caller corrupt every later render.

    ``astype`` copies, which is what makes the shared cache safe to hand out.
    Checked by writing, because the cache is a module global that outlives any
    one test and a silent alias here would surface as an unrelated failure
    somewhere else entirely.
    """
    rel = _relief()
    path = _small_tier()
    crop, _ = rel._elevation_window(-9.6, 35.9, 3.4, 43.9, path=path)
    before = rel._elevation_grid(path).copy()
    crop[:] = -12345.0
    assert np.array_equal(rel._elevation_grid(path), before), (
        "writing to a window changed the cached grid: the window aliases it"
    )


def test_the_loader_never_materialises_a_whole_extra_grid() -> None:
    """The peak is set by the *intermediates*, not by what ends up cached.

    This is the half the dtype tests above cannot see. ``cache[path]`` can be
    a perfectly lean int16 array while the code that filled it briefly held
    three more copies of the same grid -- and the OOM killer counts the peak,
    not the result.

    It is what the whole-image path did. ``np.asarray(img).astype(np.int16)``
    reads as one conversion; on a mode ``I;16`` PNG it is four full-size
    buffers, because Pillow's array interface goes through ``tobytes()``:
    Pillow's own decode buffer, a bytes object, the numpy array over it, and
    then ``astype``'s result. Measured on the finest tier, 6.03 GB peak
    against a 3.36 GB floor.

    Rather than sample RSS -- which is process-wide, so every other test in the
    session would be inside the measurement -- this watches what the loader
    *asks numpy for*. Each intermediate must be a band, never the grid. The
    assertion is in rows rather than bytes so it reads the same whichever tier
    runs it.
    """
    rel = _relief()
    tier = _small_tier()
    rel._elevation_array_cache.pop(tier, None)

    seen: list[tuple[int, ...]] = []
    real_asarray = np.asarray

    def spy(obj, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = real_asarray(obj, *args, **kwargs)
        seen.append(getattr(result, "shape", ()))
        return result

    monkeypatched = pytest.MonkeyPatch()
    try:
        monkeypatched.setattr(np, "asarray", spy)
        grid = rel._elevation_grid(tier)
    finally:
        monkeypatched.undo()
        rel._elevation_array_cache.pop(tier, None)

    height = grid.shape[0]
    full_grid_intermediates = [shape for shape in seen if len(shape) == 2 and shape[0] == height]
    assert not full_grid_intermediates, (
        f"the loader built a whole-grid intermediate {full_grid_intermediates} for a "
        f"{grid.shape} tier; it must move the decode across in bands of at most "
        f"{rel._DECODE_BAND_ROWS} rows"
    )
    assert seen, "the loader asked numpy for nothing at all -- has the decode moved?"
    assert max(shape[0] for shape in seen if len(shape) == 2) <= rel._DECODE_BAND_ROWS


def test_banding_does_not_change_a_single_value() -> None:
    """Staging the decode is a memory change and must be nothing else.

    Compared against the straightforward whole-image read rather than against a
    stored fixture, so the comparison stays honest if a tier is ever
    revendored: both sides are computed from the same file, here, now.
    """
    rel = _relief()
    tier = _small_tier()
    rel._elevation_array_cache.pop(tier, None)

    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(tier) as img:
            straightforward = np.asarray(img).astype(np.int16) - int(rel._ELEVATION_OFFSET_M)
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit

    banded = rel._elevation_grid(tier)
    rel._elevation_array_cache.pop(tier, None)

    assert banded.dtype == straightforward.dtype
    assert banded.shape == straightforward.shape
    assert np.array_equal(banded, straightforward)
