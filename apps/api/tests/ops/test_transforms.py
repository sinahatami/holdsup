import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import FlagCode, OpError, Series, change, deflate, per_capita
from holdsup.ops.change import ChangeKind

GDP = Series.from_values("IT", {"2019": 1800.0, "2020": 1650.0, "2021": 1800.0}, unit="MIO_EUR")
POP = Series.from_values("IT", {"2018": 60.4e6, "2019": 60.0e6, "2020": 59.5e6})
CPI = Series.from_values("IT", {"2019": 100.0, "2020": 100.0, "2021": 102.0, "2022": 110.0})


def test_per_capita() -> None:
    r = per_capita(GDP, POP, scale=1e6, unit="EUR per person")
    assert r.op == "per_capita"
    assert r.args == {"geo": "IT", "scale": 1e6}
    assert r.unit == "EUR per person"
    assert [(p.period, round(p.value, 2)) for p in r.series or []] == [
        ("2019", 30.0),  # 1,800 million euros over 60 million people
        ("2020", 27.73),
    ]
    assert len(r.inputs) == 6  # every point of both series
    [flag] = r.flags
    assert (flag.code, flag.items) == (FlagCode.MISSING_PERIODS, ["2018", "2021"])


def test_per_capita_output_feeds_another_op() -> None:
    s = Series.from_record(per_capita(GDP, POP, scale=1e6, unit="EUR per person"))
    r = change(s, "2019", "2020", ChangeKind.PERCENT)
    assert r.value == pytest.approx((1650 / 59.5 - 1800 / 60.0) / (1800 / 60.0) * 100)


def test_per_capita_rejects() -> None:
    with pytest.raises(OpError, match="population is for DE, not IT"):
        per_capita(GDP, Series.from_values("DE", {"2019": 1.0}))
    with pytest.raises(OpError, match="population is quarterly but the series is annual"):
        per_capita(GDP, Series.from_values("IT", {"2019-Q1": 1.0}))
    with pytest.raises(OpError, match="share no period"):
        per_capita(GDP, Series.from_values("IT", {"1990": 1.0}))
    with pytest.raises(OpError, match="not positive"):
        per_capita(GDP, Series.from_values("IT", {"2019": 0.0}))
    with pytest.raises(OpError, match="value per person in 2019 is not a finite number"):
        per_capita(GDP, Series.from_values("IT", {"2019": 1e-308}), scale=1e6)


def test_deflate() -> None:
    r = deflate(GDP, CPI, "2021")
    assert r.unit == "MIO_EUR, 2021 prices"
    out = r.series or []
    assert [p.period for p in out] == ["2019", "2020", "2021"]
    assert [p.value for p in out] == pytest.approx([1836.0, 1683.0, 1800.0])
    [flag] = r.flags
    assert flag.items == ["2022"]


def test_deflate_without_a_unit() -> None:
    bare = Series.from_values("IT", {"2019": 1.0})
    r = deflate(bare, CPI, "latest")
    assert (r.unit, r.args["base"]) == (None, "latest")
    assert r.series is not None and r.series[0].value == pytest.approx(1.1)


def test_deflate_rejects() -> None:
    with pytest.raises(OpError, match="no positive value for the base period 2000"):
        deflate(GDP, CPI, "2000")
    zero = Series.from_values("IT", {"2019": 0.0, "2020": 1.0})
    with pytest.raises(OpError, match="no positive value for the base period 2019"):
        deflate(GDP, zero, "2019")
    with pytest.raises(OpError, match="must be positive"):
        deflate(GDP, zero, "2020")
    tiny = Series.from_values("IT", {"2019": 1e-308, "2020": 1e300})
    with pytest.raises(OpError, match="real value in 2019 is not a finite number"):
        deflate(GDP, tiny, "2020")


values = st.lists(st.floats(1e-3, 1e9), min_size=1, max_size=20)


@given(xs=values, ps=values)
def test_per_capita_times_population_returns_the_series(xs: list[float], ps: list[float]) -> None:
    n = min(len(xs), len(ps))
    s = Series.from_values("X", {str(2000 + i): xs[i] for i in range(n)})
    pop = Series.from_values("X", {str(2000 + i): ps[i] for i in range(n)})
    out = per_capita(s, pop).series or []
    for i, p in enumerate(out):
        assert math.isclose(p.value * ps[i], xs[i], rel_tol=1e-9)


@given(xs=values, index=st.floats(1e-3, 1e6), base=st.integers(0, 19))
def test_constant_price_index_leaves_the_series_unchanged(
    xs: list[float], index: float, base: int
) -> None:
    s = Series.from_values("X", {str(2000 + i): v for i, v in enumerate(xs)})
    cpi = Series.from_values("X", {str(2000 + i): index for i in range(20)})
    out = deflate(s, cpi, str(2000 + base)).series or []
    assert [p.value for p in out] == pytest.approx(xs, rel=1e-12)


@given(xs=values, idx=st.lists(st.floats(1e-2, 1e4), min_size=20, max_size=20))
def test_base_period_values_are_unchanged(xs: list[float], idx: list[float]) -> None:
    s = Series.from_values("X", {str(2000 + i): v for i, v in enumerate(xs)})
    cpi = Series.from_values("X", {str(2000 + i): v for i, v in enumerate(idx)})
    base = len(xs) - 1
    out = deflate(s, cpi, str(2000 + base)).series or []
    assert out[base].value == pytest.approx(xs[base], rel=1e-12)
