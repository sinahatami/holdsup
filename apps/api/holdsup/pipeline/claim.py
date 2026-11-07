"""The claim spec: what one statistical claim asserts, in a form code can check.

The model fills `Assertion` (it is part of the extraction schema); code builds `ClaimSpec` from
the model's answer after resolving periods and checking every number against the text.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field

# "2015", "2024-03", "2025-Q1"
PERIOD_RE = re.compile(r"^\d{4}(?:-(?:0[1-9]|1[0-2])|-Q[1-4])?$")
LATEST = "latest"
VAGUE_YEARS = 5  # "for years", "recently": the years before the claim date (Basis.ASSUMED)


class AssertionType(StrEnum):
    LEVEL = "level"  # "debt is 133% of GDP"
    ABSOLUTE = "absolute"  # "grew by 116 billion euros"
    PERCENT = "percent"  # "down 23% compared with 1990"
    PERCENTAGE_POINTS = "percentage_points"  # "fallen 12 points"
    RATIO = "ratio"  # "halved", "doubled"
    TREND = "trend"  # "is falling", "has been rising for years"
    RECORD = "record"  # "the lowest since 1977", "a record high"
    RANK = "rank"  # "the lowest in the EU", "faster than any country"
    COMPARE = "compare"  # "grown more than France and Germany"
    TARGET = "target"  # "met its 2020 renewables target"
    STREAK = "streak"  # "risen almost every single month"


# These map one to one onto `holdsup.ops.ChangeKind`.
CHANGE_TYPES = frozenset(
    {
        AssertionType.ABSOLUTE,
        AssertionType.PERCENT,
        AssertionType.PERCENTAGE_POINTS,
        AssertionType.RATIO,
    }
)


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class Basis(StrEnum):
    """Where a field's value came from; shown on the receipt."""

    STATED = "stated"  # written in the text
    INFERRED = "inferred"  # the model's reading of context (speaker, a well-known event)
    LOOKBACK = "lookback"  # code: "in the past 19 years" counted back from when it was said
    OFFICE = "office"  # code: a term of office from office_terms.yaml
    ASSUMED = "assumed"  # code: "for years", "recently" read as the 5 years before the claim date


class Operator(StrEnum):
    """How the asserted number bounds the true one."""

    ABOUT = "about"  # "fell 18%": within tolerance
    MORE_THAN = "more_than"  # "more than 18%", "over 18%"
    LESS_THAN = "less_than"  # "less than 5%", "under 5%"
    AT_LEAST = "at_least"  # "at least 2 million"
    AT_MOST = "at_most"  # "at most 3%", "no more than 3%"


class Assertion(BaseModel):
    type: AssertionType = Field(
        description="level, absolute, percent, percentage_points, ratio, trend, record, rank, "
        "compare, target or streak."
    )
    value: float | None = Field(
        description="The asserted number as written (a positive magnitude), e.g. 12 for "
        "'fallen 12 points'; 0.5 for 'halved', 2 for 'doubled'; null if none."
    )
    direction: Direction | None = Field(description="up, down or flat; null if not stated.")
    unit: str | None = Field(description="The unit as written: '%', 'points', 'billion euros'.")
    start_value: float | None = Field(description="X in 'from X to Y', else null.")
    end_value: float | None = Field(description="Y in 'from X to Y' or 'fell to Y', else null.")
    operator: Operator = Field(
        default=Operator.ABOUT,
        description="about, more_than ('more than 18%', 'over'), less_than ('under'), "
        "at_least or at_most ('no more than') for the asserted value.",
    )


class ClaimSpec(BaseModel):
    """One checkable claim, after code has resolved periods and checked numbers."""

    quote: str
    indicator_phrase: str
    geo: str | None
    geo_basis: Basis | None
    peers: list[str]
    start: str | None  # PERIOD_RE
    start_basis: Basis | None
    end: str | None  # PERIOD_RE or "latest"
    end_basis: Basis | None
    assertion: Assertion
    speaker: str | None
    said_on: str | None  # "YYYY", "YYYY-MM" or "YYYY-MM-DD"
    notes: list[str] = Field(default_factory=list)  # what code changed or could not verify
