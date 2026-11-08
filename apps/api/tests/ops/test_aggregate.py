"""Yearly values from monthly and quarterly series."""

import pytest

from holdsup.ops import (
    AnnualValue,
    FlagCode,
    Frequency,
    OpError,
    Series,
    annual,
    annual_flag,
    latest_year_flag,
    year_window,
)

MONTHS = {f"2015-{m:02d}": float(m) for m in range(1, 13)}  # mean 6.5, December 12
PARTIAL = {f"2016-{m:02d}": 20.0 for m in range(1, 10)}  # January to September only


def test_mean_of_complete_years_only() -> None:
    s = annual(Series.from_values("IT", {**MONTHS, **PARTIAL}, "%"), AnnualValue.MEAN)
    assert s.frequency is Frequency.ANNUAL and s.unit == "%"
    assert [(str(p), v) for p, v in s.points] == [("2015", 6.5)]  # 2016 is incomplete


def test_end_of_year_needs_the_last_period() -> None:
    quarters = {"2015-Q1": 1.0, "2015-Q2": 2.0, "2015-Q4": 4.0, "2016-Q1": 5.0}
    s = annual(Series.from_values("IT", quarters), AnnualValue.END)
    assert [(str(p), v) for p, v in s.points] == [("2015", 4.0)]  # no 2016-Q4


def test_half_years_make_a_year_too() -> None:
    halves = {"2015-S1": 10.0, "2015-S2": 14.0, "2016-S1": 20.0, "2017-S1": 1.0, "2017-S2": 3.0}
    series = Series.from_values("DE", halves, "euro")
    assert series.frequency is Frequency.SEMIANNUAL
    mean = annual(series, AnnualValue.MEAN)
    assert [(str(p), v) for p, v in mean.points] == [("2015", 12.0), ("2017", 2.0)]  # 2016: no S2
    end = annual(series, AnnualValue.END)
    assert [(str(p), v) for p, v in end.points] == [("2015", 14.0), ("2017", 3.0)]
    with pytest.raises(OpError, match="no complete year of semiannual values"):
        annual(Series.from_values("DE", {"2016-S1": 20.0}), AnnualValue.MEAN)


def test_no_complete_year_is_an_error() -> None:
    with pytest.raises(OpError, match="no complete year of monthly values"):
        annual(Series.from_values("IT", PARTIAL), AnnualValue.MEAN)


def test_an_annual_series_is_not_aggregated() -> None:
    with pytest.raises(OpError, match="already annual"):
        annual(Series.from_values("IT", {"2015": 1.0}), AnnualValue.MEAN)


def test_flags_say_how_and_which_years() -> None:
    mean = annual_flag(Frequency.MONTHLY, AnnualValue.MEAN, ["2015", "2023"])
    assert mean.code is FlagCode.ANNUAL_VALUE and mean.items == ["2015", "2023"]
    assert mean.detail == (
        "each year's value is the average of its 12 monthly values; complete years only "
        "(2015, 2023)"
    )
    end = annual_flag(Frequency.QUARTERLY, AnnualValue.END, ["2020"])
    assert end.detail.startswith("each year's value is its last quarter (end of year)")
    halves = annual_flag(Frequency.SEMIANNUAL, AnnualValue.MEAN, ["2020"])
    assert "the average of its 2 semiannual values" in halves.detail
    last_half = annual_flag(Frequency.SEMIANNUAL, AnnualValue.END, ["2020"])
    assert "its last half-year (end of year)" in last_half.detail

    native = Series.from_values("IT", {**MONTHS, **PARTIAL})
    latest = latest_year_flag(annual(native, AnnualValue.MEAN), native)
    assert (latest.code, latest.used) == (FlagCode.LATEST_YEAR, "2015")
    assert (
        latest.detail == "IT: latest is the last complete year, 2015; the latest month is 2016-09"
    )


def test_year_window_widens_whole_years() -> None:
    monthly = Series.from_values("IT", MONTHS)
    assert year_window(monthly, "2008", "2015") == ("2008-01", "2015-12")
    assert year_window(monthly, "2008-03", "latest") == ("2008-03", "latest")
    quarterly = Series.from_values("IT", {"2015-Q1": 1.0})
    assert year_window(quarterly, "2008", "2015") == ("2008-Q1", "2015-Q4")
    halves = Series.from_values("DE", {"2015-S1": 1.0})
    assert year_window(halves, "2008", "2015") == ("2008-S1", "2015-S2")
    halves_native = Series.from_values("DE", {"2015-S1": 1.0, "2015-S2": 2.0, "2016-S1": 3.0})
    latest = latest_year_flag(annual(halves_native, AnnualValue.MEAN), halves_native)
    assert (
        latest.detail
        == "DE: latest is the last complete year, 2015; the latest half-year is 2016-S1"
    )
