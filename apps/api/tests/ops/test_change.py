import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import ChangeKind, change


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
def test_change(start: float, end: float, kind: ChangeKind, expected: float) -> None:
    assert change(start, end, kind) == pytest.approx(expected)


@pytest.mark.parametrize("kind", [ChangeKind.PERCENT, ChangeKind.RATIO])
def test_zero_start_is_undefined_for_relative_changes(kind: ChangeKind) -> None:
    with pytest.raises(ValueError, match="start value of 0"):
        change(0.0, 1.0, kind)


finite = st.floats(min_value=-1e9, max_value=1e9, allow_nan=False)
nonzero = finite.filter(lambda x: abs(x) > 1e-6)


@given(start=nonzero, end=finite)
def test_percent_change_applied_to_start_returns_end(start: float, end: float) -> None:
    pct = change(start, end, ChangeKind.PERCENT)
    assert math.isclose(start + abs(start) * pct / 100, end, rel_tol=1e-9, abs_tol=1e-6)


@given(start=nonzero, end=finite)
def test_ratio_times_start_returns_end(start: float, end: float) -> None:
    assert math.isclose(
        start * change(start, end, ChangeKind.RATIO), end, rel_tol=1e-9, abs_tol=1e-6
    )
