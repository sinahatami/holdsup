import math
import statistics

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import Series, parse_period
from holdsup.ops.extremes import Extreme, around, extreme_at, noise_scale, typical_level


def annual(values: list[float], first: int = 2010) -> Series:
    return Series.from_values("IT", {str(first + i): v for i, v in enumerate(values)})


P = parse_period
ZIGZAG = annual([5, 7, 9, 6, 4, 6, 8])  # 2010 to 2016: a peak in 2012, a trough in 2014


def test_around_takes_reach_periods_each_side() -> None:
    assert around(ZIGZAG, P("2012"), 2) == ([5, 7], [6, 4])
    assert around(ZIGZAG, P("2010"), 2) == ([], [7, 9])
    assert around(ZIGZAG, P("2016"), 1) == ([6], [])


def test_around_counts_periods_across_years() -> None:
    monthly = Series.from_values(
        "IT", {"2019-11": 1.0, "2019-12": 2.0, "2020-01": 3.0, "2020-02": 4.0}
    )
    assert around(monthly, P("2019-12"), 1) == ([1.0], [3.0])


def test_peaks_and_troughs_need_neighbours_on_both_sides() -> None:
    assert extreme_at(ZIGZAG, P("2012"), 2) is Extreme.PEAK
    assert extreme_at(ZIGZAG, P("2014"), 2) is Extreme.TROUGH
    assert extreme_at(ZIGZAG, P("2013"), 2) is None
    assert extreme_at(ZIGZAG, P("2016"), 2) is None  # the last value: no right side
    assert extreme_at(ZIGZAG, P("2010"), 2) is None
    assert extreme_at(ZIGZAG, P("2020"), 2) is None  # no value there
    flat = annual([3, 3, 3])
    assert extreme_at(flat, P("2011"), 1) is None  # equal is not higher


def test_typical_level_is_the_median_of_the_neighbours() -> None:
    assert typical_level(ZIGZAG, P("2012"), 2) == 5.5  # median of 5, 7, 6, 4
    assert typical_level(ZIGZAG, P("2016"), 2) is None
    assert typical_level(ZIGZAG, P("2010"), 1) is None


def test_noise_scale_is_robust_to_one_jump() -> None:
    assert noise_scale([1.0, 2.0]) == 0.0
    assert noise_scale([1.0, 2.0, 3.0, 4.0]) == 0.0  # a straight line has no noise
    # Differences 1, -1, 1, -1, 101, -1, 1: median 1, absolute deviations' median 2. The jump
    # of 101 moves neither median.
    jumpy = [0.0, 1.0, 0.0, 1.0, 0.0, 101.0, 100.0, 101.0]
    assert noise_scale(jumpy) == pytest.approx(1.4826 * 2 / math.sqrt(2))


@given(st.lists(st.floats(-1e6, 1e6), min_size=3, max_size=20), st.integers(1, 3), st.data())
def test_extremes_and_typical_level_agree_with_the_neighbours(
    ys: list[float], reach: int, data: st.DataObject
) -> None:
    s = annual(ys)
    i = data.draw(st.integers(0, len(ys) - 1))
    at = P(str(2010 + i))
    left, right = around(s, at, reach)
    assert len(left) == min(i, reach) and len(right) == min(len(ys) - 1 - i, reach)
    kind = extreme_at(s, at, reach)
    typical = typical_level(s, at, reach)
    if not left or not right:
        assert kind is None and typical is None
        return
    assert typical == statistics.median(left + right)
    assert min(left + right) <= typical <= max(left + right)
    if kind is Extreme.PEAK:
        assert ys[i] > max(left + right)
    elif kind is Extreme.TROUGH:
        assert ys[i] < min(left + right)
    else:
        assert min(left + right) <= ys[i] <= max(left + right)
    assert noise_scale(ys) >= 0
