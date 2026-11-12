"""Distortion checks (P3.4, D026): for each, a claim it flags and one it lets pass."""

from datetime import date
from typing import Any

import pytest

from holdsup.catalog.schema import load_catalog
from holdsup.checks import (
    CheckInput,
    CheckKind,
    DistortionCheck,
    Related,
    change_points,
    distortion_checks,
    flag_text,
    said_between,
    wants_real_terms,
)
from holdsup.checks.distortions import (
    age_ranges,
    definition_check,
    endpoints_check,
    per_capita_check,
    points_check,
    real_check,
    stale_check,
)
from holdsup.config import REPO_ROOT
from holdsup.ops import ChangeKind, OpRecord, Series, change, trend, value_at
from holdsup.pipeline.claim import LATEST, Assertion, AssertionType, ClaimSpec, Direction
from holdsup.verdict import load_tolerances

CATALOG = load_catalog(REPO_ROOT / "packages" / "catalog")
TOL = load_tolerances()
TODAY = date(2026, 11, 12)


def claim(
    *,
    type: AssertionType = AssertionType.PERCENT,
    value: float | None = None,
    direction: Direction | None = Direction.UP,
    unit: str | None = None,
    phrase: str = "x",
    quote: str = "a claim",
    geo: str = "IT",
    end: str | None = None,
    said_on: str | None = None,
) -> ClaimSpec:
    return ClaimSpec(
        quote=quote, indicator_phrase=phrase, geo=geo, geo_basis=None, peers=[],
        start=None, start_basis=None, end=end, end_basis=None,
        assertion=Assertion(type=type, value=value, direction=direction, unit=unit,
                            start_value=None, end_value=None),
        speaker=None, said_on=said_on,
    )  # fmt: skip


def annual(values: dict[int, float], unit: str | None) -> Series:
    return Series.from_values("IT", {str(y): v for y, v in values.items()}, unit)


def inp(c: ClaimSpec, spec_id: str, answer: OpRecord, series: Series, **kw: Any) -> CheckInput:
    return CheckInput(
        claim=c, spec=CATALOG.get(spec_id), answer=[answer], series=series, unit=series.unit,
        tolerances=TOL, today=TODAY, **kw,
    )  # fmt: skip


def related(spec_id: str, values: dict[int, float]) -> Related:
    spec = CATALOG.get(spec_id)
    return Related(spec, annual(values, spec.unit))


# --- the start and end (P3.3) ----------------------------------------------------------------

RATE = "% of total labour force"
# 2013 to 2023: steady around 8, with a one-year spike to 11.9 in 2015.
SPIKE = annual(
    dict(
        zip(
            range(2013, 2024), [7.0, 7.5, 11.9, 8.0, 7.9, 8.1, 8.3, 8.4, 8.2, 8.0, 7.9], strict=True
        )
    ),
    RATE,
)
STEADY = annual({y: 12 - 0.5 * (y - 2013) for y in range(2013, 2024)}, RATE)


def endpoints(series: Series) -> DistortionCheck | None:
    c = claim(type=AssertionType.PERCENTAGE_POINTS, direction=Direction.DOWN)
    r = change(series, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    points = change_points(c, r, series, tolerances=TOL)
    return endpoints_check(inp(c, "unemployment_rate_ilo", r, series, changepoints=points))


def test_a_start_on_a_spike_is_flagged() -> None:
    check = endpoints(SPIKE)
    assert check is not None and check.kind is CheckKind.ENDPOINTS and check.flagged
    points = change_points(
        claim(type=AssertionType.PERCENTAGE_POINTS, direction=Direction.DOWN),
        change(SPIKE, "2015", "2023", ChangeKind.PERCENTAGE_POINTS), SPIKE, tolerances=TOL,
    )  # fmt: skip
    assert points is not None
    assert check.text == flag_text(points.flags[0], "percentage points")


def test_a_steady_fall_passes_the_start_and_end_check() -> None:
    check = endpoints(STEADY)
    assert check is not None and not check.flagged
    assert check.text == (
        "neither the start (2015) nor the end (2023) is at a peak, a trough or a turn in the "
        "trend that carries the claim"
    )


def test_a_level_has_no_start_and_end_check() -> None:
    c = claim(type=AssertionType.LEVEL, value=7.9, direction=None)
    r = value_at(STEADY, "2023")
    assert endpoints_check(inp(c, "unemployment_rate_ilo", r, STEADY)) is None


# --- per person ------------------------------------------------------------------------------

DEBT = "government_debt_eur"  # million euro (current prices), a yearly total
DEBT_IT = annual({2015: 2000, 2023: 2200}, "million euro (current prices)")


def per_person(people: dict[int, float], **kw: Any) -> DistortionCheck | None:
    c = claim(direction=Direction.UP)
    r = change(DEBT_IT, "2015", "2023", ChangeKind.PERCENT)
    return per_capita_check(
        inp(c, DEBT, r, DEBT_IT, population=related("population_total", people), **kw)
    )


def test_a_rise_that_is_a_fall_per_person_is_flagged() -> None:
    # Debt up 10% while the population grew by a fifth.
    check = per_person({2015: 50e6, 2023: 60e6})
    assert check is not None and check.kind is CheckKind.PER_CAPITA and check.flagged
    assert check.text == (
        "per person it fell: 40 in 2015, 36.7 in 2023 (euro (current prices) per person)"
    )
    assert [r.op for r in check.records] == ["per_capita", "change"]
    assert check.uses == "population_total"


def test_a_rise_that_holds_per_person_passes() -> None:
    check = per_person({2015: 50e6, 2023: 50e6})
    assert check is not None and not check.flagged
    assert check.text.startswith("per person it also rose: 40 in 2015, 44 in 2023")


def test_per_person_is_not_checked_for_a_rate_or_a_series_the_plan_made() -> None:
    c = claim(type=AssertionType.PERCENTAGE_POINTS, direction=Direction.DOWN)
    r = change(STEADY, "2015", "2023", ChangeKind.PERCENTAGE_POINTS)
    people = related("population_total", {2015: 50e6, 2023: 60e6})
    assert per_capita_check(inp(c, "unemployment_rate_ilo", r, STEADY, population=people)) is None
    assert per_person({2015: 50e6, 2023: 60e6}, adjusted=True) is None


def test_a_trend_per_person_says_its_slope() -> None:
    debt = annual({y: 2000 + 10 * (y - 2015) for y in range(2015, 2024)}, DEBT_IT.unit)
    people = related("population_total", {y: 50e6 + 2e6 * (y - 2015) for y in range(2015, 2024)})
    c = claim(type=AssertionType.TREND, direction=Direction.UP)
    check = per_capita_check(inp(c, DEBT, trend(debt, "2015", "2023"), debt, population=people))
    assert check is not None and check.flagged
    assert check.text.startswith("per person, the trend falls: -")
    assert "euro (current prices) per person per year; R² " in check.text


# --- after inflation ---------------------------------------------------------------------------

WAGES = "net_earnings_average_wage"  # euro per year, at current prices
WAGES_IT = annual({2015: 30000, 2016: 30300, 2017: 30600, 2018: 30900, 2019: 31200,
                   2020: 31500}, "euro per year")  # fmt: skip


def after_inflation(rate: float) -> DistortionCheck | None:
    c = claim(value=5, direction=Direction.UP, unit="%")
    r = change(WAGES_IT, "2015", "2020", ChangeKind.PERCENT)
    prices = related("cpi_inflation_annual", {y: rate for y in range(2016, 2021)})
    return real_check(inp(c, WAGES, r, WAGES_IT, prices=prices))


def test_a_pay_rise_below_inflation_is_flagged() -> None:
    # Up 5% in five years with prices up 3% a year: 31,500 is 27,172 in 2015 prices.
    check = after_inflation(3.0)
    assert check is not None and check.kind is CheckKind.REAL and check.flagged
    assert check.text == (
        "after inflation it fell: 30,000 in 2015, 27,172 in 2020 (euro per year, 2015 prices)"
    )
    assert [r.op for r in check.records] == ["chain_index", "deflate", "change"]
    assert check.uses == "cpi_inflation_annual"


def test_a_pay_rise_above_inflation_passes() -> None:
    check = after_inflation(0.5)
    assert check is not None and not check.flagged
    assert check.text.startswith("after inflation it also rose: 30,000 in 2015, 30,724 in 2020")


def test_the_real_version_is_read_when_the_catalog_has_one() -> None:
    gdp = annual({2015: 100.0, 2020: 110.0}, "million euro (current prices)")
    real = related("real_gdp_volume", {2015: 100.0, 2020: 98.0})
    c = claim(direction=Direction.UP)
    r = change(gdp, "2015", "2020", ChangeKind.PERCENT)
    check = real_check(inp(c, "nominal_gdp_eur", r, gdp, real=real))
    assert check is not None and check.flagged
    assert check.uses == "real_gdp_volume" and [x.op for x in check.records] == ["change"]
    assert check.text == (
        "after inflation it fell: 100 in 2015, 98 in 2020 "
        "(million euro, chain-linked volumes (2020))"
    )


def test_without_prices_or_a_shared_year_a_check_is_left_out() -> None:
    c = claim(value=5, direction=Direction.UP, unit="%")
    r = change(WAGES_IT, "2015", "2020", ChangeKind.PERCENT)
    assert real_check(inp(c, WAGES, r, WAGES_IT)) is None  # prices not fetched
    assert per_person({2000: 50e6}) is None  # the population shares no year with the debt


def test_only_money_at_current_prices_is_adjusted_for_inflation() -> None:
    c = claim(direction=Direction.UP)
    r = change(WAGES_IT, "2015", "2020", ChangeKind.PERCENT)
    assert wants_real_terms(c, CATALOG.get(WAGES), [r], adjusted=False)
    assert not wants_real_terms(c, CATALOG.get(WAGES), [r], adjusted=True)
    assert not wants_real_terms(c, CATALOG.get("unemployment_rate_ilo"), [r], adjusted=False)
    # Half-yearly, with no real version: no price index to adjust it with yet.
    assert not wants_real_terms(c, CATALOG.get("minimum_wage_eur"), [r], adjusted=False)
    no_direction = claim(value=5, direction=None)
    assert not wants_real_terms(no_direction, CATALOG.get(WAGES), [r], adjusted=False)


# --- percent or percentage points --------------------------------------------------------------

TEN_TO_TWELVE = annual({2015: 10.0, 2023: 12.0}, RATE)


def points(value: float) -> DistortionCheck | None:
    c = claim(type=AssertionType.PERCENT, value=value, direction=Direction.UP, unit="%")
    r = change(TEN_TO_TWELVE, "2015", "2023", ChangeKind.PERCENT)
    return points_check(inp(c, "unemployment_rate_ilo", r, TEN_TO_TWELVE))


def test_points_stated_as_percent_are_flagged() -> None:
    check = points(2)
    assert check is not None and check.kind is CheckKind.POINTS and check.flagged
    assert check.text == (
        "the claimed 2% matches the change in percentage points (+2 points), not in percent (+20%)"
    )


def test_percent_stated_as_percent_passes() -> None:
    check = points(20)
    assert check is not None and not check.flagged
    assert check.text == (
        "the claimed 20% is right as a change in percent (+20%); in percentage points it is "
        "+2 points"
    )


def test_a_number_wrong_both_ways_is_not_a_points_mix_up() -> None:
    check = points(7)
    assert check is not None and not check.flagged
    assert "doesn't match the claimed 7% either" in check.text


def test_points_are_checked_only_for_a_change_in_a_rate() -> None:
    c = claim(type=AssertionType.PERCENT, value=10, direction=Direction.UP)
    r = change(DEBT_IT, "2015", "2023", ChangeKind.PERCENT)
    assert points_check(inp(c, DEBT, r, DEBT_IT)) is None  # not in %
    no_value = claim(type=AssertionType.PERCENT, direction=Direction.UP)
    r = change(TEN_TO_TWELVE, "2015", "2023", ChangeKind.PERCENT)
    assert points_check(inp(no_value, "unemployment_rate_ilo", r, TEN_TO_TWELVE)) is None


# --- definition ------------------------------------------------------------------------------

YOUTH = "youth_unemployment_rate_monthly"  # aged under 25


@pytest.mark.parametrize(
    ("text", "ages"),
    [
        ("aged 15 to 24", {(15, 24.0)}),
        ("15-24 year-olds", {(15, 24.0)}),
        ("ages 20-64", {(20, 64.0)}),
        ("the under-25s", {(None, 24.0)}),
        ("people under 25", {(None, 24.0)}),
        ("aged 15+", {(15, float("inf"))}),
        ("aged 65 and over", {(65, float("inf"))}),
        ("older than 64", {(65, float("inf"))}),
        ("from 2015 to 2024", set()),
        ("fell 15 to 24 points", set()),
    ],
)
def test_age_ranges(text: str, ages: set[tuple[int | None, float]]) -> None:
    assert age_ranges(text) == ages


def definition(c: ClaimSpec, spec_id: str = YOUTH, **kw: Any) -> DistortionCheck | None:
    r = value_at(STEADY, "2023")
    return definition_check(inp(c, spec_id, r, STEADY, **kw))


def test_another_age_group_is_flagged() -> None:
    check = definition(claim(phrase="unemployment among 15-29 year olds"))
    assert check is not None and check.kind is CheckKind.DEFINITION and check.flagged
    assert check.text == "the claim is about ages 15 to 29; the statistic covers ages under 25"


def test_the_same_age_group_passes() -> None:
    check = definition(claim(phrase="youth unemployment (15-24 year-olds)"))
    assert check is not None and not check.flagged
    assert check.text == "what the claim states matches the statistic's definition (ages under 25)"


def test_per_person_against_a_total_is_flagged() -> None:
    debt_claim = claim(phrase="public debt per person")
    check = definition_check(
        inp(debt_claim, DEBT, change(DEBT_IT, "2015", "2023", ChangeKind.PERCENT), DEBT_IT)
    )
    assert check is not None and check.flagged
    assert check.text == (
        "the claim is per person; the figures are a total (million euro (current prices))"
    )


def test_per_person_read_per_person_passes() -> None:
    made = annual({2015: 40.0, 2023: 44.0}, "euro (current prices) per person")
    debt_claim = claim(phrase="public debt per person")
    check = definition_check(
        inp(debt_claim, DEBT, change(made, "2015", "2023", ChangeKind.PERCENT), made)
    )
    assert check is not None and not check.flagged and "(per person)" in check.text


def test_another_currency_is_flagged_and_the_same_one_passes() -> None:
    r = change(DEBT_IT, "2015", "2023", ChangeKind.ABSOLUTE)
    dollars = claim(type=AssertionType.ABSOLUTE, value=200, unit="billion dollars")
    check = definition_check(inp(dollars, "nominal_gdp_eur", r, DEBT_IT))
    assert check is not None and check.flagged
    assert check.text == "the claim is in dollars; the statistic is in euro"
    euros = claim(type=AssertionType.ABSOLUTE, value=200, unit="billion euros")
    check = definition_check(inp(euros, "nominal_gdp_eur", r, DEBT_IT))
    assert check is not None and not check.flagged and "(in euro)" in check.text


def test_the_eu_before_brexit_is_flagged() -> None:
    eu = claim(geo="EU", said_on="2019")
    check = definition(eu, "unemployment_rate_ilo", said=said_between("2019", date(2019, 12, 31)))
    assert check is not None and check.flagged
    assert check.text == (
        "the claim dates from 2019, when the EU included the United Kingdom; the figures are "
        "for the 27 countries in the EU since 2020"
    )


def test_the_eu_after_brexit_passes_and_a_year_that_spans_it_is_not_judged() -> None:
    check = definition(
        claim(geo="EU", said_on="2021"), "unemployment_rate_ilo",
        said=said_between("2021", date(2021, 12, 31)),
    )  # fmt: skip
    assert check is not None and not check.flagged and "the EU's 27 countries" in check.text
    spans = definition(
        claim(geo="EU", said_on="2020"), "unemployment_rate_ilo",
        said=said_between("2020", date(2020, 12, 31)),
    )  # fmt: skip
    assert spans is None


def test_a_claim_that_states_no_definition_has_no_definition_check() -> None:
    assert definition(claim(phrase="youth unemployment")) is None


# --- stale data ------------------------------------------------------------------------------


def stale(latest: int, **kw: Any) -> DistortionCheck | None:
    c = claim(type=AssertionType.LEVEL, value=7.9, direction=None, end=LATEST, **kw)
    s = annual({y: 8.0 for y in range(2010, latest + 1)}, RATE)
    said = said_between(c.said_on, date(int(c.said_on), 12, 31)) if c.said_on else None
    return stale_check(inp(c, "unemployment_rate_ilo", value_at(s, str(latest)), s, said=said))


def test_a_now_claim_on_figures_two_years_old_is_flagged() -> None:
    check = stale(2023)
    assert check is not None and check.kind is CheckKind.STALE and check.flagged
    assert check.text == "the latest figure is for 2023, 2 or more years before today"


def test_a_now_claim_on_last_years_figures_passes() -> None:
    check = stale(2025)
    assert check is not None and not check.flagged
    assert check.text == "the latest figure is for 2025, less than 2 years before today"


def test_a_dated_claim_is_judged_on_the_first_day_it_can_have_been_made() -> None:
    # Said in 2019: on 1 January 2019, 2016 is 25 months old, 2017 13.
    old = stale(2016, said_on="2019")
    assert old is not None and old.flagged
    assert (
        old.text
        == "the latest figure is for 2016, 2 or more years before the claim was made (2019)"
    )
    recent = stale(2017, said_on="2019")
    assert recent is not None and not recent.flagged


def test_a_claim_about_a_past_year_is_not_stale() -> None:
    c = claim(type=AssertionType.LEVEL, value=7.9, direction=None, end="2016")
    s = annual({2016: 8.0}, RATE)
    assert stale_check(inp(c, "unemployment_rate_ilo", value_at(s, "2016"), s)) is None


@pytest.mark.parametrize(
    ("said_on", "by", "expected"),
    [
        ("2019", date(2019, 12, 31), (date(2019, 1, 1), date(2019, 12, 31))),
        ("2019-03", date(2019, 3, 31), (date(2019, 3, 1), date(2019, 3, 31))),
        ("2019-03-05", date(2019, 3, 5), (date(2019, 3, 5), date(2019, 3, 5))),
        ("2026", date(2026, 11, 12), (date(2026, 1, 1), date(2026, 11, 12))),
        (None, None, None),
        ("soon", date(2026, 11, 12), None),
    ],
)
def test_said_between(
    said_on: str | None, by: date | None, expected: tuple[date, date] | None
) -> None:
    assert said_between(said_on, by) == expected


# --- all of them -----------------------------------------------------------------------------


def test_the_checks_that_apply_come_in_reading_order() -> None:
    c = claim(type=AssertionType.PERCENT, value=2, direction=Direction.UP, unit="%",
              phrase="unemployment among people aged 15 to 74")  # fmt: skip
    r = change(TEN_TO_TWELVE, "2015", "2023", ChangeKind.PERCENT)
    checks = distortion_checks(inp(c, "unemployment_rate_monthly", r, TEN_TO_TWELVE))
    assert [(ch.kind, ch.flagged) for ch in checks] == [
        (CheckKind.POINTS, True),
        (CheckKind.DEFINITION, False),
    ]
