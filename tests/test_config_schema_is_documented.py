"""
Every config key the generator accepts must be written down somewhere.

``validate_config`` refuses an unknown key and suggests the one you probably
meant, which is a good error and only useful if the list of known keys is
discoverable. It was not. ``EXAMPLES.md`` sends a reader to
``make_situation_map``'s module docstring "for the full list of fields it
accepts", and that docstring named **ten of thirty-one**: a documented
pointer leading to a third of the schema.

The honest fix for "the docs are incomplete" is not a bigger docstring, it
is a test that fails when they go incomplete again — the same reasoning as
``test_demo_examples_are_current``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re

from sprezzature_maps import _load_script

msm = _load_script("make_situation_map")


def test_every_accepted_key_appears_in_the_module_docstring() -> None:
    """
    A key the validator accepts and no document mentions is a key nobody can
    use on purpose.
    """
    documented = msm.__doc__ or ""
    missing = sorted(key for key in msm.CONFIG_KEYS if key not in documented)
    assert not missing, (
        f"{len(missing)} config key(s) accepted by validate_config and absent from "
        f"make_situation_map's module docstring: {', '.join(missing)}. "
        "Add a line to its 'Every configuration key' section."
    )


def test_the_docstring_does_not_promise_keys_the_validator_rejects() -> None:
    """
    The other direction, which is the one that wastes an afternoon: a key
    documented here and refused at runtime reads as a bug in the caller.

    Checked against the reference section only, since the rest of the
    docstring is prose that legitimately names other things.
    """
    doc = msm.__doc__ or ""
    start = doc.index("Every configuration key")
    section = doc[start:]
    # A top-level entry in that section is a numpydoc definition term: a line
    # holding nothing but one or more ``quoted`` keys. Sub-keys are described
    # inside their parent's indented body and prose names functions, so
    # anything else on the line disqualifies it.
    # A term sits at column zero; its body, and the sub-keys named inside it,
    # are indented. Matching on the pattern alone caught a wrapped line of
    # marker sub-keys that happened to contain nothing but quoted tokens.
    term = re.compile(r"^(``\w+``)(, ``\w+``)*$")
    documented: set[str] = set()
    for line in section.splitlines():
        if line[:1].isspace() or not term.match(line.rstrip()):
            continue
        documented.update(token.strip("`") for token in line.rstrip().split(", "))
    assert documented, "the reference section parsed to nothing; the format changed"
    unknown = sorted(documented - set(msm.CONFIG_KEYS))
    assert not unknown, (
        f"documented as top-level config keys but rejected by validate_config: "
        f"{', '.join(unknown)}"
    )
    # And the section really does cover the schema, not just a subset.
    assert documented == set(msm.CONFIG_KEYS), (
        "reference section and CONFIG_KEYS disagree: "
        f"only in docs {sorted(documented - set(msm.CONFIG_KEYS))}, "
        f"only in code {sorted(set(msm.CONFIG_KEYS) - documented)}"
    )
