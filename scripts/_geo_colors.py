"""
_geo_colors: perceptually uniform colour ramps, shared by the map generators.

Module summary
--------------
A colour ramp is a rule for turning a number into a colour: give it 0 and
it returns pale blue, give it 1 and it returns navy, give it 0.5 and it
should return something visually halfway between the two. ``make_choropleth.py``
used to compute that halfway point the naive way, blending the red, green,
and blue channels straight through (``r = ar + (br - ar) * t``, and the same
for g and b), in sRGB, the ordinary colour space a screen pixel is stored
in. The problem: sRGB is gamma-encoded, meaning its numbers do not increase
in a straight line with how bright a colour actually looks to the eye, so a
straight blend of two sRGB colours does not look like a straight blend of
brightness. In practice, the ramp appears to sag in the middle: the colour
at ``t=0.5`` reads darker and muddier than either endpoint would suggest.

This module ports (writes its own copy of, since ``sprezzature-colors`` is a
separate, unpackaged Claude skill rather than something this repo can
depend on at runtime) the small handful of OKLab and OKLCH primitives
needed to blend in a space where straight-line blending really does match
perceived brightness. OKLab is a colour space published by Björn Ottosson
in 2020, designed specifically so that equal numeric steps look like equal
visual steps; OKLCH is the same space described by Lightness, Chroma
(colour intensity), and Hue (the angle on the colour wheel) instead of
three raw coordinates, which is the easier form to interpolate in. The
recipe: convert both ramp endpoints to OKLCH, blend each of the three
values independently (Hue blends the short way around the wheel, the way
you would turn a dial rather than spin it all the way past zero), then
convert the blended result back to an sRGB hex string for the SVG's
``fill`` attribute.

The module also carries the matrices used to simulate colour-vision
deficiency, CVD (a limitation, most commonly the inability to distinguish
red from green, that affects how a ramp actually looks to some readers),
and the WCAG (Web Content Accessibility Guidelines) contrast helpers
needed to check a rendered ramp rather than merely assert it is fine. The
Ralph Eyeball Loop, this project's render-then-look review process, follows
one rule here: verify, don't assert. A docstring that claims a ramp is
"colour-vision-deficiency-safe by construction" is not evidence of
anything; only actually running the simulation on the real rendered output
is.

Usage example
-------------
>>> from _geo_colors import sequential_ramp_hex
>>> sequential_ramp_hex(0.0, ((0.0, "#EAF3FF"), (0.62, "#007AFF"), (1.0, "#0A4DA0")))
'#EAF3FF'

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
from collections.abc import Sequence

# A ramp stop is (position, hex_color), position in [0, 1] -- the same
# (t, hex) tuple order make_choropleth.py's original ``_RAMP`` constant
# already used, kept identical here rather than silently swapping it.
RampStop = tuple[float, str]


# ---------------------------------------------------------------------------
# sRGB <-> linear-light sRGB
#
# OKLab (and therefore OKLCH) is defined on *linear* light, not the
# gamma-encoded 0-255 values a hex string carries. Every conversion below
# has to pass through this gamma step first -- skipping it is the single
# most common way to get a "perceptual" ramp that is not actually
# perceptual (the classic bug: converting hex -> OKLab directly on the
# encoded 0-1 values instead of decoding gamma first).
# ---------------------------------------------------------------------------


def _srgb_to_linear(channel_8bit: int) -> float:
    """Decode one 8-bit sRGB channel to linear light in ``[0.0, 1.0]``.

    Parameters
    ----------
    channel_8bit : int
        A single R, G, or B channel value in ``[0, 255]``.

    Returns
    -------
    float
        The same channel in linear light, ``[0.0, 1.0]``. Uses the exact
        piecewise sRGB transfer function (not a flat gamma-2.2
        approximation), which matters near black where the two diverge.

    Examples
    --------
    >>> round(_srgb_to_linear(255), 4)
    1.0
    >>> round(_srgb_to_linear(0), 4)
    0.0
    """
    # Normalize to [0, 1] first -- the piecewise sRGB curve is defined on
    # that range, not on raw 0-255 integers.
    fraction = channel_8bit / 255.0
    if fraction <= 0.04045:
        # Near black, sRGB is (almost) linear -- a plain divide by the
        # slope of the linear segment, no gamma curve involved yet.
        return fraction / 12.92
    # Everywhere else, invert the standard sRGB gamma-encoding formula.
    return ((fraction + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(linear_channel: float) -> int:
    """Encode one linear-light channel back to an 8-bit sRGB value.

    Parameters
    ----------
    linear_channel : float
        A channel in linear light. Values outside ``[0.0, 1.0]`` are
        clamped rather than raising -- OKLab round-trips can overshoot
        slightly by floating-point error at the extremes (pure black/white).

    Returns
    -------
    int
        The channel re-encoded to sRGB gamma and rounded to ``[0, 255]``.

    Examples
    --------
    >>> _linear_to_srgb(1.0)
    255
    >>> _linear_to_srgb(0.0)
    0
    """
    # Clamp first: a value fractionally below 0 or above 1 (floating-point
    # noise from the OKLab round-trip) must not propagate into a negative
    # or >255 channel.
    if linear_channel <= 0.0:
        return 0
    if linear_channel >= 1.0:
        return 255
    if linear_channel <= 0.0031308:
        encoded = linear_channel * 12.92
    else:
        encoded = 1.055 * (linear_channel ** (1.0 / 2.4)) - 0.055
    return max(0, min(255, round(encoded * 255)))


def _parse_hex(hex_color: str) -> tuple[int, int, int]:
    """Parse a ``#RRGGBB`` (or ``#RGB``) string into an 8-bit ``(R, G, B)``.

    Parameters
    ----------
    hex_color : str
        A hex color, with or without the leading ``#``. Accepts both the
        3-digit shorthand (``"#fff"``) and the full 6-digit form.

    Returns
    -------
    tuple of int
        ``(r, g, b)``, each in ``[0, 255]``.

    Raises
    ------
    ValueError
        If ``hex_color`` is not a valid 3- or 6-digit hex string.

    Examples
    --------
    >>> _parse_hex("#007AFF")
    (0, 122, 255)
    >>> _parse_hex("fff")
    (255, 255, 255)
    """
    stripped = hex_color.lstrip("#").strip()
    # Expand the 3-digit shorthand ("abc" -> "aabbcc") so the rest of this
    # function only has to handle one length.
    if len(stripped) == 3:
        stripped = "".join(ch * 2 for ch in stripped)
    if len(stripped) != 6:
        raise ValueError(f"Bad hex color: {hex_color!r}")
    return int(stripped[0:2], 16), int(stripped[2:4], 16), int(stripped[4:6], 16)


def _hex_to_linear(hex_color: str) -> tuple[float, float, float]:
    """Parse a hex color straight through to linear-light sRGB.

    Parameters
    ----------
    hex_color : str
        A ``#RRGGBB`` (or shorthand) hex string.

    Returns
    -------
    tuple of float
        ``(r, g, b)`` in linear light, each in ``[0.0, 1.0]``.

    Examples
    --------
    >>> r, g, b = _hex_to_linear("#000000")
    >>> (round(r, 4), round(g, 4), round(b, 4))
    (0.0, 0.0, 0.0)
    """
    r, g, b = _parse_hex(hex_color)
    # Decode each of the three 8-bit channels independently -- the sRGB
    # transfer function is applied per-channel, there is no cross-channel
    # term at this stage.
    return _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)


def _linear_to_hex(linear_rgb: tuple[float, float, float]) -> str:
    """Format a linear-light triple back to an upper-case ``#RRGGBB`` string.

    Parameters
    ----------
    linear_rgb : tuple of float
        ``(r, g, b)`` in linear light.

    Returns
    -------
    str
        The re-encoded, clamped, upper-case hex string.

    Examples
    --------
    >>> _linear_to_hex((1.0, 1.0, 1.0))
    '#FFFFFF'
    """
    return "#" + "".join(f"{_linear_to_srgb(c):02X}" for c in linear_rgb)


# ---------------------------------------------------------------------------
# OKLab / OKLCH (Bjorn Ottosson, 2020) -- https://bottosson.github.io/posts/oklab/
#
# OKLab is a perceptually-uniform Lab-like space derived from a fit to
# human color-matching data; OKLCH is just its polar form (Lightness,
# Chroma, Hue) -- the same relationship as CIELab/CIELCh, but built on a
# model that better matches perceived hue and lightness uniformity than
# the older CIE spaces. Interpolating in OKLCH is what keeps a ramp's
# *perceived* brightness changing at a constant rate from one stop to the
# next, instead of the naive RGB lerp's uneven-looking midpoints.
# ---------------------------------------------------------------------------


def _linear_to_oklab(linear_rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert linear-light sRGB to OKLab.

    Parameters
    ----------
    linear_rgb : tuple of float
        ``(r, g, b)`` in linear light, ``[0.0, 1.0]``.

    Returns
    -------
    tuple of float
        ``(L, a, b)`` in OKLab. ``L`` is roughly ``[0, 1]``; ``a``/``b`` are
        signed and typically small (``|a|, |b| < 0.5`` for in-gamut sRGB).

    Examples
    --------
    >>> l, a, b = _linear_to_oklab((1.0, 1.0, 1.0))
    >>> round(l, 2), round(a, 2), round(b, 2)
    (1.0, 0.0, 0.0)
    """
    r, g, b = linear_rgb
    # Step 1: linear sRGB -> an LMS-like cone-response space. These three
    # 3x3-matrix rows are Ottosson's published constants, not derived here.
    l_cone = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_cone = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_cone = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    # Step 2: cube root, signed (negative cone responses can occur for
    # saturated/out-of-gamut colors -- preserve the sign rather than
    # letting a plain ``**(1/3)`` raise or return a complex result).
    l_ = l_cone ** (1 / 3) if l_cone >= 0 else -((-l_cone) ** (1 / 3))
    m_ = m_cone ** (1 / 3) if m_cone >= 0 else -((-m_cone) ** (1 / 3))
    s_ = s_cone ** (1 / 3) if s_cone >= 0 else -((-s_cone) ** (1 / 3))
    # Step 3: the cube-rooted cone space -> OKLab's (L, a, b) axes, again
    # Ottosson's published matrix.
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklab_to_linear(oklab: tuple[float, float, float]) -> tuple[float, float, float]:
    """Invert :func:`_linear_to_oklab`: OKLab back to linear-light sRGB.

    Parameters
    ----------
    oklab : tuple of float
        ``(L, a, b)`` in OKLab.

    Returns
    -------
    tuple of float
        ``(r, g, b)`` in linear light. Not clamped -- a ramp endpoint that
        is barely out of sRGB gamut after interpolation is expected to be
        clamped later, at the hex-encoding step (:func:`_linear_to_srgb`),
        not silently distorted here.

    Examples
    --------
    >>> r, g, b = _oklab_to_linear((1.0, 0.0, 0.0))
    >>> (round(r, 2), round(g, 2), round(b, 2))
    (1.0, 1.0, 1.0)
    """
    big_l, a, b = oklab
    # Inverse of OKLab's forward matrix -- maps back into the cube-rooted
    # cone space.
    l_ = big_l + 0.3963377774 * a + 0.2158037573 * b
    m_ = big_l - 0.1055613458 * a - 0.0638541728 * b
    s_ = big_l - 0.0894841775 * a - 1.2914855480 * b
    # Undo the cube root from the forward direction (plain cube this time,
    # sign is preserved automatically since cubing keeps the sign).
    l_cone = l_**3
    m_cone = m_**3
    s_cone = s_**3
    # Inverse of the cone-response matrix -> back to linear sRGB.
    return (
        4.0767416621 * l_cone - 3.3077115913 * m_cone + 0.2309699292 * s_cone,
        -1.2684380046 * l_cone + 2.6097574011 * m_cone - 0.3413193965 * s_cone,
        -0.0041960863 * l_cone - 0.7034186147 * m_cone + 1.7076147010 * s_cone,
    )


def _oklab_to_oklch(oklab: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert OKLab (Cartesian) to OKLCH (polar): ``(L, C, H)``.

    Parameters
    ----------
    oklab : tuple of float
        ``(L, a, b)``.

    Returns
    -------
    tuple of float
        ``(L, C, H)`` -- Lightness unchanged, Chroma is the radius
        ``sqrt(a^2 + b^2)``, Hue is the angle in degrees, normalized to
        ``[0, 360)`` so ramp interpolation never has to special-case a
        negative angle.

    Examples
    --------
    >>> l, c, h = _oklab_to_oklch((0.5, 0.1, 0.0))
    >>> round(c, 2), round(h, 2)
    (0.1, 0.0)
    """
    big_l, a, b = oklab
    chroma = math.sqrt(a * a + b * b)
    hue_deg = math.degrees(math.atan2(b, a))
    if hue_deg < 0:
        # atan2 returns (-180, 180]; fold negative angles into [0, 360) so
        # the shortest-path hue interpolation below has one consistent
        # convention to reason about.
        hue_deg += 360.0
    return big_l, chroma, hue_deg


def _oklch_to_oklab(oklch: tuple[float, float, float]) -> tuple[float, float, float]:
    """Invert :func:`_oklab_to_oklch`: OKLCH (polar) back to OKLab (Cartesian).

    Parameters
    ----------
    oklch : tuple of float
        ``(L, C, H)``, ``H`` in degrees.

    Returns
    -------
    tuple of float
        ``(L, a, b)``.

    Examples
    --------
    >>> l, a, b = _oklch_to_oklab((0.5, 0.1, 0.0))
    >>> round(a, 2), round(b, 2)
    (0.1, 0.0)
    """
    big_l, chroma, hue_deg = oklch
    hue_rad = math.radians(hue_deg)
    return big_l, chroma * math.cos(hue_rad), chroma * math.sin(hue_rad)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between two scalars.

    Parameters
    ----------
    a, b : float
        Endpoints.
    t : float
        Interpolation position, expected in ``[0.0, 1.0]`` but not clamped
        (callers already clamp ``t`` once, at the public entry point).

    Returns
    -------
    float
        ``a + (b - a) * t``.

    Examples
    --------
    >>> _lerp(0.0, 10.0, 0.5)
    5.0
    """
    return a + (b - a) * t


def _lerp_hue(hue_a: float, hue_b: float, t: float) -> float:
    """Interpolate two hue angles (degrees) along their *shortest* arc.

    Parameters
    ----------
    hue_a, hue_b : float
        Hue angles in degrees, each expected in ``[0, 360)``.
    t : float
        Interpolation position in ``[0.0, 1.0]``.

    Returns
    -------
    float
        The interpolated hue, normalized to ``[0, 360)``.

    Notes
    -----
    A naive ``_lerp(hue_a, hue_b, t)`` is wrong whenever the two hues are on
    opposite sides of the 0/360 seam (e.g. 350 degrees and 10 degrees):
    linearly interpolating the raw numbers sweeps the *long* way around the
    color wheel (350 -> 180 -> 10) instead of the short 20-degree arc a
    viewer would actually expect. This picks whichever direction is
    shorter before interpolating.

    Examples
    --------
    >>> round(_lerp_hue(350.0, 10.0, 0.5), 1)
    0.0
    """
    delta = hue_b - hue_a
    # Fold the raw difference into (-180, 180] -- that is by definition the
    # shorter of the two possible arcs around the circle.
    delta = (delta + 180.0) % 360.0 - 180.0
    return (hue_a + delta * t) % 360.0


def _interpolate_oklch_hex(hex_a: str, hex_b: str, t: float) -> str:
    """Interpolate between two hex colors in OKLCH space.

    Parameters
    ----------
    hex_a, hex_b : str
        Endpoint colors as hex strings.
    t : float
        Interpolation position in ``[0.0, 1.0]`` (0 -> ``hex_a``, 1 ->
        ``hex_b``).

    Returns
    -------
    str
        The interpolated color as an upper-case hex string.

    Examples
    --------
    >>> _interpolate_oklch_hex("#000000", "#FFFFFF", 0.5)
    '#636363'

    An achromatic endpoint (near-zero chroma, e.g. a neutral grey) has an
    essentially arbitrary hue -- ``atan2(b, a)`` on two near-zero numbers
    is noise, not signal. Interpolating hue *through* that noise produces
    a visible, wrong-looking color swing at the midpoint (verified during
    this module's own CVD pass: a terracotta-to-grey diverging ramp came
    out mauve/pink at its midpoint before this guard existed). When either
    endpoint is (near) achromatic, hue interpolation is skipped and the
    *other* endpoint's hue is used for the whole segment instead:

    >>> _interpolate_oklch_hex("#B4530A", "#F2F2F7", 0.5)
    '#D9A386'
    """
    # Exact boundaries bypass the OKLCH round-trip entirely: the
    # achromatic-endpoint hue substitution below is a *blend-only*
    # adjustment, but at t=0/t=1 the caller expects the untouched input
    # color back, not a version perturbed by a hue swapped in from the
    # other endpoint.
    if t <= 0.0:
        # Round-trips exactly for any valid input (3- or 6-digit, any
        # case) because sRGB<->linear is an exact inverse pair at 8-bit
        # precision -- this also normalizes the output to upper-case
        # 6-digit form, same as every other return path in this module.
        return _linear_to_hex(_hex_to_linear(hex_a))
    if t >= 1.0:
        return _linear_to_hex(_hex_to_linear(hex_b))
    # Round-trip both endpoints through the full hex -> linear -> OKLab ->
    # OKLCH chain, interpolate each of the three OKLCH channels on its own
    # terms (L and C linearly, H along the shortest arc), then reverse the
    # chain back to a hex string for the SVG.
    lch_a = _oklab_to_oklch(_linear_to_oklab(_hex_to_linear(hex_a)))
    lch_b = _oklab_to_oklch(_linear_to_oklab(_hex_to_linear(hex_b)))
    lightness = _lerp(lch_a[0], lch_b[0], t)
    chroma = _lerp(lch_a[1], lch_b[1], t)
    # Chroma below this is visually indistinguishable from grey, so its
    # OKLCH hue angle is noise rather than a real color direction -- see
    # the achromatic-endpoint example above.
    achromatic_chroma = 0.01
    chroma_a_is_grey = lch_a[1] < achromatic_chroma
    chroma_b_is_grey = lch_b[1] < achromatic_chroma
    if chroma_a_is_grey and chroma_b_is_grey:
        # Both endpoints are effectively grey -- any hue is equally
        # meaningless, so hue can't introduce a visible artifact either
        # way; 0.0 is as good as any other value.
        hue = 0.0
    elif chroma_a_is_grey:
        # Only hex_a is grey: carry hex_b's real hue across the whole
        # segment instead of interpolating from noise.
        hue = lch_b[2]
    elif chroma_b_is_grey:
        hue = lch_a[2]
    else:
        # Both endpoints have a real hue -- interpolate along the shorter
        # arc, same as before.
        hue = _lerp_hue(lch_a[2], lch_b[2], t)
    return _linear_to_hex(_oklab_to_linear(_oklch_to_oklab((lightness, chroma, hue))))


# ---------------------------------------------------------------------------
# Public ramps
# ---------------------------------------------------------------------------


def sequential_ramp_hex(t: float, stops: Sequence[RampStop]) -> str:
    """Sample a multi-stop sequential ramp at ``t``, interpolated in OKLCH.

    Parameters
    ----------
    t : float
        Ramp position, clamped to ``[0.0, 1.0]``.
    stops : sequence of (float, str)
        ``(position, hex_color)`` pairs, sorted by ``position`` ascending,
        with the first position ``0.0`` and the last ``1.0`` (the same
        shape ``make_choropleth.py``'s old ``_RAMP`` tuple already used).

    Returns
    -------
    str
        The interpolated hex color at ``t``.

    Examples
    --------
    >>> stops = ((0.0, "#EAF3FF"), (0.62, "#007AFF"), (1.0, "#0A4DA0"))
    >>> sequential_ramp_hex(0.62, stops)
    '#007AFF'
    """
    # Clamp once here so every caller downstream (including the two
    # helpers below) can assume t is already in range.
    t = min(1.0, max(0.0, t))
    for (lo_t, lo_color), (hi_t, hi_color) in zip(stops, stops[1:], strict=False):
        if lo_t <= t <= hi_t:
            # Re-scale t from the stop's own [lo_t, hi_t] window to a
            # local [0, 1] before handing it to the OKLCH interpolator,
            # which only knows about its two immediate endpoints.
            local_t = (t - lo_t) / (hi_t - lo_t) if hi_t > lo_t else 0.0
            return _interpolate_oklch_hex(lo_color, hi_color, local_t)
    # t == 1.0 falls through the loop when the last segment's upper bound
    # is an exact float match handled above; this is the safety net for
    # any floating-point edge case, returning the final stop's color.
    return stops[-1][1]


def diverging_ramp_hex(
    t: float,
    *,
    low: str = "#B4530A",
    mid: str = "#F2F2F7",
    high: str = "#0A4DA0",
) -> str:
    """Sample a three-stop diverging ramp at ``t`` in ``[-1, 1]``.

    Parameters
    ----------
    t : float
        Ramp position, clamped to ``[-1.0, 1.0]``. ``-1`` is the most
        negative extreme, ``0`` the neutral midpoint, ``1`` the most
        positive extreme.
    low : str, optional
        Hex color for the negative extreme (default: a warm terracotta,
        distinguishable from ``high`` under all three CVD types --
        verified via :func:`simulate_cvd_hex`, not just asserted).
    mid : str, optional
        Hex color for the neutral midpoint (default: a light neutral grey,
        matching the house palette's Apple-inspired neutrals).
    high : str, optional
        Hex color for the positive extreme (default: the same house navy
        blue :func:`sequential_ramp_hex`'s default ramp ends on, so a
        choropleth's positive tail reads consistently whether the caller
        picked the sequential or diverging ramp).

    Returns
    -------
    str
        The interpolated hex color at ``t``.

    Examples
    --------
    >>> diverging_ramp_hex(0.0)
    '#F2F2F7'
    >>> diverging_ramp_hex(1.0)
    '#0A4DA0'
    """
    t = min(1.0, max(-1.0, t))
    if t >= 0.0:
        # Positive half: interpolate from the neutral midpoint up to the
        # "high" extreme.
        return _interpolate_oklch_hex(mid, high, t)
    # Negative half: interpolate from the neutral midpoint down to the
    # "low" extreme. Flipping the sign of t turns "-1..0" into "1..0" so
    # the same interpolator direction (mid -> low) still reads t=0 as mid.
    return _interpolate_oklch_hex(mid, low, -t)


# ---------------------------------------------------------------------------
# Verification: CVD simulation + WCAG contrast.
#
# Not used by the generators at render time -- these exist so a ramp can
# be *checked*, not just designed by eye. Ported from the same Machado et
# al. (2009) matrices sprezzature-colors' simulate_cvd.py already carries,
# at CVD severity 1.0 (full dichromacy, the worst case).
# ---------------------------------------------------------------------------

#: Machado et al. (2009) 3x3 CVD simulation matrices, applied in linear
#: sRGB. Keyed by the CVD type name so callers can iterate all three for a
#: full accessibility pass.
CVD_MATRICES = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def simulate_cvd_hex(hex_color: str, cvd_type: str) -> str:
    """Simulate how ``hex_color`` looks to a viewer with the given CVD type.

    Parameters
    ----------
    hex_color : str
        The color as rendered for a viewer with normal color vision.
    cvd_type : {"protanopia", "deuteranopia", "tritanopia"}
        Which dichromacy to simulate.

    Returns
    -------
    str
        The hex color as it would appear to that viewer.

    Raises
    ------
    KeyError
        If ``cvd_type`` is not one of the three known keys.

    Examples
    --------
    >>> simulate_cvd_hex("#0A4DA0", "protanopia")
    '#1356A3'
    """
    matrix = CVD_MATRICES[cvd_type]
    # The matrix operates on linear light, same reasoning as the OKLab
    # conversions above: simulating color-vision deficiency is a physical
    # transform on the light itself, not on the gamma-encoded byte values.
    r, g, b = _hex_to_linear(hex_color)
    simulated = (
        matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b,
        matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b,
        matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b,
    )
    return _linear_to_hex(simulated)


def wcag_contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.x contrast ratio between two opaque colors.

    Parameters
    ----------
    hex_a, hex_b : str
        The two colors to compare (order does not matter -- the formula
        is symmetric, it always divides the lighter relative luminance by
        the darker one).

    Returns
    -------
    float
        The contrast ratio, in ``[1.0, 21.0]``. WCAG AA for normal text
        requires ``>= 4.5``; for large text (>=18pt or >=14pt bold),
        ``>= 3.0``.

    Examples
    --------
    >>> round(wcag_contrast_ratio("#000000", "#FFFFFF"), 2)
    21.0
    """

    def relative_luminance(linear_rgb: tuple[float, float, float]) -> float:
        # WCAG's fixed luminance-weighting coefficients (Rec. 709), applied
        # to the same linear-light triple the rest of this module already
        # works with.
        r, g, b = linear_rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    luminance_a = relative_luminance(_hex_to_linear(hex_a))
    luminance_b = relative_luminance(_hex_to_linear(hex_b))
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    # The "+0.05" on both sides of the WCAG formula avoids a division by
    # (near-)zero for pure black and keeps the ratio bounded at 21.0 for
    # pure black-on-white.
    return (lighter + 0.05) / (darker + 0.05)
