from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import Frequency, OpError, Period, parse_period, published_by, years_between
from holdsup.ops.periods import periods_between


@pytest.mark.parametrize(
    ("text", "year", "sub", "frequency", "time"),
    [
        ("2024", 2024, 1, Frequency.ANNUAL, 2024.0),
        ("2024-Q3", 2024, 3, Frequency.QUARTERLY, 2024.5),
        ("2024-03", 2024, 3, Frequency.MONTHLY, 2024 + 2 / 12),
    ],
)
def test_parse_period(text: str, year: int, sub: int, frequency: Frequency, time: float) -> None:
    p = parse_period(text)
    assert (p.year, p.sub, p.frequency) == (year, sub, frequency)
    assert p.time == pytest.approx(time)
    assert str(p) == text


@pytest.mark.parametrize("text", ["24", "2024-13", "2024-Q5", "2024M03", "2024-03-01", "latest"])
def test_parse_period_rejects(text: str) -> None:
    with pytest.raises(OpError, match="unsupported period"):
        parse_period(text)


def test_years_between() -> None:
    assert years_between(parse_period("2015"), parse_period("2020")) == 5
    assert years_between(parse_period("2023-Q4"), parse_period("2024-Q2")) == 0.5
    assert years_between(parse_period("2024-12"), parse_period("2024-03")) == -0.75


def test_periods_of_different_frequencies_do_not_mix() -> None:
    with pytest.raises(OpError, match="is annual but"):
        periods_between(parse_period("2015"), parse_period("2020-Q1"))


periods = st.one_of(
    st.builds(Period, st.integers(1800, 2100), st.just(1), st.just(Frequency.ANNUAL)),
    st.builds(Period, st.integers(1800, 2100), st.integers(1, 4), st.just(Frequency.QUARTERLY)),
    st.builds(Period, st.integers(1800, 2100), st.integers(1, 12), st.just(Frequency.MONTHLY)),
)


@given(p=periods)
def test_label_round_trips(p: Period) -> None:
    assert parse_period(str(p)) == p


@given(year=st.integers(1800, 2100), a=st.integers(1, 12), b=st.integers(1, 12))
def test_years_between_matches_the_time_axis(year: int, a: int, b: int) -> None:
    pa, pb = Period(year, a, Frequency.MONTHLY), Period(year + 1, b, Frequency.MONTHLY)
    assert years_between(pa, pb) == pytest.approx(pb.time - pa.time)


@pytest.mark.parametrize(
    ("frequency", "as_of", "lag", "last"),
    [
        (Frequency.MONTHLY, date(2018, 12, 31), 1, "2018-11"),
        (Frequency.MONTHLY, date(2018, 1, 15), 1, "2017-12"),
        (Frequency.QUARTERLY, date(2018, 12, 31), 1, "2018-Q3"),
        (Frequency.QUARTERLY, date(2013, 12, 31), 4, "2013-Q2"),
        (Frequency.ANNUAL, date(2015, 12, 31), 18, "2013"),
        (Frequency.ANNUAL, date(2013, 12, 31), 12, "2012"),
        (Frequency.ANNUAL, date(2015, 12, 31), 0, "2015"),
    ],
)
def test_published_by(frequency: Frequency, as_of: date, lag: int, last: str) -> None:
    assert str(published_by(frequency, as_of, lag)) == last


def test_published_by_rejects_a_negative_lag() -> None:
    with pytest.raises(OpError, match="cannot be negative"):
        published_by(Frequency.ANNUAL, date(2015, 1, 1), -1)
