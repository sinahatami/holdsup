"""One whole check: extract → per claim match, fetch, plan, execute, verdict, explain.

Every step announces itself (`step_started`, then `step_done` with a one-line summary and
the model behind it) so the result page can show the live trace. The ledger lookup happens
before this, in the service, because a hit must not reach any model.

Failures:
- the router out of providers in extract, match or plan → `RouterError` propagates (the
  check fails with "at capacity"); in explain → the code-written template is used;
- no match, no place, no data, an invalid plan, an op error → that claim is `cant_check`;
- the source down, or a plan the model got wrong twice → `cant_check` marked `retryable`,
  so the result is not cached (another try may well work).
"""

import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from importlib.metadata import version
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from holdsup.adapters.base import (
    AdapterError,
    FetchedSeries,
    Filters,
    Observation,
    SourceUnavailable,
)
from holdsup.catalog.schema import Catalog, IndicatorSpec
from holdsup.geo import UnknownPlace, geo_filter, to_claim_codes
from holdsup.ops import OpRecord
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.explain import explain, template_explanation
from holdsup.pipeline.extract import extract_claims, parse_said_on
from holdsup.pipeline.match import CatalogSearch, Matcher
from holdsup.pipeline.plan import PlanContext, SeriesInfo, execute_plan, plan_analysis
from holdsup.pipeline.terms import OfficeTerms
from holdsup.router import Router, RouterError, Use
from holdsup.verdict import Label, Tolerances, Verdict, cant_check, decide


class Step(StrEnum):
    LEDGER = "ledger"
    EXTRACT = "extract"
    MATCH = "match"
    FETCH = "fetch"
    PLAN = "plan"
    EXECUTE = "execute"
    VERDICT = "verdict"
    EXPLAIN = "explain"


StepStatus = Literal["ok", "cant_check"]


class StepEvent(BaseModel):
    """One line of the live trace."""

    event: Literal["step_started", "step_done"]
    step: Step
    claim: int | None = None  # which extracted claim; None for check-wide steps
    status: StepStatus | None = None  # step_done only
    summary: str = ""
    models: list[str] = Field(default_factory=list)  # "provider/model" per model call
    ms: float | None = None  # step_done only


Emit = Callable[[StepEvent], Awaitable[None]]


class Fetcher(Protocol):
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries: ...


# --- the result ------------------------------------------------------------------------------


class IndicatorRef(BaseModel):
    id: str
    name: str
    source: str
    source_code: str
    unit: str
    frequency: str
    definition: str

    @classmethod
    def of(cls, spec: IndicatorSpec) -> "IndicatorRef":
        return cls(
            id=spec.id,
            name=spec.name,
            source=str(spec.source),
            source_code=spec.source_code,
            unit=spec.unit,
            frequency=str(spec.frequency),
            definition=spec.definition,
        )


class DataRef(BaseModel):
    """Where the numbers came from: enough to cite and re-fetch them."""

    source: str
    dataset: str
    url: str
    retrieved_at: datetime
    raw_sha256: str
    label: str = ""
    updated: str | None = None
    citation: str | None = None
    places: list[str]  # claim codes with at least one value
    rows: int  # observations with a value

    @classmethod
    def of(cls, series: FetchedSeries, observations: Sequence[Observation]) -> "DataRef":
        present = [o for o in observations if o.value is not None]
        return cls(
            source=series.source,
            dataset=series.dataset,
            url=series.url,
            retrieved_at=series.retrieved_at,
            raw_sha256=series.raw_sha256,
            label=series.label,
            updated=series.updated,
            citation=series.citation,
            places=sorted({o.geo for o in present}),
            rows=len(present),
        )


class ModelUse(BaseModel):
    step: Step
    provider: str
    model: str


class ClaimResult(BaseModel):
    index: int
    claim: ClaimSpec
    indicator: IndicatorRef | None = None
    alternatives: list[str] = Field(default_factory=list)
    match_reason: str = ""
    data: DataRef | None = None
    plan_reason: str | None = None
    operations: list[OpRecord] = Field(default_factory=list)
    answer: list[int] = Field(default_factory=list)  # which operations decide the claim
    verdict: Verdict
    explanation: str
    explanation_source: Literal["model", "template"] = "template"
    models: list[ModelUse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # what code dropped, fixed or rejected
    # cant_check because something was briefly unavailable: worth checking again later.
    retryable: bool = False


class Versions(BaseModel):
    app: str
    catalog: str
    tolerances: int


class PipelineOutput(BaseModel):
    claims: list[ClaimResult]
    versions: Versions
    models: list[ModelUse]  # check-wide model calls (extraction)
    notes: list[str] = Field(default_factory=list)

    @property
    def retryable(self) -> bool:
        return any(c.retryable for c in self.claims)


def app_version() -> str:
    return version("holdsup")


# --- the run ---------------------------------------------------------------------------------


@dataclass
class _Trace:
    emit: Emit
    started: dict[tuple[Step, int | None], float] = field(default_factory=dict)

    async def start(self, step: Step, claim: int | None = None) -> None:
        self.started[step, claim] = time.monotonic()
        await self.emit(StepEvent(event="step_started", step=step, claim=claim))

    async def done(
        self,
        step: Step,
        claim: int | None,
        summary: str,
        *,
        status: StepStatus = "ok",
        models: Sequence[ModelUse] = (),
    ) -> None:
        began = self.started.pop((step, claim), time.monotonic())
        await self.emit(
            StepEvent(
                event="step_done",
                step=step,
                claim=claim,
                status=status,
                summary=summary,
                models=[f"{m.provider}/{m.model}" for m in models],
                ms=round((time.monotonic() - began) * 1000, 1),
            )
        )


class _CantCheck(Exception):
    def __init__(
        self,
        step: Step,
        reason: str,
        *,
        retryable: bool = False,
        models: Sequence[ModelUse] = (),
    ) -> None:
        super().__init__(reason)
        self.step = step
        self.reason = reason
        self.retryable = retryable
        self.models = models


@dataclass
class Pipeline:
    router: Router
    catalog: Catalog
    search: CatalogSearch
    fetcher: Fetcher
    tolerances: Tolerances
    use: Use = Use.LIVE
    terms: OfficeTerms | None = None
    today: Callable[[], date] | None = None

    def _as_of(self, claim: ClaimSpec) -> date | None:
        """The day a dated claim is checked as of: the last day it can have been said."""
        if claim.said_on is None:
            return None
        today = self.today() if self.today else datetime.now(UTC).date()
        return parse_said_on(claim.said_on, today).by

    def versions(self) -> dict[str, object]:
        """What a stored result must match to be reused (the ledger): the catalog and the
        tolerances its verdicts came from."""
        return {"catalog": self.catalog.version, "tolerances": self.tolerances.version}

    def _uses(self, step: Step, providers: Sequence[str]) -> list[ModelUse]:
        models = {p.name: p.model for p in self.router.config.providers}
        return [ModelUse(step=step, provider=p, model=models.get(p, "?")) for p in providers]

    async def run(self, text: str, emit: Emit) -> PipelineOutput:
        """Check every claim in `text`. RouterError propagates (see the module docstring)."""
        trace = _Trace(emit)
        await trace.start(Step.EXTRACT)
        extracted = await extract_claims(
            self.router,
            text,
            use=self.use,
            terms=self.terms,
            today=self.today() if self.today else None,
        )
        extract_models = self._uses(Step.EXTRACT, [extracted.provider])
        n = len(extracted.claims)
        await trace.done(
            Step.EXTRACT,
            None,
            f"Found {n} claim{'s' if n != 1 else ''}." if n else "Found no numeric claim.",
            status="ok" if n else "cant_check",
            models=extract_models,
        )
        claims = [await self._claim(trace, i, c) for i, c in enumerate(extracted.claims)]
        return PipelineOutput(
            claims=claims,
            versions=Versions(
                app=app_version(),
                catalog=self.catalog.version,
                tolerances=self.tolerances.version,
            ),
            models=extract_models,
            notes=[] if n else ["No numeric claim was found in the text."],
        )

    async def _claim(self, trace: _Trace, i: int, claim: ClaimSpec) -> ClaimResult:
        out = ClaimResult(index=i, claim=claim, verdict=cant_check(""), explanation="")
        try:
            await self._check(trace, i, claim, out)
        except _CantCheck as stop:
            await trace.done(stop.step, i, stop.reason, status="cant_check", models=stop.models)
            out.verdict, out.retryable = cant_check(stop.reason), stop.retryable
            out.explanation = template_explanation(out.verdict, _name(out))
        return out

    async def _check(self, trace: _Trace, i: int, claim: ClaimSpec, out: ClaimResult) -> None:
        # Match.
        await trace.start(Step.MATCH, i)
        matcher = Matcher(self.router, self.catalog, self.search, self.use)
        match = await matcher.match(claim)
        match_models = self._uses(Step.MATCH, match.providers)
        out.models += match_models
        out.match_reason, out.alternatives = match.reason, match.alternatives
        out.notes += match.notes
        if match.status == "cant_check" or match.indicator_id is None:
            reason = match.reason or "No catalog indicator fits the claim."
            raise _CantCheck(Step.MATCH, reason, models=match_models)
        spec = self.catalog.get(match.indicator_id)
        out.indicator = IndicatorRef.of(spec)
        await trace.done(
            Step.MATCH, i, f"Matched {spec.name} ({spec.source} {spec.source_code}).",
            models=match_models,
        )  # fmt: skip

        # Fetch.
        await trace.start(Step.FETCH, i)
        observations = await self._fetch(claim, spec, out)
        info = SeriesInfo.from_data(spec, observations)
        if claim.geo not in info.geos:
            raise _CantCheck(Step.FETCH, f"The source has no {spec.name} data for {claim.geo}.")
        await trace.done(
            Step.FETCH, i, f"Fetched {len(observations)} rows, {info.first} to {info.last}."
        )

        # Plan.
        await trace.start(Step.PLAN, i)
        ctx = PlanContext(claim=claim, main=info, as_of=self._as_of(claim))
        planned = await plan_analysis(self.router, ctx, use=self.use)
        plan_models = self._uses(Step.PLAN, planned.providers)
        out.models += plan_models
        if planned.status == "cant_check" or planned.plan is None:
            out.notes += [f"Plan rejected: {e}" for e in planned.errors]
            # A plan the model got wrong may come out right next time; an unsupported claim
            # type (no model call) will not.
            raise _CantCheck(
                Step.PLAN, planned.reason, retryable=planned.attempts > 0, models=plan_models
            )
        plan = planned.plan
        out.notes += plan.notes
        out.plan_reason, out.answer = plan.reason, plan.answer
        ops = ", ".join(c.op for c in plan.calls)
        await trace.done(Step.PLAN, i, f"Planned {ops}.", models=plan_models)

        # Execute.
        await trace.start(Step.EXECUTE, i)
        execution = execute_plan(plan, ctx, {spec.id: observations}, self.tolerances)
        out.operations = execution.records
        if execution.error is not None:
            raise _CantCheck(Step.EXECUTE, execution.error)
        n = len(execution.records)
        await trace.done(Step.EXECUTE, i, f"Ran {n} operation{'s' if n != 1 else ''}.")

        # Verdict.
        await trace.start(Step.VERDICT, i)
        out.verdict = decide(
            claim, execution.records, plan.answer, unit=execution.unit, tolerances=self.tolerances
        )
        status: StepStatus = "cant_check" if out.verdict.label is Label.CANT_CHECK else "ok"
        await trace.done(
            Step.VERDICT, i, f"{out.verdict.label}: {out.verdict.reason}", status=status
        )

        # Explain.
        await trace.start(Step.EXPLAIN, i)
        if out.verdict.label is Label.CANT_CHECK:
            out.explanation = template_explanation(out.verdict, spec.name)
            await trace.done(Step.EXPLAIN, i, "Explained by code (nothing to check).")
            return
        try:
            explained = await explain(
                self.router, claim, out.verdict, execution.records,
                indicator=spec.name, unit=execution.unit, use=self.use,
            )  # fmt: skip
        except RouterError:
            out.explanation = template_explanation(out.verdict, spec.name)
            await trace.done(Step.EXPLAIN, i, "No model available; explained by code.")
            return
        explain_models = self._uses(Step.EXPLAIN, explained.providers)
        out.models += explain_models
        out.explanation, out.explanation_source = explained.text, explained.source
        summary = (
            "Explained." if explained.source == "model"
            else "The model's explanation used numbers not in the results; explained by code."
        )  # fmt: skip
        await trace.done(Step.EXPLAIN, i, summary, models=explain_models)

    async def _fetch(
        self, claim: ClaimSpec, spec: IndicatorSpec, out: ClaimResult
    ) -> list[Observation]:
        if claim.geo is None:
            raise _CantCheck(Step.FETCH, "The claim names no place.")
        try:
            filters = {**spec.filters, **geo_filter(spec.source, [claim.geo, *claim.peers])}
            series = await self.fetcher.fetch_series(str(spec.source), spec.source_code, filters)
        except UnknownPlace as exc:
            raise _CantCheck(Step.FETCH, f"{exc}.") from exc
        except SourceUnavailable as exc:
            raise _CantCheck(
                Step.FETCH, f"{spec.source} did not answer; try again later.", retryable=True
            ) from exc
        except AdapterError as exc:
            raise _CantCheck(Step.FETCH, f"{spec.source} could not provide the data.") from exc
        observations = to_claim_codes(spec.source, series.observations)
        out.data = DataRef.of(series, observations)
        return observations


def _name(out: ClaimResult) -> str:
    return out.indicator.name if out.indicator else "matched"
