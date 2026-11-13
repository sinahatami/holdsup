"""Score the pipeline's output against the labels, per claim and in total.

Each step is scored on the claims that reached it, so one early miss does not also count
against every later step; the verdict has a second, end-to-end figure that counts a claim the
extractor never found as wrong. A wrong verdict is traced to the first step that went wrong.

What leaves the figures: a text the router could not serve (`not_run`: no step ran) and a
claim whose source was down (`verdict_unavailable`: extraction and matching still count).
Both are counted and shown, so an outage is never mistaken for a model failure, and the gate
refuses to judge a run where too many claims dropped out.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, Field

from holdsup.pipeline.result import ClaimResult, PipelineOutput
from holdsup.pipeline.trace import Step
from holdsup.verdict import Label
from scripts.evaluation.align import align, end_ok, geo_ok, start_ok
from scripts.evaluation.benchmark import BenchmarkText, LabelledClaim
from scripts.evaluation.meter import Call

MISSED = "missed"  # a labelled claim the extractor never found
LABELS = [str(label) for label in Label]
TOP_K = 8
RATE_DIGITS = 4

Status = Literal["scored", "verdict_unavailable", "not_run"]
ExplanationState = Literal["passed", "rejected", "not_asked"]


class Rate(BaseModel):
    """`hits` of `total`; `rate` is None when there was nothing to measure."""

    hits: int
    total: int
    rate: float | None


def rate_of(hits: int, total: int) -> Rate:
    return Rate(hits=hits, total=total, rate=round(hits / total, RATE_DIGITS) if total else None)


class ClaimOutcome(BaseModel):
    """One labelled claim: what the pipeline did with it, step by step."""

    text_id: str
    index: int  # the claim's position among its text's labelled claims
    quote: str
    expected: Label
    expected_indicator: str | None
    status: Status = "scored"
    note: str = ""  # why a claim is not `scored`
    found: bool = False
    geo_ok: bool | None = None
    start_ok: bool | None = None
    end_ok: bool | None = None
    indicator: str | None = None  # the statistic the pipeline matched
    match_ok: bool | None = None
    in_top8: bool | None = None  # retrieval alone: the labelled statistic among the top 8
    verdict: str | None = None  # a label, or MISSED
    verdict_ok: bool | None = None
    reason: str = ""  # the verdict's reason, as the pipeline wrote it
    stopped_at: str | None = None
    explanation: ExplanationState | None = None
    failed_step: str | None = None  # for a wrong verdict: the first step that went wrong


class TextOutcome(BaseModel):
    id: str
    error: str | None = None  # the router could not serve this text
    labelled: int
    extracted: int = 0
    linked: int = 0  # extracted claims paired with a labelled one
    seconds: float = 0.0
    model_calls: int = 0
    outcomes: list[ClaimOutcome]


def not_run(item: BenchmarkText, reason: str, seconds: float, model_calls: int) -> TextOutcome:
    """A text no step could run for (the router had no provider)."""
    return TextOutcome(
        id=item.id,
        error=reason,
        labelled=len(item.claims),
        seconds=seconds,
        model_calls=model_calls,
        outcomes=[
            ClaimOutcome(
                text_id=item.id,
                index=i,
                quote=c.quote,
                expected=c.expected,
                expected_indicator=c.indicator,
                status="not_run",
                note=reason,
            )
            for i, c in enumerate(item.claims)
        ],
    )


def explanation_state(result: ClaimResult) -> ExplanationState:
    """Whether a model explained the verdict, and whether code let its numbers through."""
    if not any(m.step is Step.EXPLAIN for m in result.models):
        return "not_asked"
    return "passed" if result.explanation_source == "model" else "rejected"


def failed_step(label: LabelledClaim, result: ClaimResult, *, fields_ok: bool) -> str:
    """The first step that went wrong for a claim whose verdict is wrong."""
    got = result.indicator.id if result.indicator else None
    if not fields_ok:
        return str(Step.EXTRACT)
    if got != label.indicator:
        return str(Step.MATCH)
    if result.stopped_at is not None:
        return str(result.stopped_at)
    return str(Step.VERDICT)


def score_text(
    item: BenchmarkText,
    output: PipelineOutput,
    retrieval: Mapping[int, Sequence[str]],
    *,
    seconds: float,
    model_calls: int,
) -> TextOutcome:
    """`retrieval` maps an extracted claim's index to the ids the catalog search returned
    for its statistic's phrase (top 8)."""
    links = {link.label: link for link in align(item.claims, [c.claim for c in output.claims])}
    outcomes = []
    for i, label in enumerate(item.claims):
        link = links.get(i)
        if link is None:
            outcomes.append(_missed(item, i, label))
        else:
            result = output.claims[link.extracted]
            outcomes.append(_scored(item, i, label, result, retrieval.get(result.index)))
    return TextOutcome(
        id=item.id,
        labelled=len(item.claims),
        extracted=len(output.claims),
        linked=len(links),
        seconds=seconds,
        model_calls=model_calls,
        outcomes=outcomes,
    )


def _missed(item: BenchmarkText, i: int, label: LabelledClaim) -> ClaimOutcome:
    return ClaimOutcome(
        text_id=item.id,
        index=i,
        quote=label.quote,
        expected=label.expected,
        expected_indicator=label.indicator,
        verdict=MISSED,
        verdict_ok=False,
        failed_step=str(Step.EXTRACT),
    )


def _scored(
    item: BenchmarkText,
    i: int,
    label: LabelledClaim,
    result: ClaimResult,
    top8: Sequence[str] | None,
) -> ClaimOutcome:
    claim = result.claim
    geo, start, end = geo_ok(label, claim), start_ok(label, claim), end_ok(label, claim)
    got = result.indicator.id if result.indicator else None
    out = ClaimOutcome(
        text_id=item.id,
        index=i,
        quote=label.quote,
        expected=label.expected,
        expected_indicator=label.indicator,
        found=True,
        geo_ok=geo,
        start_ok=start,
        end_ok=end,
        indicator=got,
        match_ok=got == label.indicator,
        in_top8=None if label.indicator is None or top8 is None else label.indicator in top8,
        stopped_at=None if result.stopped_at is None else str(result.stopped_at),
        explanation=explanation_state(result),
    )
    if result.retryable:
        out.status, out.note = "verdict_unavailable", result.verdict.reason
        return out
    out.verdict = str(result.verdict.label)
    out.reason = result.verdict.reason
    out.verdict_ok = result.verdict.label is label.expected
    if not out.verdict_ok:
        out.failed_step = failed_step(label, result, fields_ok=geo and start and end)
    return out


# --- totals ----------------------------------------------------------------------------------


class ExtractionMetrics(BaseModel):
    precision: Rate  # extracted claims that are a labelled claim
    recall: Rate  # labelled claims that were extracted
    geo: Rate  # of the claims found: right place ...
    start: Rate  # ... right start ...
    end: Rate  # ... right end
    window: Rate  # ... start and end both right


class MatchingMetrics(BaseModel):
    top1: Rate  # the statistic picked is the labelled one (or none, when none is labelled)
    recall_at_8: Rate  # the labelled statistic is in the search's top 8


class VerdictMetrics(BaseModel):
    accuracy: Rate  # every labelled claim; one the extractor missed is wrong
    accuracy_given_found: Rate  # only claims the extractor found
    labels: list[str]
    # confusion[expected][got]; `got` is a label or "missed".
    confusion: dict[str, dict[str, int]]
    per_label: dict[str, Rate]  # of each expected label, the share answered correctly


class ExplanationMetrics(BaseModel):
    pass_rate: Rate  # explanations whose numbers were all in the computed results


class CallStats(BaseModel):
    step: str
    provider: str
    model: str
    calls: int
    failed: int
    tokens: int
    mean_latency_ms: float


class CostMetrics(BaseModel):
    model_calls: int
    failed_calls: int
    calls_per_claim: float | None
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    seconds_per_claim: float | None
    seconds_p50_per_text: float | None
    seconds_p95_per_text: float | None
    series_requests: int
    series_cache_hits: int
    series_cache_hit_rate: float | None
    by_step_provider: list[CallStats]
    # Providers that said their quota for the day was spent: the router moved on to the next
    # choice for the rest of the run. Reports from before this field read as none.
    daily_limited: list[str] = Field(default_factory=list)


class Excluded(BaseModel):
    texts_not_run: int
    claims_not_run: int
    claims_verdict_unavailable: int
    share: float | None  # of all labelled claims


class Metrics(BaseModel):
    texts: int
    labelled_claims: int
    extracted_claims: int
    excluded: Excluded
    extraction: ExtractionMetrics
    matching: MatchingMetrics
    verdict: VerdictMetrics
    explanation: ExplanationMetrics
    cost: CostMetrics
    # For each wrong verdict, the step that broke first (the error analysis, P4.6).
    failures: dict[str, int] = Field(default_factory=dict)


def _percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank percentile; None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def _count(flags: Sequence[bool | None]) -> Rate:
    known = [f for f in flags if f is not None]
    return rate_of(sum(known), len(known))


def summarize(
    texts: Sequence[TextOutcome],
    calls: Sequence[Call],
    *,
    series_requests: int = 0,
    series_fetches: int = 0,
) -> Metrics:
    claims = [o for t in texts for o in t.outcomes]
    ran = [t for t in texts if t.error is None]
    found = [o for o in claims if o.found]
    judged = [o for o in claims if o.status == "scored"]
    excluded = Excluded(
        texts_not_run=sum(t.error is not None for t in texts),
        claims_not_run=sum(o.status == "not_run" for o in claims),
        claims_verdict_unavailable=sum(o.status == "verdict_unavailable" for o in claims),
        share=None,
    )
    if claims:
        excluded.share = round(
            (excluded.claims_not_run + excluded.claims_verdict_unavailable) / len(claims),
            RATE_DIGITS,
        )
    extracted = sum(t.extracted for t in ran)
    labelled_ran = sum(t.labelled for t in ran)
    return Metrics(
        texts=len(texts),
        labelled_claims=len(claims),
        extracted_claims=sum(t.extracted for t in texts),
        excluded=excluded,
        extraction=ExtractionMetrics(
            precision=rate_of(sum(t.linked for t in ran), extracted),
            recall=rate_of(len(found), labelled_ran),
            geo=_count([o.geo_ok for o in found]),
            start=_count([o.start_ok for o in found]),
            end=_count([o.end_ok for o in found]),
            window=_count([bool(o.start_ok and o.end_ok) for o in found]),
        ),
        matching=MatchingMetrics(
            top1=_count([o.match_ok for o in found]),
            recall_at_8=_count([o.in_top8 for o in found]),
        ),
        verdict=_verdicts(judged),
        explanation=ExplanationMetrics(
            pass_rate=_count([_passed(o) for o in found if o.explanation != "not_asked"])
        ),
        cost=_cost(texts, calls, len(claims), series_requests, series_fetches),
        failures=dict(Counter(o.failed_step for o in judged if o.failed_step is not None)),
    )


def _passed(outcome: ClaimOutcome) -> bool | None:
    return None if outcome.explanation is None else outcome.explanation == "passed"


def _verdicts(judged: Sequence[ClaimOutcome]) -> VerdictMetrics:
    confusion: dict[str, dict[str, int]] = {
        expected: {got: 0 for got in [*LABELS, MISSED]} for expected in LABELS
    }
    for o in judged:
        confusion[str(o.expected)][o.verdict or MISSED] += 1
    per_label = {label: rate_of(row[label], sum(row.values())) for label, row in confusion.items()}
    return VerdictMetrics(
        accuracy=_count([o.verdict_ok for o in judged]),
        accuracy_given_found=_count([o.verdict_ok for o in judged if o.found]),
        labels=[*LABELS, MISSED],
        confusion=confusion,
        per_label=per_label,
    )


def _cost(
    texts: Sequence[TextOutcome],
    calls: Sequence[Call],
    claims: int,
    series_requests: int,
    series_fetches: int,
) -> CostMetrics:
    seconds = [t.seconds for t in texts]
    hits = max(0, series_requests - series_fetches)
    grouped: dict[tuple[str, str, str], list[Call]] = defaultdict(list)
    for call in calls:
        grouped[call.step, call.provider, call.model].append(call)
    return CostMetrics(
        model_calls=len(calls),
        failed_calls=sum(not c.ok for c in calls),
        calls_per_claim=round(len(calls) / claims, 2) if claims else None,
        prompt_tokens=sum(c.prompt_tokens for c in calls),
        completion_tokens=sum(c.completion_tokens for c in calls),
        seconds=round(sum(seconds), 1),
        seconds_per_claim=round(sum(seconds) / claims, 2) if claims else None,
        seconds_p50_per_text=_rounded(_percentile(seconds, 0.5)),
        seconds_p95_per_text=_rounded(_percentile(seconds, 0.95)),
        series_requests=series_requests,
        series_cache_hits=hits,
        series_cache_hit_rate=round(hits / series_requests, RATE_DIGITS)
        if series_requests
        else None,
        by_step_provider=[
            CallStats(
                step=step,
                provider=provider,
                model=model,
                calls=len(group),
                failed=sum(not c.ok for c in group),
                tokens=sum(c.prompt_tokens + c.completion_tokens for c in group),
                mean_latency_ms=round(sum(c.latency_ms for c in group) / len(group), 1),
            )
            for (step, provider, model), group in sorted(grouped.items())
        ],
        daily_limited=sorted({c.provider for c in calls if c.daily_limit}),
    )


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 2)
