"""
The shapes a model is allowed to answer in.

The model never writes code and never calls a renderer: every call in this
package is scoped to one of the schemas below, validated — and given exactly
one repair attempt — before anything downstream sees it. That is the whole
reason these are Pydantic models rather than free text.

Two of the fields validate against this package's own registries instead of
repeating them: :attr:`KindChoice.kind` against
:func:`sprezzature_maps.kinds.kind_names`, and :attr:`KindChoice.roles`
against :data:`sprezzature_maps.data.CHOROPLETH_ROLES`. A fourth kind of map,
or a third choropleth role, therefore needs no edit here — and cannot be
answered by a model until it really exists, which is the failure this shape is
guarding against: an invented kind name reads perfectly and renders nothing.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from sprezzature_maps.data import CHOROPLETH_ROLES
from sprezzature_maps.kinds import kind_names

#: What a reading concludes. Three states and not a number, because "ship it"
#: and "this cannot be read at all" are decisions, while the scores below are
#: observations — and a loop needs the decision to stop and the observations to
#: tell whether it is getting anywhere.
VERDICTS: tuple[str, ...] = ("satisfied", "needs_changes", "blocked")

#: What a column looks like, as a closed vocabulary. Deliberately coarse: the
#: distinctions that change which map can be drawn, and no others.
COLUMN_LOOKS: tuple[str, ...] = (
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "number",
    "date",
    "text",
)


class ColumnProfile(BaseModel):
    """One column, described without any of its values.

    Parameters
    ----------
    name : str
        The column header, as the file spells it.
    looks_like : str
        One of :data:`COLUMN_LOOKS`.
    distinct : int
        How many distinct values it holds. A country column has tens to a
        couple of hundred; a measurement has nearly as many as there are rows.
    nulls : int
        How many rows leave it empty.
    """

    name: str
    looks_like: str = "text"
    distinct: int = 0
    nulls: int = 0

    @field_validator("looks_like")
    @classmethod
    def _known_look(cls, value: str) -> str:
        if value not in COLUMN_LOOKS:
            raise ValueError(f"looks_like must be one of {', '.join(COLUMN_LOOKS)}, got {value!r}")
        return value


class DataProfile(BaseModel):
    """A dataset summarised to the point where it carries no data.

    This is the only description of the user's file that leaves this machine on
    a cloud backend: headers, shapes and counts. No cell value is ever part of
    a prompt — which is what lets the Studio ask a model about a dataset it
    would be wrong to upload.

    Parameters
    ----------
    rows : int
        Row count.
    columns : list of ColumnProfile
        One entry per column, in file order.
    source : str
        A name for the file, for the model's benefit. A bare file name, not a
        path: a path carries a user name and a directory layout, and neither
        helps answer which map to draw.
    """

    rows: int = 0
    columns: list[ColumnProfile] = Field(default_factory=list)
    source: str = ""


class KindChoice(BaseModel):
    """Which map to draw, and what to bind to what.

    Parameters
    ----------
    kind : str
        A registered kind name (``choropleth``, ``situation_map``,
        ``density``). Validated against the registry, so a plausible-sounding
        invention — ``heatmap``, ``bubble_map`` — is refused here rather than
        failing later inside a renderer.
    roles : dict
        Column bindings, ``role`` to column name, for the kinds that bind any.
        A choropleth binds :data:`sprezzature_maps.data.CHOROPLETH_ROLES`; the
        other two take their data positionally and leave this empty.
    title : str
        A title for the map, or empty to leave the renderer's default.
    why : str
        One or two sentences a person can disagree with. The Studio shows this
        next to the choice: a recommendation nobody can argue with is a
        recommendation nobody can correct.
    confidence : float
        0 to 1. Low confidence is a reason to show alternatives, not to refuse.
    alternatives : list of str
        Other registered kinds worth offering, best first.
    """

    kind: str
    roles: dict[str, str] = Field(default_factory=dict)
    title: str = ""
    why: str = ""
    confidence: float = 0.5
    alternatives: list[str] = Field(default_factory=list)

    @field_validator("kind")
    @classmethod
    def _registered(cls, value: str) -> str:
        known = kind_names()
        if value not in known:
            raise ValueError(f"kind must be one of {', '.join(known)}, got {value!r}")
        return value

    @field_validator("alternatives")
    @classmethod
    def _registered_alternatives(cls, value: list[str]) -> list[str]:
        known = kind_names()
        unknown = [v for v in value if v not in known]
        if unknown:
            raise ValueError(f"alternatives name no such kind: {', '.join(unknown)}")
        return value

    @field_validator("roles")
    @classmethod
    def _bindable_roles(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = [r for r in value if r not in CHOROPLETH_ROLES]
        if unknown:
            raise ValueError(
                f"roles names {', '.join(unknown)}, which no kind binds; "
                f"the bindable roles are {', '.join(CHOROPLETH_ROLES)}"
            )
        return value


class MapIssue(BaseModel):
    """Something wrong with a rendered map, as read off the image.

    Parameters
    ----------
    severity : str
        ``"blocking"`` if the map cannot be read, ``"notable"`` otherwise.
    what : str
        The problem, in a reader's words — "the legend's smallest two swatches
        are the same colour", not "palette error".
    fix : str
        What to change. Empty when the reader can see a problem but not a cure,
        which is an honest answer and better than an invented one.
    """

    severity: str = "notable"
    what: str = ""
    fix: str = ""

    @field_validator("severity")
    @classmethod
    def _known_severity(cls, value: str) -> str:
        if value not in ("blocking", "notable"):
            raise ValueError(f"severity must be blocking or notable, got {value!r}")
        return value


class MapReading(BaseModel):
    """What a vision model can actually read off a rendered map.

    The point is not a score. It is the comparison: a map asked for as a
    density map and *read back* as a choropleth has failed in a way no unit
    test of the renderer would catch, because every function returned
    successfully and the picture is wrong.

    Parameters
    ----------
    kind_seen : str
        The kind the image looks like, from the registry, or empty when the
        reader cannot tell — which is itself a finding.
    title_read : str
        The title as read off the image, letter for letter where possible. A
        title that renders outside the viewport comes back empty.
    legend_present, legend_readable : bool
        Whether a legend is there, and whether its labels can be read at the
        size they are drawn.
    issues : list of MapIssue
        Everything else, worst first.
    verdict : str
        One of :data:`VERDICTS`.
    readability, colour_separation, geographic_honesty, clarity,
    answers_the_question : int
        0 to 100, each judged by looking.

        Five, and they are a map's and not a chart's.
        ``sprezzature-figures`` scores message alignment, readability, visual
        hierarchy, accessibility and data fidelity; four of those transfer and
        one does not, because the way a *map* misleads has no analogue on a
        bar chart: an equal-area projection drawn as if it were conformal, a
        frame that crops the data, a colour ramp whose classes do not match
        how the values are actually distributed. That is
        ``geographic_honesty``, and it is the dimension worth having a
        separate number for.

        The scores exist so a loop can tell *progress* from *change*: a total
        that falls after a repair is a regression, and a loop that cannot see
        one will happily trade a legible legend for a cluttered coastline.
    """

    kind_seen: str = ""
    title_read: str = ""
    legend_present: bool = False
    legend_readable: bool = False
    verdict: str = "needs_changes"
    readability: int = 50
    colour_separation: int = 50
    geographic_honesty: int = 50
    clarity: int = 50
    answers_the_question: int = 50
    issues: list[MapIssue] = Field(default_factory=list)

    @field_validator("verdict")
    @classmethod
    def _known_verdict(cls, value: str) -> str:
        if value not in VERDICTS:
            raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}, got {value!r}")
        return value

    @field_validator(
        "readability", "colour_separation", "geographic_honesty", "clarity",
        "answers_the_question",
    )
    @classmethod
    def _in_range(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError(f"a score runs 0 to 100, got {value}")
        return value

    @field_validator("kind_seen")
    @classmethod
    def _registered_or_unsure(cls, value: str) -> str:
        if value and value not in kind_names():
            raise ValueError(
                f"kind_seen must be one of {', '.join(kind_names())} or empty, got {value!r}"
            )
        return value

    @property
    def blocking(self) -> list[MapIssue]:
        """The issues that make the map unreadable."""
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def score_total(self) -> int:
        """The five dimensions added up, 0 to 500.

        A total and not an average, because the comparison a loop makes is
        between two totals of its own rounds — and an average hides how many
        dimensions moved.
        """
        return (
            self.readability
            + self.colour_separation
            + self.geographic_honesty
            + self.clarity
            + self.answers_the_question
        )
