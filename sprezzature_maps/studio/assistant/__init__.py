"""
sprezzature_maps.studio.assistant — the model-facing layer of the Studio.

The model never generates or runs code. Every call made from here is scoped to
one Pydantic schema in :mod:`~sprezzature_maps.studio.assistant.schemas`, and
validated — with exactly one repair attempt — before anything downstream sees
it. :mod:`~sprezzature_maps.studio.assistant.client` wraps
``best_engine_ai_helper.llm.chat()`` as the only path to a model, and imports
it *lazily*, so this package and all of its tests work with that package
absent.

Three of the files here — ``client.py``, ``repair.py``, ``fake_client.py`` —
are shared verbatim with ``sprezzature-figures``, which is canonical for them;
``sprezzature/scripts/sync_helpers.py`` propagates and compares them, keyed by
path suffix. Edit them there, not here.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from .choose import choose_kind
from .client import BestEngineLLMClient, LLMClient, default_client
from .fake_client import FakeLLMClient, FakeLLMTimeout
from .profile import classify, profile_points, profile_rows
from .prompts import kind_catalogue
from .read_map import MapReadingError, read_map
from .repair import LLMResponseError, validate_or_repair
from .schemas import (
    COLUMN_LOOKS,
    ColumnProfile,
    DataProfile,
    KindChoice,
    MapIssue,
    MapReading,
)

__all__ = [
    "COLUMN_LOOKS",
    "BestEngineLLMClient",
    "ColumnProfile",
    "DataProfile",
    "FakeLLMClient",
    "FakeLLMTimeout",
    "KindChoice",
    "LLMClient",
    "LLMResponseError",
    "MapIssue",
    "MapReading",
    "MapReadingError",
    "choose_kind",
    "classify",
    "default_client",
    "kind_catalogue",
    "profile_points",
    "profile_rows",
    "read_map",
    "validate_or_repair",
]
