"""Periods as sources write them: "2024", "2024-Q1", "2024-03"."""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from holdsup.ops.record import OpError

LATEST = "latest"

_PERIOD_RE = re.compile(r"^(\d{4})(?:-(0[1-9]|1[0-2])|-Q([1-4]))?$")


class Frequency(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"

    @property
    def per_year(self) -> int:
        return {Frequency.ANNUAL: 1, Frequency.QUARTERLY: 4, Frequency.MONTHLY: 12}[self]


@dataclass(frozen=True)
class Period:
    year: int
    sub: int  # 1 for annual; the quarter (1-4) or month (1-12) otherwise
    frequency: Frequency

    @property
    def ordinal(self) -> int:
        """Position on a count of periods of this frequency; consecutive periods differ by 1."""
        return self.year * self.frequency.per_year + self.sub - 1

    @property
    def time(self) -> float:
        """Start of the period in years, e.g. 2024-Q3 → 2024.5 (the x of a trend fit)."""
        return self.year + (self.sub - 1) / self.frequency.per_year

    def __str__(self) -> str:
        if self.frequency is Frequency.QUARTERLY:
            return f"{self.year}-Q{self.sub}"
        if self.frequency is Frequency.MONTHLY:
            return f"{self.year}-{self.sub:02d}"
        return str(self.year)


def parse_period(text: str) -> Period:
    match = _PERIOD_RE.match(text)
    if match is None:
        raise OpError(f"unsupported period {text!r} (expected YYYY, YYYY-Qn or YYYY-MM)")
    year, month, quarter = match.groups()
    if month is not None:
        return Period(int(year), int(month), Frequency.MONTHLY)
    if quarter is not None:
        return Period(int(year), int(quarter), Frequency.QUARTERLY)
    return Period(int(year), 1, Frequency.ANNUAL)


def periods_between(start: Period, end: Period) -> int:
    """Number of periods from `start` to `end` (negative if `end` is earlier)."""
    same_frequency(start, end)
    return end.ordinal - start.ordinal


def years_between(start: Period, end: Period) -> float:
    return periods_between(start, end) / start.frequency.per_year


def same_frequency(a: Period, b: Period) -> None:
    if a.frequency is not b.frequency:
        raise OpError(f"period {a} is {a.frequency} but {b} is {b.frequency}")


def published_by(frequency: Frequency, as_of: date, lag_months: int) -> Period:
    """The last period of `frequency` out by `as_of`, if a period is published `lag_months`
    after it ends: 2018-12-31 with a 1-month lag gives 2018-11 (monthly), 2017 (annual)."""
    if lag_months < 0:
        raise OpError("a publication lag cannot be negative")
    # The last month whose data could be out: the period must end by then.
    month = as_of.year * 12 + as_of.month - 1 - lag_months
    year, month0 = divmod(month, 12)
    months_per = 12 // frequency.per_year
    sub = (month0 + 1) // months_per  # periods of this frequency complete by that month
    if sub == 0:
        return Period(year - 1, frequency.per_year, frequency)
    return Period(year, sub, frequency)
