"""What every operation returns: its inputs, its output and anything a reader should know.

Records are the receipt: the explain step may only use numbers that appear in them, and the
exported notebook replays them.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field


class OpError(ValueError):
    """The operation cannot give a meaningful answer for these inputs (→ can't check)."""


def finite(value: float, what: str) -> float:
    """`value`, or an OpError if it overflowed to infinity or is not a number."""
    if not math.isfinite(value):
        raise OpError(f"{what} is not a finite number")
    return value


class DataPoint(BaseModel):
    geo: str
    period: str
    value: float


class FlagCode(StrEnum):
    NEAREST_PERIOD = "nearest_period"  # the requested period has no value; a neighbour was used
    MISSING_PERIODS = "missing_periods"  # periods present in only one input were dropped
    MISSING_GEOS = "missing_geos"  # places with no value for the period were left out of a rank
    TIE = "tie"  # the ranked place shares its position
    ZERO_DENOMINATOR = "zero_denominator"  # a ratio was left out because it divides by zero
    FEW_POINTS = "few_points"  # a fit through two points (R² is trivially 1)
    CONSTANT_SERIES = "constant_series"  # every value is equal, so R² is undefined
    WINDOW_NOT_COVERED = "window_not_covered"  # data starts after or ends before the window


class Flag(BaseModel):
    code: FlagCode
    detail: str
    requested: str | None = None
    used: str | None = None
    distance: int | None = None  # periods between requested and used
    items: list[str] = Field(default_factory=list)  # periods or geos the flag is about


ArgValue = str | float | int | bool | list[str] | None


class OpRecord(BaseModel):
    op: str
    args: dict[str, ArgValue]
    inputs: list[DataPoint]
    value: float | None = None  # the headline number of a scalar op
    extras: dict[str, float] = Field(default_factory=dict)  # other numbers it computed
    series: list[DataPoint] | None = None  # the output of a series op
    unit: str | None = None
    flags: list[Flag] = Field(default_factory=list)

    def numbers(self) -> list[float]:
        """Every number this record makes available to the explanation step."""
        out = [p.value for p in self.inputs]
        if self.value is not None:
            out.append(self.value)
        out.extend(self.extras.values())
        out.extend(p.value for p in self.series or [])
        return out
