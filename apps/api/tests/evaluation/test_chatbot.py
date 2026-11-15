"""The chatbot baseline: the question it is asked, how its answers are scored, and a run."""

import json
from pathlib import Path

import pytest
from scripts.evaluation.chatbot import (
    LABEL_HELP,
    STEP,
    ChatAnswer,
    ChatRig,
    ChatVerdict,
    evaluate_chatbot,
    messages,
    score_answer,
)
from scripts.evaluation.meter import Meter, MeteredClient
from scripts.evaluation.patient import PatientRouter
from scripts.evaluation.report import build_report, markdown, write_report
from scripts.evaluation.run import TextRun
from scripts.evaluation.score import MISSED, summarize

from holdsup.router import RouterConfig, Use
from holdsup.router.client import ChatResponse
from holdsup.verdict import Label
from tests.evaluation.helpers import FALL, FALL_QUOTE, label, make_report, text
from tests.router.fakes import FakeClient, FakeClock, config, provider

TWO = text(
    "r002",
    FALL + " Rents rose too.",
    label(expected=Label.SUPPORTED),
    label("Rents rose too", indicator=None, expected=Label.CANT_CHECK),
)


def reply(*pairs: tuple[int, str]) -> ChatResponse:
    body = {"verdicts": [{"claim": n, "label": name} for n, name in pairs]}
    return ChatResponse(content=json.dumps(body), prompt_tokens=100, completion_tokens=10)


def rig(
    *script: ChatResponse, keys: set[str] | None = None
) -> tuple[ChatRig, FakeClient, RouterConfig]:
    client = FakeClient(keys=keys)
    client.script("fake", script)
    meter = Meter()
    meter.step = STEP
    conf = config(provider("fake"), steps={STEP: ["fake"]})
    router = PatientRouter(conf, MeteredClient(client, meter), clock=FakeClock())
    return ChatRig(router, meter), client, conf


def test_the_question_is_plain_and_carries_the_text_the_claims_and_every_label() -> None:
    system, user = messages(TWO)

    assert "general-purpose assistant" in str(system["content"])
    body = str(user["content"])
    assert TWO.text in body
    assert f"1. {FALL_QUOTE}" in body and "2. Rents rose too" in body
    assert all(f"- {name}:" in body for name, _ in LABEL_HELP)
    assert "web" not in body.lower() and "tool" not in body.lower()  # nothing it could use


def test_each_labelled_claim_is_scored_against_the_answer_for_it() -> None:
    answer = ChatAnswer(
        verdicts=[ChatVerdict(claim=1, label=Label.SUPPORTED), ChatVerdict(claim=2, label=Label.NOT_SUPPORTED)]
    )  # fmt: skip

    out = score_answer(TWO, answer, seconds=1.5, model_calls=1)

    assert [o.verdict_ok for o in out.outcomes] == [True, False]
    assert [o.verdict for o in out.outcomes] == ["supported", "not_supported"]
    assert [o.failed_step for o in out.outcomes] == [None, STEP]
    assert out.labelled == 2 and out.extracted == 0 and not any(o.found for o in out.outcomes)


def test_a_claim_it_gave_no_answer_for_is_wrong_and_extra_or_repeated_numbers_do_not_count() -> (
    None
):
    answer = ChatAnswer(
        verdicts=[
            ChatVerdict(claim=1, label=Label.SUPPORTED),
            ChatVerdict(claim=1, label=Label.NOT_SUPPORTED),  # the first answer to a number wins
            ChatVerdict(claim=7, label=Label.CANT_CHECK),  # no such claim
        ]
    )

    out = score_answer(TWO, answer, seconds=0, model_calls=1)

    assert [o.verdict for o in out.outcomes] == ["supported", MISSED]
    assert [o.verdict_ok for o in out.outcomes] == [True, False]


async def test_a_run_asks_once_per_text_and_records_the_calls() -> None:
    chat, client, _ = rig(reply((1, "supported"), (2, "cant_check")))
    seen: list[TextRun] = []

    out = await evaluate_chatbot(chat, [TWO], Use.OFFLINE, on_text=seen.append)

    assert client.called() == ["fake"]
    assert [o.verdict_ok for o in out[0].outcomes] == [True, True]
    assert out[0].model_calls == 1
    assert [(c.step, c.provider, c.prompt_tokens) for c in seen[0].calls] == [(STEP, "fake", 100)]


async def test_a_text_the_router_cannot_serve_is_not_run_rather_than_wrong() -> None:
    chat, _, _ = rig(keys=set())  # no provider has a key

    out = await evaluate_chatbot(chat, [TWO], Use.OFFLINE)

    assert out[0].error is not None and out[0].error.startswith("router:")
    assert [o.status for o in out[0].outcomes] == ["not_run", "not_run"]


async def test_the_report_is_a_chatbot_report_with_verdicts_and_cost_only(tmp_path: Path) -> None:
    chat, _, conf = rig(reply((1, "supported"), (2, "not_supported")))
    outcomes = await evaluate_chatbot(chat, [TWO], Use.OFFLINE)
    report = build_report(
        name="dev.chatbot",
        benchmark="claims.jsonl",
        split="dev",
        provider="router",
        use="offline",
        versions=make_report(1, 1).versions,
        config=conf,
        metrics=summarize(outcomes, chat.meter.calls),
        texts=outcomes,
        kind="chatbot",
    )

    md = markdown(report)
    write_report(report, tmp_path)

    assert report.kind == "chatbot" and report.metrics.verdict.accuracy.rate == 0.5
    assert "# Chatbot baseline: dev.chatbot" in md
    assert "Accuracy: 50.0% (1/2)" in md and "no web search" in md
    assert "Extraction" not in md and "Source series" not in md  # nothing the chatbot did not do
    assert "dev.chatbot.json" in {p.name for p in tmp_path.iterdir()}


@pytest.mark.parametrize("bad", ["", "not json", '{"verdicts": [{"claim": 1, "label": "maybe"}]}'])
async def test_an_unusable_answer_is_a_router_failure_not_a_wrong_verdict(bad: str) -> None:
    chat, _, _ = rig(*[ChatResponse(content=bad)] * 4)

    out = await evaluate_chatbot(chat, [TWO], Use.OFFLINE)

    assert out[0].error is not None
