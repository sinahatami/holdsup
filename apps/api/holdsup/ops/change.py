"""Scalar arithmetic behind the operations (golden rule 1: arithmetic lives here)."""

import math
from enum import StrEnum

from holdsup.ops.record import OpError, finite


class ChangeKind(StrEnum):
    ABSOLUTE = "absolute"  # end - start, in the series' unit
    PERCENT = "percent"  # relative change, in % of the start value
    PERCENTAGE_POINTS = "percentage_points"  # end - start, for series already in %
    RATIO = "ratio"  # end / start


def change_between(start: float, end: float, kind: ChangeKind) -> float:
    """Change from `start` to `end`. Percent and ratio need a non-zero start."""
    if kind in (ChangeKind.ABSOLUTE, ChangeKind.PERCENTAGE_POINTS):
        return end - start
    if start == 0:
        raise OpError(f"{kind} change is undefined for a start value of 0")
    if kind is ChangeKind.PERCENT:
        return finite((end - start) / abs(start) * 100, f"the {kind} change")
    return finite(end / start, f"the {kind} change")


def compound_rate(start: float, end: float, years: float) -> float:
    """Constant yearly growth in % that takes `start` to `end` in `years`."""
    if years <= 0:
        raise OpError("compound growth needs an end after the start")
    if start <= 0 or end < 0:
        raise OpError("compound growth needs a positive start and a non-negative end")
    try:
        rate = ((end / start) ** (1 / years) - 1) * 100
    except OverflowError:
        rate = math.inf
    return finite(rate, "the compound growth rate")
