"""
Choose a kind of map for a dataset and a sentence of intent.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from .client import LLMClient
from .prompts import CHOOSE_SYSTEM, choose_prompt
from .schemas import DataProfile, KindChoice


def choose_kind(client: LLMClient, request: str, profile: DataProfile) -> KindChoice:
    """Ask which of the registered kinds fits.

    The answer is validated against the registry before it is returned, so a
    caller can pass ``choice.kind`` straight to
    :func:`sprezzature_maps.studio.render.render` without re-checking it.

    Parameters
    ----------
    client : LLMClient
        Real or fake, injected by the caller. This module never constructs one.
    request : str
        The user's free-text description of what they want to show.
    profile : DataProfile
        The dataset, described without its values.

    Returns
    -------
    KindChoice

    Raises
    ------
    LLMResponseError
        If the model's answer still does not match the schema after one repair
        attempt — including when it names a kind that does not exist.
    """
    answer = client.chat_text(
        choose_prompt(request, profile),
        system=CHOOSE_SYSTEM,
        response_model=KindChoice,
        temperature=0.1,
    )
    assert isinstance(answer, KindChoice)  # chat_text guarantees this with a response_model
    return answer
