"""Matching step with a fake router and the 6-entry test catalog (no network, no model)."""

import json
from collections.abc import Sequence
from typing import Any

import pytest

from holdsup.catalog.index import IndicatorHit, InMemoryIndex
from holdsup.catalog.schema import Catalog, load_catalog
from holdsup.config import REPO_ROOT
from holdsup.pipeline import match as match_module
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction, says_now
from holdsup.pipeline.match import (
    FINAL_PROMPT,
    MATCH_SYSTEM,
    MAX_TOOL_CALLS,
    TOOLS,
    Matcher,
    _Run,
    claim_message,
    needs_level_series,
    vector_search,
    yearly_note,
)
from holdsup.router import Router
from holdsup.router.client import ChatResponse, ToolCall
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder
from tests.router.fakes import FakeClient, FakeClock, config, provider

CATALOG = load_catalog(FIXTURE_CATALOG)
EMBEDDER = HashEmbedder()
INDEX = InMemoryIndex.build(CATALOG.indicators, EMBEDDER)


def claim(phrase: str = "youth unemployment rate", geo: str | None = "IT", **kw: Any) -> ClaimSpec:
    base: dict[str, Any] = {
        "quote": f"Italy's {phrase} fell 12 points since 2014",
        "indicator_phrase": phrase,
        "geo": geo,
        "geo_basis": "stated" if geo else None,
        "peers": [],
        "start": "2014",
        "start_basis": "stated",
        "end": "latest",
        "end_basis": "stated",
        "assertion": Assertion(
            type=AssertionType.PERCENTAGE_POINTS,
            value=12,
            direction=Direction.DOWN,
            unit="points",
            start_value=None,
            end_value=None,
        ),
        "speaker": None,
        "said_on": None,
    }
    return ClaimSpec.model_validate({**base, **kw})


def answer(
    indicator_id: str | None, confidence: str = "high", alternatives: Sequence[str] = ()
) -> str:
    return json.dumps(
        {
            "indicator_id": indicator_id,
            "confidence": confidence,
            "reason": "Same population and unit.",
            "alternatives": list(alternatives),
        }
    )


def tools(*calls: tuple[str, str]) -> ChatResponse:
    return ChatResponse(
        content=None,
        tool_calls=tuple(
            ToolCall(id=f"call_{i}", name=n, arguments=a) for i, (n, a) in enumerate(calls)
        ),
    )


def matcher(outcomes: list[ChatResponse], catalog: Catalog = CATALOG) -> tuple[Matcher, FakeClient]:
    client = FakeClient()
    client.script("fake", outcomes)
    router = Router(config(provider("fake"), steps={"match": ["fake"]}), client, clock=FakeClock())
    return Matcher(router, catalog, vector_search(INDEX.search, EMBEDDER)), client


# --- the three outcomes the task names -------------------------------------------------------


async def test_clear_match() -> None:
    m, client = matcher([ChatResponse(content=answer("youth_unemployment_rate"))])

    result = await m.match(claim())

    assert (result.status, result.indicator_id, result.confidence) == (
        "matched",
        "youth_unemployment_rate",
        "high",
    )
    assert result.alternatives == [] and result.notes == [] and result.providers == ["fake"]
    # Only entries that cover Italy reach the model; the world-only ones are dropped first.
    assert {c.id for c in result.candidates} == {
        "youth_unemployment_rate",
        "unemployment_rate",
        "hicp_inflation",
    }
    assert set(result.excluded_by_geo) == {"life_expectancy", "gdp_per_capita", "co2_per_capita"}
    [(_, request)] = client.calls
    assert request.tools == TOOLS and request.response_format is None
    assert request.messages[0]["content"] == MATCH_SYSTEM
    user = str(request.messages[1]["content"])
    assert user.startswith("<claim>\n") and "Place: IT" in user and "Period: 2014 to latest" in user
    assert "- youth_unemployment_rate:" in user and "life_expectancy" not in user


async def test_ambiguous_match_keeps_valid_alternatives() -> None:
    m, _ = matcher(
        [
            ChatResponse(
                content=answer(
                    "unemployment_rate",
                    "medium",
                    ["youth_unemployment_rate", "made_up", "unemployment_rate", "life_expectancy",
                     "youth_unemployment_rate"],
                )
            )
        ]
    )  # fmt: skip

    result = await m.match(claim("unemployment rate"))

    assert (result.status, result.indicator_id, result.confidence) == (
        "matched",
        "unemployment_rate",
        "medium",
    )
    # Unknown ids, the pick itself, entries not covering Italy, and repeats are dropped.
    assert result.alternatives == ["youth_unemployment_rate"]


async def test_no_match_is_cant_check() -> None:
    m, _ = matcher([ChatResponse(content=answer(None, "high"))])

    result = await m.match(claim("number of dentists"))

    assert (result.status, result.indicator_id, result.alternatives) == ("cant_check", None, [])
    assert result.reason == "Same population and unit."


async def test_low_confidence_is_cant_check_with_the_pick_as_first_alternative() -> None:
    m, _ = matcher(
        [ChatResponse(content=answer("unemployment_rate", "low", ["youth_unemployment_rate"]))]
    )

    result = await m.match(claim("jobless rate"))

    assert (result.status, result.indicator_id, result.confidence) == ("cant_check", None, "low")
    assert result.alternatives == ["unemployment_rate", "youth_unemployment_rate"]
    assert result.notes == ["model picked 'unemployment_rate' with low confidence"]


# --- coverage filter -------------------------------------------------------------------------


async def test_no_indicator_covers_the_place_means_no_model_call() -> None:
    m, client = matcher([])

    result = await m.match(claim(geo="ZA"))

    assert result.status == "cant_check" and result.reason == "No catalog indicator covers ZA."
    assert len(result.excluded_by_geo) == 6 and client.calls == []


async def test_a_pick_that_does_not_cover_the_place_is_rejected() -> None:
    m, _ = matcher([ChatResponse(content=answer("life_expectancy"))])

    result = await m.match(claim())

    assert result.status == "cant_check"
    assert result.notes == ["model picked 'life_expectancy', which it was not shown for this place"]


async def test_no_place_means_no_filter() -> None:
    m, _ = matcher([ChatResponse(content=answer("life_expectancy"))])

    result = await m.match(claim("life expectancy", geo=None))

    assert result.status == "matched" and result.excluded_by_geo == []
    assert len(result.candidates) == 6


# --- tools -----------------------------------------------------------------------------------


async def test_tool_calls_run_and_can_widen_the_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(match_module, "TOP_K", 1)  # the model sees one candidate at first
    m, client = matcher(
        [
            tools(("get_indicator_meta", '{"indicator_id": "youth_unemployment_rate"}')),
            tools(("search_catalog", '{"query": "harmonised consumer price inflation"}'),
                  ("get_indicator_meta", '{"indicator_id": "unemployment_rate"}')),
            ChatResponse(
                content="```json\n"
                + answer("unemployment_rate", "high", ["hicp_inflation", "life_expectancy"])
                + "\n```"
            ),
        ]
    )  # fmt: skip

    result = await m.match(claim("youth unemployment rate"))

    assert [c.id for c in result.candidates] == ["youth_unemployment_rate"]
    # Both the entry read with get_indicator_meta and the one found by search became eligible.
    assert result.status == "matched" and result.indicator_id == "unemployment_rate"
    assert result.alternatives == ["hicp_inflation"]
    assert [(t.name, t.ok) for t in result.tool_calls] == [
        ("get_indicator_meta", True),
        ("search_catalog", True),
        ("get_indicator_meta", True),
    ]
    assert len(client.calls) == 3 and result.providers == ["fake"] * 3
    second = client.calls[1][1].messages
    assert second[-2]["role"] == "assistant" and second[-1]["role"] == "tool"
    assert second[-1]["tool_call_id"] == "call_0"
    meta = json.loads(str(second[-1]["content"]))
    assert meta["id"] == "youth_unemployment_rate" and meta["covers_claim_place"] is True
    assert meta["related"] == ["unemployment_rate"]
    found = json.loads(str(client.calls[2][1].messages[-2]["content"]))["results"]
    assert len(found) == 1 and found[0].startswith("hicp_inflation:")


async def test_list_geos_answers_coverage_without_making_the_entry_eligible() -> None:
    m, client = matcher(
        [
            tools(("list_geos", '{"indicator_id": "life_expectancy"}')),
            ChatResponse(content=answer("life_expectancy")),
        ]
    )

    result = await m.match(claim())

    geos = json.loads(str(client.calls[1][1].messages[-1]["content"]))
    assert geos == {"geo_coverage": ["WLD"], "covers_claim_place": False}
    assert result.status == "cant_check" and "not shown for this place" in result.notes[0]


async def test_tool_budget_then_a_final_schema_call() -> None:
    meta = ("get_indicator_meta", '{"indicator_id": "unemployment_rate"}')
    m, client = matcher(
        [
            tools(*[meta] * (MAX_TOOL_CALLS + 1)),
            ChatResponse(content=answer("youth_unemployment_rate", "medium")),
        ]
    )

    result = await m.match(claim())

    assert result.indicator_id == "youth_unemployment_rate"
    assert [t.ok for t in result.tool_calls] == [True] * MAX_TOOL_CALLS + [False]
    final = client.calls[-1][1]
    assert final.tools is None and final.response_format is not None
    assert final.messages[-1] == {"role": "user", "content": FINAL_PROMPT}
    spent = json.loads(str(final.messages[-2]["content"]))
    assert "budget" in spent["error"]


async def test_prose_answer_gets_a_final_schema_call() -> None:
    m, client = matcher(
        [
            ChatResponse(content="It is the youth unemployment rate."),
            ChatResponse(content=answer("youth_unemployment_rate")),
        ]
    )

    result = await m.match(claim())

    assert result.status == "matched" and len(client.calls) == 2
    final = client.calls[1][1].messages
    assert final[-2] == {"role": "assistant", "content": "It is the youth unemployment rate."}


@pytest.mark.parametrize(
    ("call", "error"),
    [(("get_indicator_meta", "not json"), "arguments must be a JSON object"),
     (("get_indicator_meta", "[1]"), "arguments must be a JSON object"),
     (("get_indicator_meta", '{"indicator_id": "nope"}'), "unknown indicator_id 'nope'"),
     (("run_python", "{}"), "unknown tool 'run_python'")],
)  # fmt: skip
async def test_bad_tool_calls_answer_with_an_error(call: tuple[str, str], error: str) -> None:
    m, client = matcher([tools(call), ChatResponse(content=answer("youth_unemployment_rate"))])

    result = await m.match(claim())

    assert result.status == "matched" and [t.ok for t in result.tool_calls] == [False]
    reply = json.loads(str(client.calls[1][1].messages[-1]["content"]))
    assert reply == {"error": error}


def test_no_answer_at_all_is_cant_check() -> None:
    m, _ = matcher([])
    result = m._verdict(_Run(claim()), None, [], [])
    assert (result.status, result.confidence, result.reason) == (
        "cant_check",
        None,
        "No answer from the model.",
    )


async def test_vector_search_accepts_an_async_index() -> None:
    async def search(vector: Sequence[float], k: int) -> list[IndicatorHit]:
        return INDEX.search(vector, k)

    hits = await vector_search(search, EMBEDDER)("youth unemployment rate", 2)
    assert hits[0].id == "youth_unemployment_rate" and len(hits) == 2


@pytest.mark.parametrize(
    ("kind", "start", "end", "needs"),
    [(AssertionType.COMPARE, "2020", "latest", True), (AssertionType.RATIO, "1950", "latest", True),
     (AssertionType.PERCENT, "2000", "2014", True), (AssertionType.ABSOLUTE, "2022-10", "2024-01", True),
     (AssertionType.PERCENT, "2025-Q2", "2025-Q2", False),
     (AssertionType.PERCENTAGE_POINTS, "2014", "latest", False),
     (AssertionType.LEVEL, "2013", "latest", False), (AssertionType.COMPARE, None, "latest", False)],
)  # fmt: skip
def test_needs_level_series(kind: AssertionType, start: str | None, end: str, needs: bool) -> None:
    a = Assertion(
        type=kind, value=None, direction=None, unit=None, start_value=None, end_value=None
    )
    spec = claim(start=start, end=end, assertion=a)
    assert needs_level_series(spec) is needs
    assert ("pick a series of levels" in claim_message(spec, [])) is needs


def test_claim_message_names_peers() -> None:
    message = claim_message(claim(peers=["FR", "DE"]), [])
    assert "Place: IT (compared with FR, DE)" in message


async def test_empty_answer_gets_a_final_schema_call() -> None:
    m, client = matcher(
        [ChatResponse(content=None), ChatResponse(content=answer("unemployment_rate"))]
    )

    result = await m.match(claim("unemployment rate"))

    assert result.indicator_id == "unemployment_rate" and len(client.calls) == 2


# --- frequency never rules a series out ------------------------------------------------------

REAL = load_catalog(REPO_ROOT / "packages" / "catalog")


async def real_search(phrase: str, k: int) -> list[IndicatorHit]:
    ids = ["youth_unemployment_rate_monthly", "unemployment_rate_monthly", "unemployment_rate_ilo",
           "real_gdp_growth_quarterly_qoq"]  # fmt: skip
    return [
        IndicatorHit(id=s.id, name=s.name, source=str(s.source), source_code=s.source_code,
                     unit=s.unit, frequency=str(s.frequency), definition=s.definition, score=0.9)
        for s in (REAL.get(i) for i in ids[:k])
    ]  # fmt: skip


def real_matcher(outcomes: list[ChatResponse]) -> tuple[Matcher, FakeClient]:
    client = FakeClient()
    client.script("fake", outcomes)
    router = Router(config(provider("fake"), steps={"match": ["fake"]}), client, clock=FakeClock())
    return Matcher(router, REAL, real_search), client


def test_candidates_say_how_a_year_is_made() -> None:
    assert "Frequency never rules a candidate out." in MATCH_SYSTEM
    assert yearly_note(REAL.get("youth_unemployment_rate_monthly")) == (
        " Yearly values: the average of the year's months."
    )
    assert yearly_note(REAL.get("government_debt_pct_gdp_quarterly")) == (
        " Yearly values: the year's last quarter."
    )
    assert yearly_note(REAL.get("real_gdp_growth_quarterly_qoq")) == " No yearly values."
    assert yearly_note(REAL.get("unemployment_rate_ilo")) == ""
    user = claim_message(claim(), [REAL.get("youth_unemployment_rate_monthly")])
    assert "Frequency: monthly. Yearly values: the average of the year's months." in user


@pytest.mark.parametrize(
    "first",
    [
        answer(None, alternatives=["youth_unemployment_rate_monthly"]),
        answer("youth_unemployment_rate_monthly", confidence="low"),
    ],
)
async def test_a_series_turned_down_for_its_frequency_is_asked_about_again(first: str) -> None:
    m, client = real_matcher(
        [ChatResponse(content=first),
         ChatResponse(content=answer("youth_unemployment_rate_monthly"))]
    )  # fmt: skip
    result = await m.match(claim())
    assert (result.status, result.indicator_id) == ("matched", "youth_unemployment_rate_monthly")
    assert result.notes[0] == (
        "asked again: youth_unemployment_rate_monthly was turned down, and frequency is no reason"
    )
    assert len(client.calls) == 2 and result.providers == ["fake", "fake"]
    nudge = str(client.calls[1][1].messages[-1]["content"])
    assert nudge.startswith(
        "Frequency is not a reason to turn down youth_unemployment_rate_monthly"
    )
    assert client.calls[1][1].response_format is not None  # the answer must fit the schema


async def test_asking_again_can_still_end_in_no_match() -> None:
    m, client = real_matcher(
        [ChatResponse(content=answer(None, alternatives=["unemployment_rate_monthly"])),
         ChatResponse(content=answer(None))]
    )  # fmt: skip
    result = await m.match(claim())
    assert result.status == "cant_check" and len(client.calls) == 2


@pytest.mark.parametrize(
    "alternatives", [["unemployment_rate_ilo"], ["real_gdp_growth_quarterly_qoq"], []]
)
async def test_no_second_ask_without_a_series_that_has_yearly_values(
    alternatives: list[str],
) -> None:
    m, client = real_matcher([ChatResponse(content=answer(None, alternatives=alternatives))])
    result = await m.match(claim())
    assert result.status == "cant_check" and len(client.calls) == 1
    assert not any(n.startswith("asked again") for n in result.notes)


# --- a claim about the present prefers the more frequent series ------------------------------

DEBT = ["government_debt_pct_gdp", "government_debt_pct_gdp_quarterly", "government_debt_eur"]


async def debt_search(phrase: str, k: int) -> list[IndicatorHit]:
    return [
        IndicatorHit(id=s.id, name=s.name, source=str(s.source), source_code=s.source_code,
                     unit=s.unit, frequency=str(s.frequency), definition=s.definition, score=0.9)
        for s in (REAL.get(i) for i in DEBT[:k])
    ]  # fmt: skip


def debt_matcher(outcomes: list[ChatResponse]) -> tuple[Matcher, FakeClient]:
    client = FakeClient()
    client.script("fake", outcomes)
    router = Router(config(provider("fake"), steps={"match": ["fake"]}), client, clock=FakeClock())
    return Matcher(router, REAL, debt_search), client


def level(said_on: str | None, start: str | None, end: str | None) -> ClaimSpec:
    return claim(
        "public debt", start=start, end=end, said_on=said_on,
        quote="Italy's public debt is 133% of GDP",
        assertion=Assertion(type=AssertionType.LEVEL, value=133, direction=None, unit="%",
                            start_value=None, end_value=None),
    )  # fmt: skip


@pytest.mark.parametrize(
    ("claim_", "now"),
    [
        (level(None, None, "latest"), True),
        (level("2013", None, "2013"), True),  # Renzi, 2013: "is 133%"
        (level("2013-06", "2013", "2013"), True),
        (level("2015", None, "2013"), False),  # said later about an earlier year
        (level(None, None, "2013"), False),  # no date to say it was about the present
        (claim(start="2014", end="2020", said_on="2020"), False),  # not a level
    ],
)
def test_a_claim_is_about_the_present_when_it_says_latest_or_a_level_of_its_own_year(
    claim_: ClaimSpec, now: bool
) -> None:
    assert says_now(claim_) is now


async def test_a_present_tense_claim_is_asked_again_about_a_more_frequent_alternative() -> None:
    m, client = debt_matcher(
        [ChatResponse(content=answer("government_debt_pct_gdp", alternatives=DEBT[1:])),
         ChatResponse(content=answer("government_debt_pct_gdp_quarterly"))]
    )  # fmt: skip
    result = await m.match(level("2013", None, "2013"))
    assert result.indicator_id == "government_debt_pct_gdp_quarterly"
    asked = "asked again: government_debt_pct_gdp_quarterly is quarterly, more often than"
    assert result.notes == [f"{asked} government_debt_pct_gdp, and the claim is about the present"]
    nudge = str(client.calls[1][1].messages[-1]["content"])
    assert nudge.startswith("The claim is about the present, and government_debt_pct_gdp_quarterly")
    assert "otherwise keep government_debt_pct_gdp" in nudge
    assert client.calls[1][1].response_format is not None


async def test_the_model_may_keep_the_annual_series_when_asked_again() -> None:
    m, client = debt_matcher(
        [ChatResponse(content=answer("government_debt_pct_gdp", alternatives=DEBT[1:2])),
         ChatResponse(content=answer("government_debt_pct_gdp"))]
    )  # fmt: skip
    result = await m.match(level(None, None, "latest"))
    assert result.indicator_id == "government_debt_pct_gdp" and len(client.calls) == 2


@pytest.mark.parametrize(
    ("claim_", "first"),
    [
        (level(None, None, "2013"), answer("government_debt_pct_gdp", alternatives=DEBT[1:2])),
        (
            level(None, None, "latest"),
            answer("government_debt_pct_gdp_quarterly"),
        ),  # already finest
        (level(None, None, "latest"), answer("government_debt_pct_gdp", alternatives=DEBT[2:])),
        (level(None, None, "latest"), answer("government_debt_pct_gdp", alternatives=["nope"])),
    ],
)
async def test_no_second_ask_unless_a_present_claim_has_a_more_frequent_same_unit_alternative(
    claim_: ClaimSpec, first: str
) -> None:
    m, client = debt_matcher([ChatResponse(content=first)])
    result = await m.match(claim_)
    assert result.status == "matched" and len(client.calls) == 1 and result.notes == []
