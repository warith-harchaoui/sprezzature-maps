#!/usr/bin/env python3
"""
audit_map — is this plate honest about how it was made?

``sprezzature-figures``' auditor reads a rendered SVG as a chart, and it is
right to. What it cannot ask are the questions that only apply to a map, and
they are the questions a map most often gets wrong:

================== =======================================================
``method-unnamed`` The legend shows discrete classes and does not say how
                   the breaks were chosen. Quantile, equal interval and
                   natural breaks put the same data in different colours
                   and tell different stories; a method nobody can name is
                   a method nobody can question. This repository already
                   paid for that once.
``breaks-missing`` A classed legend with no boundary values printed. The
                   swatches become a lookup table with no key: a reader can
                   see that a country is darker and cannot say than what.
``no-data-hidden`` Regions are drawn with the no-data fill and nothing in
                   the legend says so, so absent reads as low — the single
                   most common way a choropleth misleads.
``no-provenance``  The plate says neither when it was true nor that it is a
                   schematic. A map with neither is read as current,
                   forever. Saying "synthetic illustrative values" counts,
                   and counts for more than a date would: stamping a vintage
                   on invented data would be a fabrication.
``untitled``       No title text, which in an article means a plate nobody
                   can attribute or caption.
``unlabelled``     No ``role="img"`` with an accessible name on the root. A
                   screen reader announces "graphic" and nothing else, in a
                   suite whose whole point is that this does not happen.
================== =======================================================

Static: it reads the SVG the generator wrote and nothing else. No rendering,
no network, no geometry.

What it deliberately does not do: judge whether the *right* classification
was chosen, whether the projection suits the latitudes, or whether the data
is any good. Those are cartography, not parsing. This checks that the plate
says enough for a reader to ask those questions themselves.

Usage
-----
::

    sprezzature-maps-audit plate.svg
    sprezzature-maps-audit plates/ --format json

Exits 1 when any finding is reported.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

#: The note a classed legend prints: "5 classes, natural breaks".
_METHOD_RE = re.compile(r">\s*(\d+)\s+classes?,\s*([^<]+?)\s*</text>")

#: Any visible text on the plate.
_TEXT_RE = re.compile(r">([^<>]{1,200})</text>")

#: A vintage, however it is phrased: "as of 2024", "Positions as of ~2024",
#: "2019-2023". Deliberately loose — the point is that a date is *there*, not
#: that it follows a house format.
_DATE_RE = re.compile(r"\b(?:as of|à jour|situation)\b|\b(?:19|20)\d{2}\b", re.I)

#: A plate that says it is not describing the world — a demo, a schematic, a
#: set of synthetic values. That is a provenance statement, and a *better*
#: one than a date would be: stamping a vintage on invented data would be a
#: fabrication, not an improvement.
_SYNTHETIC_RE = re.compile(
    r"\b(?:synthetic|illustrative|schematic|demo|sample|example|"
    r"synthétique|illustratif|fictif)\b", re.I
)

#: Discrete class swatches, as the classed legend draws them.
_SWATCH_RE = re.compile(r"<rect[^>]*\bclass=\"(?:legend-)?swatch\"")


@dataclass(frozen=True)
class Finding:
    """One thing the plate does not say about itself."""

    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.message}"


def _strip_payloads(svg: str) -> str:
    """Drop embedded base64 so the regexes stay cheap on a 2 MB plate."""
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,…", svg)


def audit(svg: str) -> list[Finding]:
    """
    Report what a rendered plate fails to say about how it was made.

    Parameters
    ----------
    svg : str
        The SVG document as written by one of this package's generators, or
        by anything else — the check reads markup, not provenance.

    Returns
    -------
    list of Finding
        Empty when the plate carries everything a reader needs to question
        it.
    """
    text = _strip_payloads(svg)
    labels = [t.strip() for t in _TEXT_RE.findall(text) if t.strip()]
    findings: list[Finding] = []

    root = text[: text.index(">") + 1] if ">" in text else ""
    # Both roles are correct, and the generators use both: `img` for a flat
    # plate, `graphics-document` (WAI-ARIA Graphics Module) for an
    # interactive one, which is the better answer where it applies. A rule
    # that demanded `img` alone would push a maintainer to downgrade correct
    # markup to satisfy the linter — which is how linters lose their users.
    named = (
        re.search(r'role="(?:img|graphics-document|graphics-symbol)"', root)
        and ("aria-label" in root or "aria-labelledby" in root)
        and "<title" in text
    )
    if not named:
        findings.append(Finding(
            "unlabelled",
            'the root carries no role="img" with an accessible name, so a '
            'screen reader announces "graphic" and stops there',
        ))

    if not labels:
        findings.append(Finding(
            "untitled",
            "the plate has no visible text at all, so nobody can attribute "
            "or caption it",
        ))
        return findings

    # ── classification ──────────────────────────────────────────────────
    classed = bool(_SWATCH_RE.search(text)) or bool(_METHOD_RE.search(text))
    if classed:
        method = _METHOD_RE.search(text)
        if method is None:
            findings.append(Finding(
                "method-unnamed",
                "the legend shows discrete classes and never says how the "
                "breaks were chosen; quantile, equal interval and natural "
                "breaks put the same data in different colours and tell "
                "different stories",
            ))
        else:
            # A classed legend is a lookup table, and a lookup table with no
            # key is decoration. The generator prints the boundary values
            # between swatches; their absence means a reader can see that one
            # country is darker and cannot say than what.
            count = int(method.group(1))
            numeric = [t for t in labels if re.fullmatch(r"[-+]?[\d\s.,kKmMbB%]+", t)]
            if len(numeric) < count - 1:
                findings.append(Finding(
                    "breaks-missing",
                    f"the legend shows {count} classes and prints "
                    f"{len(numeric)} boundary value(s); the swatches are a "
                    f"lookup table with no key",
                ))

    # ── absent is not low ───────────────────────────────────────────────
    has_no_data_fill = "no-data" in text or "noData" in text
    says_no_data = any(
        re.search(r"\b(no data|sans donn|pas de donn)", t, re.I) for t in labels
    )
    if has_no_data_fill and not says_no_data:
        findings.append(Finding(
            "no-data-hidden",
            "regions are drawn with the no-data fill and the legend never "
            "names it, so absent reads as low — the commonest way a "
            "choropleth misleads",
        ))

    # ── a reader has to be able to place the plate in time, or outside it ─
    dated = any(_DATE_RE.search(t) for t in labels)
    declared_synthetic = any(_SYNTHETIC_RE.search(t) for t in labels)
    if not dated and not declared_synthetic:
        findings.append(Finding(
            "no-provenance",
            "the plate says neither when it was true nor that it is a "
            "schematic; a map with neither is read as current, forever, "
            "including years after it stopped being so",
        ))

    return findings


def _plates(target: Path) -> list[Path]:
    """Every SVG under a path, or the path itself."""
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*.svg") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    """Audit one plate or a folder of them. Returns the exit code."""
    parser = argparse.ArgumentParser(
        prog="sprezzature-maps-audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Check that a rendered map says enough about itself for a reader "
            "to question it: the classification method named, the class "
            "breaks printed, no-data distinguishable from low, a vintage, a "
            "title, and an accessible name."
        ),
        epilog=(
            "Examples:\n"
            "  sprezzature-maps-audit plate.svg\n"
            "  sprezzature-maps-audit assets/ --format json\n"
            "\n"
            "What it does not do: judge whether the right classification was "
            "chosen or whether the data is any good. Those are cartography, "
            "not parsing. This checks the plate says enough for someone to "
            "ask.\n"
        ),
    )
    parser.add_argument("target", type=Path, help="An SVG plate, or a folder of them.")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="Output shape (default: text).",
    )
    args = parser.parse_args(argv)

    if not args.target.exists():
        sys.stderr.write(f"{args.target}: no such file or directory\n")
        return 2

    plates = _plates(args.target)
    if not plates:
        sys.stderr.write(f"{args.target}: no SVG found\n")
        return 2

    report: dict[str, list[Finding]] = {}
    for plate in plates:
        report[str(plate)] = audit(
            plate.read_text(encoding="utf-8", errors="replace")
        )
    total = sum(len(f) for f in report.values())

    if args.format == "json":
        json.dump(
            {
                "plates": len(plates),
                "findings_total": total,
                "plates_detail": {
                    name: [{"rule": f.rule, "message": f.message} for f in found]
                    for name, found in report.items()
                },
            },
            sys.stdout, indent=2, ensure_ascii=False,
        )
        sys.stdout.write("\n")
    else:
        for name, found in report.items():
            for finding in found:
                print(f"{name}: {finding}")
        print(
            f"{len(plates)} plate(s), {total} finding(s)." if total
            else f"{len(plates)} plate(s), each says how it was made."
        )
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
