"""A value against its neighbours: peaks, troughs, the typical level around a period, and the
noise in a series (for the change-point penalty). The change-point check (D025) reads these."""

import math
import statistics
from collections.abc import Sequence
from enum import StrEnum
from itertools import pairwise

from holdsup.ops.periods import Period
from holdsup.ops.series import Series


class Extreme(StrEnum):
    PEAK = "peak"  # higher than every value within reach on both sides
    TROUGH = "trough"  # lower than every value within reach on both sides


def around(series: Series, period: Period, reach: int) -> tuple[list[float], list[float]]:
    """The values up to `reach` periods before `period` and up to `reach` after it, without
    the value at `period` itself."""
    window = series.between(_shift(period, -reach), _shift(period, reach))
    left = [v for p, v in window if p.ordinal < period.ordinal]
    right = [v for p, v in window if p.ordinal > period.ordinal]
    return left, right


def extreme_at(series: Series, period: Period, reach: int) -> Extreme | None:
    """Whether the value at `period` is a peak or a trough among its neighbours. Both sides
    need a value: the last value of a series is never called a peak."""
    value = series.get(period)
    left, right = around(series, period, reach)
    if value is None or not left or not right:
        return None
    others = left + right
    if value > max(others):
        return Extreme.PEAK
    if value < min(others):
        return Extreme.TROUGH
    return None


def typical_level(series: Series, period: Period, reach: int) -> float | None:
    """The median of the neighbours within `reach` on both sides, or None if a side is empty."""
    left, right = around(series, period, reach)
    if not left or not right:
        return None
    return statistics.median(left + right)


def noise_scale(values: Sequence[float]) -> float:
    """A robust size of the period-to-period noise: the median absolute deviation of the
    differences of `values`, scaled to a standard deviation (1.4826 × MAD) and divided by √2
    because a difference adds two noises. 0 for fewer than three values."""
    if len(values) < 3:
        return 0.0
    diffs = [b - a for a, b in pairwise(values)]
    centre = statistics.median(diffs)
    mad = statistics.median(abs(d - centre) for d in diffs)
    return 1.4826 * mad / math.sqrt(2)


def _shift(period: Period, n: int) -> Period:
    ordinal = period.ordinal + n
    per = period.frequency.per_year
    year, sub0 = divmod(ordinal, per)
    return Period(year, sub0 + 1, period.frequency)
