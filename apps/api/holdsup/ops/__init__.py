"""Safe analysis operations: pure, typed, no I/O. The only place numbers users see are computed.

Each operation takes `Series` values and plain arguments and returns an `OpRecord` with its
inputs, output and flags; an `OpError` means it cannot give a meaningful answer.
"""

from holdsup.ops.aggregate import (
    AnnualValue,
    annual,
    annual_flag,
    latest_year_flag,
    year_window,
)
from holdsup.ops.change import ChangeKind, change_between, compound_rate
from holdsup.ops.periods import (
    LATEST,
    Frequency,
    Period,
    months_since,
    parse_period,
    published_by,
    years_between,
)
from holdsup.ops.record import DataPoint, Flag, FlagCode, OpError, OpRecord
from holdsup.ops.series import Series
from holdsup.ops.transforms import chain_index, deflate, per_capita
from holdsup.ops.trend import LinearFit, linear_fit, trend
from holdsup.ops.units import is_rate, per_person_unit, unit_scale
from holdsup.ops.values import cagr, change, compare, rank, value_at

__all__ = [
    "LATEST",
    "AnnualValue",
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
    "annual",
    "annual_flag",
    "cagr",
    "chain_index",
    "change",
    "change_between",
    "compare",
    "compound_rate",
    "deflate",
    "is_rate",
    "latest_year_flag",
    "linear_fit",
    "months_since",
    "parse_period",
    "per_capita",
    "per_person_unit",
    "published_by",
    "rank",
    "trend",
    "unit_scale",
    "value_at",
    "year_window",
    "years_between",
]
