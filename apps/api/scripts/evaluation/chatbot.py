"""The head-to-head baseline (P4.6): a general chatbot, asked plainly whether each claim is true.

One call per text. The model gets the text, the labelled claims (the quotes a person marked, so
it is asked about exactly what the pipeline is scored on) and the five verdict labels with a line
each. It has no tools, no data and no web search: it answers from what it knows, as a person
pasting the text into a chat window would get. Its answers are scored with the same labels, the
same confusion matrix and the same cost figures as the pipeline's (score.py), and written as a
report of `kind: chatbot`.

Every call goes through the router, like every other model call. Offline tooling only: it may
use the offline-only provider (Gemini, D003), so it is never imported by a request path.
"""

import sys
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from holdsup.router import RouterConfig, RouterError, Use
from holdsup.router.client import OpenAICompatibleClient
from holdsup.verdict import Label
from scripts.evaluation.benchmark import BenchmarkText
from scripts.evaluation.meter import Meter, MeteredClient
from scripts.evaluation.patient import BUDGET_S, PatientRouter
from scripts.evaluation.run import OnText, Progress, TextRun
from scripts.evaluation.score import MISSED, ClaimOutcome, TextOutcome, not_run

STEP = "baseline"  # the router step (providers.yaml)

SYSTEM = "You are a helpful general-purpose assistant. Answer from what you know."

LABEL_HELP = (
    (Label.SUPPORTED, "the claim is true as stated"),
    (Label.SUPPORTED_FRAMING_MATTERS, "the figures are right, but the way they are presented misleads"),
    (Label.PARTLY_SUPPORTED, "part of the claim is true and part is not"),
    (Label.NOT_SUPPORTED, "the claim is false"),
    (Label.CANT_CHECK, "you cannot tell"),
)  # fmt: skip


class ChatVerdict(BaseModel):
    claim: int  # the claim's number in the prompt, from 1
    label: Label


class ChatAnswer(BaseModel):
    verdicts: list[ChatVerdict]


def messages(item: BenchmarkText) -> list[ChatCompletionMessageParam]:
    """The plain question: is each of these claims true?"""
    labels = "\n".join(f"- {label}: {help_}" for label, help_ in LABEL_HELP)
    claims = "\n".join(f"{n}. {c.quote}" for n, c in enumerate(item.claims, 1))
    user = (
        f"Here is a text:\n\n{item.text}\n\n"
        "Is each of the numbered claims below true? Answer each with exactly one of these "
        f"labels:\n{labels}\n\nClaims:\n{claims}\n\n"
        'Reply with JSON only: {"verdicts": [{"claim": 1, "label": "supported"}, ...]}, '
        "one entry per claim."
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def score_answer(
    item: BenchmarkText, answer: ChatAnswer, *, seconds: float, model_calls: int
) -> TextOutcome:
    """Each labelled claim against the chatbot's answer for it. A claim it gave no answer for
    counts as wrong ("missed" in the matrix, shown as "no answer"); the first answer to a
    number wins, and numbers outside the text's claims are ignored."""
    given: dict[int, Label] = {}
    for v in answer.verdicts:
        given.setdefault(v.claim, v.label)
    outcomes = []
    for n, claim in enumerate(item.claims, 1):
        label = given.get(n)
        ok = label is claim.expected if label is not None else False
        outcomes.append(
            ClaimOutcome(
                text_id=item.id,
                index=n - 1,
                quote=claim.quote,
                expected=claim.expected,
                expected_indicator=claim.indicator,
                verdict=MISSED if label is None else str(label),
                verdict_ok=ok,
                failed_step=None if ok else STEP,
            )
        )
    return TextOutcome(
        id=item.id,
        labelled=len(item.claims),
        seconds=seconds,
        model_calls=model_calls,
        outcomes=outcomes,
    )


@dataclass
class ChatRig:
    """What a baseline run needs: a router and the meter that counts its calls."""

    router: PatientRouter
    meter: Meter


@asynccontextmanager
async def live_chat_rig(
    config: RouterConfig, wait_budget_s: float = BUDGET_S
) -> AsyncIterator[ChatRig]:  # pragma: no cover (live)
    meter = Meter()
    meter.step = STEP
    yield ChatRig(
        PatientRouter(
            config,
            MeteredClient(OpenAICompatibleClient(), meter),
            budget_s=wait_budget_s,
            progress=lambda line: print(line, file=sys.stderr),
        ),
        meter,
    )


async def evaluate_chatbot(
    rig: ChatRig,
    texts: Sequence[BenchmarkText],
    use: Use,
    progress: Progress = lambda _: None,
    *,
    on_text: OnText = lambda _: None,
) -> list[TextOutcome]:
    """Ask the chatbot about every text and score the answers. A text the router cannot serve
    is recorded as not run (left out of the accuracy, and counted); each text, once scored,
    goes to `on_text` with the calls it made."""
    out: list[TextOutcome] = []
    for n, item in enumerate(texts, 1):
        before = len(rig.meter.calls)
        started = time.monotonic()
        try:
            result = await rig.router.complete(STEP, messages(item), use=use, schema=ChatAnswer)
        except RouterError as exc:
            outcome = not_run(
                item,
                f"router: {exc}",
                round(time.monotonic() - started, 2),
                len(rig.meter.calls) - before,
            )
        else:
            if result.parsed is None:  # the router returns the schema it was asked for
                raise AssertionError("no parsed answer")  # pragma: no cover
            outcome = score_answer(
                item,
                result.parsed,
                seconds=round(time.monotonic() - started, 2),
                model_calls=len(rig.meter.calls) - before,
            )
        out.append(outcome)
        on_text(TextRun(outcome=outcome, calls=rig.meter.calls[before:]))
        progress(_line(n, len(texts), outcome))
    return out


def _line(n: int, total: int, outcome: TextOutcome) -> str:
    if outcome.error is not None:
        return f"[{n}/{total}] {outcome.id}: not run ({outcome.error})"
    right = sum(o.verdict_ok is True for o in outcome.outcomes)
    return f"[{n}/{total}] {outcome.id}: {right}/{outcome.labelled} verdicts right"
