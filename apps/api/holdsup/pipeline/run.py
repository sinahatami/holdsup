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

Each step is one method that starts its trace line, does its work, fills in the claim's
result and ends the line, or raises `_CantCheck` to stop that claim.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from holdsup.adapters.base import (
    AdapterError,
    FetchedSeries,
    Filters,
    Observation,
    SourceUnavailable,
)
from holdsup.catalog.schema import Catalog, IndicatorSpec
from holdsup.catalog.search import CatalogSearch
from holdsup.geo import UnknownPlace, geo_filter, to_claim_codes
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.explain import explain, template_explanation
from holdsup.pipeline.extract import extract_claims, parse_said_on
from holdsup.pipeline.match import Matcher
from holdsup.pipeline.plan import (
    Execution,
    PlanContext,
    SeriesInfo,
    ValidPlan,
    execute_plan,
    plan_analysis,
)
from holdsup.pipeline.result import (
    ClaimResult,
    DataRef,
    IndicatorRef,
    PipelineOutput,
    Versions,
    app_version,
)
from holdsup.pipeline.terms import OfficeTerms
from holdsup.pipeline.trace import Emit, ModelUse, Step, StepStatus, Trace
from holdsup.router import Router, RouterError, Use
from holdsup.verdict import Label, Tolerances, cant_check, decide


class Fetcher(Protocol):
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries: ...


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
class _ClaimRun:
    """One claim on its way through the steps: its trace lines and the result it fills in."""

    trace: Trace
    index: int
    claim: ClaimSpec
    out: ClaimResult

    async def start(self, step: Step) -> None:
        await self.trace.start(step, self.index)

    async def done(
        self,
        step: Step,
        summary: str,
        *,
        status: StepStatus = "ok",
        models: Sequence[ModelUse] = (),
    ) -> None:
        await self.trace.done(step, self.index, summary, status=status, models=models)


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
        trace = Trace(emit)
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

    async def _claim(self, trace: Trace, i: int, claim: ClaimSpec) -> ClaimResult:
        out = ClaimResult(index=i, claim=claim, verdict=cant_check(""), explanation="")
        c = _ClaimRun(trace, i, claim, out)
        try:
            spec = await self._match(c)
            observations, info = await self._fetch(c, spec)
            ctx = PlanContext(claim=claim, main=info, as_of=self._as_of(claim))
            plan = await self._plan(c, ctx)
            execution = await self._execute(c, plan, ctx, {spec.id: observations})
            await self._verdict(c, plan, execution)
            await self._explain(c, spec, execution)
        except _CantCheck as stop:
            await c.done(stop.step, stop.reason, status="cant_check", models=stop.models)
            out.verdict, out.retryable = cant_check(stop.reason), stop.retryable
            out.explanation = template_explanation(out.verdict, _name(out))
        return out

    # --- the steps, in order ----------------------------------------------------------------

    async def _match(self, c: _ClaimRun) -> IndicatorSpec:
        await c.start(Step.MATCH)
        matcher = Matcher(self.router, self.catalog, self.search, self.use)
        match = await matcher.match(c.claim)
        models = self._uses(Step.MATCH, match.providers)
        c.out.models += models
        c.out.match_reason, c.out.alternatives = match.reason, match.alternatives
        c.out.notes += match.notes
        if match.status == "cant_check" or match.indicator_id is None:
            reason = match.reason or "No catalog indicator fits the claim."
            raise _CantCheck(Step.MATCH, reason, models=models)
        spec = self.catalog.get(match.indicator_id)
        c.out.indicator = IndicatorRef.of(spec)
        await c.done(
            Step.MATCH, f"Matched {spec.name} ({spec.source} {spec.source_code}).", models=models
        )
        return spec

    async def _fetch(
        self, c: _ClaimRun, spec: IndicatorSpec
    ) -> tuple[list[Observation], SeriesInfo]:
        await c.start(Step.FETCH)
        observations = await self._observations(c, spec)
        info = SeriesInfo.from_data(spec, observations)
        if c.claim.geo not in info.geos:
            raise _CantCheck(Step.FETCH, f"The source has no {spec.name} data for {c.claim.geo}.")
        await c.done(Step.FETCH, f"Fetched {len(observations)} rows, {info.first} to {info.last}.")
        return observations, info

    async def _observations(self, c: _ClaimRun, spec: IndicatorSpec) -> list[Observation]:
        """The indicator's series for the claim's place and its peers, in claim codes."""
        claim = c.claim
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
        c.out.data = DataRef.of(series, observations)
        return observations

    async def _plan(self, c: _ClaimRun, ctx: PlanContext) -> ValidPlan:
        await c.start(Step.PLAN)
        planned = await plan_analysis(self.router, ctx, use=self.use)
        models = self._uses(Step.PLAN, planned.providers)
        c.out.models += models
        if planned.status == "cant_check" or planned.plan is None:
            c.out.notes += [f"Plan rejected: {e}" for e in planned.errors]
            # A plan the model got wrong may come out right next time; an unsupported claim
            # type (no model call) will not.
            raise _CantCheck(
                Step.PLAN, planned.reason, retryable=planned.attempts > 0, models=models
            )
        plan = planned.plan
        c.out.notes += plan.notes
        c.out.plan_reason, c.out.answer = plan.reason, plan.answer
        ops = ", ".join(call.op for call in plan.calls)
        await c.done(Step.PLAN, f"Planned {ops}.", models=models)
        return plan

    async def _execute(
        self,
        c: _ClaimRun,
        plan: ValidPlan,
        ctx: PlanContext,
        data: dict[str, list[Observation]],
    ) -> Execution:
        await c.start(Step.EXECUTE)
        execution = execute_plan(plan, ctx, data, self.tolerances)
        c.out.operations = execution.records
        if execution.error is not None:
            raise _CantCheck(Step.EXECUTE, execution.error)
        n = len(execution.records)
        await c.done(Step.EXECUTE, f"Ran {n} operation{'s' if n != 1 else ''}.")
        return execution

    async def _verdict(self, c: _ClaimRun, plan: ValidPlan, execution: Execution) -> None:
        await c.start(Step.VERDICT)
        verdict = decide(
            c.claim, execution.records, plan.answer, unit=execution.unit, tolerances=self.tolerances
        )
        c.out.verdict = verdict
        status: StepStatus = "cant_check" if verdict.label is Label.CANT_CHECK else "ok"
        await c.done(Step.VERDICT, f"{verdict.label}: {verdict.reason}", status=status)

    async def _explain(self, c: _ClaimRun, spec: IndicatorSpec, execution: Execution) -> None:
        await c.start(Step.EXPLAIN)
        out = c.out
        if out.verdict.label is Label.CANT_CHECK:
            out.explanation = template_explanation(out.verdict, spec.name)
            await c.done(Step.EXPLAIN, "Explained by code (nothing to check).")
            return
        try:
            explained = await explain(
                self.router, c.claim, out.verdict, execution.records,
                indicator=spec.name, unit=execution.unit, use=self.use,
            )  # fmt: skip
        except RouterError:
            out.explanation = template_explanation(out.verdict, spec.name)
            await c.done(Step.EXPLAIN, "No model available; explained by code.")
            return
        models = self._uses(Step.EXPLAIN, explained.providers)
        out.models += models
        out.explanation, out.explanation_source = explained.text, explained.source
        summary = (
            "Explained." if explained.source == "model"
            else "The model's explanation used numbers not in the results; explained by code."
        )  # fmt: skip
        await c.done(Step.EXPLAIN, summary, models=models)


def _name(out: ClaimResult) -> str:
    return out.indicator.name if out.indicator else "matched"
