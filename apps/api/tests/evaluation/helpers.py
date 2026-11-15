"""Shared pieces for the evaluation tests: a rig of fakes (a scripted provider, recorded
source series, the real catalog) and builders for benchmark texts. No network, no model."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from scripts.evaluation.benchmark import BenchmarkText, LabelledClaim
from scripts.evaluation.meter import Call, Meter, MeteredClient
from scripts.evaluation.report import ROUTER, Report, Stamp, build_report
from scripts.evaluation.run import Rig
from scripts.evaluation.score import TextOutcome, score_text, summarize
from scripts.evaluation.score import not_run as not_run_text

from holdsup.pipeline.claim import Assertion, AssertionType, ClaimSpec
from holdsup.pipeline.result import ClaimResult, IndicatorRef, PipelineOutput, Versions
from holdsup.pipeline.run import Fetcher, Pipeline
from holdsup.pipeline.trace import ModelUse, Step
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.router.errors import ProviderError
from holdsup.verdict import Label, Verdict, load_tolerances
from tests.pipeline.test_regressions import (
    CATALOG,
    EXPLAINED,
    TODAY,
    RecordedFetcher,
    extraction,
    match,
    model_claim,
    plan,
    search,
)
from tests.router.fakes import FakeClient, FakeClock, config, provider

STEPS = ("extract", "match", "plan", "explain")

FALL = "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023."
FALL_QUOTE = FALL[:-1]


def make_rig(
    script: Sequence[ChatResponse | ProviderError],
    *,
    fetcher: Fetcher | None = None,
    keys: set[str] | None = None,
) -> tuple[Rig, FakeClient, Meter]:
    """A rig whose one provider, "fake", replays `script`; every step uses it."""
    client = FakeClient(keys=keys)
    client.script("fake", script)
    meter = Meter()
    pipeline = Pipeline(
        router=Router(
            config(provider("fake"), steps={s: ["fake"] for s in STEPS}),
            MeteredClient(client, meter),
            clock=FakeClock(),
        ),
        catalog=CATALOG,
        search=search,
        fetcher=fetcher or RecordedFetcher(),
        tolerances=load_tolerances(),
        today=lambda: TODAY,
    )
    return Rig(pipeline, search, meter), client, meter


def label(
    quote: str = FALL_QUOTE,
    *,
    indicator: str | None = "unemployment_rate_monthly",
    geo: str | None = "IT",
    window: tuple[str, str] = ("2015", "2023"),
    expected: Label = Label.SUPPORTED,
) -> LabelledClaim:
    return LabelledClaim(
        quote=quote,
        indicator=indicator,
        geo=geo,
        window=window,
        expected=expected,
        justification="Because the series says so.",
    )


def text(
    id: str = "r001", body: str = FALL, *claims: LabelledClaim, split: str | None = None
) -> BenchmarkText:
    fields: dict[str, Any] = {"split": split} if split else {}
    return BenchmarkText(id=id, text=body, claims=claims or (label(),), **fields)


def fall_claim() -> dict[str, Any]:
    """The extractor's reading of FALL, as a model reply carries it."""
    return model_claim(
        FALL_QUOTE, "unemployment rate", "2015", "2023", direction="down", start_value=11.9,
        end_value=7.7,
    )  # fmt: skip


def fall_script() -> list[ChatResponse | ProviderError]:
    """The recorded r001 run: extract, match, plan, explain (see test_regressions.py)."""
    return [
        extraction(fall_claim()),
        match("unemployment_rate_monthly", ["unemployment_rate_ilo"]),
        plan({"op": "change", "geo": "IT", "start": "2015-01", "end": "2023-12",
              "kind": "percentage_points"}),
        EXPLAINED,
    ]  # fmt: skip


def spec(
    quote: str = FALL_QUOTE,
    *,
    geo: str | None = "IT",
    start: str | None = "2015",
    end: str | None = "2023",
) -> ClaimSpec:
    """A claim as the extractor returns it."""
    return ClaimSpec(
        quote=quote,
        indicator_phrase="unemployment rate",
        geo=geo,
        geo_basis=None,
        peers=[],
        start=start,
        start_basis=None,
        end=end,
        end_basis=None,
        assertion=Assertion(
            type=AssertionType.LEVEL,
            value=None,
            direction=None,
            unit=None,
            start_value=None,
            end_value=None,
        ),
        speaker=None,
        said_on=None,
    )


def result(
    claim: ClaimSpec | None = None,
    *,
    got: Label = Label.SUPPORTED,
    indicator: str | None = "unemployment_rate_monthly",
    stopped_at: Step | None = None,
    retryable: bool = False,
    explained: str = "model",  # "model", "template" (rejected) or "none" (no model asked)
    index: int = 0,
) -> ClaimResult:
    """One claim's result, as the pipeline would have left it."""
    models = [ModelUse(step=Step.EXPLAIN, provider="p", model="m")] if explained != "none" else []
    return ClaimResult(
        index=index,
        claim=claim or spec(),
        indicator=IndicatorRef.of(CATALOG.get(indicator)) if indicator else None,
        verdict=Verdict(label=got, reason=f"{got} because of the numbers."),
        explanation="",
        explanation_source="model" if explained == "model" else "template",
        models=models,
        retryable=retryable,
        stopped_at=stopped_at,
    )


def output(*results: ClaimResult) -> PipelineOutput:
    return PipelineOutput(
        claims=list(results),
        versions=Versions(app="0.0.0", catalog=CATALOG.version, tolerances=5),
        models=[],
    )


def make_report(
    right: int,
    total: int,
    *,
    not_run: int = 0,
    eval: str = "0.1.0",
    benchmark: str = "smoke_claims.jsonl",
    provider_name: str | None = None,
    calls: Sequence[Call] = (),
) -> Report:
    """A report of `total` one-claim texts, `right` of them answered correctly, and `not_run`
    more texts the router could not serve. Every step's only choice is the provider `fake`."""
    texts: list[TextOutcome] = [
        score_text(
            text(f"t{i}", "x", label()),
            output(result(got=Label.SUPPORTED if i < right else Label.NOT_SUPPORTED)),
            {0: ["unemployment_rate_monthly"]},
            seconds=1.0,
            model_calls=4,
        )
        for i in range(total)
    ]
    texts += [
        not_run_text(text(f"n{i}", "x", label()), "router: out", 0.5, 0) for i in range(not_run)
    ]
    return build_report(
        name="smoke",
        benchmark=benchmark,
        split="dev",
        provider=provider_name or ROUTER,
        use="live",
        versions=Stamp(app="0.0.0+abc1234", catalog=CATALOG.version, tolerances=5, eval=eval),
        config=config(provider("fake"), steps={s: ["fake"] for s in STEPS}),
        metrics=summarize(texts, list(calls)),
        texts=texts,
        now=datetime(2026, 11, 12, 9, 30, tzinfo=UTC),
    )
