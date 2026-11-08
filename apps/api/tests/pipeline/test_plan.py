"""Planning and execution with a fake router (no network, no model)."""

import json
from datetime import date
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from holdsup.adapters.base import Observation
from holdsup.catalog.schema import load_catalog
from holdsup.ops import AnnualValue, ChangeKind, FlagCode, Frequency
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction
from holdsup.pipeline.plan import (
    MAX_CALLS,
    OPERATIONS,
    PLAN_SYSTEM,
    ModelPlan,
    OpCall,
    OpName,
    PlanContext,
    PlanInvalid,
    SeriesInfo,
    execute_plan,
    per_person_unit,
    plan_analysis,
    plan_message,
    validate_plan,
)
from holdsup.router import Router, RouterError
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label, decide, load_tolerances
from tests.catalog.helpers import FIXTURE_CATALOG
from tests.router.fakes import FakeClient, FakeClock, config, provider

TOL = load_tolerances()


def claim(
    type: AssertionType = AssertionType.PERCENTAGE_POINTS,
    value: float | None = 12,
    direction: Direction | None = Direction.DOWN,
    geo: str | None = "IT",
    **kw: Any,
) -> ClaimSpec:
    base: dict[str, Any] = {
        "quote": "Italy's unemployment fell 12 points since 2015",
        "indicator_phrase": "unemployment rate",
        "geo": geo,
        "geo_basis": "stated",
        "peers": [],
        "start": "2015",
        "start_basis": "stated",
        "end": "latest",
        "end_basis": "stated",
        "assertion": Assertion(
            type=type,
            value=value,
            direction=direction,
            unit="points",
            start_value=None,
            end_value=None,
        ),
        "speaker": None,
        "said_on": None,
    }
    return ClaimSpec.model_validate({**base, **kw})


def obs(indicator: dict[str, dict[str, float | None]]) -> list[Observation]:
    return [Observation(g, p, v) for g, values in indicator.items() for p, v in values.items()]


DATA = {
    "rate": obs(
        {
            "IT": {
                "2015": 40.0,
                "2016": 37.0,
                "2017": 35.0,
                "2018": 32.0,
                "2019": 30.0,
                "2020": 28.0,
                "2021": None,
            },
            "DE": {"2015": 7.0, "2020": 6.0},
            "FR": {"2015": 24.0, "2020": 20.0},
        }
    ),
    "gdp": obs({"IT": {"2015": 1_650_000.0, "2020": 1_660_000.0}}),
    "pop": obs({"IT": {"2015": 60_000.0, "2020": 59_000.0}}),
    "cpi": obs({"IT": {"2015": 100.0, "2020": 104.0}}),
    "pop_q": obs({"IT": {"2015-Q1": 60_000.0}}),
}
RATE = SeriesInfo("rate", "Unemployment rate", "% of labour force", Frequency.ANNUAL,
                  frozenset({"IT", "DE", "FR"}), "2015", "2020")  # fmt: skip
GDP = SeriesInfo("gdp", "GDP", "million euro", Frequency.ANNUAL, frozenset({"IT"}), "2015", "2020")
POP = SeriesInfo("pop", "Population", "thousand persons", Frequency.ANNUAL, frozenset({"IT"}),
                 "2015", "2020")  # fmt: skip
CPI = SeriesInfo("cpi", "Prices", "index 2015=100", Frequency.ANNUAL, frozenset({"IT"}), "2015",
                 "2020")  # fmt: skip
POP_Q = SeriesInfo("pop_q", "Population", "thousand persons", Frequency.QUARTERLY,
                   frozenset({"IT"}), "2015-Q1", "2015-Q1")  # fmt: skip


def ctx(c: ClaimSpec | None = None, main: SeriesInfo = RATE, *others: SeriesInfo) -> PlanContext:
    return PlanContext(c or claim(), main, others)


def plan(*calls: dict[str, Any], answer: list[int] | None = None) -> ModelPlan:
    return ModelPlan.model_validate(
        {"calls": list(calls), "answer": [0] if answer is None else answer, "reason": "Because."}
    )


CHANGE = {"op": "change", "geo": "IT", "start": "2015", "end": "latest",
          "kind": "percentage_points"}  # fmt: skip


# --- the plan schema rejects unknown operations ----------------------------------------------


def test_unknown_op_fails_the_schema() -> None:
    with pytest.raises(ValidationError, match="value_at"):
        plan({"op": "regress", "geo": "IT"})


async def test_unknown_op_is_rejected_through_the_router() -> None:
    bad = json.dumps({"calls": [{"op": "exec_python", "geo": "IT"}], "answer": [0], "reason": ""})
    client = FakeClient()
    client.script("fake", [ChatResponse(content=bad), ChatResponse(content=bad)])
    router = Router(config(provider("fake"), steps={"plan": ["fake"]}), client, clock=FakeClock())
    with pytest.raises(RouterError):
        await plan_analysis(router, ctx())
    # The router asked once for a corrected answer before giving up on the provider.
    assert len(client.calls) == 2
    assert "not valid for the required JSON Schema" in str(client.calls[1][1].messages[-1])


# --- validation ------------------------------------------------------------------------------


def test_valid_plan_drops_arguments_the_op_does_not_take() -> None:
    p = validate_plan(plan({**CHANGE, "period": "2020", "geo_b": "DE"}), ctx())
    assert p.calls[0].period is None and p.calls[0].geo_b is None
    assert p.notes == [
        "call 0 (change): dropped geo_b, which change does not take",
        "call 0 (change): dropped period, which change does not take",
    ]


@pytest.mark.parametrize(
    ("call", "error"),
    [
        ({"op": "change", "geo": "IT", "start": "2015"}, "call 0 (change): missing end"),
        ({**CHANGE, "start": "2015-03"}, "start '2015-03' must be YYYY for the annual rate"),
        ({**CHANGE, "start": "around 2015"}, "start 'around 2015' is not a period"),
        ({**CHANGE, "start": "2015", "end": "2014-Q1"}, "end '2014-Q1' must be YYYY"),
        ({**CHANGE, "geo": "ES"}, "no data for geo 'ES' in rate"),
        ({**CHANGE, "start": "2020", "end": "2015"}, "start must be before end"),
        ({**CHANGE, "series": "gdp_nominal"}, "unknown series 'gdp_nominal'"),
        ({**CHANGE, "series": "@0"}, "series '@0' must name an earlier per_capita or deflate"),
        ({**CHANGE, "series": "@x"}, "series '@x' must name an earlier"),
        ({"op": "rank", "geo": "IT", "geos": ["IT", "XX"], "period": "2020"},
         "no data for 'XX' in rate"),
        ({"op": "compare", "geo": "IT", "geo_b": "XX", "period": "2020"},
         "no data for geo_b 'XX'"),
    ],
)  # fmt: skip
def test_invalid_calls(call: dict[str, Any], error: str) -> None:
    with pytest.raises(PlanInvalid) as info:
        validate_plan(plan(call), ctx())
    assert any(error in e for e in info.value.errors), info.value.errors


@pytest.mark.parametrize(
    ("call", "error"),
    [
        ({"op": "per_capita", "geo": "IT", "series": "gdp", "population": "rate"},
         "population 'rate' is not a listed indicator"),
        ({"op": "per_capita", "geo": "IT", "series": "gdp", "population": "nope"},
         "population 'nope' is not a listed indicator"),
        ({"op": "per_capita", "geo": "IT", "series": "gdp", "population": "pop_q"},
         "population 'pop_q' is quarterly, not annual"),
    ],
)  # fmt: skip
def test_invalid_series_arguments(call: dict[str, Any], error: str) -> None:
    with pytest.raises(PlanInvalid) as info:
        validate_plan(plan(call, CHANGE, answer=[1]), ctx(None, RATE, GDP, POP_Q))
    assert any(error in e for e in info.value.errors), info.value.errors


def test_reference_to_a_call_with_an_unknown_series_reports_it_once() -> None:
    p = plan(
        {"op": "per_capita", "geo": "IT", "series": "nope", "population": "pop"},
        {**CHANGE, "series": "@0"},
        answer=[1],
    )
    with pytest.raises(PlanInvalid) as info:
        validate_plan(p, ctx(None, RATE, POP))
    assert info.value.errors == ["call 0 (per_capita): unknown series 'nope'"]


def test_chained_references_resolve_to_the_indicator() -> None:
    c = claim(AssertionType.PERCENT, 1, Direction.UP)
    p = plan(
        {"op": "deflate", "geo": "IT", "series": "gdp", "price_index": "cpi", "base": "2020"},
        {"op": "per_capita", "geo": "IT", "series": "@0", "population": "pop"},
        {"op": "change", "geo": "IT", "start": "2015", "end": "2020", "kind": "percent",
         "series": "@1"},
        answer=[2],
    )  # fmt: skip
    assert validate_plan(p, ctx(c, RATE, GDP, POP, CPI)).answer == [2]


def test_plan_limits() -> None:
    with pytest.raises(PlanInvalid, match="no calls"):
        validate_plan(plan(), ctx())
    with pytest.raises(PlanInvalid, match=f"at most {MAX_CALLS} calls"):
        validate_plan(plan(*[CHANGE] * (MAX_CALLS + 1)), ctx())


@pytest.mark.parametrize(
    ("c", "calls", "answer", "error"),
    [
        (claim(), [CHANGE], [], "at least one call"),
        (claim(), [CHANGE], [1], "distinct indexes"),
        (claim(), [CHANGE, CHANGE], [0, 0], "distinct indexes"),
        (claim(), [{**CHANGE, "geo": "DE"}], [0], "about IT, not DE"),
        (claim(), [{**CHANGE, "kind": "percent"}], [0], "do not answer a percentage_points"),
        (claim(AssertionType.LEVEL, 28), [CHANGE], [0], "do not answer a level"),
        (claim(AssertionType.TREND), [CHANGE], [0], "do not answer a trend"),
        (claim(AssertionType.RANK), [CHANGE], [0], "do not answer a rank"),
        (claim(AssertionType.PERCENTAGE_POINTS),
         [{"op": "cagr", "geo": "IT", "start": "2015", "end": "2020"}], [0], "do not answer"),
        (claim(AssertionType.COMPARE),
         [CHANGE, {**CHANGE, "geo": "FR", "kind": "percent"}], [0, 1], "do not answer a compare"),
        (claim(AssertionType.COMPARE), [CHANGE, CHANGE], [0, 1], "do not answer a compare"),
    ],
)  # fmt: skip
def test_answer_must_fit_the_claim(
    c: ClaimSpec, calls: list[dict[str, Any]], answer: list[int], error: str
) -> None:
    with pytest.raises(PlanInvalid, match=error):
        validate_plan(plan(*calls, answer=answer), ctx(c))


@pytest.mark.parametrize(
    ("c", "calls", "answer"),
    [
        (claim(AssertionType.LEVEL, 28), [{"op": "value_at", "geo": "IT", "period": "2020"}], [0]),
        (claim(AssertionType.PERCENT, 1, Direction.UP),
         [{"op": "value_at", "geo": "IT", "period": "2020"}], [0]),
        (claim(AssertionType.PERCENT, 2, Direction.UP),
         [{"op": "cagr", "geo": "IT", "start": "2015", "end": "2020"}], [0]),
        (claim(AssertionType.TREND), [{"op": "trend", "geo": "IT", "start": "2015",
                                       "end": "latest"}], [0]),
        (claim(AssertionType.RANK, None), [{"op": "rank", "geo": "IT", "geos": ["DE", "FR"],
                                            "period": "2020"}], [0]),
        (claim(AssertionType.COMPARE), [{"op": "compare", "geo": "IT", "geo_b": "DE",
                                         "period": "2020"}], [0]),
        (claim(AssertionType.COMPARE), [CHANGE, {**CHANGE, "geo": "FR"}], [0, 1]),
        (claim(geo=None), [{**CHANGE, "geo": "DE"}], [0]),
    ],
)  # fmt: skip
def test_answers_that_fit(c: ClaimSpec, calls: list[dict[str, Any]], answer: list[int]) -> None:
    assert validate_plan(plan(*calls, answer=answer), ctx(c)).answer == answer


# --- the model call --------------------------------------------------------------------------


def planner(*contents: str) -> tuple[Router, FakeClient]:
    client = FakeClient()
    client.script("fake", [ChatResponse(content=c) for c in contents])
    router = Router(config(provider("fake"), steps={"plan": ["fake"]}), client, clock=FakeClock())
    return router, client


def as_json(p: ModelPlan) -> str:
    return p.model_dump_json(exclude_none=True)


async def test_plan_on_the_first_try() -> None:
    router, client = planner(as_json(plan(CHANGE)))
    result = await plan_analysis(router, ctx())
    assert (result.status, result.attempts, result.providers) == ("planned", 1, ["fake"])
    assert result.plan is not None and result.plan.calls[0].kind is ChangeKind.PERCENTAGE_POINTS
    [(_, request)] = client.calls
    assert request.messages[0]["content"] == PLAN_SYSTEM
    assert request.response_format is not None and request.response_format["type"] == "json_schema"


async def test_rejected_plan_gets_one_repair_turn() -> None:
    router, client = planner(as_json(plan({**CHANGE, "geo": "ES"})), as_json(plan(CHANGE)))
    result = await plan_analysis(router, ctx())
    assert (result.status, result.attempts, result.errors) == ("planned", 2, [])
    repair = str(client.calls[1][1].messages[-1]["content"])
    assert repair.startswith("Code rejected that plan:\n- call 0 (change): no data for geo 'ES'")


async def test_plan_invalid_twice_is_cant_check() -> None:
    bad = as_json(plan({**CHANGE, "start": "2015-01"}))
    router, client = planner(bad, bad, as_json(plan(CHANGE)))
    result = await plan_analysis(router, ctx())
    assert (result.status, result.plan, result.attempts) == ("cant_check", None, 2)
    assert result.reason == "The analysis plan was invalid twice."
    assert result.errors and "must be YYYY" in result.errors[0]
    assert len(client.calls) == 2


async def test_unsupported_claims_make_no_model_call() -> None:
    router, client = planner()
    result = await plan_analysis(router, ctx(claim(AssertionType.RECORD)))
    assert (result.status, result.reason) == ("cant_check", "record claims cannot be checked yet")
    assert client.calls == []


def test_plan_message() -> None:
    c = claim(peers=["FR", "DE"], assertion=Assertion(
        type=AssertionType.PERCENTAGE_POINTS, value=12, direction=Direction.DOWN, unit="points",
        start_value=40, end_value=None))  # fmt: skip
    text = plan_message(ctx(c, RATE, POP))
    assert text.startswith("<claim>\nItaly's unemployment")
    assert "Place: IT (compared with FR, DE)" in text and "Period: 2015 to latest" in text
    assert "states a value: yes; states start/end levels: yes" in text
    assert "- rate: Unemployment rate. Unit: % of labour force. Frequency: annual. " in text
    assert "Places: DE, FR, IT. Periods: 2015 to 2020." in text
    assert "Other indicators:\n- pop:" in text
    assert "12" not in text.split("</claim>")[1]  # the asserted number is not repeated
    bare = plan_message(ctx(claim(geo=None, start=None, end=None, value=None)))
    assert "Place: not stated\nPeriod: ? to ?" in bare and "Other indicators" not in bare


def test_series_info_from_data() -> None:
    spec = load_catalog(FIXTURE_CATALOG).get("unemployment_rate")
    info = SeriesInfo.from_data(spec, DATA["rate"])
    assert (info.geos, info.first, info.last) == (frozenset({"IT", "DE", "FR"}), "2015", "2020")
    empty = SeriesInfo.from_data(spec, [])
    assert (empty.first, empty.last) == (None, None)
    assert "Places: none. Periods: ? to ?." in empty.describe()


# --- execution and the verdict ---------------------------------------------------------------


def run(c: ClaimSpec, *calls: dict[str, Any], answer: list[int] | None = None,
        others: tuple[SeriesInfo, ...] = (), main: SeriesInfo = RATE) -> Any:  # fmt: skip
    context = PlanContext(c, main, others)
    valid = validate_plan(plan(*calls, answer=answer), context)
    return execute_plan(valid, context, DATA, TOL), valid


def test_execute_change_and_decide_supported() -> None:
    ex, valid = run(claim(), CHANGE)
    assert ex.error is None and ex.unit == "% of labour force"
    [r] = ex.records
    assert (r.op, r.value, [p.period for p in r.inputs]) == ("change", -12.0, ["2015", "2020"])
    v = decide(claim(), ex.records, valid.answer, unit=ex.unit, tolerances=TOL)
    assert v.label is Label.SUPPORTED


def test_execute_every_value_op() -> None:
    c = claim(AssertionType.LEVEL, 28, None)
    ex, _ = run(
        c,
        {"op": "value_at", "geo": "IT", "period": "2021"},  # empty cell → 2020, flagged
        {"op": "cagr", "geo": "IT", "start": "2015", "end": "2020"},
        {"op": "trend", "geo": "IT", "start": "2015", "end": "latest"},
        {"op": "compare", "geo": "IT", "geo_b": "DE", "period": "2020"},
        {"op": "rank", "geo": "IT", "geos": ["DE", "FR"], "period": "2020"},
    )
    value, growth, line, diff, position = ex.records
    assert (value.value, value.flags[0].code) == (28.0, FlagCode.NEAREST_PERIOD)
    assert growth.value is not None and growth.value < 0
    assert line.value is not None and line.value < 0
    assert (diff.value, position.value) == (22.0, 1.0)  # highest first: IT has the most


def test_rank_order_follows_a_down_claim() -> None:
    c = claim(AssertionType.RANK, None, Direction.DOWN, geo="DE")
    ex, valid = run(c, {"op": "rank", "geo": "DE", "geos": ["IT", "FR", "DE"], "period": "2020"})
    assert ex.records[0].value == 1.0 and ex.records[0].args["highest_first"] is False
    assert (
        decide(c, ex.records, valid.answer, unit=ex.unit, tolerances=TOL).label is Label.SUPPORTED
    )


def test_execute_series_ops_and_units() -> None:
    c = claim(AssertionType.PERCENT, 2, Direction.DOWN)
    ex, valid = run(
        c,
        {"op": "deflate", "geo": "IT", "series": "gdp", "price_index": "cpi", "base": "2020"},
        {"op": "per_capita", "geo": "IT", "series": "@0", "population": "pop"},
        {"op": "change", "geo": "IT", "start": "2015", "end": "2020", "kind": "percent",
         "series": "@1"},
        {"op": "value_at", "geo": "IT", "period": "2020", "series": "@1"},
        answer=[2],
        others=(GDP, POP, CPI),
    )  # fmt: skip
    assert ex.error is None
    real, per_person, growth, level = ex.records
    assert real.unit == "million euro, 2020 prices"
    assert per_person.unit == "euro, 2020 prices per person"
    # 1,650,000 million × 1.04 / 60,000 thousand = 28,600 euro; 1,660,000 / 59,000 ≈ 28,136.
    assert per_person.series is not None
    assert per_person.series[0].value == pytest.approx(28_600.0)
    assert level.value == pytest.approx(1_660_000 / 59)
    assert growth.value == pytest.approx((1_660_000 / 59 / 28_600 - 1) * 100)
    assert ex.unit == "euro, 2020 prices per person"
    v = decide(c, ex.records, valid.answer, unit=ex.unit, tolerances=TOL)
    # -1.62% against "down 2%": |0.38| is within the rounding of "2" (±0.5).
    assert v.label is Label.SUPPORTED


def test_execution_error_stops_the_plan() -> None:
    far = {"op": "value_at", "geo": "DE", "period": "2018"}  # DE has 2015 and 2020: 2 years off
    ex, _ = run(claim(geo=None, assertion=Assertion(type=AssertionType.LEVEL, value=6,
                direction=None, unit=None, start_value=None, end_value=None)), far, CHANGE)  # fmt: skip
    assert ex.records == [] and ex.unit is None
    assert ex.error == "DE has no value within 1 periods of 2018 (nearest is 2020)"


def test_from_to_levels_end_to_end() -> None:
    c = claim(assertion=Assertion(type=AssertionType.PERCENTAGE_POINTS, value=12,
              direction=Direction.DOWN, unit="%", start_value=40, end_value=30))  # fmt: skip
    ex, valid = run(c, CHANGE)
    v = decide(c, ex.records, valid.answer, unit=ex.unit, tolerances=TOL)
    assert v.label is Label.PARTLY_SUPPORTED  # 2020 is 28, not 30


def test_per_person_unit() -> None:
    assert per_person_unit("million euro (current prices)") == "euro (current prices) per person"
    assert per_person_unit(None) is None
    assert OpCall(op="value_at").given() == set()


# --- whole years on monthly and quarterly series ---------------------------------------------

MONTHLY = {f"{y}-{m:02d}": float(y - 2000) + m / 100 for y in (2015, 2016) for m in range(1, 13)}
MONTHLY_DATA = {
    "m": obs({"IT": {**MONTHLY, "2017-01": 30.0}, "DE": dict.fromkeys(MONTHLY, 5.0)}),
}
M = SeriesInfo("m", "Unemployment rate (monthly)", "%", Frequency.MONTHLY,
               frozenset({"IT", "DE"}), "2015-01", "2017-01", AnnualValue.MEAN)  # fmt: skip
QOQ = SeriesInfo("q", "GDP growth on previous quarter", "%", Frequency.QUARTERLY,
                 frozenset({"IT"}), "2015-Q1", "2016-Q4")  # fmt: skip


def year_claim(start: str | None = "2015", end: str | None = "2016") -> ClaimSpec:
    return claim(start=start, end=end)


def test_a_whole_year_is_allowed_on_a_series_with_yearly_values() -> None:
    p = validate_plan(plan({**CHANGE, "start": "2015", "end": "2016"}), ctx(year_claim(), M))
    assert (p.calls[0].start, p.calls[0].end) == ("2015", "2016") and p.notes == []
    assert "A whole year (YYYY) is the average of its months." in M.describe()


def test_a_series_without_yearly_values_needs_its_own_periods() -> None:
    with pytest.raises(PlanInvalid) as info:
        validate_plan(plan({**CHANGE, "start": "2015", "end": "2016"}), ctx(year_claim(), QOQ))
    assert "'2015': q has no yearly value; use YYYY-Qn" in info.value.errors[0]
    assert "No yearly value: use YYYY-Qn (a trend may use YYYY)." in QOQ.describe()
    # A trend over whole years reads their quarters.
    trend_call = {"op": "trend", "geo": "IT", "start": "2015", "end": "2016"}
    validate_plan(plan(trend_call), ctx(claim(type=AssertionType.TREND, value=None), QOQ))


def test_months_inside_years_the_claim_names_become_the_years() -> None:
    call = {**CHANGE, "start": "2015-01", "end": "2016-12"}
    p = validate_plan(plan(call), ctx(year_claim(), M))
    assert (p.calls[0].start, p.calls[0].end) == ("2015", "2016")
    assert p.notes == [
        "call 0 (change): start 2015-01 → 2015, the claim names the whole year",
        "call 0 (change): end 2016-12 → 2016, the claim names the whole year",
    ]


@pytest.mark.parametrize(
    ("claim_start", "call"),
    [
        ("2015-03", {**CHANGE, "start": "2015-03", "end": "2016-12"}),  # the claim names a month
        ("2015", {**CHANGE, "start": "2015-01", "end": "2015-12"}),  # a change within the year
    ],
)
def test_months_are_kept_when_the_claim_means_them(claim_start: str, call: dict[str, Any]) -> None:
    p = validate_plan(plan(call), ctx(year_claim(start=claim_start, end="2016"), M))
    assert (p.calls[0].start, p.calls[0].end) == (call["start"], call["end"])
    assert not any("whole year" in n for n in p.notes)


def test_start_and_end_must_use_one_form() -> None:
    with pytest.raises(PlanInvalid) as info:
        call = {**CHANGE, "start": "2015", "end": "2016-06"}  # the claim does not name 2016
        validate_plan(plan(call), ctx(year_claim(end="latest"), M))
    assert "start and end must both be whole years (YYYY) or both YYYY-MM" in info.value.errors[0]


def test_whole_years_run_on_yearly_averages() -> None:
    p = validate_plan(plan({**CHANGE, "start": "2015", "end": "2016"}), ctx(year_claim(), M))
    run = execute_plan(p, ctx(year_claim(), M), MONTHLY_DATA, TOL)
    [r] = run.records
    assert [(i.period, round(i.value, 3)) for i in r.inputs] == [("2015", 15.065), ("2016", 16.065)]
    assert [f.code for f in r.flags] == [FlagCode.ANNUAL_VALUE]


def test_latest_among_whole_years_is_the_last_complete_year() -> None:
    p = validate_plan(plan({**CHANGE, "start": "2015", "end": "latest"}), ctx(year_claim(), M))
    [r] = execute_plan(p, ctx(year_claim(), M), MONTHLY_DATA, TOL).records
    assert [i.period for i in r.inputs] == ["2015", "2016"]  # 2017 has only January
    latest = next(f for f in r.flags if f.code is FlagCode.LATEST_YEAR)
    assert latest.detail == (
        "IT: latest is the last complete year, 2016; the latest month is 2017-01"
    )


def test_compare_and_rank_use_yearly_values_for_every_place() -> None:
    c = claim(type=AssertionType.COMPARE, value=None, direction=Direction.UP, peers=["DE"])
    calls: list[dict[str, Any]] = [
        {"op": "compare", "geo": "IT", "geo_b": "DE", "period": "2016"},
        {"op": "rank", "geo": "IT", "geos": ["IT", "DE"], "period": "2016"},
    ]
    p = validate_plan(plan(*calls), ctx(c, M))
    cmp_, rnk = execute_plan(p, ctx(c, M), MONTHLY_DATA, TOL).records
    assert [(i.geo, i.period, i.value) for i in cmp_.inputs] == [
        ("IT", "2016", pytest.approx(16.065)), ("DE", "2016", 5.0),
    ]  # fmt: skip
    assert rnk.value == 1.0 and {i.period for i in rnk.inputs} == {"2016"}


def test_a_trend_over_whole_years_reads_their_months() -> None:
    c = claim(type=AssertionType.TREND, value=None, direction=Direction.UP)
    call = {"op": "trend", "geo": "IT", "start": "2015", "end": "2016"}
    [r] = execute_plan(validate_plan(plan(call), ctx(c, M)), ctx(c, M), MONTHLY_DATA, TOL).records
    assert (r.args["start"], r.args["end"]) == ("2015-01", "2016-12")
    assert len(r.inputs) == 24 and not r.flags


# --- a dated claim is checked as of its date -------------------------------------------------

LAGGED = SeriesInfo("m", "Unemployment rate (monthly)", "%", Frequency.MONTHLY,
                    frozenset({"IT", "DE"}), "2015-01", "2017-01", AnnualValue.MEAN,
                    lag_months=1)  # fmt: skip


def dated(c: ClaimSpec, said_on: str, as_of: date) -> PlanContext:
    return PlanContext(c.model_copy(update={"said_on": said_on}), LAGGED, as_of=as_of)


def test_latest_for_a_dated_claim_is_the_last_period_out_by_then() -> None:
    c = dated(claim(type=AssertionType.LEVEL, value=15, direction=None), "2016-06",
              date(2016, 6, 30))  # fmt: skip
    assert c.published(LAGGED) == "2016-05"
    assert 'Claim date: 2016-06. "latest" means the last period published by then (2016-05).' in (
        plan_message(c)
    )
    p = validate_plan(plan({"op": "value_at", "geo": "IT", "period": "latest"}), c)
    [r] = execute_plan(p, c, MONTHLY_DATA, TOL).records
    assert [(i.period, i.value) for i in r.inputs] == [("2016-05", 16.05)]
    [note] = r.flags
    assert (note.code, note.used) == (FlagCode.AS_OF, "2016-05")
    assert note.detail.startswith(
        "claim date 2016-06: latest is the last period published by then, 2016-05 (a release "
        "about 1 month after a period ends)"
    )


def test_a_claim_date_after_the_data_cuts_nothing() -> None:
    c = dated(claim(type=AssertionType.LEVEL, value=15, direction=None), "2026", date(2026, 12, 31))
    p = validate_plan(plan({"op": "value_at", "geo": "IT", "period": "latest"}), c)
    [r] = execute_plan(p, c, MONTHLY_DATA, TOL).records
    assert r.inputs[0].period == "2017-01" and r.flags == []


def test_explicit_periods_of_a_dated_claim_are_not_cut() -> None:
    c = dated(year_claim(), "2015", date(2015, 12, 31))
    p = validate_plan(plan({**CHANGE, "start": "2015", "end": "2016"}), c)
    [r] = execute_plan(p, c, MONTHLY_DATA, TOL).records
    assert [i.period for i in r.inputs] == ["2015", "2016"]
    assert FlagCode.AS_OF not in {f.code for f in r.flags}


def test_latest_among_yearly_values_of_a_dated_claim() -> None:
    call = {**CHANGE, "start": "2015", "end": "latest"}
    # Said in January 2017: December 2016 is out, so 2016 is a complete year.
    c = dated(year_claim(end="latest"), "2017-01", date(2017, 1, 31))
    [r] = execute_plan(validate_plan(plan(call), c), c, MONTHLY_DATA, TOL).records
    assert [i.period for i in r.inputs] == ["2015", "2016"]
    assert [f.code for f in r.flags] == [
        FlagCode.ANNUAL_VALUE, FlagCode.LATEST_YEAR, FlagCode.AS_OF,
    ]  # fmt: skip
    # Said in December 2016: 2016 is not complete yet, so there is nothing after 2015.
    c = dated(year_claim(end="latest"), "2016-12", date(2016, 12, 31))
    run = execute_plan(validate_plan(plan(call), c), c, MONTHLY_DATA, TOL)
    assert run.error == "IT: the window resolves to 2015..2015"


def test_a_period_the_plan_wrote_for_latest_is_turned_back_into_latest() -> None:
    c = dated(claim(type=AssertionType.LEVEL, value=15, direction=None, start="latest",
                    end="latest"), "2016-06", date(2016, 6, 30))  # fmt: skip
    p = validate_plan(plan({"op": "value_at", "geo": "IT", "period": "2016-05"}), c)
    assert p.calls[0].period == "latest"
    note = "call 0 (value_at): period 2016-05 → latest, the last period published by the claim"
    assert p.notes == [f"{note} date 2016-06"]
    [r] = execute_plan(p, c, MONTHLY_DATA, TOL).records
    assert [f.code for f in r.flags] == [FlagCode.AS_OF]  # the receipt gets its claim-date note


def test_a_change_to_the_cutoff_period_ends_at_latest() -> None:
    c = dated(year_claim(start="2015-06", end="latest"), "2016-06", date(2016, 6, 30))
    call = {**CHANGE, "start": "2015-06", "end": "2016-05"}
    p = validate_plan(plan(call), c)
    assert (p.calls[0].start, p.calls[0].end) == ("2015-06", "latest")


@pytest.mark.parametrize(
    ("end", "as_of"),
    [("2016-05", date(2016, 6, 30)), ("latest", None), ("latest", date(2016, 7, 31))],
)
def test_a_period_is_kept_unless_it_is_the_claim_date_s_cutoff_for_latest(
    end: str, as_of: date | None
) -> None:
    base = claim(type=AssertionType.LEVEL, value=15, direction=None, start=end, end=end)
    c = PlanContext(base.model_copy(update={"said_on": "2016-06"}), LAGGED, as_of=as_of)
    p = validate_plan(plan({"op": "value_at", "geo": "IT", "period": "2016-05"}), c)
    assert p.calls[0].period == "2016-05" and p.notes == []


# --- a window code assumed, and level answers -------------------------------------------------


def assumed(start: str = "2015") -> ClaimSpec:
    return claim(type=AssertionType.TREND, value=None, direction=Direction.UP, start=start,
                 start_basis="assumed", end="latest", end_basis="assumed")  # fmt: skip


def test_the_assumed_window_replaces_the_plan_s_start_in_the_end_s_form() -> None:
    call = {"op": "trend", "geo": "IT", "start": "1983-01", "end": "2016-12"}
    p = validate_plan(plan(call), ctx(assumed(), M))
    assert p.calls[0].start == "2015-01"
    assert "call 0 (trend): start 1983-01 → 2015-01, the assumed window" in p.notes
    [r] = execute_plan(p, ctx(assumed(), M), MONTHLY_DATA, TOL).records
    assert [f.code for f in r.flags] == [FlagCode.ASSUMED_WINDOW]


def test_a_stated_start_is_left_to_the_plan() -> None:
    call = {"op": "trend", "geo": "IT", "start": "2015-03", "end": "2016-12"}
    c = claim(type=AssertionType.TREND, value=None, direction=Direction.UP, start="2014",
              end="2016")  # fmt: skip
    p = validate_plan(plan(call), ctx(c, M))
    assert p.calls[0].start == "2015-03" and p.notes == []


def test_a_level_claim_keeps_its_one_value_at_as_the_answer() -> None:
    c = claim(type=AssertionType.LEVEL, value=32, direction=Direction.UP, start="2020", end="2020")
    calls = [{"op": "value_at", "geo": "IT", "period": "2020"},
             {**CHANGE, "start": "2015", "end": "2020"}]  # fmt: skip
    p = validate_plan(plan(*calls, answer=[1, 0]), ctx(c))
    assert p.answer == [0]
    assert p.notes == ["answer [1, 0] → [0]: a level claim is answered by its value_at"]
    # Two values, or none, cannot be settled by code: the model is asked to fix it.
    two = [{"op": "value_at", "geo": "IT", "period": "2020"},
           {"op": "value_at", "geo": "IT", "period": "2019"}]  # fmt: skip
    with pytest.raises(PlanInvalid):
        validate_plan(plan(*two, answer=[0, 1]), ctx(c))


# --- two value_at calls for a "from X to Y" change -------------------------------------------

VALUES = [{"op": "value_at", "geo": "IT", "period": "2015"},
          {"op": "value_at", "geo": "IT", "period": "2020"}]  # fmt: skip


def test_two_values_for_a_change_claim_become_one_change() -> None:
    valid = validate_plan(plan(*VALUES, answer=[0, 1]), ctx())
    [call] = valid.calls
    assert (call.op, call.geo, call.start, call.end, call.kind) == (
        "change", "IT", "2015", "2020", ChangeKind.PERCENTAGE_POINTS,
    )  # fmt: skip
    assert valid.answer == [0]
    note = "calls 0 and 1: two value_at (2015, 2020) → one change 2015 to 2020"
    assert valid.notes == [f"{note} (percentage_points), the claim is about a change"]


def test_the_later_value_first_still_makes_a_forward_change() -> None:
    valid = validate_plan(plan(VALUES[1], VALUES[0], answer=[0, 1]), ctx())
    assert (valid.calls[0].start, valid.calls[0].end) == ("2015", "2020")


def test_latest_is_the_end_of_the_change() -> None:
    later = {**VALUES[1], "period": "latest"}
    valid = validate_plan(plan(later, VALUES[0], answer=[0, 1]), ctx())
    assert (valid.calls[0].start, valid.calls[0].end) == ("2015", "latest")


def test_the_change_has_the_claims_own_kind() -> None:
    valid = validate_plan(plan(*VALUES, answer=[0, 1]), ctx(claim(AssertionType.PERCENT, 5)))
    assert valid.calls[0].kind is ChangeKind.PERCENT


def test_calls_after_the_merged_pair_move_up() -> None:
    pop = {"op": "per_capita", "geo": "IT", "population": "pop"}
    later = {"op": "value_at", "geo": "IT", "period": "2020", "series": "@2"}
    c = ctx(claim(AssertionType.ABSOLUTE, 5), GDP, POP)
    valid = validate_plan(plan(VALUES[0], VALUES[1], pop, later, answer=[0, 1]), c)
    assert [x.op for x in valid.calls] == ["change", "per_capita", "value_at"]
    assert valid.calls[2].series == "@1" and valid.answer == [0]


@pytest.mark.parametrize(
    "calls",
    [
        # two values on different places, or the same period twice
        [VALUES[0], {**VALUES[1], "geo": "DE"}],
        [VALUES[0], {**VALUES[0]}],
        # a series that is not the same one
        [VALUES[0], {**VALUES[1], "series": "gdp"}],
    ],
)
def test_two_values_that_are_not_one_change_are_left_to_the_checks(
    calls: list[dict[str, Any]],
) -> None:
    with pytest.raises(PlanInvalid):
        validate_plan(plan(*calls, answer=[0, 1]), ctx(None, RATE, GDP))


def test_a_level_claim_with_two_values_is_not_turned_into_a_change() -> None:
    with pytest.raises(PlanInvalid, match="do not answer a level claim"):
        validate_plan(plan(*VALUES, answer=[0, 1]), ctx(claim(AssertionType.LEVEL, 28, None)))


def test_one_value_of_a_growth_rate_series_stays_a_value() -> None:
    valid = validate_plan(plan(VALUES[0]), ctx())
    assert [c.op for c in valid.calls] == ["value_at"] and valid.notes == []


# --- the operation registry ------------------------------------------------------------------


def test_every_operation_name_has_exactly_one_registry_entry() -> None:
    assert set(OPERATIONS) == set(get_args(OpName))


def test_the_prompt_describes_every_operation() -> None:
    for name, spec in OPERATIONS.items():
        args = ", ".join(sorted(spec.required))
        assert f"- {name}(" in PLAN_SYSTEM, f"{name} ({args}) is missing from PLAN_SYSTEM"
