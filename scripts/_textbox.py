"""
_textbox — how wide a label really is, and the rectangle of paper it inks.

Module summary
--------------
An SVG writer has no text measurement. It emits ``<text>`` and the reader's
browser decides, from a font the writer never sees, how much paper the words
take. Every layer in this repository that decides *whether a name fits* has
therefore had to estimate, and all of them estimated the same way: one flat
advance of ``0.55`` em per character, whatever the character.

Measured against the faces these plates actually declare
(``Roboto, 'Helvetica Neue', Arial, sans-serif``) that constant is close to
right for lower case, which averages ``0.54`` em, and wrong for the capitals
cartography sets its names in, which average ``0.69``. So an all-caps name
was measured 15 to 21 per cent narrower than it draws — ``DONETSK`` at 38.5
units where it takes 49.0 — and the error grows with the length of the name,
which is to say with the chance that it runs into something. That is not a
rounding error: it is the reason ``AD-DAMAZIN`` and the river label ``Blue
Nile`` shared 56 by 10 units of the Sudan plate, and ``Sutlej`` sat inside
``Jullundur`` on the Himalaya one, while every "does it fit" check in the
generator reported clearance.

So this module carries the real numbers:

* :data:`ADVANCE` — a per-character advance width in em, taken as the
  **maximum** across the six faces a reader of these plates can land on
  (Arial, Arial Bold, Helvetica Neue, Roboto Regular/Medium/Bold). The
  maximum, not the mean, because the question asked of it is always "may
  this label be drawn here", and an answer that only holds for readers with
  Roboto installed is not an answer. Derived once with ``fontTools`` from
  the faces on the author's machine, the same one-time-build-tool status as
  the ``mapshaper`` and ``rasterio`` conversions behind ``assets/geo``;
  advance widths are measurements of a typeface, not a copy of one.
* :data:`INK_TOP_CAPS`, :data:`INK_TOP`, :data:`INK_TOP_ACCENT_LOWER`,
  :data:`INK_TOP_ACCENT_CAPS`, :data:`INK_BOTTOM` — how far the ink reaches
  above and below the baseline, again the deepest and tallest the stack
  draws, measured from the glyph outlines rather than from the font's
  declared line metrics (which describe line spacing, not ink).

What this module is *not*: a text shaper. It knows nothing of kerning pairs,
ligatures, or scripts that join. Kerning narrows a real line by a per-cent or
so, so ignoring it keeps the estimate on the safe side; a non-Latin script
falls back to :data:`DEFAULT_ADVANCE`, which is a capital's width, and is
therefore also on the safe side.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import unicodedata

#: Advance width in em, per character: the widest the declared font stack
#: draws it. Characters sharing a width are grouped, which keeps 327 of
#: them readable as 61 rows and makes an odd value easy to spot.
_ADVANCE_GROUPS: dict[float, str] = {
    0.2778: 'ijlìíîïĩīĭįıĺļ',
    0.278: " ',\xa0ſ‘’",
    0.2798: '|¦',
    0.2817: 'ĵ',
    0.2905: '.',
    0.2915: 'IÌÍÎÏĨĪĬĮİ',
    0.3057: 'ł',
    0.333: '!:;[]`¡´·¸',
    0.3379: 'tţŧ',
    0.3511: '(',
    0.3525: ')',
    0.3584: 'f',
    0.3594: '•',
    0.3726: '²³¹',
    0.3853: 'ľ',
    0.389: '-\xad',
    0.3892: 'r{}ŕŗř',
    0.4: '°',
    0.4121: '/',
    0.4219: '\\',
    0.4468: 'ª',
    0.4531: '*',
    0.457: 'º',
    0.4668: '¨',
    0.4741: '"',
    0.479: 'ŀť',
    0.5: '“”',
    0.5088: 'zźżž',
    0.5522: '¯',
    0.5562: '_aceksvxy¥«»àáâãäåçèéêëýÿāăąćĉċčēĕėęěĳķśŝşšŷ',
    0.5586: 'JĴ',
    0.5737: '$0123456789',
    0.5752: '¢',
    0.5898: 'ĸ',
    0.5942: '£',
    0.6: '+<=>^¬±¶×÷',
    0.6108: '?FLbdghnopqu¿ðñòóôõöøùúûüþĝğġģĥħĹĻĽĿŁńņňŋōŏőũūŭůűų',
    0.611: 'ZŹŻŽ',
    0.6157: '#µ',
    0.6187: 'TŢŤŦ',
    0.6284: '§',
    0.6304: 'đ',
    0.6309: 'ß',
    0.6562: '–',
    0.667: 'EPSVXYÈÉÊËÝÞĒĔĖĘĚŚŜŞŠŶŸ',
    0.6802: '~',
    0.7085: 'ŉ',
    0.7129: '¤',
    0.7188: 'ď',
    0.7222: '&ABCDHKNRUÀÁÂÃÄÅÇÐÑÙÚÛÜĀĂĄĆĈĊČĎĐĤĦĶŃŅŇŔŖŘŨŪŬŮŰŲ',
    0.7231: 'Ŋ',
    0.7778: 'GOQwÒÓÔÕÖØĜĞĠĢŌŎŐŵ',
    0.8: '©®',
    0.834: '¼½¾',
    0.8501: 'Ĳ',
    0.876: 'M',
    0.8892: 'mæ',
    0.9438: 'WœŴ',
    1.0: '%Æ—…',
    1.0151: '@',
    1.074: 'Œ',}

#: ``character -> advance in em``, flattened from :data:`_ADVANCE_GROUPS`.
ADVANCE: dict[str, float] = {
    char: width for width, chars in _ADVANCE_GROUPS.items() for char in chars
}

#: What an unknown character costs. A capital's width: the glyph is most
#: likely from a script this table does not cover (Cyrillic, Arabic, Han),
#: and over-estimating there drops a label that might have fitted, while
#: under-estimating prints one on top of another.
DEFAULT_ADVANCE = 0.7222

#: Ink above the baseline, in em, for a run with no lower case and no
#: accents: the tallest capital or digit the stack draws, round letters'
#: overshoot included.
INK_TOP_CAPS = 0.731

#: Ink above the baseline for a run containing lower case: the tallest
#: ascender (Roboto's ``b d f h k l t`` reach furthest of the six faces).
INK_TOP = 0.760

#: Ink above the baseline for an accented lower-case letter (``ô``, ``ű``).
INK_TOP_ACCENT_LOWER = 0.795

#: Ink above the baseline for an accented capital (``É``, ``Ů``) — the
#: tallest ink in the stack, and nearly a third of an em above a plain
#: capital, which is why it is worth a case of its own.
INK_TOP_ACCENT_CAPS = 0.949

#: Ink below the baseline: the deepest descender the stack draws, which is
#: not ``g`` or ``y`` but the parenthesis and the cedilla.
INK_BOTTOM = 0.256

#: Characters that put ink below the baseline. There is no property to test
#: for this the way :func:`unicodedata.combining` answers "is it accented",
#: so the set is written out: the five lower-case descenders, the marks that
#: hang (comma, semicolon, the bracket family, the solidi), the capitals
#: with a tail, and the cedilla and ogonek letters that carry European place
#: names (``Timişoara``, ``Łódź``).
DESCENDING = frozenset(
    "gjpqy,;()[]{}/\\@_$QµßÇçýÿĄąĘęĢģĮįĶķĻļŅņŖŗŞşŢţŲų"
)


def _has_accent(text: str) -> bool:
    """Whether any character carries a combining mark once decomposed.

    Examples
    --------
    >>> _has_accent("RHONE"), _has_accent("Rhône")
    (False, True)
    """
    return any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", text))


def text_width(text: str, size: float, tracking: float = 0.0) -> float:
    """Return the ink width of ``text``, in the same units as ``size``.

    Parameters
    ----------
    text : str
        The string as it will be drawn, already upper-cased if the caller
        intends to upper-case it.
    size : float
        Font size in user units.
    tracking : float, optional
        Extra letter-spacing in user units, as passed to SVG's
        ``letter-spacing``.

    Returns
    -------
    float
        Distance from the left edge of the first glyph's ink to the right
        edge of the last one's. The *advance* a browser lays out is one
        ``tracking`` wider than this, because letter-spacing is added after
        every character including the last; :func:`text_box` is where that
        distinction matters, and it is half a tracking unit either way.

    Examples
    --------
    A capital is far wider than the flat ``0.55`` em the generators used to
    assume, and a tracked name wider still:

    >>> round(text_width("DONETSK", 10.0), 2)
    48.97
    >>> round(text_width("DONETSK", 10.0, tracking=2.0), 2)
    60.97

    Lower case is where the old constant was about right:

    >>> round(text_width("Donetsk", 10.0), 2)
    39.5
    """
    total = sum(ADVANCE.get(ch, DEFAULT_ADVANCE) for ch in text) * size
    if len(text) > 1:
        total += tracking * (len(text) - 1)
    return total


def ink_top(text: str) -> float:
    """Return how far above the baseline ``text`` inks, in em.

    Examples
    --------
    >>> ink_top("DONETSK"), ink_top("Donetsk")
    (0.731, 0.76)
    >>> ink_top("RHÔNE")
    0.949
    """
    if _has_accent(text):
        # An accent over a capital sits highest; over lower case it starts
        # from x-height and lands well below that.
        return INK_TOP_ACCENT_CAPS if any(ch.isupper() for ch in text) else INK_TOP_ACCENT_LOWER
    return INK_TOP_CAPS if text == text.upper() else INK_TOP


def ink_bottom(text: str) -> float:
    """Return how far below the baseline ``text`` inks, in em.

    Examples
    --------
    >>> ink_bottom("DONETSK"), ink_bottom("Donetsk"), ink_bottom("Jullundur")
    (0.0, 0.0, 0.0)
    >>> ink_bottom("Zaporizhzhia"), ink_bottom("QATAR")
    (0.256, 0.256)
    """
    return INK_BOTTOM if any(ch in DESCENDING for ch in text) else 0.0


def text_box(
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    tracking: float = 0.0,
    anchor: str = "start",
    caps: bool = False,
) -> tuple[float, float, float, float]:
    """Return ``(x0, y0, x1, y1)``: the paper a ``<text>`` element inks.

    Parameters
    ----------
    x, y : float
        The element's ``x``/``y``, which SVG places at the text anchor on
        the baseline.
    text : str
        The label. Pass it exactly as the config carries it and set
        ``caps`` to match the drawing call, rather than upper-casing at one
        of the two sites and not the other.
    size : float
        Font size in user units.
    tracking : float, optional
        ``letter-spacing`` in user units.
    anchor : {"start", "middle", "end"}, optional
        SVG's ``text-anchor``.
    caps : bool, optional
        True when the drawing call upper-cases the label, as
        ``tracked_text`` does by default.

    Returns
    -------
    tuple of float
        The ink rectangle, in the coordinate system ``x``/``y`` are given in.

    Examples
    --------
    A left-anchored name grows rightwards from its anchor, and the box
    reaches above the baseline, not below, when nothing descends:

    >>> tuple(round(v, 2) for v in text_box(100.0, 50.0, "Donetsk", size=10))
    (100.0, 42.4, 139.5, 50.0)

    Centred and upper-cased, the same name straddles its anchor:

    >>> tuple(round(v, 2) for v in
    ...       text_box(100.0, 50.0, "Donetsk", size=10, anchor="middle", caps=True))
    (75.51, 42.69, 124.49, 50.0)
    """
    label = text.upper() if caps else text
    width = text_width(label, size, tracking)
    # Letter-spacing is added after the last glyph too, so the advance the
    # anchor is measured from is one tracking wider than the ink. Half of
    # that shows up as a leftward shift of a centred label.
    advance = width + (tracking if len(label) > 1 else 0.0)
    if anchor == "middle":
        x0 = x - advance / 2.0
    elif anchor == "end":
        x0 = x - advance
    else:
        x0 = x
    return x0, y - ink_top(label) * size, x0 + width, y + ink_bottom(label) * size


def boxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    pad: float = 0.0,
) -> bool:
    """Whether two boxes touch, counting a gap of ``pad`` or less as touching.

    ``pad`` is the clearance demanded *between* the two, not a margin added
    to each. The difference is a factor of two, and at label sizes a factor
    of two in clearance is the difference between "crowded" and "dropped":
    ``PORTUGAL`` cleared ``ATLANTIC OCEAN`` by two units on the Iberia
    plate, which reads as two names close together, and a double-counted
    pad deleted it.

    Examples
    --------
    >>> boxes_overlap((0, 0, 10, 10), (10, 0, 20, 10))
    True
    >>> boxes_overlap((0, 0, 10, 10), (12, 0, 20, 10), pad=1.0)
    False
    >>> boxes_overlap((0, 0, 10, 10), (10.5, 0, 20, 10), pad=1.0)
    True
    """
    return (
        a[0] - pad <= b[2]
        and a[2] + pad >= b[0]
        and a[1] - pad <= b[3]
        and a[3] + pad >= b[1]
    )


def box_inside(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
    pad: float = 0.0,
) -> bool:
    """Whether ``inner`` lies wholly within ``outer``, less a ``pad`` margin.

    Examples
    --------
    >>> box_inside((1, 1, 9, 9), (0, 0, 10, 10))
    True
    >>> box_inside((1, 1, 9, 9), (0, 0, 10, 10), pad=2.0)
    False
    """
    return (
        inner[0] >= outer[0] + pad
        and inner[1] >= outer[1] + pad
        and inner[2] <= outer[2] - pad
        and inner[3] <= outer[3] - pad
    )


#: Advance width in em of **every** glyph in the monospace stack these
#: plates declare for their provenance footer (``'Roboto Mono',
#: ui-monospace, SFMono-Regular, Menlo, monospace``). One number, because
#: that is what monospace means.
#:
#: The maximum across the stack, by the same rule :data:`ADVANCE` follows
#: and for the same reason: the question is always "will this line fit",
#: and an answer that only holds for a reader with Roboto Mono installed
#: is not an answer. Measured with ``fontTools`` on the four faces
#: resolvable here -- Roboto Mono 0.6001, SF Mono 0.6182, Menlo 0.6001,
#: PT Mono 0.6000.
MONO_ADVANCE = 0.6182


def mono_width(text: str, size: float) -> float:
    """Return the ink width of ``text`` set in the monospace stack.

    The sans measurement in :func:`text_width` is per character and is
    wrong here in both directions: it reads ``l`` as a quarter em and
    ``W`` as most of one, where a monospace face gives both the same.

    This was not academic. The provenance footer is the one line on a
    plate long enough to run off it, and after the evidence-basis sentence
    was added to the five conflict plates two of them did exactly that --
    the eastern-DRC footer reaching 982 units on a 944-unit canvas, with
    the last eleven words simply absent.

    Parameters
    ----------
    text : str
        The line.
    size : float
        Font size in user units.

    Returns
    -------
    float
        Width in the same units as ``size``.

    Examples
    --------
    >>> round(mono_width("abcd", 10), 3)
    24.728
    >>> mono_width("llll", 10) == mono_width("WWWW", 10)
    True
    """
    return len(text) * MONO_ADVANCE * size


def mono_wrap(text: str, size: float, available: float) -> list[str]:
    """Break ``text`` into lines no wider than ``available``.

    Breaks on spaces, and never mid-word: a hyphenation this module cannot
    do correctly is worse than a slightly ragged edge. A single word longer
    than the line is emitted on its own and overflows, which is visible and
    therefore fixable, rather than silently truncated.

    Parameters
    ----------
    text : str
        The line to break.
    size : float
        Font size in user units.
    available : float
        Width to fit, in the same units.

    Returns
    -------
    list of str
        At least one line, even for empty input.

    Examples
    --------
    >>> mono_wrap("the final boundary has not been determined", 10, 150)
    ['the final boundary has', 'not been determined']

    A word wider than the line keeps its own:

    >>> mono_wrap("antidisestablishmentarianism is long", 10, 60)
    ['antidisestablishmentarianism', 'is long']
    """
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if mono_width(candidate, size) <= available:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines
