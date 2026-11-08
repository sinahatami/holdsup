"""Explanation step with a fake router: the invented-number check, retry and template."""

import json
from typing import Any

import pytest

from holdsup.ops import (
    AnnualValue,
    ChangeKind,
    Frequency,
    Series,
    annual_flag,
    change,
    compare,
    rank,
    value_at,
)
from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec, Direction
from holdsup.pipeline.explain import (
    EXPLAIN_SYSTEM,
    allowed_numbers,
    explain,
    explain_message,
    fmt,
    invented_numbers,
    template_explanation,
    written_numbers,
)
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label, Verdict, cant_check, decide, load_tolerances
from tests.router.fakes import FakeClient, FakeClock, config, provider

TOL = load_tolerances()
RATE = Series.from_values(
    "IT", {"2015": 40.0, "2016": 37.25, "2018": 32.0, "2020": 28.0937}, "% of labour force"
)


def claim(quote: str = "Unemployment fell 12 points since 2015", value: float = 12) -> ClaimSpec:
    base: dict[str, Any] = {
        "quote": quote,
        "indicator_phrase": "unemployment",
        "geo": "IT",
        "geo_basis": "stated",
        "peers": [],
        "start": "2015",
        "start_basis": "stated",
        "end": "latest",
        "end_basis": "stated",
        "assertion": Assertion(
            type=AssertionType.PERCENTAGE_POINTS,
            value=value,
            direction=Direction.DOWN,
            unit="points",
            start_value=None,
            end_value=None,
        ),
        "speaker": None,
        "said_on": None,
    }
    return ClaimSpec.model_validate(base)


RECORDS = [change(RATE, "2013", "2020", ChangeKind.PERCENTAGE_POINTS)]  # 2013 → 2015, flagged
VERDICT = decide(claim(), RECORDS, [0], unit="% of labour force", tolerances=TOL)
ALLOWED = allowed_numbers(RECORDS, VERDICT, claim(), "% of labour force")


# --- reading numbers -------------------------------------------------------------------------


def test_written_numbers() -> None:
    found = written_numbers(
        "From 1,660,000 to 28.1% in 2024-Q1 (Q3 2023), -12 points, 1.7 trillion euros, 28,000 "
        "people, CO2 and 2015-2020."
    )
    assert [(w.text, w.value, w.half_unit) for w in found] == [
        ("1,660,000", 1_660_000, 5_000),
        ("28.1", 28.1, pytest.approx(0.05)),
        ("2023", 2023, 0.5),
        ("-12", 12, 0.5),
        ("1.7 trillion", 1.7e12, pytest.approx(0.05e12)),
        ("28,000", 28_000, 500),
        ("2015", 2015, 0.5),
        ("2020", 2020, 0.5),
    ]


def test_half_year_labels_are_dates_not_numbers() -> None:
    found = written_numbers("The price was 0.31 in 2024-S1 and 0.29 in S2 2023.")
    assert [(w.text, w.value) for w in found] == [("0.31", 0.31), ("0.29", 0.29), ("2023", 2023)]


def test_allowed_numbers_cover_records_parts_periods_and_the_claim() -> None:
    text = "From 40 to 28.0937, -11.9063 against 12 ± 0.5 (2013 asked, 2015 used, 2020)."
    assert invented_numbers(text, ALLOWED) == []
    # A ratio of 0.52 may be written as 52%; an amount in million euro with a scale word.
    r = change(Series.from_values("IT", {"2015": 10.0, "2020": 5.2}), "2015", "2020",
               ChangeKind.RATIO)  # fmt: skip
    v = decide(claim(), [r], [0], unit="million euro", tolerances=TOL)
    allowed = allowed_numbers([r], v, claim(), "million euro")
    assert invented_numbers("The ratio was 0.52, a 52% level; 5.2 million euro.", allowed) == []
    assert invented_numbers("That is 5.2 trillion.", allowed) == ["5.2 trillion"]


def test_window_share_and_threshold_are_allowed() -> None:
    v = decide(claim(), RECORDS, [0], unit="%", tolerances=TOL, window_share=0.4)
    allowed = allowed_numbers(RECORDS, v, claim(), "%")
    assert invented_numbers("It holds in 40% of windows; the bar is 70%.", allowed) == []


def test_numbers_in_code_written_notes_are_allowed() -> None:
    note = annual_flag(Frequency.MONTHLY, AnnualValue.MEAN, ["2015", "2023"])
    r = RECORDS[0].model_copy(update={"flags": [note]})
    allowed = allowed_numbers([r], VERDICT, claim(), "%")
    assert invented_numbers("Each year is the average of its 12 monthly values.", allowed) == []
    assert invented_numbers("Each year is the average of 13 values.", ALLOWED) == ["13"]


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("Unemployment fell from 40% in 2015 to 28.1% in 2020, about 12 points.", []),
        ("It fell 11.9 points, close to the 12 claimed.", []),
        ("It fell 11.91 points.", []),
        ("It fell 11.90 points.", ["11.90"]),  # written to two decimals, but it is 11.906
        ("It fell 13 points.", ["13"]),
        ("That is a 30% drop.", ["30"]),  # a percent change the model computed itself
        ("Unemployment was 37.25% in 2016.", ["37.25", "2016"]),  # not a computed result
        ("It fell by 2.3 points a year.", ["2.3"]),
    ],
)
def test_invented_numbers(text: str, bad: list[str]) -> None:
    assert invented_numbers(text, ALLOWED) == bad


@pytest.mark.parametrize(
    ("x", "text"),
    [(28135.6, "28,136"), (28.0937, "28.1"), (0.5214, "0.52"), (-12.0, "-12"), (10.0, "10"),
     (0.004, "0"), (-0.001, "0")],
)  # fmt: skip
def test_fmt(x: float, text: str) -> None:
    assert fmt(x) == text


# --- the model call --------------------------------------------------------------------------


def explainer(*texts: str) -> tuple[Router, FakeClient]:
    client = FakeClient()
    client.script("fake", [ChatResponse(content=json.dumps({"explanation": t})) for t in texts])
    router = Router(config(provider("fake"), steps={"explain": ["fake"]}), client,
                    clock=FakeClock())  # fmt: skip
    return router, client


GOOD = "Unemployment fell from 40% in 2015 to 28.1% in 2020, about 12 points as claimed."
INVENTED = "Unemployment fell by about 30%, from 40% to 28.1%."


async def test_a_clean_explanation_is_used() -> None:
    router, client = explainer(GOOD)
    out = await explain(router, claim(), VERDICT, RECORDS, indicator="Unemployment rate",
                        unit="%")  # fmt: skip
    assert (out.text, out.source, out.rejected, out.providers) == (GOOD, "model", [], ["fake"])
    [(_, request)] = client.calls
    assert request.messages[0]["content"] == EXPLAIN_SYSTEM


async def test_an_invented_number_is_rejected_and_retried() -> None:
    router, client = explainer(INVENTED, GOOD)
    out = await explain(router, claim(), VERDICT, RECORDS, indicator="Unemployment rate",
                        unit="%")  # fmt: skip
    assert (out.text, out.source, out.rejected) == (GOOD, "model", [["30"]])
    feedback = str(client.calls[1][1].messages[-1]["content"])
    assert feedback.startswith("These numbers are not in RESULTS: 30.")


async def test_rejected_twice_falls_back_to_the_template() -> None:
    router, client = explainer(INVENTED, "")
    out = await explain(router, claim(), VERDICT, RECORDS, indicator="unemployment rate",
                        unit="%")  # fmt: skip
    assert out.source == "template" and out.rejected == [["30"], ["(empty)"]]
    assert len(client.calls) == 2
    assert "Holds within tolerance" not in out.text  # the page shows the reason above
    assert "the unemployment rate data gives -11.9 against -12 claimed" in out.text
    assert invented_numbers(out.text, ALLOWED) == []


def test_template_passes_the_check_for_every_label() -> None:
    it = Series.from_values("IT", {"2020": 28.0}, "%")
    de = Series.from_values("DE", {"2020": 6.0}, "%")
    cases: list[tuple[list[Any], Verdict]] = [
        ([], cant_check("no data for IT")),
        ([value_at(it, "2020")],
         decide(claim(value=30), [value_at(it, "2020")], [0], unit="%", tolerances=TOL)),
        ([compare(it, de, "2020")], VERDICT),
        ([rank([it, de], "IT", "2020")], VERDICT),
    ]  # fmt: skip
    for records, verdict in cases:
        text = template_explanation(verdict, "unemployment rate")
        assert (
            invented_numbers(text, allowed_numbers(records + RECORDS, verdict, claim(), "%")) == []
        )
    assert template_explanation(cant_check("no data for IT"), "x") == ""


def test_explain_message() -> None:
    text = explain_message(claim(), VERDICT, RECORDS, "Unemployment rate (Eurostat une_rt_a)")
    assert text.startswith("<claim>\nUnemployment fell 12 points since 2015\n</claim>\n")
    assert "Verdict: Supported by the data. Holds within tolerance." in text
    assert "- assertion: holds; computed -11.9063" in text
    assert "change(geo=IT, start=2013, end=2020, kind=percentage_points) = -11.9 percentage " \
        "points" in text  # fmt: skip
    assert "  from: IT 2015: 40, IT 2020: 28.1" in text
    assert "  note: IT has no value for 2013; used 2015" in text
    long = rank([Series.from_values(f"G{i:02d}", {"2020": float(i)}) for i in range(14)], "G00",
                "2020")  # fmt: skip
    text = explain_message(claim(), cant_check("x"), [long], "x")
    assert "(+2 more)" in text and "  also: of 14" in text and "Checks:" not in text
    assert Label.CANT_CHECK.value == "cant_check"


def test_template_skips_parts_without_a_computed_value() -> None:
    from holdsup.verdict import Part

    v = Verdict(label=Label.NOT_SUPPORTED, reason="Outside tolerance.",
                parts=[Part(name="assertion", holds=False, detail="no value")])  # fmt: skip
    assert template_explanation(v, "x") == ""
