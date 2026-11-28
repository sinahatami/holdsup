"""A check as one Telegram message: every claim's verdict, escaped, within Telegram's limit."""

from datetime import UTC, datetime

import pytest

from holdsup.problems import (
    Problem,
    at_capacity,
    internal_error,
    no_figures,
    pages_limited,
    rate_limited,
)
from holdsup.service.store import CheckResult, PageSource
from holdsup.telegram.bot import outcome
from holdsup.telegram.format import BUDGET, MAX_QUOTE, problem_message, result_message
from tests.service.fakes import EXPLANATION, QUOTE, TEXT, happy_script, make_runner
from tests.telegram.fakes import SITE


@pytest.fixture
async def checked() -> CheckResult:
    runner, _, _ = make_runner(happy_script())
    submitted = await runner.submit(TEXT, "someone")
    result = await outcome(runner, submitted.id)
    assert isinstance(result, CheckResult)
    return result


def test_one_claim(checked: CheckResult) -> None:
    assert result_message(checked, SITE) == (
        "<b>Holds up</b>\n"
        f"“{QUOTE}”\n"
        f"{EXPLANATION}\n"
        "<i>Unemployment rate · Eurostat</i>\n\n"
        f'<a href="{SITE}/check/{checked.id}">See the receipt</a>'
    )


def test_text_from_people_and_pages_is_escaped(checked: CheckResult) -> None:
    claim = checked.claims[0]
    sly = claim.model_copy(
        update={"claim": claim.claim.model_copy(update={"quote": '<a href="x">5%</a> & more'})}
    )
    page = PageSource(
        url='https://news.example/?a=1&b="2"', title="<script>Jobs</script>",
        read_at=datetime.now(UTC), used=1, found=1,
    )  # fmt: skip
    message = result_message(checked.model_copy(update={"claims": [sly], "page": page}), SITE)
    assert message.startswith(
        'From <a href="https://news.example/?a=1&amp;b=&quot;2&quot;">'
        "&lt;script&gt;Jobs&lt;/script&gt;</a>\n\n"
    )
    assert '“&lt;a href="x"&gt;5%&lt;/a&gt; &amp; more”' in message
    assert "<script>" not in message and '<a href="x">' not in message


def test_a_long_quote_is_cut(checked: CheckResult) -> None:
    claim = checked.claims[0]
    long = claim.model_copy(update={"claim": claim.claim.model_copy(update={"quote": "9% " * 400})})
    message = result_message(checked.model_copy(update={"claims": [long]}), SITE)
    assert "“" + ("9% " * 400)[:MAX_QUOTE] + "…”" in message


def test_claims_past_the_budget_are_left_to_the_receipt(checked: CheckResult) -> None:
    many = checked.model_copy(update={"claims": checked.claims * 40})
    message = result_message(many, SITE)
    shown = message.count("<b>Holds up</b>")
    assert 1 < shown < 40
    assert f"…and {40 - shown} more in the receipt." in message
    assert len(message) < BUDGET + 200 < 4_096
    assert message.endswith(f'<a href="{SITE}/check/{checked.id}">See the receipt</a>')


def test_no_claims(checked: CheckResult) -> None:
    message = result_message(checked.model_copy(update={"claims": []}), SITE)
    assert message.startswith("I found no claim with a number in it.")
    assert "/check/" not in message


@pytest.mark.parametrize(
    ("problem", "said"),
    [
        (rate_limited(61), "too many new checks this hour. Try again in about 2 minutes."),
        (pages_limited(30), "too many links this hour. Try again in about 1 minute,"),
        (at_capacity(600), "Every free model provider is busy or out of quota."),
        (no_figures("The page <b>states</b> no figure."), "The page &lt;b&gt;states"),
        (internal_error(), "Sorry, that check failed."),
    ],
)
def test_problems_in_the_bots_words(problem: Problem, said: str) -> None:
    assert said in problem_message(problem)
    assert "address" not in problem_message(problem)
