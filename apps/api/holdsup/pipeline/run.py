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

The steps code does alone (fetch, execute, the checks, the verdict) live in `steps.CodeSteps`;
this module adds the model's: extract, match, plan, explain. Each claim stores its plan, so
`CodeSteps.replay` can compute it again later with no model (S1, the claim watch).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from holdsup.catalog.schema import IndicatorSpec
from holdsup.catalog.search import CatalogSearch
from holdsup.checks import DistortionCheck
from holdsup.ml import reranker as reranker_model
from holdsup.ml.confidence import Confidence, Signals, rerank_signals
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.explain import explain, template_explanation
from holdsup.pipeline.extract import extract_claims
from holdsup.pipeline.match import SKIP_MARGIN, Matcher, Reranker
from holdsup.pipeline.match.model import MatchResult
from holdsup.pipeline.plan import Execution, PlanContext, ValidPlan, plan_analysis
from holdsup.pipeline.result import (
    ClaimResult,
    IndicatorRef,
    PipelineOutput,
    StoredPlan,
    Suggestion,
    Versions,
    app_version,
)
from holdsup.pipeline.steps import (
    NO_PLACE,
    ClaimRun,
    ClaimStopped,
    CodeSteps,
    Fetcher,
    ReplayError,
    read_extents,
)
from holdsup.pipeline.terms import OfficeTerms
from holdsup.pipeline.trace import Emit, ModelUse, Step, StepEvent, Trace
from holdsup.router import Router, RouterError, Use
from holdsup.verdict import Label, cant_check

__all__ = ["CHOSEN", "GONE", "NO_CLAIM", "NO_MATCH", "NO_PLACE", "REUSED", "Choice", "Fetcher",
           "Pipeline"]  # fmt: skip

NO_CLAIM = (
    "HoldsUp found no claim with a number in it. Try a sentence such as "
    "“Italy's unemployment rate fell to 7.7% in 2023.”"
)
NO_MATCH = "HoldsUp doesn't have a statistic that matches this claim yet."
MAX_SUGGESTIONS = 3


@dataclass(frozen=True)
class Choice:
    """A reader's pick for a re-check: the statistic to use, and the others offered (the first
    check's own statistic among them), which the new result offers in turn."""

    indicator_id: str
    others: tuple[str, ...] = ()


REUSED = "Using the claim as the earlier check read it."
CHOSEN = "Chosen by the reader instead of the statistic the first check matched."
GONE = "That statistic is no longer in the catalog."


@dataclass(kw_only=True)
class Pipeline(CodeSteps):
    router: Router
    search: CatalogSearch
    use: Use = Use.LIVE
    terms: OfficeTerms | None = None
    reranker: Reranker | None = None  # None: the match model always picks
    skip_margin: float = SKIP_MARGIN

    def _uses(self, step: Step, providers: Sequence[str]) -> list[ModelUse]:
        known = {p.name: p for p in self.router.config.providers}
        return [
            ModelUse(
                step=step,
                provider=p,
                model=known[p].model if p in known else "?",
                label=(known[p].label or known[p].model) if p in known else "?",
            )
            for p in providers
        ]

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
            f"Found {n} claim{'s' if n != 1 else ''}."
            if n
            else "Found no claim with a number in it.",
            status="ok" if n else "cant_check",
            models=extract_models,
        )
        claims = [
            await self._claim(trace, i, c, check_models=extract_models)
            for i, c in enumerate(extracted.claims)
        ]
        return PipelineOutput(
            claims=claims,
            versions=Versions(
                app=app_version(),
                catalog=self.catalog.version,
                tolerances=self.tolerances.version,
            ),
            models=extract_models,
            notes=[] if n else [NO_CLAIM],
        )

    async def recheck(self, claim: ClaimSpec, choice: Choice, emit: Emit) -> PipelineOutput:
        """Check one claim again, as an earlier check read it, with the statistic a reader
        chose instead of the one matched: no extract or match model call."""
        trace = Trace(emit)
        await trace.start(Step.EXTRACT)
        await trace.done(Step.EXTRACT, None, REUSED)
        out = await self._claim(trace, 0, claim, choice)
        return PipelineOutput(
            claims=[out],
            versions=Versions(
                app=app_version(), catalog=self.catalog.version, tolerances=self.tolerances.version
            ),
            models=[],
        )

    async def _claim(
        self,
        trace: Trace,
        i: int,
        claim: ClaimSpec,
        choice: Choice | None = None,
        *,
        check_models: Sequence[ModelUse] = (),
    ) -> ClaimResult:
        out = ClaimResult(index=i, claim=claim, verdict=cant_check(""), explanation="")
        c = ClaimRun(trace, i, claim, out, self._today(), check_models=check_models)
        try:
            spec = await self._match(c) if choice is None else await self._chosen(c, choice)
            spec, data, ctx = await self._read(c, spec)
            plan = await self._plan(c, ctx)
            c.out.extra_sources = self._plan_sources(c, plan)
            execution = await self._execute(c, spec, plan, ctx, data)
            # What a later replay needs: the plan, and where each series ended (S1).
            out.plan = StoredPlan(calls=plan.calls, read_until=read_extents(data))
            await self._verdict(c, plan, execution)
            out.confidence = self._confidence(c)
            await self._explain(c, spec, execution)
        except ClaimStopped as stop:
            await c.done(stop.step, stop.reason, status="cant_check", models=stop.models)
            out.verdict, out.retryable = cant_check(stop.reason), stop.retryable
            out.stopped_at = stop.step
            out.explanation = template_explanation(out.verdict, _name(out))
        return out

    async def plan_again(self, old: ClaimResult, checked_on: date) -> ClaimResult:
        """A claim checked before plans were stored, planned again by the model (one call,
        through the router) and computed with that plan on today's data (`CodeSteps.adopt`).
        The claim watch's backfill keeps the plan only when the figures come out the same.
        Raises `ReplayError` when no plan is made; `RouterError` when no model is available."""
        if old.indicator is None:
            raise ReplayError("no statistic matched")
        try:
            spec = self.catalog.get(old.indicator.id)
        except KeyError:
            raise ReplayError(f"{old.indicator.id} is no longer in the catalog") from None
        scratch = old.model_copy(deep=True)
        c = ClaimRun(Trace(_quiet), old.index, old.claim, scratch, checked_on)
        try:
            _, _, ctx = await self._read(c, spec)
            plan = await self._plan(c, ctx)
        except ClaimStopped as stop:
            raise ReplayError(stop.reason) from None
        return await self.adopt(old, checked_on, plan)

    # --- the steps, in order ----------------------------------------------------------------

    async def _match(self, c: ClaimRun) -> IndicatorSpec:
        await c.start(Step.MATCH)
        matcher = Matcher(
            self.router, self.catalog, self.search, self.use, self.reranker, self.skip_margin
        )
        match = await matcher.match(c.claim)
        c.match = match
        models = self._reranker_use(match) + self._uses(Step.MATCH, match.providers)
        c.out.models += models
        c.out.match_reason, c.out.alternatives = match.reason, match.alternatives
        c.out.notes += match.notes
        if match.status == "cant_check" or match.indicator_id is None:
            # The model's own reason stays in match_reason (the receipt); the reader gets a
            # plain sentence, with the closest statistics as suggestions.
            reason = match.reason if not match.candidates else NO_MATCH
            c.out.suggestions = self._suggestions(match)
            raise ClaimStopped(Step.MATCH, reason, models=models)
        spec = self.catalog.get(match.indicator_id)
        c.out.indicator = IndicatorRef.of(spec)
        # What a reader can re-check the claim with: the other statistics the model named.
        c.out.suggestions = self._named([a for a in match.alternatives if a != spec.id])
        by = " The reranker was clear, so no model was asked." if match.skipped_model else ""
        await c.done(
            Step.MATCH,
            f"Matched {spec.name} ({spec.source} {spec.source_code}).{by}",
            models=models,
        )
        return spec

    @staticmethod
    def _reranker_use(match: MatchResult) -> list[ModelUse]:
        """The reranker, when it ordered the candidates: receipts name every model a step used."""
        if match.reranker is None:
            return []
        return [
            ModelUse(
                step=Step.MATCH,
                provider=reranker_model.PROVIDER,
                model=match.reranker,
                label=reranker_model.LABEL,
            )
        ]

    async def _chosen(self, c: ClaimRun, choice: Choice) -> IndicatorSpec:
        """The statistic a reader picked for a re-check: no model call."""
        await c.start(Step.MATCH)
        try:
            spec = self.catalog.get(choice.indicator_id)
        except KeyError:
            raise ClaimStopped(Step.MATCH, GONE) from None
        c.out.indicator = IndicatorRef.of(spec)
        c.out.match_reason = CHOSEN
        others = [i for i in choice.others if i != spec.id]
        c.out.alternatives = others
        c.out.suggestions = self._named(others)
        await c.done(
            Step.MATCH, f"Using {spec.name} ({spec.source} {spec.source_code}), as chosen."
        )
        return spec

    def _named(self, ids: Sequence[str]) -> list[Suggestion]:
        """Statistics by id, with their names; ids no longer in the catalog are left out."""
        known = {s.id: s for s in self.catalog.indicators}
        return [Suggestion(id=i, name=known[i].name) for i in dict.fromkeys(ids) if i in known]

    def _suggestions(self, match: MatchResult) -> list[Suggestion]:
        """The closest statistics when nothing matched: the ones the model named, then the best
        search hits, then the hits dropped because they do not cover the place."""
        ids = [*match.alternatives, *(h.id for h in match.candidates), *match.excluded_by_geo]
        return self._named(ids)[:MAX_SUGGESTIONS]

    async def _plan(self, c: ClaimRun, ctx: PlanContext) -> ValidPlan:
        await c.start(Step.PLAN)
        planned = await plan_analysis(self.router, ctx, use=self.use)
        models = self._uses(Step.PLAN, planned.providers)
        c.out.models += models
        if planned.status == "cant_check" or planned.plan is None:
            c.out.notes += [f"Plan rejected: {e}" for e in planned.errors]
            # A plan the model got wrong may come out right next time; an unsupported claim
            # type (no model call) will not.
            raise ClaimStopped(
                Step.PLAN, planned.reason, retryable=planned.attempts > 0, models=models
            )
        plan = planned.plan
        c.out.notes += plan.notes
        c.out.plan_reason, c.out.answer = plan.reason, plan.answer
        ops = ", ".join(call.op for call in plan.calls)
        await c.done(Step.PLAN, f"Planned {ops}.", models=models)
        return plan

    def _confidence(self, c: ClaimRun) -> Confidence | None:
        """How sure the check is of its verdict (P4.5): the reranker's and the router's
        signals, then what the data and the verdict show (`CodeSteps._scored`)."""
        probability, margin = (None, None)
        # The matched statistic, which the reranker scored, even when the same measure from
        # another source was read instead (`CodeSteps._same_measure`).
        if c.match is not None and c.match.indicator_id is not None:
            probability, margin = rerank_signals(
                [(h.id, h.rerank) for h in c.match.candidates], c.match.indicator_id
            )
        base = Signals(
            rerank_probability=probability,
            rerank_margin=margin,
            fallback_steps=self._fallback_steps([*c.check_models, *c.out.models]),
        )
        return self._scored(c, base)

    def _fallback_steps(self, models: Sequence[ModelUse]) -> int:
        """Of extraction, matching and planning, the steps a model other than the router's
        first choice served (the reranker is not a router model)."""
        config = self.router.config
        n = 0
        for step in (Step.EXTRACT, Step.MATCH, Step.PLAN):
            served = [
                p for p in config.steps.get(str(step), ()) if config.provider(p).serves(self.use)
            ]
            used = {
                m.provider
                for m in models
                if m.step is step and m.provider != reranker_model.PROVIDER
            }
            n += bool(used - set(served[:1]))
        return n

    async def _explain(self, c: ClaimRun, spec: IndicatorSpec, execution: Execution) -> None:
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
                checks=[_check_line(ch) for ch in out.distortion_checks],
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


def _check_line(check: DistortionCheck) -> str:
    """A distortion check as the explanation step reads it: "per_capita (flagged): ..."."""
    return f"{check.kind} ({'flagged' if check.flagged else 'passed'}): {check.text}"


async def _quiet(event: StepEvent) -> None:
    """A backfill's trace goes nowhere: no reader is watching it run."""
