import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import FlagCode, OpError, Series, linear_fit, trend


def test_trend_on_a_line() -> None:
    s = Series.from_values("IT", {str(y): 2.0 * (y - 2010) + 5 for y in range(2010, 2021)}, "%")
    r = trend(s, "2012", "2018")
    assert r.value == pytest.approx(2.0)
    assert r.extras == pytest.approx({"n": 7.0, "fitted_start": 9.0, "fitted_end": 21.0, "r2": 1.0})
    assert (r.unit, r.flags) == ("% per year", [])
    assert [p.period for p in r.inputs] == [str(y) for y in range(2012, 2019)]


def test_trend_monthly_slope_is_per_year() -> None:
    s = Series.from_values("IT", {f"2024-{m:02d}": float(m) for m in range(1, 13)})
    assert trend(s, "2024-01", "latest").value == pytest.approx(12.0)


def test_trend_half_yearly_slope_is_per_year() -> None:
    values = {f"{y}-S{h}": 3.0 * (y + (h - 1) / 2) for y in (2020, 2021, 2022) for h in (1, 2)}
    r = trend(Series.from_values("DE", values), "2020-S1", "latest")
    assert r.value == pytest.approx(3.0) and r.extras["n"] == 6.0


def test_trend_noisy_r2() -> None:
    s = Series.from_values("IT", {"2020": 1.0, "2021": 3.0, "2022": 2.0, "2023": 4.0})
    r = trend(s, "2020", "2023")
    assert r.value == pytest.approx(0.8)
    assert r.extras["r2"] == pytest.approx(0.64)


def test_trend_flags_a_window_the_data_does_not_cover() -> None:
    s = Series.from_values("IT", {"2015": 1.0, "2016": 2.0, "2017": 3.0})
    r = trend(s, "2010", "2020")
    [flag] = r.flags
    assert flag.code is FlagCode.WINDOW_NOT_COVERED
    assert (flag.requested, flag.used) == ("2010..2020", "2015..2017")


def test_trend_two_points_and_constant_series() -> None:
    s = Series.from_values("IT", {"2015": 4.0, "2016": 4.0})
    r = trend(s, "2015", "2016")
    assert r.value == 0.0
    assert "r2" not in r.extras
    assert [f.code for f in r.flags] == [FlagCode.FEW_POINTS, FlagCode.CONSTANT_SERIES]


def test_trend_rejects() -> None:
    s = Series.from_values("IT", {"2015": 1.0, "2020": 2.0})
    with pytest.raises(OpError, match="empty or reversed"):
        trend(s, "2018", "2016")
    with pytest.raises(OpError, match="fewer than two values"):
        trend(s, "2016", "2019")


def test_linear_fit_slope_overflow() -> None:
    with pytest.raises(OpError, match="slope is not a finite number"):
        linear_fit([0.0, 1e-150], [-1e300, 1e300])


def test_linear_fit_r2_is_undefined_when_the_spread_underflows() -> None:
    assert linear_fit([0.0, 1.0, 2.0], [0.0, 0.0, 5e-212]).r2 is None


def test_linear_fit_rejects() -> None:
    with pytest.raises(OpError, match="at least two points"):
        linear_fit([1.0], [1.0])
    with pytest.raises(OpError, match="at least two points"):
        linear_fit([1.0, 2.0], [1.0])
    with pytest.raises(OpError, match="two different times"):
        linear_fit([1.0, 1.0], [1.0, 2.0])


@given(
    # Slopes below 1e-6 sit under float resolution next to the intercept, so R² is noise.
    slope=st.floats(-1e3, 1e3).filter(lambda m: m == 0 or abs(m) >= 1e-6),
    intercept=st.floats(-1e4, 1e4),
    years=st.lists(st.integers(1950, 2030), min_size=2, max_size=40, unique=True),
)
def test_points_on_a_line_recover_its_slope(
    slope: float, intercept: float, years: list[int]
) -> None:
    fit = linear_fit([float(y) for y in years], [intercept + slope * (y - 1950) for y in years])
    assert fit.slope == pytest.approx(slope, abs=1e-6)
    assert fit.at(1950.0) == pytest.approx(intercept, abs=1e-4)
    if fit.r2 is not None:
        assert fit.r2 == pytest.approx(1.0)


@given(
    ys=st.lists(st.floats(-1e6, 1e6), min_size=3, max_size=30),
    shift=st.floats(-1e6, 1e6),
)
def test_shifting_values_keeps_the_slope_and_r2_in_range(ys: list[float], shift: float) -> None:
    xs = [float(i) for i in range(len(ys))]
    a, b = linear_fit(xs, ys), linear_fit(xs, [y + shift for y in ys])
    assert b.slope == pytest.approx(a.slope, rel=1e-6, abs=1e-3)
    for fit in (a, b):
        assert fit.r2 is None or 0.0 <= fit.r2 <= 1.0
