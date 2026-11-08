import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from holdsup.ops import (
    ChangeKind,
    DataPoint,
    FlagCode,
    OpError,
    Series,
    cagr,
    change,
    compare,
    rank,
    value_at,
)

IT = Series.from_values("IT", {"2015": 100.0, "2016": 110.0, "2018": 121.0}, unit="EUR")


# value_at


def test_value_at_exact_period() -> None:
    r = value_at(IT, "2016")
    assert (r.op, r.value, r.unit, r.flags) == ("value_at", 110.0, "EUR", [])
    assert r.inputs == [DataPoint(geo="IT", period="2016", value=110.0)]
    assert r.args == {"geo": "IT", "period": "2016", "max_distance": None}


def test_value_at_latest() -> None:
    r = value_at(IT, "latest")
    assert (r.inputs[0].period, r.value) == ("2018", 121.0)


def test_value_at_nearest_period_is_flagged() -> None:
    r = value_at(IT, "2020")
    assert (r.inputs[0].period, r.value) == ("2018", 121.0)
    [flag] = r.flags
    assert flag.code is FlagCode.NEAREST_PERIOD
    assert (flag.requested, flag.used, flag.distance) == ("2020", "2018", 2)


def test_value_at_nearest_prefers_the_earlier_period_on_a_tie() -> None:
    r = value_at(IT, "2017")  # 2016 and 2018 are both one year away
    assert r.inputs[0].period == "2016"


def test_value_at_max_distance() -> None:
    assert value_at(IT, "2019", max_distance=1).value == 121.0
    with pytest.raises(OpError, match="within 1 periods of 2020"):
        value_at(IT, "2020", max_distance=1)


def test_value_at_frequency_mismatch() -> None:
    with pytest.raises(OpError, match="2016-03 is monthly but the IT series is annual"):
        value_at(IT, "2016-03")


@given(
    values=st.dictionaries(
        st.integers(1950, 2030).map(str), st.floats(-1e6, 1e6), min_size=1, max_size=40
    ),
    year=st.integers(1900, 2080),
)
def test_value_at_returns_a_value_at_minimal_distance(values: dict[str, float], year: int) -> None:
    s = Series.from_values("X", values)
    r = value_at(s, str(year))
    used = int(r.inputs[0].period)
    assert r.value == values[str(used)]
    assert abs(used - year) == min(abs(int(k) - year) for k in values)
    assert bool(r.flags) == (str(year) not in values)


# change


def test_change_records_both_points() -> None:
    r = change(IT, "2015", "2018", ChangeKind.PERCENT)
    assert r.value == pytest.approx(21.0)
    assert (r.unit, r.flags) == ("%", [])
    assert [p.period for p in r.inputs] == ["2015", "2018"]
    assert r.args["kind"] == "percent"


@pytest.mark.parametrize(
    ("kind", "value", "unit"),
    [
        (ChangeKind.ABSOLUTE, 21.0, "EUR"),
        (ChangeKind.PERCENTAGE_POINTS, 21.0, "percentage points"),
        (ChangeKind.RATIO, 1.21, None),
    ],
)
def test_change_units(kind: ChangeKind, value: float, unit: str | None) -> None:
    r = change(IT, "2015", "latest", kind)
    assert r.value == pytest.approx(value)
    assert r.unit == unit


def test_change_with_a_missing_start_is_flagged() -> None:
    r = change(IT, "2013", "2016", ChangeKind.ABSOLUTE)
    assert r.value == pytest.approx(10.0)
    assert [f.requested for f in r.flags] == ["2013"]


def test_change_window_must_move_forward() -> None:
    with pytest.raises(OpError, match="resolves to 2018..2015"):
        change(IT, "2018", "2015", ChangeKind.PERCENT)
    with pytest.raises(OpError, match="resolves to 2018..2018"):
        change(IT, "2019", "2020", ChangeKind.PERCENT)  # both resolve to 2018


@given(
    a=st.floats(1e-3, 1e6),
    b=st.floats(1e-3, 1e6),
    c=st.floats(1e-3, 1e6),
)
def test_ratio_changes_chain(a: float, b: float, c: float) -> None:
    s = Series.from_values("X", {"2000": a, "2001": b, "2002": c})
    whole = change(s, "2000", "2002", ChangeKind.RATIO).value
    first = change(s, "2000", "2001", ChangeKind.RATIO).value
    second = change(s, "2001", "2002", ChangeKind.RATIO).value
    assert whole is not None and first is not None and second is not None
    assert math.isclose(whole, first * second, rel_tol=1e-9)


# cagr


def test_cagr() -> None:
    r = cagr(IT, "2016", "2018")
    assert r.value == pytest.approx(math.sqrt(1.1) * 100 - 100)
    assert (r.extras, r.unit) == ({"years": 2.0}, "% per year")


def test_cagr_quarterly_uses_years() -> None:
    s = Series.from_values("IT", {"2020-Q1": 100.0, "2021-Q3": 115.0})
    r = cagr(s, "2020-Q1", "2021-Q3")
    assert r.extras["years"] == 1.5
    assert r.value == pytest.approx((1.15 ** (1 / 1.5) - 1) * 100)


def test_half_years_count_two_to_a_year() -> None:
    s = Series.from_values("DE", {"2022-S1": 100.0, "2022-S2": 110.0, "2023-S2": 121.0})
    r = cagr(s, "2022-S2", "2023-S2")
    assert r.extras["years"] == 1.0 and r.value == pytest.approx(10.0)
    assert cagr(s, "2022-S1", "2022-S2").extras["years"] == 0.5
    gap = value_at(s, "2023-S1")  # no value: the earlier of the two neighbours, one period away
    assert (gap.inputs[0].period, gap.flags[0].distance) == ("2022-S2", 1)
    with pytest.raises(OpError, match="is quarterly but the DE series is semiannual"):
        value_at(s, "2023-Q1")
    with pytest.raises(OpError, match="is annual but the DE series is semiannual"):
        value_at(s, "2023")


def test_cagr_needs_a_positive_start() -> None:
    s = Series.from_values("IT", {"2020": -1.0, "2021": 1.0})
    with pytest.raises(OpError, match="positive start"):
        cagr(s, "2020", "2021")


@given(start=st.floats(1e-3, 1e6), rate=st.floats(-50, 50), years=st.integers(1, 30))
def test_cagr_recovers_a_constant_growth_rate(start: float, rate: float, years: int) -> None:
    end = start * (1 + rate / 100) ** years
    s = Series.from_values("X", {"2000": start, str(2000 + years): end})
    assert cagr(s, "2000", "latest").value == pytest.approx(rate, abs=1e-6)


# compare

DE = Series.from_values("DE", {"2015": 50.0, "2016": 55.0, "2017": 0.0}, unit="EUR")


def test_compare() -> None:
    r = compare(IT, DE, "2016")
    assert (r.value, r.extras, r.unit, r.flags) == (55.0, {"ratio": 2.0}, "EUR", [])
    assert [p.geo for p in r.inputs] == ["IT", "DE"]
    assert r.args == {"geo_a": "IT", "geo_b": "DE", "period": "2016", "max_distance": None}


def test_compare_tiny_denominator_drops_the_ratio() -> None:
    tiny = Series.from_values("DE", {"2016": 1e-308}, unit="EUR")
    r = compare(IT, tiny, "2016")
    assert (r.extras, [f.code for f in r.flags]) == ({}, [FlagCode.ZERO_DENOMINATOR])


def test_compare_zero_denominator_drops_the_ratio() -> None:
    r = compare(IT, DE, "2017")  # IT 2017 → 2016 (earlier on a tie), DE 2017 = 0
    assert r.extras == {}
    assert [f.code for f in r.flags] == [FlagCode.NEAREST_PERIOD, FlagCode.ZERO_DENOMINATOR]


def test_compare_rejects_different_units_and_frequencies() -> None:
    usd = Series.from_values("US", {"2016": 1.0}, unit="USD")
    with pytest.raises(OpError, match="in EUR but US is in USD"):
        compare(IT, usd, "2016")
    quarterly = Series.from_values("DE", {"2016-Q1": 1.0})
    with pytest.raises(OpError, match="IT is annual but DE is quarterly"):
        compare(IT, quarterly, "2016")


def test_compare_unit_falls_back_to_the_other_series() -> None:
    bare = Series.from_values("FR", {"2016": 1.0})
    assert compare(bare, IT, "2016").unit == "EUR"


@given(a=st.floats(-1e6, 1e6), b=st.floats(-1e6, 1e6))
def test_compare_is_antisymmetric(a: float, b: float) -> None:
    sa = Series.from_values("A", {"2020": a})
    sb = Series.from_values("B", {"2020": b})
    ab, ba = compare(sa, sb, "2020"), compare(sb, sa, "2020")
    assert ab.value == -(ba.value or 0.0)
    if "ratio" in ab.extras and "ratio" in ba.extras:
        assert math.isclose(ab.extras["ratio"] * ba.extras["ratio"], 1.0, rel_tol=1e-9)


# rank


def _places(values: dict[str, float | None], period: str = "2020") -> list[Series]:
    out = []
    for geo, v in values.items():
        data = {"2019": 0.0} if v is None else {period: v}
        out.append(Series.from_values(geo, data))
    return out


def test_rank_highest_first() -> None:
    places = _places({"IT": 5.0, "DE": 9.0, "FR": 7.0})
    r = rank(places, "IT", "2020")
    assert (r.value, r.extras, r.flags) == (3.0, {"of": 3.0}, [])
    assert [p.geo for p in r.inputs] == ["DE", "FR", "IT"]
    assert rank(places, "IT", "2020", highest_first=False).value == 1.0


def test_rank_ties_share_a_position() -> None:
    r = rank(_places({"IT": 7.0, "DE": 9.0, "FR": 7.0, "ES": 1.0}), "IT", "2020")
    assert r.value == 2.0
    [flag] = r.flags
    assert (flag.code, flag.items) == (FlagCode.TIE, ["FR"])


def test_rank_leaves_out_places_without_the_period() -> None:
    r = rank(_places({"IT": 7.0, "DE": None, "FR": 8.0}), "IT", "2020")
    assert (r.value, r.extras["of"]) == (2.0, 2.0)
    [flag] = r.flags
    assert (flag.code, flag.items) == (FlagCode.MISSING_GEOS, ["DE"])


def test_rank_latest_is_the_target_latest_period() -> None:
    places = [
        Series.from_values("IT", {"2019": 1.0, "2020": 3.0}),
        Series.from_values("DE", {"2020": 2.0, "2021": 9.0}),
    ]
    r = rank(places, "IT", "latest")
    assert (r.value, r.inputs[0].period) == (1.0, "2020")


@pytest.mark.parametrize(
    ("places", "geo", "match"),
    [
        (_places({"IT": 1.0}) + _places({"IT": 2.0}), "IT", "appears twice"),
        (_places({"DE": 1.0}), "IT", "IT is not among"),
        (_places({"IT": None, "DE": 1.0}), "IT", "IT has no value for 2020"),
        (_places({"IT": 1.0}) + _places({"DE": 1.0}, "2020-Q1"), "IT", "is annual but"),
    ],
)
def test_rank_rejects(places: list[Series], geo: str, match: str) -> None:
    with pytest.raises(OpError, match=match):
        rank(places, geo, "2020")


@given(values=st.lists(st.floats(-1e6, 1e6), min_size=1, max_size=12, unique=True))
def test_rank_reverses_with_the_order(values: list[float]) -> None:
    places = [Series.from_values(f"G{i}", {"2020": v}) for i, v in enumerate(values)]
    n = len(values)
    for s in places:
        up = rank(places, s.geo, "2020").value
        down = rank(places, s.geo, "2020", highest_first=False).value
        assert up is not None and down is not None
        assert up + down == n + 1
    top = max(range(n), key=lambda i: values[i])
    assert rank(places, f"G{top}", "2020").value == 1.0


@given(values=st.lists(st.integers(0, 3).map(float), min_size=2, max_size=10))
def test_rank_with_ties_counts_strictly_better_places(values: list[float]) -> None:
    assume(len(values) >= 2)
    places = [Series.from_values(f"G{i}", {"2020": v}) for i, v in enumerate(values)]
    for i, v in enumerate(values):
        expected = 1 + sum(1 for w in values if w > v)
        assert rank(places, f"G{i}", "2020").value == expected


def test_record_numbers_lists_every_number_it_holds() -> None:
    from holdsup.ops import per_capita

    assert compare(IT, DE, "2016").numbers() == [110.0, 55.0, 55.0, 2.0]
    pc = per_capita(
        Series.from_values("IT", {"2020": 6.0}), Series.from_values("IT", {"2020": 3.0})
    )
    assert pc.numbers() == [6.0, 3.0, 2.0]
