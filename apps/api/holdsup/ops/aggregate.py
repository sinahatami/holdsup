"""Yearly values from a monthly or quarterly series, for claims about a whole year."""

import math
from enum import StrEnum

from holdsup.ops.periods import Frequency, Period
from holdsup.ops.record import Flag, FlagCode, OpError
from holdsup.ops.series import Series


class AnnualValue(StrEnum):
    """How a year's value is made (the catalog's `annual_value`)."""

    MEAN = "mean"  # the average of the year's months or quarters
    END = "end"  # the year's last month or quarter


def _sub(frequency: Frequency) -> str:
    return "month" if frequency is Frequency.MONTHLY else "quarter"


def annual(series: Series, how: AnnualValue) -> Series:
    """One value per complete year: a year missing any month or quarter is left out (for
    `end`, a year without its last one), so a partial year never passes as a whole one."""
    if series.frequency is Frequency.ANNUAL:
        raise OpError(f"the {series.geo} series is already annual")
    n = series.frequency.per_year
    years: dict[int, list[tuple[Period, float]]] = {}
    for p, v in series.points:
        years.setdefault(p.year, []).append((p, v))
    values: dict[str, float] = {}
    for year, points in years.items():
        if how is AnnualValue.MEAN and len(points) == n:
            values[str(year)] = math.fsum(v for _, v in points) / n
        elif how is AnnualValue.END and points[-1][0].sub == n:
            values[str(year)] = points[-1][1]
    if not values:
        raise OpError(f"{series.geo} has no complete year of {series.frequency} values")
    return Series.from_values(series.geo, values, series.unit)


def annual_flag(frequency: Frequency, how: AnnualValue, years: list[str]) -> Flag:
    """The receipt's note on how the yearly values in an operation were made."""
    if how is AnnualValue.MEAN:
        made = f"the average of its {frequency.per_year} {frequency} values"
    else:
        made = f"its last {_sub(frequency)} (end of year)"
    return Flag(
        code=FlagCode.ANNUAL_VALUE,
        detail=f"each year's value is {made}; complete years only ({', '.join(years)})",
        items=years,
    )


def latest_year_flag(yearly: Series, native: Series) -> Flag:
    """'latest' among yearly values is the last complete year, not the latest month."""
    return Flag(
        code=FlagCode.LATEST_YEAR,
        detail=f"{yearly.geo}: latest is the last complete year, {yearly.last}; the latest "
        f"{_sub(native.frequency)} is {native.last}",
        requested="latest",
        used=str(yearly.last),
    )


def year_window(series: Series, start: str, end: str) -> tuple[str, str]:
    """A window given in whole years, in the series' own periods: 2008 → 2008-01 for the start,
    2015 → 2015-12 for the end ("latest" and finer periods pass through)."""

    def widen(text: str, last: bool) -> str:
        if len(text) != 4 or not text.isdigit():
            return text
        sub = series.frequency.per_year if last else 1
        return str(Period(int(text), sub, series.frequency))

    return widen(start, False), widen(end, True)
