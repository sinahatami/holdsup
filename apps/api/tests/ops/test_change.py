import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from holdsup.ops import ChangeKind, OpError, change_between, compound_rate


@pytest.mark.parametrize(
    ("start", "end", "kind", "expected"),
    [
        (10.0, 15.0, ChangeKind.ABSOLUTE, 5.0),
        (10.0, 15.0, ChangeKind.PERCENT, 50.0),
        (-10.0, -5.0, ChangeKind.PERCENT, 50.0),  # relative to |start|: rising is positive
        (20.0, 10.0, ChangeKind.PERCENT, -50.0),
        (12.5, 10.0, ChangeKind.PERCENTAGE_POINTS, -2.5),
        (10.0, 5.0, ChangeKind.RATIO, 0.5),
        (0.0, 3.0, ChangeKind.ABSOLUTE, 3.0),
    ],
)
def test_change_between(start: float, end: float, kind: ChangeKind, expected: float) -> None:
    assert change_between(start, end, kind) == pytest.approx(expected)


@pytest.mark.parametrize("kind", [ChangeKind.PERCENT, ChangeKind.RATIO])
def test_zero_start_is_undefined_for_relative_changes(kind: ChangeKind) -> None:
    with pytest.raises(OpError, match="start value of 0"):
        change_between(0.0, 1.0, kind)


def test_compound_rate() -> None:
    assert compound_rate(100.0, 121.0, 2) == pytest.approx(10.0)
    assert compound_rate(100.0, 0.0, 3) == pytest.approx(-100.0)


@pytest.mark.parametrize(
    ("start", "end", "years", "match"),
    [
        (100.0, 110.0, 0, "end after the start"),
        (100.0, 110.0, -1, "end after the start"),
        (0.0, 110.0, 2, "positive start"),
        (-5.0, 110.0, 2, "positive start"),
        (100.0, -1.0, 2, "non-negative end"),
    ],
)
def test_compound_rate_rejects(start: float, end: float, years: float, match: str) -> None:
    with pytest.raises(OpError, match=match):
        compound_rate(start, end, years)


finite = st.floats(min_value=-1e9, max_value=1e9, allow_nan=False)
nonzero = finite.filter(lambda x: abs(x) > 1e-6)
positive = st.floats(min_value=1e-3, max_value=1e9)


@given(start=nonzero, end=finite)
def test_percent_change_applied_to_start_returns_end(start: float, end: float) -> None:
    pct = change_between(start, end, ChangeKind.PERCENT)
    assert math.isclose(start + abs(start) * pct / 100, end, rel_tol=1e-9, abs_tol=1e-6)


@given(start=nonzero, end=finite)
def test_ratio_times_start_returns_end(start: float, end: float) -> None:
    ratio = change_between(start, end, ChangeKind.RATIO)
    assert math.isclose(start * ratio, end, rel_tol=1e-9, abs_tol=1e-6)


@given(a=finite, b=finite)
def test_absolute_change_forward_is_minus_backward(a: float, b: float) -> None:
    assert change_between(a, b, ChangeKind.ABSOLUTE) == -change_between(b, a, ChangeKind.ABSOLUTE)


@given(start=positive, end=positive, years=st.integers(min_value=1, max_value=200))
def test_compounding_start_at_the_rate_returns_end(start: float, end: float, years: int) -> None:
    # Beyond a 10,000× change, 1 + rate/100 keeps too few digits for a round trip.
    assume(1e-4 <= end / start <= 1e4)
    rate = compound_rate(start, end, years)
    assert math.isclose(start * (1 + rate / 100) ** years, end, rel_tol=1e-7)


def test_overflow_is_an_error_not_infinity() -> None:
    with pytest.raises(OpError, match="percent change is not a finite number"):
        change_between(1e-308, 1e308, ChangeKind.PERCENT)
    with pytest.raises(OpError, match="ratio change is not a finite number"):
        change_between(1e-308, 1e308, ChangeKind.RATIO)
    with pytest.raises(OpError, match="compound growth rate is not a finite number"):
        compound_rate(1e-300, 1e300, 2)  # the ratio is already infinite
    with pytest.raises(OpError, match="compound growth rate is not a finite number"):
        compound_rate(1.0, 1e200, 0.5)  # the power overflows
