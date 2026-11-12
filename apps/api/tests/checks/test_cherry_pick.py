"""The cherry-pick sweep on synthetic series with known answers (P3.1, D023)."""

from collections.abc import Sequence
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.checks import Sweep, sweep
from holdsup.ops import (
    ChangeKind,
    OpRecord,
    Series,
    cagr,
    change,
    compare,
    trend,
    value_at,
)
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction, Operator
from holdsup.verdict import Label, decide, load_tolerances

TOL = load_tolerances()
T, F = True, False


def claim(
    type: AssertionType = AssertionType.PERCENT,
    direction: Direction | None = Direction.UP,
    value: float | None = None,
    **assertion: Any,
) -> ClaimSpec:
    return ClaimSpec(
        quote="a claim",
        indicator_phrase="x",
        geo="IT",
        geo_basis=None,
        peers=[],
        start=None,
        start_basis=None,
        end=None,
        end_basis=None,
        assertion=Assertion(
            type=type,
            value=value,
            direction=direction,
            unit=None,
            start_value=assertion.pop("start_value", None),
            end_value=assertion.pop("end_value", None),
            **assertion,
        ),
        speaker=None,
        said_on=None,
    )


def annual(values: Sequence[float], first: int = 2010, unit: str | None = "%") -> Series:
    return Series.from_values("IT", {str(first + i): v for i, v in enumerate(values)}, unit)


def run(c: ClaimSpec, r: OpRecord, s: Series) -> Sweep:
    out = sweep(c, r, s, unit=s.unit, tolerances=TOL)
    assert out is not None
    return out


def cell(sw: Sweep, start: str, end: str) -> tuple[float | None, bool | None]:
    i, j = sw.starts.index(start), sw.ends.index(end)
    return sw.values[i][j], sw.holds[i][j]


def near(value: float, holds: bool) -> Any:  # Any: pytest.approx compares with a float
    """A cell's (value, holds) with the value up to float rounding."""
    return (pytest.approx(value), holds)


# --- grids with known answers ----------------------------------------------------------------


def test_a_known_grid() -> None:
    s = annual([10, 12, 11, 13])  # 2010 to 2013
    r = change(s, "2010", "2013", ChangeKind.ABSOLUTE)
    sw = run(claim(AssertionType.ABSOLUTE, Direction.UP, 3), r, s)

    assert sw.op == "change" and sw.kind == "absolute" and sw.unit == "%"
    assert sw.starts == sw.ends == ["2010", "2011", "2012", "2013"]
    n = None
    assert sw.values == [
        [n, 2.0, 1.0, 3.0],
        [n, n, -1.0, 1.0],
        [n, n, n, 2.0],
        [n, n, n, n],
    ]
    # The claim's number (3) is not asked of other windows: a rise of 1 still holds.
    assert sw.holds == [[n, T, T, T], [n, n, F, T], [n, n, n, T], [n, n, n, n]]
    assert (sw.claim_start, sw.claim_end) == ("2010", "2013")
    # Starts within 2 years of 2010 (no 2008 or 2009 in the data); ends up to 2 years before 2013.
    assert sw.near_starts == ["2010", "2011", "2012"]
    assert sw.near_ends == ["2011", "2012", "2013"]
    assert (sw.counted, sw.held, sw.windows) == (6, 5, 6)
    assert sw.share == pytest.approx(5 / 6)


# 2008 to 2017: a long fall with a trough in 2013.
TROUGH = annual([20, 19, 18, 17, 16, 10, 15, 14, 13, 12], first=2008)


def test_a_rise_from_a_trough_holds_in_few_nearby_windows() -> None:
    c = claim(AssertionType.PERCENT, Direction.UP, 20)  # "up 20% since 2013"
    r = change(TROUGH, "2013", "2017", ChangeKind.PERCENT)
    sw = run(c, r, TROUGH)

    assert sw.near_starts == ["2011", "2012", "2013", "2014", "2015"]
    assert sw.near_ends == ["2015", "2016", "2017"]
    # Only windows that start in 2013 rise: 3 of the 14 nearby windows (2015 → 2015 is none).
    assert (sw.counted, sw.held) == (14, 3)
    assert cell(sw, "2013", "2017") == near(20.0, True)
    assert cell(sw, "2012", "2017") == near(-25.0, False)

    # The verdict: the number holds for 2013 to 2017, the framing does not.
    alone = decide(c, [r], [0], unit="%", tolerances=TOL)
    swept = decide(c, [r], [0], unit="%", tolerances=TOL, window_share=sw.share)
    assert alone.label is Label.SUPPORTED
    assert swept.label is Label.SUPPORTED_FRAMING_MATTERS
    assert swept.window_share == pytest.approx(3 / 14)
    assert swept.reason == (
        "Holds within tolerance, but the rise shows in only 21% of nearby time windows."
    )


def test_a_steady_fall_holds_in_every_nearby_window() -> None:
    s = annual([12.0, 11.5, 11.1, 10.4, 10.0, 9.1, 8.8, 8.0, 7.7])
    c = claim(AssertionType.PERCENTAGE_POINTS, Direction.DOWN, 3.4)
    r = change(s, "2012", "2018", ChangeKind.PERCENTAGE_POINTS)
    sw = run(c, r, s)
    assert sw.counted == 15 and sw.share == 1.0
    v = decide(c, [r], [0], unit="%", tolerances=TOL, window_share=sw.share)
    assert v.label is Label.SUPPORTED


def test_a_failed_claim_stays_not_supported_whatever_the_windows() -> None:
    c = claim(AssertionType.PERCENT, Direction.UP, 80)  # the data says +20%
    r = change(TROUGH, "2013", "2017", ChangeKind.PERCENT)
    sw = run(c, r, TROUGH)
    v = decide(c, [r], [0], unit="%", tolerances=TOL, window_share=sw.share)
    assert v.label is Label.NOT_SUPPORTED


def test_bounds_and_stated_levels_are_not_swept() -> None:
    """'Rose more than 50%, from 10 to 12': each window is asked only whether it rose."""
    c = claim(
        AssertionType.PERCENT, Direction.UP, 50,
        operator=Operator.MORE_THAN, start_value=10, end_value=12,
    )  # fmt: skip
    r = change(TROUGH, "2013", "2017", ChangeKind.PERCENT)
    sw = run(c, r, TROUGH)
    assert cell(sw, "2013", "2014") == near(50.0, True)
    assert cell(sw, "2013", "2016") == near(30.0, True)


def test_a_ratio_claim_is_swept_as_ratios() -> None:
    s = annual([8, 4, 6, 2])
    r = change(s, "2010", "2013", ChangeKind.RATIO)
    sw = run(claim(AssertionType.RATIO, Direction.DOWN, 0.25), r, s)
    assert sw.kind == "ratio" and sw.unit is None
    assert cell(sw, "2010", "2011") == (0.5, True)
    assert cell(sw, "2011", "2012") == (1.5, False)


def test_a_flat_claim_holds_where_the_change_is_small() -> None:
    s = annual([100, 101, 110, 100.5])
    r = change(s, "2010", "2013", ChangeKind.PERCENT)
    sw = run(claim(AssertionType.PERCENT, Direction.FLAT, 0), r, s)
    assert cell(sw, "2010", "2011")[1] is True  # 1% is within 2% of the start
    assert cell(sw, "2010", "2012")[1] is False  # 10% is not
    assert cell(sw, "2010", "2013")[1] is True


def test_windows_without_an_answer_are_empty() -> None:
    s = annual([0, 2, 4, 8])
    pct = run(claim(), change(s, "2011", "2013", ChangeKind.PERCENT), s)
    assert cell(pct, "2010", "2012") == (None, None)  # a percent change from 0
    assert cell(pct, "2011", "2013") == near(300.0, True)

    growth = run(claim(), cagr(s, "2011", "2013"), s)
    assert growth.op == "cagr" and growth.kind is None and growth.unit == "% per year"
    assert cell(growth, "2010", "2013") == (None, None)  # compound growth from 0
    assert cell(growth, "2011", "2013") == near(100.0, True)


def test_a_window_reads_exact_periods_only() -> None:
    """A gap year is an empty row and column, never filled from a neighbour; the claim's own
    window is where its operation read, after any substitution."""
    s = Series.from_values("IT", {"2010": 1.0, "2012": 2.0, "2013": 3.0, "2014": 4.0}, "%")
    r = change(s, "2011", "2014", ChangeKind.ABSOLUTE, max_distance=1)  # 2011 → 2010
    sw = run(claim(AssertionType.ABSOLUTE), r, s)
    assert sw.starts == ["2010", "2011", "2012", "2013", "2014"]
    assert (sw.claim_start, sw.claim_end) == ("2010", "2014")
    assert sw.values[1] == [None] * 5
    assert [row[1] for row in sw.values] == [None] * 5


def test_a_trend_window_needs_a_clear_line() -> None:
    s = annual([1, 5, 2, 6, 3, 7])
    r = trend(s, "2010", "2015")
    sw = run(claim(AssertionType.TREND, Direction.UP), r, s)
    assert sw.op == "trend" and sw.unit == "% per year"
    assert cell(sw, "2010", "2011") == near(4.0, True)  # two points: R² is 1
    assert cell(sw, "2011", "2012") == near(-3.0, False)
    # Rising (slope 1.2), but R² 0.42 is under 0.5: no clear trend.
    assert cell(sw, "2010", "2013") == near(1.2, False)


# --- which windows ---------------------------------------------------------------------------


def test_monthly_windows_keep_their_place_in_the_year() -> None:
    s = Series.from_values(
        "IT", {f"{y}-{m:02d}": float(y * 12 + m) for y in range(2018, 2022) for m in range(1, 13)}
    )
    r = change(s, "2019-03", "2021-09", ChangeKind.ABSOLUTE)
    sw = run(claim(AssertionType.ABSOLUTE), r, s)
    assert sw.starts == ["2018-03", "2019-03", "2020-03", "2021-03"]
    assert sw.ends == ["2018-09", "2019-09", "2020-09", "2021-09"]
    assert (sw.claim_start, sw.claim_end) == ("2019-03", "2021-09")
    assert sw.near_ends == ["2019-09", "2020-09", "2021-09"]
    assert cell(sw, "2021-03", "2021-09") == (6.0, True)
    assert cell(sw, "2021-03", "2020-09") == (None, None)


def test_a_trend_over_whole_years_of_months_sweeps_whole_years() -> None:
    s = Series.from_values(
        "IT",
        {f"{y}-{m:02d}": float(-(y * 12 + m)) for y in range(2015, 2021) for m in range(1, 13)},
    )
    r = trend(s, "2016-01", "2020-12")
    sw = run(claim(AssertionType.TREND, Direction.DOWN), r, s)
    assert sw.starts[0] == "2015-01" and sw.ends[-1] == "2020-12"
    assert (sw.claim_start, sw.claim_end) == ("2016-01", "2020-12")
    assert sw.share == 1.0


def test_a_short_claim_gets_a_grid_but_no_share() -> None:
    """'Rose in 2013' is about that year; there was no window to pick."""
    r = change(TROUGH, "2013", "2014", ChangeKind.PERCENT)
    sw = run(claim(), r, TROUGH)
    assert sw.windows == 45
    assert (sw.near_starts, sw.near_ends, sw.counted, sw.held, sw.share) == ([], [], 0, 0, None)


def test_nearby_ends_never_move_later() -> None:
    s = annual(range(11))  # 2010 to 2020
    sw = run(claim(AssertionType.ABSOLUTE), change(s, "2012", "2015", ChangeKind.ABSOLUTE), s)
    assert sw.near_starts == ["2010", "2011", "2012", "2013", "2014"]
    assert sw.near_ends == ["2013", "2014", "2015"]
    assert sw.ends[-1] == "2020"  # the grid itself shows every end


def test_the_grid_keeps_the_last_fifty_years_and_the_claims_window() -> None:
    s = annual([float(i) for i in range(126)], first=1900)  # 1900 to 2025
    recent = run(claim(AssertionType.ABSOLUTE), change(s, "2000", "2020", ChangeKind.ABSOLUTE), s)
    assert (recent.starts[0], recent.starts[-1], len(recent.ends)) == ("1976", "2025", 50)
    old = run(claim(AssertionType.ABSOLUTE), change(s, "1950", "1960", ChangeKind.ABSOLUTE), s)
    assert old.starts[0] == "1948" and old.near_starts[0] == "1948"


def test_claims_that_pick_no_window_are_not_swept() -> None:
    s = annual([1, 2, 3])
    other = Series.from_values("FR", {"2010": 1.0, "2011": 2.0, "2012": 3.0}, "%")
    up = claim()
    assert sweep(up, value_at(s, "2012"), s, unit="%", tolerances=TOL) is None
    assert sweep(up, compare(s, other, "2012"), s, unit="%", tolerances=TOL) is None
    no_direction = claim(AssertionType.PERCENT, None, 5)  # "changed by 5%"
    r = change(s, "2010", "2012", ChangeKind.PERCENT)
    assert sweep(no_direction, r, s, unit="%", tolerances=TOL) is None


def test_a_record_from_another_series_is_not_swept() -> None:
    monthly = Series.from_values("IT", {"2020-01": 1.0, "2020-02": 2.0})
    r = change(annual([1, 2, 3]), "2010", "2012", ChangeKind.ABSOLUTE)
    assert sweep(claim(), r, monthly, unit=None, tolerances=TOL) is None


# --- properties ------------------------------------------------------------------------------

values = st.lists(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False), min_size=2, max_size=30
)


@given(
    values,
    st.data(),
    st.sampled_from(list(ChangeKind)),
    st.sampled_from(list(Direction)),
)
def test_sweep_invariants(
    ys: list[float], data: st.DataObject, kind: ChangeKind, direction: Direction
) -> None:
    s = annual(ys)
    i = data.draw(st.integers(0, len(ys) - 2))
    j = data.draw(st.integers(i + 1, len(ys) - 1))
    try:
        r = change(s, str(2010 + i), str(2010 + j), kind)
    except ValueError:
        return  # no answer for the claim's own window (a percent change from 0)
    sw = run(claim(direction=direction), r, s)

    for row, (vs, hs) in enumerate(zip(sw.values, sw.holds, strict=True)):
        assert len(vs) == len(hs) == len(sw.ends)
        for col, (v, h) in enumerate(zip(vs, hs, strict=True)):
            assert (v is None) == (h is None)
            if sw.starts[row] >= sw.ends[col]:
                assert v is None
    # The claim's own cell is the claim's own number.
    assert cell(sw, sw.claim_start, sw.claim_end)[0] == r.value
    assert 0 <= sw.held <= sw.counted
    assert sw.share is None or 0 <= sw.share <= 1
