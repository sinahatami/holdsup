"""Safe analysis operations: pure, typed, no I/O. The only place numbers users see are computed.

Each operation takes `Series` values and plain arguments and returns an `OpRecord` with its
inputs, output and flags; an `OpError` means it cannot give a meaningful answer.
"""

from holdsup.ops.change import ChangeKind, change_between, compound_rate
from holdsup.ops.periods import LATEST, Frequency, Period, parse_period, years_between
from holdsup.ops.record import DataPoint, Flag, FlagCode, OpError, OpRecord
from holdsup.ops.series import Series
from holdsup.ops.transforms import deflate, per_capita
from holdsup.ops.trend import LinearFit, linear_fit, trend
from holdsup.ops.values import cagr, change, compare, rank, value_at

__all__ = [
    "LATEST",
    "ChangeKind",
    "DataPoint",
    "Flag",
    "FlagCode",
    "Frequency",
    "LinearFit",
    "OpError",
    "OpRecord",
    "Period",
    "Series",
    "cagr",
    "change",
    "change_between",
    "compare",
    "compound_rate",
    "deflate",
    "linear_fit",
    "parse_period",
    "per_capita",
    "rank",
    "trend",
    "value_at",
    "years_between",
]
