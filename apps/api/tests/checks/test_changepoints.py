"""Change points on synthetic series with known breaks, and the start-or-end flag (P3.3, D025)."""

from typing import Any

import pytest

from holdsup.checks import EndpointFlag, change_points, flag_text
from holdsup.checks.changepoints import endpoint_flags, find_breaks
from holdsup.ops import ChangeKind, Series, cagr, change, parse_period, trend, value_at
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction
from holdsup.verdict import Label, decide, load_tolerances

TOL = load_tolerances()


def claim(direction: Direction | None, type: AssertionType = AssertionType.PERCENT) -> ClaimSpec:
    return ClaimSpec(
        quote="a claim", indicator_phrase="x", geo="IT", geo_basis=None, peers=[],
        start=None, start_basis=None, end=None, end_basis=None,
        assertion=Assertion(type=type, value=None, direction=direction, unit=None,
                            start_value=None, end_value=None),
        speaker=None, said_on=None,
    )  # fmt: skip


def annual(values: list[float], first: int = 2010) -> Series:
    return Series.from_values("IT", {str(first + i): v for i, v in enumerate(values)}, "%")


def wiggle(i: int) -> float:
    """A small fixed noise, so the tests do not depend on a random seed."""
    return 0.05 * ((i * 7) % 5 - 2)


def flags(c: ClaimSpec, s: Series, r: Any) -> list[EndpointFlag]:
    return endpoint_flags(c, r, s, find_breaks(s), tolerances=TOL)


# --- breaks ----------------------------------------------------------------------------------


def test_a_turn_in_the_trend_is_found_where_it_turns() -> None:
    # Up one a year from 2010 to 2020, then down one a year to 2030.
    s = annual([(i if i <= 10 else 20 - i) + wiggle(i) for i in range(21)])
    assert [str(p) for p in find_breaks(s)] == ["2020"]


def test_a_steady_trend_has_no_break() -> None:
    s = annual([30 - 0.5 * i + wiggle(i) for i in range(30)])
    assert find_breaks(s) == []


def test_a_level_jump_turns_the_trend_around_it() -> None:
    s = annual([(10 if i < 10 else 14) + wiggle(i) for i in range(20)])
    found = [p.year for p in find_breaks(s)]
    assert found and all(abs(y - 2019.5) <= 2 for y in found)  # around the 2019→2020 jump


def test_a_noiseless_kink_is_found() -> None:
    s = annual([float(min(i, 8)) for i in range(16)])
    assert [str(p) for p in find_breaks(s)] == ["2018"]


def test_a_short_series_has_no_break() -> None:
    assert find_breaks(annual([1, 5, 1, 5, 1])) == []


# --- the flag --------------------------------------------------------------------------------

# 2013 to 2023: steady around 8, with a one-year spike to 11.9 in 2015.
SPIKE_VALUES = [7.0, 7.5, 11.9, 8.0, 7.9, 8.1, 8.3, 8.4, 8.2, 8.0, 7.9]
SPIKE = annual(SPIKE_VALUES, first=2013)


def test_a_fall_from_a_spike_is_flagged() -> None:
    r = change(SPIKE, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    [f] = flags(claim(Direction.DOWN), SPIKE, r)
    assert (f.end, f.period, f.why) == ("start", "2015", "peak")
    assert f.value == 11.9 and f.typical == pytest.approx(7.7)  # median of 7, 7.5, 8, 7.9
    assert f.claimed == pytest.approx(-4.0) and f.shifted == pytest.approx(0.2)
    assert flag_text(f, r.unit) == (
        "it starts at a peak (2015): from the usual level around then, 7.7, the change is "
        "+0.2 percentage points rather than -4 percentage points"
    )


def test_a_start_that_moves_the_change_a_little_is_not_flagged() -> None:
    # r001's shape: 2015 sits beside the 2014 peak, but the usual level around it is close.
    s = annual([12.1, 12.7, 12.02, 11.7, 11.2, 10.6, 9.9, 9.3, 9.5, 8.1, 7.68], first=2013)
    r = change(s, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    assert flags(claim(Direction.DOWN), s, r) == []


def test_a_trough_is_flagged_where_it_carries_the_claim_and_not_where_it_hides_it() -> None:
    s = annual([17.0, 16.0, 10.0, 15.0, 14.0, 13.0, 12.0], first=2011)
    up = change(s, "2013", "2017", ChangeKind.PERCENT)  # a rise from the trough
    [f] = flags(claim(Direction.UP), s, up)
    assert (f.end, f.why, f.typical) == ("start", "trough", 15.5)
    assert f.shifted < 0 < f.claimed
    down = change(s, "2011", "2013", ChangeKind.PERCENT)  # a fall to the trough
    [f] = flags(claim(Direction.DOWN), s, down)
    assert (f.end, f.why) == ("end", "trough")
    assert f.claimed == pytest.approx(-41.18, abs=0.01) and f.shifted == pytest.approx(
        -8.82, abs=0.01
    )
    # A fall that starts at the trough: from the usual level the fall would be larger.
    later = annual([17.0, 16.0, 10.0, 15.0, 14.0, 13.0, 9.0], first=2011)
    assert (
        flags(claim(Direction.DOWN), later, change(later, "2013", "2017", ChangeKind.PERCENT)) == []
    )


def test_a_rise_that_ends_on_a_peak_is_flagged() -> None:
    s = annual([10.0, 10.5, 11.0, 11.2, 16.0, 11.4, 11.5], first=2010)
    r = change(s, "2010", "2014", ChangeKind.ABSOLUTE)
    [f] = flags(claim(Direction.UP, AssertionType.ABSOLUTE), s, r)
    assert (f.end, f.period, f.why) == ("end", "2014", "peak")
    assert f.typical == pytest.approx(11.3) and f.shifted == pytest.approx(1.3)


def test_a_start_next_to_a_break_can_carry_the_claim() -> None:
    # Flat at 10, then a jump to 20 in 2015: 2014 is no trough (2012 and 2013 are equal), but
    # the trend turns beside it and the rise from 2014 is half the rise from the level there.
    s = annual([10.0] * 5 + [20.0] * 6)
    r = change(s, "2014", "2020", ChangeKind.ABSOLUTE)
    [f] = flags(claim(Direction.UP, AssertionType.ABSOLUTE), s, r)
    assert (f.why, f.typical, f.claimed, f.shifted) == ("break", 15.0, 10.0, 5.0)


# Italy's debt in % of GDP, 2008 to 2019 (Eurostat, rounded): it rises to 2014, then levels off.
DEBT = annual(
    [106.2, 116.6, 119.2, 119.7, 126.1, 132.0, 135.4, 135.3, 134.8, 134.2, 134.4, 134.1], 2008
)


def test_a_window_shorter_than_the_sweeps_is_not_read() -> None:
    # The c007 smoke claim: "up from 127% in 2012" to 132.6% in 2013. The trend turns in 2014,
    # and the usual level around 2013 (the median of 2011, 2012, 2014 and 2015) takes in the
    # claim's own start, so without the rule the one-year rise would be flagged.
    c = claim(Direction.UP, AssertionType.PERCENTAGE_POINTS)
    r = change(DEBT, "2012", "2013", ChangeKind.PERCENTAGE_POINTS)
    assert TOL.sweep.min_years == 2
    assert flags(c, DEBT, r) == []
    every = TOL.model_copy(update={"sweep": TOL.sweep.model_copy(update={"min_years": 0})})
    [f] = endpoint_flags(c, r, DEBT, find_breaks(DEBT), tolerances=every)
    assert (f.end, f.period, f.why) == ("end", "2013", "break")
    assert f.typical == pytest.approx(130.7)  # the median of 119.7, 126.1, 135.3 and 135.4
    # A window of the sweep's length is read: the fall to the 2013 trough over two years.
    s = annual([17.0, 16.0, 10.0, 15.0, 14.0, 13.0, 12.0], first=2011)
    assert flags(claim(Direction.DOWN), s, change(s, "2012", "2013", ChangeKind.PERCENT)) == []
    [f] = flags(claim(Direction.DOWN), s, change(s, "2011", "2013", ChangeKind.PERCENT))
    assert (f.end, f.why) == ("end", "trough")


def test_ratios_are_compared_on_a_log_scale() -> None:
    s = annual([4.0, 4.2, 8.0, 4.1, 3.9, 2.0], first=2010)
    r = change(s, "2012", "2015", ChangeKind.RATIO)  # "quartered" from a peak
    [f] = flags(claim(Direction.DOWN, AssertionType.RATIO), s, r)
    assert f.why == "peak" and f.shifted == pytest.approx(2.0 / 4.05)
    assert flag_text(f, r.unit).endswith("the change is +0.49 rather than +0.25")
    negative = annual([1.0, 2.0, 4.0, 1.0, 0.5, -1.0])
    r = change(negative, "2012", "2015", ChangeKind.RATIO)
    assert flags(claim(Direction.DOWN, AssertionType.RATIO), negative, r) == []


def test_growth_rates_are_rerun_as_growth_rates() -> None:
    s = annual([5.0, 4.0, 1.0, 4.5, 5.0, 6.0], first=2010)
    r = cagr(s, "2012", "2015")
    [f] = flags(claim(Direction.UP), s, r)
    assert f.why == "trough" and f.claimed == pytest.approx(81.7, abs=0.1)
    assert flag_text(f, r.unit).endswith("% per year")
    # 2012 is a peak among negative values: the usual level around it is below 0, and no
    # growth rate starts there.
    below = annual([-5.0, -4.0, 1.0, -4.5, -3.0, 6.0], first=2010)
    assert flags(claim(Direction.UP), below, cagr(below, "2012", "2015")) == []


def test_no_flag_without_a_rise_or_fall_or_when_the_claim_does_not_hold() -> None:
    r = change(SPIKE, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    assert flags(claim(None), SPIKE, r) == []
    assert flags(claim(Direction.FLAT), SPIKE, r) == []
    # "Rose since 2015": the window falls, so the start carries nothing for the claim.
    assert flags(claim(Direction.UP), SPIKE, r) == []
    monthly = Series.from_values("IT", {f"2020-{m:02d}": float(m) for m in range(1, 13)})
    assert flags(claim(Direction.DOWN), monthly, r) == []  # the record is not this series'


# --- what the run gets -----------------------------------------------------------------------


def test_change_points_for_a_window_and_none_for_a_single_value() -> None:
    r = change(SPIKE, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    cp = change_points(claim(Direction.DOWN), r, SPIKE, tolerances=TOL)
    assert cp is not None and [f.period for f in cp.flags] == ["2015"]
    assert all(isinstance(b, str) for b in cp.breaks)
    assert (
        change_points(claim(Direction.DOWN), value_at(SPIKE, "2015"), SPIKE, tolerances=TOL) is None
    )


def test_a_trend_is_read_from_its_first_value_to_its_last() -> None:
    # "Fell from 11.9 in 2015 to 7.9 in 2023", planned as a trend: the start is the spike.
    c = claim(Direction.DOWN, AssertionType.TREND)
    cp = change_points(c, trend(SPIKE, "2015", "2023"), SPIKE, tolerances=TOL)
    assert cp is not None and [f.period for f in cp.flags] == ["2015"]
    [f] = cp.flags
    assert (f.end, f.why, f.value, f.typical) == ("start", "peak", 11.9, 7.7)
    assert f.claimed == pytest.approx(-4.0)  # an absolute change, 7.9 - 11.9
    assert f.shifted == pytest.approx(0.2)  # 7.9 - 7.7: it did not fall


def test_a_trend_is_not_flagged_when_it_is_flat_or_has_no_value_at_an_end() -> None:
    r = trend(SPIKE, "2015", "2023")
    assert flags(claim(Direction.FLAT, AssertionType.TREND), SPIKE, r) == []
    assert flags(claim(None, AssertionType.TREND), SPIKE, r) == []
    values = dict(zip(range(2013, 2024), SPIKE_VALUES, strict=True))
    del values[2022]  # no value at the end the claim names
    gap = Series.from_values("IT", {str(y): v for y, v in values.items()}, "%")
    assert flags(claim(Direction.DOWN, AssertionType.TREND), gap, trend(gap, "2015", "2022")) == []


def test_a_trend_with_a_steady_fall_has_no_flag() -> None:
    steady = annual([12 - 0.5 * i for i in range(11)], 2013)
    c = claim(Direction.DOWN, AssertionType.TREND)
    assert flags(c, steady, trend(steady, "2015", "2023")) == []


def test_a_trend_at_another_frequency_than_the_series_is_not_read() -> None:
    monthly = Series.from_values("IT", {f"2020-{m:02d}": float(m) for m in range(1, 13)})
    r = trend(SPIKE, "2015", "2023")  # an annual record against a monthly series
    assert flags(claim(Direction.UP, AssertionType.TREND), monthly, r) == []


def test_the_flag_turns_supported_into_framing_matters() -> None:
    c = claim(Direction.DOWN, AssertionType.PERCENTAGE_POINTS).model_copy(
        update={"assertion": Assertion(type=AssertionType.PERCENTAGE_POINTS, value=4,
                                       direction=Direction.DOWN, unit="points",
                                       start_value=None, end_value=None)}
    )  # fmt: skip
    r = change(SPIKE, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    [f] = flags(c, SPIKE, r)
    assert decide(c, [r], [0], unit="%", tolerances=TOL).label is Label.SUPPORTED
    v = decide(c, [r], [0], unit="%", tolerances=TOL, distortions=[flag_text(f, r.unit)])
    assert v.label is Label.SUPPORTED_FRAMING_MATTERS
    assert v.reason.startswith("Holds within tolerance, but it starts at a peak (2015)")
    assert v.distortions == [flag_text(f, r.unit)]
    assert parse_period(f.period).year == 2015
