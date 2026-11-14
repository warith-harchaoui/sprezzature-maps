"""
sprezzature_maps.ralph — render, read the picture back, change one thing.

The loop never lets a model touch the image and never lets it choose the
keyword. The model looks at a PNG and says what it can read; the table in
:mod:`~sprezzature_maps.ralph.repair` turns that into a keyword change,
and :mod:`~sprezzature_maps.ralph.policy` turns the change into a value
from a ladder with an end.

The line it will not cross on its own: anything that can alter what the map
says about the data — the classification method, the number of classes, the
frame, counts per area. Those are proposed and carried in the result for a
person to decide. Widening a map cannot mislead a reader; re-cutting the
classes can.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from .engine import RalphResult, RalphRound, Renderer, improve
from .policy import (
    DIRECTIONS,
    NoRoomLeft,
    default_for,
    is_safe,
    next_value,
    requires_confirmation,
)
from .repair import RULES, Repair, RepairRule, apply_safe, issues_in, propose_repairs
from .stopping import (
    MAX_AUTO_REPAIRS,
    MAX_ROUNDS,
    has_blocking,
    issue_signature,
    should_stop,
    signature_set,
)

__all__ = [
    "DIRECTIONS",
    "MAX_AUTO_REPAIRS",
    "MAX_ROUNDS",
    "RULES",
    "NoRoomLeft",
    "RalphResult",
    "RalphRound",
    "Renderer",
    "Repair",
    "RepairRule",
    "apply_safe",
    "default_for",
    "has_blocking",
    "improve",
    "is_safe",
    "issue_signature",
    "issues_in",
    "next_value",
    "propose_repairs",
    "requires_confirmation",
    "should_stop",
    "signature_set",
]
