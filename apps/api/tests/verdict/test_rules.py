from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.ops import (
    ChangeKind,
    OpRecord,
    Series,
    cagr,
    change,
    compare,
    per_capita,
    rank,
    trend,
    value_at,
)
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction, Operator
from holdsup.verdict import Label, cant_check, combine, decide, load_tolerances
from holdsup.verdict.tolerances import ValueTolerance, half_unit

TOL = load_tolerances()


def claim(
    type: AssertionType,
    value: float | None = None,
    direction: Direction | None = None,
    unit: str | None = None,
    start_value: float | None = None,
    end_value: float | None = None,
) -> ClaimSpec:
    base: dict[str, Any] = {
        "quote": "a claim",
        "indicator_phrase": "x",
        "geo": "IT",
        "geo_basis": "stated",
        "peers": [],
        "start": "2015",
        "start_basis": "stated",
        "end": "2020",
        "end_basis": "stated",
        "assertion": Assertion(
            type=type,
            value=value,
            direction=direction,
            unit=unit,
            start_value=start_value,
            end_value=end_value,
        ),
        "speaker": None,
        "said_on": None,
    }
    return ClaimSpec.model_validate(base)


RATE = Series.from_values("IT", {str(y): v for y, v in zip(range(2015, 2021), [40, 38, 35, 32, 30, 28], strict=True)}, "%")  # fmt: skip
DEBT = Series.from_values("IT", {"2015": 2_200_000.0, "2020": 2_600_000.0}, "million euro")


def verdict(c: ClaimSpec, *records: OpRecord, unit: str | None = "%", **kw: Any) -> Label:
    return decide(
        c, list(records), list(range(len(records))), unit=unit, tolerances=TOL, **kw
    ).label


# --- one test per label ----------------------------------------------------------------------


def test_supported() -> None:
    c = claim(AssertionType.PERCENTAGE_POINTS, 12, Direction.DOWN, "points")
    v = decide(c, [change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)], [0], unit="%",
               tolerances=TOL, window_share=0.9)  # fmt: skip
    assert v.label is Label.SUPPORTED
    [part] = v.parts
    assert (part.computed, part.asserted, part.tolerance) == (-12.0, -12.0, 0.5)
    assert (v.tolerances_version, v.framing_threshold, v.window_share) == (2, 0.7, 0.9)


def test_supported_framing_matters_by_window_share() -> None:
    c = claim(AssertionType.PERCENTAGE_POINTS, 12, Direction.DOWN)
    r = change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)
    v = decide(c, [r], [0], unit="%", tolerances=TOL, window_share=0.4)
    assert v.label is Label.SUPPORTED_FRAMING_MATTERS
    assert "holds in 40% of time windows" in v.reason


def test_supported_framing_matters_by_distortion() -> None:
    c = claim(AssertionType.PERCENTAGE_POINTS, 12, Direction.DOWN)
    r = change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)
    v = decide(c, [r], [0], unit="%", tolerances=TOL, distortions=["not per capita"])
    assert (v.label, v.distortions) == (Label.SUPPORTED_FRAMING_MATTERS, ["not per capita"])


def test_not_supported() -> None:
    c = claim(AssertionType.PERCENTAGE_POINTS, 20, Direction.DOWN)
    r = change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)
    v = decide(c, [r], [0], unit="%", tolerances=TOL)
    assert v.label is Label.NOT_SUPPORTED
    assert v.parts[0].holds is False


def test_partly_supported_from_to_levels() -> None:
    # "fell from 40% to 25%": the start level holds, the end level and the change do not.
    c = claim(AssertionType.PERCENTAGE_POINTS, 15, Direction.DOWN, "%", 40, 25)
    r = change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)
    v = decide(c, [r], [0], unit="%", tolerances=TOL)
    assert v.label is Label.PARTLY_SUPPORTED
    assert [(p.name, p.holds) for p in v.parts] == [
        ("assertion", False),
        ("start value", True),
        ("end value", False),
    ]
    assert v.reason == "Holds for start value; not for assertion, end value."


@pytest.mark.parametrize(
    ("c", "reason"),
    [
        (claim(AssertionType.RECORD, direction=Direction.DOWN), "claims about records"),
        (claim(AssertionType.TARGET), "claims about reaching a target"),
        (claim(AssertionType.STREAK, direction=Direction.UP), "claims about a streak"),
        (claim(AssertionType.PERCENT), "gives no number"),
        (claim(AssertionType.LEVEL, direction=Direction.UP), "doesn't give the number"),
    ],
)
def test_cant_check(c: ClaimSpec, reason: str) -> None:
    v = decide(c, [value_at(RATE, "2020")], [0], unit="%", tolerances=TOL)
    assert v.label is Label.CANT_CHECK
    assert reason in v.reason


def test_cant_check_without_an_answer() -> None:
    v = decide(claim(AssertionType.LEVEL, 28), [], [], unit="%", tolerances=TOL)
    assert (v.label, v.reason) == (
        Label.CANT_CHECK,
        "HoldsUp couldn't find a calculation that answers this claim.",
    )
    assert cant_check("x").parts == []


# --- each operation as the answer ------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "label"),
    [(28, Label.SUPPORTED), (28.3, Label.SUPPORTED), (28.4, Label.NOT_SUPPORTED),
     (27.7, Label.SUPPORTED), (29, Label.NOT_SUPPORTED)],
)  # fmt: skip
def test_level_of_a_rate_uses_points(value: float, label: Label) -> None:
    # 28.0 in the data: "28.3" allows 0.05 + 1% = 0.333; "28.4" allows 0.334; "27.7" 0.327.
    assert verdict(claim(AssertionType.LEVEL, value), value_at(RATE, "2020")) is label


def test_level_with_scale_words() -> None:
    # "debt of 2.6 trillion euros" against a series in million euro.
    c = claim(AssertionType.LEVEL, 2.6, unit="trillion euros")
    v = decide(c, [value_at(DEBT, "2020")], [0], unit="million euro", tolerances=TOL)
    assert v.label is Label.SUPPORTED
    assert v.parts[0].asserted == pytest.approx(2.6e6)
    # Half a unit of "2.6" (0.05 trillion) plus 1% for revisions (0.026 trillion).
    assert v.parts[0].tolerance == pytest.approx(0.076e6)


def test_absolute_change_with_scale_words() -> None:
    c = claim(AssertionType.ABSOLUTE, 400, Direction.UP, "billion euros")
    r = change(DEBT, "2015", "2020", ChangeKind.ABSOLUTE)
    assert verdict(c, r, unit="million euro") is Label.SUPPORTED
    c = claim(AssertionType.ABSOLUTE, 300, Direction.UP, "billion euros")
    assert verdict(c, r, unit="million euro") is Label.NOT_SUPPORTED


def test_percent_change_rounding() -> None:
    r = change(DEBT, "2015", "2020", ChangeKind.PERCENT)  # +18.18%
    assert verdict(claim(AssertionType.PERCENT, 18, Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.PERCENT, 18, Direction.DOWN), r) is Label.NOT_SUPPORTED
    # No direction: "changed by 18%" compares sizes.
    assert verdict(claim(AssertionType.PERCENT, 18), r) is Label.SUPPORTED


def test_ratio() -> None:
    r = change(Series.from_values("IT", {"2015": 10.0, "2020": 5.2}), "2015", "2020",
               ChangeKind.RATIO)  # fmt: skip
    assert verdict(claim(AssertionType.RATIO, 0.5, Direction.DOWN), r) is Label.SUPPORTED
    r = change(Series.from_values("IT", {"2015": 10.0, "2020": 6.0}), "2015", "2020",
               ChangeKind.RATIO)  # fmt: skip
    assert verdict(claim(AssertionType.RATIO, 0.5, Direction.DOWN), r) is Label.NOT_SUPPORTED


@pytest.mark.parametrize(
    ("direction", "label"),
    [(Direction.DOWN, Label.SUPPORTED), (Direction.UP, Label.NOT_SUPPORTED),
     (Direction.FLAT, Label.NOT_SUPPORTED)],
)  # fmt: skip
def test_direction_only_change(direction: Direction, label: Label) -> None:
    r = change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)
    assert verdict(claim(AssertionType.PERCENTAGE_POINTS, direction=direction), r) is label


def test_direction_only_ratio_and_flat() -> None:
    flat = Series.from_values("IT", {"2015": 100.0, "2020": 101.0})
    r = change(flat, "2015", "2020", ChangeKind.RATIO)
    assert verdict(claim(AssertionType.RATIO, direction=Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.RATIO, direction=Direction.FLAT), r) is Label.SUPPORTED
    r = change(flat, "2015", "2020", ChangeKind.PERCENT)
    assert verdict(claim(AssertionType.PERCENT, direction=Direction.FLAT), r) is Label.SUPPORTED


def test_growth_rate_series_value() -> None:
    growth = Series.from_values("IT", {"2024": 0.7}, "% change on previous year")
    r = value_at(growth, "2024")
    assert verdict(claim(AssertionType.PERCENT, 0.7, Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.PERCENT, 0.7, Direction.DOWN), r) is Label.NOT_SUPPORTED
    assert verdict(claim(AssertionType.PERCENT, direction=Direction.UP), r) is Label.SUPPORTED
    pp = claim(AssertionType.PERCENTAGE_POINTS, 1, Direction.UP)
    assert verdict(pp, r) is Label.SUPPORTED  # within ±0.5 points


def test_cagr() -> None:
    r = cagr(Series.from_values("IT", {"2015": 100.0, "2020": 110.4}), "2015", "2020")  # ≈2%
    assert verdict(claim(AssertionType.PERCENT, 2, Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.PERCENT, direction=Direction.DOWN), r) is Label.NOT_SUPPORTED


def test_trend() -> None:
    r = trend(RATE, "2015", "2020")
    assert verdict(claim(AssertionType.TREND, direction=Direction.DOWN), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.TREND, direction=Direction.UP), r) is Label.NOT_SUPPORTED


def test_trend_needs_a_clear_line() -> None:
    noisy = Series.from_values("IT", {"2015": 1.0, "2016": 9.0, "2017": 0.0, "2018": 9.5})
    v = decide(claim(AssertionType.TREND, direction=Direction.UP), [trend(noisy, "2015", "2018")],
               [0], unit="%", tolerances=TOL)  # fmt: skip
    assert v.label is Label.NOT_SUPPORTED
    assert "below 0.5, so no clear trend" in v.parts[0].detail


def test_trend_flat_and_constant() -> None:
    const = Series.from_values("IT", {"2015": 5.0, "2016": 5.0, "2017": 5.0})
    r = trend(const, "2015", "2017")
    assert verdict(claim(AssertionType.TREND, direction=Direction.FLAT), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.TREND, direction=Direction.UP), r) is Label.NOT_SUPPORTED


def test_compare_one_period() -> None:
    de = Series.from_values("DE", {"2020": 20.0}, "%")
    r = compare(RATE, de, "2020")  # 28 - 20
    assert verdict(claim(AssertionType.COMPARE, direction=Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.COMPARE, direction=Direction.DOWN), r) is Label.NOT_SUPPORTED
    assert verdict(claim(AssertionType.COMPARE, 8, Direction.UP), r) is Label.SUPPORTED
    assert verdict(claim(AssertionType.COMPARE, 6, Direction.UP), r) is Label.NOT_SUPPORTED


def test_compare_changes_with_peers() -> None:
    it = Series.from_values("IT", {"2020": 100.0, "2024": 106.0})
    fr = Series.from_values("FR", {"2020": 100.0, "2024": 104.0})
    de = Series.from_values("DE", {"2020": 100.0, "2024": 107.0})
    records = [change(s, "2020", "2024", ChangeKind.PERCENT) for s in (it, fr, de)]
    v = decide(claim(AssertionType.COMPARE, direction=Direction.UP), records, [0, 1, 2],
               unit="million euro", tolerances=TOL)  # fmt: skip
    assert v.label is Label.PARTLY_SUPPORTED
    assert [(p.name, p.holds) for p in v.parts] == [("vs FR", True), ("vs DE", False)]


@pytest.mark.parametrize(
    ("direction", "value", "label"),
    [
        (Direction.DOWN, None, Label.SUPPORTED),  # "the lowest"
        (Direction.UP, None, Label.SUPPORTED),  # rank order comes from the direction
        (None, 2.0, Label.SUPPORTED),  # "second": IT is behind DE
        (None, 1.0, Label.NOT_SUPPORTED),  # "first"
    ],
)
def test_rank(direction: Direction | None, value: float | None, label: Label) -> None:
    places = [Series.from_values(g, {"2020": v}) for g, v in (("IT", 1.0), ("DE", 5.0))]
    r = rank(places, "IT", "2020", highest_first=direction is not Direction.DOWN)
    if direction is Direction.UP:
        r = rank(places[::-1], "DE", "2020")
    assert verdict(claim(AssertionType.RANK, value, direction), r, unit=None) is label


def test_record_without_a_value_is_an_error() -> None:
    with pytest.raises(ValueError, match="has no value"):
        decide(claim(AssertionType.LEVEL, 1.0), [OpRecord(op="value_at", args={}, inputs=[])], [0],
               unit=None, tolerances=TOL)  # fmt: skip


# --- tolerances and combining ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "half"), [(23.0, 0.5), (2.3, 0.05), (0.25, 0.005), (-1.5, 0.05), (1e-20, 0.0)]
)
def test_half_unit(value: float, half: float) -> None:
    assert half_unit(value) == pytest.approx(half)


def test_band_takes_the_largest_allowance() -> None:
    t = ValueTolerance(relative=0.05, absolute=0.2, rounding=True)
    assert t.band(100.0) == 5.0
    assert t.band(1.0) == 0.5  # rounding of "1"
    assert t.band(1.5) == 0.2


@given(asserted=st.floats(0.01, 1e6), share=st.floats(0, 0.0099))
def test_within_relative_tolerance_holds(asserted: float, share: float) -> None:
    # Levels allow 1% for revisions on top of the rounding of the stated number (D020).
    s = Series.from_values("IT", {"2020": asserted * (1 + share)}, "euro")
    v = decide(claim(AssertionType.LEVEL, asserted), [value_at(s, "2020")], [0], unit="euro",
               tolerances=TOL)  # fmt: skip
    assert v.label is Label.SUPPORTED


@pytest.mark.parametrize(
    ("labels", "out"),
    [
        ([], Label.CANT_CHECK),
        ([Label.CANT_CHECK], Label.CANT_CHECK),
        ([Label.SUPPORTED, Label.CANT_CHECK], Label.SUPPORTED),
        ([Label.SUPPORTED, Label.SUPPORTED_FRAMING_MATTERS], Label.SUPPORTED_FRAMING_MATTERS),
        ([Label.SUPPORTED, Label.NOT_SUPPORTED], Label.PARTLY_SUPPORTED),
        ([Label.SUPPORTED, Label.PARTLY_SUPPORTED], Label.PARTLY_SUPPORTED),
        ([Label.NOT_SUPPORTED, Label.NOT_SUPPORTED], Label.NOT_SUPPORTED),
    ],
)
def test_combine(labels: list[Label], out: Label) -> None:
    assert combine(labels) is out


def test_tolerances_file() -> None:
    assert TOL.values.percentage_points.band(12.0) == 0.5
    assert TOL.max_period_gap


# --- bounds: "more than", "at most" ----------------------------------------------------------


def bounded(c: ClaimSpec, op: Operator) -> ClaimSpec:
    return c.model_copy(update={"assertion": c.assertion.model_copy(update={"operator": op})})


# RATE: 40 (2015) → 28 (2020) is -30%; -12 points.
@pytest.mark.parametrize(
    ("type", "value", "op", "label"),
    [
        (AssertionType.PERCENT, 25, Operator.MORE_THAN, Label.SUPPORTED),  # fell 30% > 25%
        (AssertionType.PERCENT, 30, Operator.MORE_THAN, Label.NOT_SUPPORTED),  # not more than 30
        (AssertionType.PERCENT, 31, Operator.AT_LEAST, Label.SUPPORTED),  # within ± 1.55
        (AssertionType.PERCENT, 35, Operator.LESS_THAN, Label.SUPPORTED),
        (AssertionType.PERCENT, 25, Operator.LESS_THAN, Label.NOT_SUPPORTED),
        (AssertionType.PERCENTAGE_POINTS, 12, Operator.AT_MOST, Label.SUPPORTED),
        (AssertionType.PERCENTAGE_POINTS, 10, Operator.AT_MOST, Label.NOT_SUPPORTED),
    ],
)
def test_bounds_compare_sizes_in_the_claimed_direction(
    type: AssertionType, value: float, op: Operator, label: Label
) -> None:
    c = bounded(claim(type, value, Direction.DOWN), op)
    kind = ChangeKind.PERCENT if type is AssertionType.PERCENT else ChangeKind.PERCENTAGE_POINTS
    assert verdict(c, change(RATE, "2015", "2020", kind)) is label


def test_a_bound_fails_when_it_moved_the_other_way() -> None:
    rising = Series.from_values("IT", {"2015": 10.0, "2020": 11.0}, "%")
    c = bounded(claim(AssertionType.PERCENT, 5, Direction.DOWN), Operator.LESS_THAN)
    assert verdict(c, change(rising, "2015", "2020", ChangeKind.PERCENT)) is Label.NOT_SUPPORTED


def test_a_level_bound_and_its_detail() -> None:
    c = bounded(claim(AssertionType.LEVEL, 25), Operator.MORE_THAN)
    v = decide(c, [value_at(RATE, "2020")], [0], unit="%", tolerances=TOL)
    [part] = v.parts
    assert (v.label, part.operator) == (Label.SUPPORTED, Operator.MORE_THAN)
    assert part.detail == "computed 28 for 2020, asserted more than 25 (± 0.75)"


def test_stated_levels_are_always_about() -> None:
    c = bounded(
        claim(AssertionType.PERCENTAGE_POINTS, 10, Direction.DOWN, start_value=40, end_value=28),
        Operator.MORE_THAN,
    )
    v = decide(c, [change(RATE, "2015", "2020", ChangeKind.PERCENTAGE_POINTS)], [0], unit="%",
               tolerances=TOL)  # fmt: skip
    assert [p.operator for p in v.parts] == [Operator.MORE_THAN, Operator.ABOUT, Operator.ABOUT]
    assert v.label is Label.SUPPORTED


def test_a_series_making_operation_cannot_decide_a_claim() -> None:
    population = Series.from_values("IT", {"2015": 60.0, "2020": 59.0}, "million persons")
    record = per_capita(DEBT, population)
    v = decide(claim(AssertionType.LEVEL, 40), [record], [0], unit="%", tolerances=TOL)
    assert v.label is Label.CANT_CHECK
    assert "can't settle" in v.reason
