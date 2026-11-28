"""The steps of a check that code does alone: fetch the series, run the plan, the framing
checks, the verdict. `Pipeline` (run.py) adds the model's steps: extract, match, plan, explain.

`CodeSteps.replay` computes a stored claim again from its plan with these steps only (S1, the
claim watch): no model call, so a watch needs no provider key and spends no quota.

Each step starts its trace line, does its work, fills in the claim's result and ends the line,
or raises `ClaimStopped` to stop that claim (cant_check).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Protocol

from holdsup.adapters.base import (
    AdapterError,
    FetchedSeries,
    Filters,
    Observation,
    SourceUnavailable,
)
from holdsup.catalog.coverage import covers
from holdsup.catalog.schema import Catalog, IndicatorSpec
from holdsup.checks import (
    ChangePoints,
    CheckInput,
    CheckKind,
    DistortionCheck,
    Related,
    Sweep,
    change_points,
    distortion_checks,
    points_reading,
    said_between,
    sweep,
    wants_real_terms,
)
from holdsup.geo import UnknownPlace, geo_filter, to_claim_codes
from holdsup.ml.confidence import (
    Confidence,
    ConfidenceModel,
    Signals,
    boundary_distance,
    data_age_years,
    unscored,
)
from holdsup.ops import OpError, Series, parse_period
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.explain import template_explanation
from holdsup.pipeline.extract import parse_said_on
from holdsup.pipeline.match.model import MatchResult
from holdsup.pipeline.plan import Execution, PlanContext, SeriesInfo, ValidPlan, execute_plan
from holdsup.pipeline.population import population_for, wants_population
from holdsup.pipeline.prices import real_terms_source
from holdsup.pipeline.result import (
    ChartSeries,
    ClaimResult,
    DataRef,
    ExtraSource,
    IndicatorRef,
    StoredPlan,
)
from holdsup.pipeline.same_measure import claim_years, missing_years, slack_years, swap_note
from holdsup.pipeline.trace import ModelUse, Step, StepEvent, StepStatus, Trace
from holdsup.places import place_name
from holdsup.verdict import Label, Tolerances, decide


class Fetcher(Protocol):
    async def fetch_series(self, source: str, dataset: str, filters: Filters) -> FetchedSeries: ...


NO_PLACE = "The claim doesn't say which country or place it is about."
# Each extent maps an indicator id to its places, and each place to the last period read.
Extents = Mapping[str, Mapping[str, str]]


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


class ClaimStopped(Exception):
    """A step cannot go on with this claim: it is cant_check, for `reason`."""

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


class ReplayError(Exception):
    """A stored claim could not be computed again: no stored plan, the statistic gone from
    the catalog, the source down, or the figures it read no longer there. The watch leaves the
    check as it is and tries again on a later run."""


@dataclass
class ClaimRun:
    """One claim on its way through the steps: its trace lines and the result it fills in."""

    trace: Trace
    index: int
    claim: ClaimSpec
    out: ClaimResult
    today: date  # the day it is checked on: today, or the first check's day in a replay
    # A replay: the last period each series held for each place when the claim was first
    # checked; anything later is cut, so figures published since never count.
    until: Extents | None = None
    # Series fetched besides the matched one (the population), by indicator id, until a plan uses them.
    extra: dict[str, ExtraSource] = field(default_factory=dict)
    # The check-wide model calls (extraction), which the confidence model reads.
    check_models: Sequence[ModelUse] = ()
    match: MatchResult | None = None  # None for a reader's re-check or a replay

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


@dataclass(kw_only=True)
class CodeSteps:
    catalog: Catalog
    fetcher: Fetcher
    tolerances: Tolerances
    today: Callable[[], date] | None = None
    # None: claims carry the confidence signals only, with no probability and no abstaining.
    confidence: ConfidenceModel | None = None

    def _today(self) -> date:
        return self.today() if self.today else datetime.now(UTC).date()

    @staticmethod
    def _as_of(claim: ClaimSpec, today: date) -> date | None:
        """The day a dated claim is checked as of: the last day it can have been said."""
        if claim.said_on is None:
            return None
        return parse_said_on(claim.said_on, today).by

    def versions(self) -> dict[str, object]:
        """What a stored result must match to be reused (the ledger): the catalog and the
        tolerances its verdicts came from."""
        return {"catalog": self.catalog.version, "tolerances": self.tolerances.version}

    # --- a stored claim, computed again (S1) -------------------------------------------------

    async def replay(self, old: ClaimResult, checked_on: date) -> ClaimResult:
        """`old` computed again from its stored plan, on the data as it is now but cut at the
        last period each series held when it was first checked: revised figures count, figures
        published since do not. `checked_on` is that first check's day; the claim's date and
        the stale-data check read as of it, as they did then.

        No model call: the claim, the statistic and the plan are the first check's, and the
        explanation is the code's. Raises `ReplayError` when the claim cannot be computed."""
        stored = old.plan
        if stored is None:
            raise ReplayError("no stored plan")
        plan = ValidPlan(calls=stored.calls, answer=old.answer, reason=old.plan_reason or "")
        out, _ = await self._recompute(old, checked_on, plan, stored.read_until)
        return out

    async def adopt(self, old: ClaimResult, checked_on: date, plan: ValidPlan) -> ClaimResult:
        """`old` (checked before plans were stored) computed with `plan`, a plan made for it
        now, on the data as it is now. The result stores the plan with where each series ends
        now; the caller keeps it only if it gives the same figures as `old` did."""
        out, data = await self._recompute(old, checked_on, plan, None)
        out.plan = StoredPlan(calls=plan.calls, read_until=read_extents(data))
        out.answer, out.plan_reason = plan.answer, plan.reason
        return out

    async def _recompute(
        self, old: ClaimResult, checked_on: date, plan: ValidPlan, until: Extents | None
    ) -> tuple[ClaimResult, dict[str, list[Observation]]]:
        """`old`'s claim and statistic, with `plan`, through the code's steps: the result and
        the data it read."""
        if old.indicator is None:
            raise ReplayError("no statistic matched")
        try:
            spec = self.catalog.get(old.indicator.id)
        except KeyError:
            raise ReplayError(f"{old.indicator.id} is no longer in the catalog") from None
        out = old.model_copy(
            deep=True,
            update={
                "data": None,
                "extra_sources": [],
                "operations": [],
                "series": None,
                "sweep": None,
                "changepoints": None,
                "distortion_checks": [],
            },
        )
        c = ClaimRun(Trace(_ignore), old.index, old.claim, out, checked_on, until)
        try:
            _, data, ctx = await self._read(c, spec)
            if missing := _unlisted(plan, ctx):
                raise ReplayError(f"no figures for {', '.join(missing)}")
            out.extra_sources = self._plan_sources(c, plan)
            execution = await self._execute(c, spec, plan, ctx, data)
            await self._verdict(c, plan, execution)
        except ClaimStopped as stop:
            raise ReplayError(stop.reason) from None
        if out.verdict.label is Label.CANT_CHECK:
            raise ReplayError(f"the figures no longer decide the claim: {out.verdict.reason}")
        out.confidence = self._scored(c, old.confidence.signals if old.confidence else Signals())
        out.explanation = template_explanation(out.verdict, spec.name)
        out.explanation_source = "template"
        out.models = [m for m in old.models if m.step is not Step.EXPLAIN]
        return out, data

    async def _read(
        self, c: ClaimRun, spec: IndicatorSpec
    ) -> tuple[IndicatorSpec, dict[str, list[Observation]], PlanContext]:
        """Fetch the claim's series and its population: the statistic read (the matched one,
        or the same measure from another source), the data, and what a plan may know."""
        spec, observations, info = await self._fetch(c, spec)
        data = {spec.id: observations}
        others = await self._denominator(c, spec, data)
        ctx = PlanContext(
            claim=c.claim, main=info, others=others, as_of=self._as_of(c.claim, c.today)
        )
        return spec, data, ctx

    # --- the steps code does, in order --------------------------------------------------------

    async def _fetch(
        self, c: ClaimRun, spec: IndicatorSpec
    ) -> tuple[IndicatorSpec, list[Observation], SeriesInfo]:
        await c.start(Step.FETCH)
        series, observations = await self._load(c, spec)
        note = ""
        # Only a claim matched in this run: a reader's pick and a replay keep their statistic.
        if c.match is not None and (swap := await self._same_measure(c, spec, observations)):
            matched, (spec, series, observations, missing) = spec, swap
            note = swap_note(matched, spec, c.claim.geo, missing)
            c.out.indicator = IndicatorRef.of(spec)
            c.out.suggestions = [s for s in c.out.suggestions if s.id != spec.id]
            c.out.notes.append(note)
            note += " "
        c.out.data = DataRef.of(series, observations)
        info = SeriesInfo.from_data(spec, observations)
        if c.claim.geo not in info.geos:
            raise ClaimStopped(
                Step.FETCH,
                f"{_cap(spec.source.label)} has no {spec.name} figures for "
                f"{place_name(c.claim.geo)}.",
            )
        await c.done(
            Step.FETCH, f"{note}Fetched {len(observations)} rows, {info.first} to {info.last}."
        )
        return spec, observations, info

    async def _same_measure(
        self, c: ClaimRun, spec: IndicatorSpec, observations: Sequence[Observation]
    ) -> tuple[IndicatorSpec, FetchedSeries, list[Observation], list[int]] | None:
        """When the claim's place has no figures for some of its years, the first entry of
        `spec.same_measure` that has them all: that entry, its series and rows, and the years
        `spec` lacked. None when nothing is missing or no other source does better."""
        gap = self.tolerances.max_period_gap
        years = claim_years(c.claim)
        missing = missing_years(years, observations, c.claim.geo, slack_years(spec, gap))
        if not missing:
            return None
        for twin in map(self.catalog.get, spec.same_measure):
            if not covers(twin.geo_coverage, c.claim.geo):
                continue
            try:
                series, rows = await self._load(c, twin)
            except ClaimStopped:
                continue  # that source down or without the place: keep the matched one
            if not missing_years(years, rows, c.claim.geo, slack_years(twin, gap)):
                return twin, series, rows, missing
        return None

    async def _load(
        self, c: ClaimRun, spec: IndicatorSpec
    ) -> tuple[FetchedSeries, list[Observation]]:
        claim = c.claim
        if claim.geo is None:
            raise ClaimStopped(Step.FETCH, NO_PLACE)
        try:
            filters = {**spec.filters, **geo_filter(spec.source, [claim.geo, *claim.peers])}
            series = await self.fetcher.fetch_series(str(spec.source), spec.source_code, filters)
        except UnknownPlace as exc:
            raise ClaimStopped(
                Step.FETCH,
                f"{_cap(spec.source.label)} has no figures for "
                f"{place_name(exc.place or claim.geo)}.",
            ) from exc
        except SourceUnavailable as exc:
            raise ClaimStopped(
                Step.FETCH,
                f"{_cap(spec.source.label)} didn't answer just now. "
                "Please try again in a few minutes.",
                retryable=True,
            ) from exc
        except AdapterError as exc:
            raise ClaimStopped(
                Step.FETCH, f"{_cap(spec.source.label)} couldn't provide the figures."
            ) from exc
        observations = to_claim_codes(spec.source, series.observations)
        if c.until is not None:
            observations = cut_at(observations, c.until.get(spec.id, {}))
        return series, observations

    async def _denominator(
        self, c: ClaimRun, spec: IndicatorSpec, data: dict[str, list[Observation]]
    ) -> tuple[SeriesInfo, ...]:
        """The place's total population, so a plan can divide by it (per_capita). Best effort:
        a claim that needs no population is checked without it."""
        if not wants_population(spec):
            return ()
        population = population_for(self.catalog, c.claim.geo)
        if population is None:
            return ()
        try:
            series, observations = await self._load(c, population)
        except ClaimStopped:
            return ()
        info = SeriesInfo.from_data(population, observations)
        if c.claim.geo not in info.geos:
            return ()
        data[population.id] = observations
        c.extra[population.id] = ExtraSource(
            indicator=IndicatorRef.of(population), data=DataRef.of(series, observations)
        )
        return (info,)

    @staticmethod
    def _plan_sources(c: ClaimRun, plan: ValidPlan) -> list[ExtraSource]:
        """The series fetched besides the matched one that the plan divides by."""
        return [
            c.extra[call.population]
            for call in plan.calls
            if call.population is not None and call.population in c.extra
        ]

    async def _execute(
        self,
        c: ClaimRun,
        spec: IndicatorSpec,
        plan: ValidPlan,
        ctx: PlanContext,
        data: dict[str, list[Observation]],
    ) -> Execution:
        await c.start(Step.EXECUTE)
        execution = execute_plan(plan, ctx, data, self.tolerances)
        c.out.operations = execution.records
        if execution.error is not None:
            raise ClaimStopped(
                Step.EXECUTE,
                f"HoldsUp found the data but couldn't finish the calculation: {execution.error}.",
            )
        first = plan.answer[0]
        if first < len(execution.series):
            c.out.series = ChartSeries.of(execution.series[first])
        c.out.sweep = self._sweep(c.claim, plan, execution)
        c.out.changepoints = self._change_points(c.claim, plan, execution)
        checks = await self._distortions(c, spec, plan, execution, data)
        c.out.distortion_checks = checks
        n = len(execution.records)
        summary = f"Ran {n} operation{'s' if n != 1 else ''}"
        if c.out.sweep is not None:
            summary += f"; recomputed {c.out.sweep.windows} time windows"
        if checks:
            flagged = sum(ch.flagged for ch in checks)
            summary += f"; {len(checks)} framing check{'s' if len(checks) != 1 else ''}"
            summary += f", {flagged} flagged" if flagged else ", none flagged"
        await c.done(Step.EXECUTE, summary + ".")
        return execution

    def _sweep(self, claim: ClaimSpec, plan: ValidPlan, execution: Execution) -> Sweep | None:
        """The cherry-pick sweep of the claim's one answer. Several answers compare places
        ("grew more than France"), which is not a choice of window."""
        if len(plan.answer) != 1:
            return None
        i = plan.answer[0]
        return sweep(
            claim,
            execution.records[i],
            execution.series[i],
            unit=execution.unit,
            tolerances=self.tolerances,
        )

    def _change_points(
        self, claim: ClaimSpec, plan: ValidPlan, execution: Execution
    ) -> ChangePoints | None:
        """Breaks in the trend of the series the claim's one answer read, and the claim's
        start or end leaning on one (P3.3)."""
        if len(plan.answer) != 1:
            return None
        i = plan.answer[0]
        return change_points(
            claim, execution.records[i], execution.series[i], tolerances=self.tolerances
        )

    async def _distortions(
        self,
        c: ClaimRun,
        spec: IndicatorSpec,
        plan: ValidPlan,
        execution: Execution,
        data: dict[str, list[Observation]],
    ) -> list[DistortionCheck]:
        """The distortion checks (P3.4) of the claim's answer. The series a check reads besides
        the claim's (population, prices, a real version) join the receipt's sources."""
        first = plan.answer[0]
        answer = [execution.records[i] for i in plan.answer]
        call = plan.calls[first]
        adjusted = call.series not in (None, spec.id)  # a series the plan made, or another one
        geo = c.claim.geo or ""
        population = population_for(self.catalog, c.claim.geo) if wants_population(spec) else None
        prices: Related | None = None
        source = None
        if wants_real_terms(c.claim, spec, answer, adjusted):
            source = real_terms_source(self.catalog, spec, c.claim.geo)
        if source is not None:
            prices = await self._related(c, source, data)
        checks = distortion_checks(
            CheckInput(
                claim=c.claim,
                spec=spec,
                answer=answer,
                series=execution.series[first] if first < len(execution.series) else None,
                unit=execution.unit,
                tolerances=self.tolerances,
                today=c.today,
                said=said_between(c.claim.said_on, self._as_of(c.claim, c.today)),
                adjusted=adjusted,
                changepoints=c.out.changepoints,
                population=_related(population, data, geo),
                real=prices if source is not None and source.id == spec.real_version else None,
                prices=prices if source is not None and source.id != spec.real_version else None,
            )
        )
        listed = {e.indicator.id for e in c.out.extra_sources}
        for used in dict.fromkeys(ch.uses for ch in checks if ch.uses is not None):
            if used not in listed and used in c.extra:
                c.out.extra_sources.append(c.extra[used])
        return checks

    async def _related(
        self, c: ClaimRun, spec: IndicatorSpec, data: dict[str, list[Observation]]
    ) -> Related | None:
        """A series a check reads (fetched now, only when the check applies). Best effort: the
        check is left out when the source has nothing."""
        try:
            series, observations = await self._load(c, spec)
        except ClaimStopped:
            return None
        data[spec.id] = observations
        c.extra[spec.id] = ExtraSource(
            indicator=IndicatorRef.of(spec), data=DataRef.of(series, observations)
        )
        return _related(spec, data, c.claim.geo or "")

    async def _verdict(self, c: ClaimRun, plan: ValidPlan, execution: Execution) -> None:
        await c.start(Step.VERDICT)
        claim, records, answer = c.claim, execution.records, plan.answer
        # A number wrong as stated but right as the other kind (percent or points) is judged
        # there; the points check's flag then makes it "framing matters", not "not supported".
        if (reading := points_reading(c.claim, c.out.distortion_checks)) is not None:
            claim, records, answer = reading[0], reading[1], [0]
        verdict = decide(
            claim,
            records,
            answer,
            unit=execution.unit,
            tolerances=self.tolerances,
            window_share=c.out.sweep.share if c.out.sweep else None,
            distortions=[ch.text for ch in c.out.distortion_checks if ch.flagged],
        )
        c.out.verdict = verdict
        status: StepStatus = "cant_check" if verdict.label is Label.CANT_CHECK else "ok"
        await c.done(Step.VERDICT, f"{verdict.label}: {verdict.reason}", status=status)

    def _scored(self, c: ClaimRun, base: Signals) -> Confidence | None:
        """How sure the check is of its verdict (P4.5): `base` (what matching and the router
        found) with what the data and the verdict show. None when the verdict is cant_check:
        there is nothing to be sure of."""
        out = c.out
        if out.verdict.label is Label.CANT_CHECK or out.indicator is None:
            return None
        last = out.series.points[-1].period if out.series and out.series.points else None
        signals = base.model_copy(
            update={
                "definition_mismatch": any(
                    ch.kind is CheckKind.DEFINITION and ch.flagged for ch in out.distortion_checks
                ),
                "data_age_years": data_age_years(last, self._as_of(c.claim, c.today) or c.today),
                "series_length": len(out.series.points) if out.series else None,
                "boundary_distance": boundary_distance(out.verdict.parts),
            }
        )
        return unscored(signals) if self.confidence is None else self.confidence.score(signals)


async def _ignore(event: StepEvent) -> None:
    """A replay's trace goes nowhere: no reader is watching it run."""


def _unlisted(plan: ValidPlan, ctx: PlanContext) -> list[str]:
    """The indicators the plan reads that this run did not fetch (a population gone)."""
    named = (
        ref
        for call in plan.calls
        for ref in (call.series, call.population, call.price_index)
        if ref is not None and not ref.startswith("@")
    )
    return [ref for ref in dict.fromkeys(named) if ctx.info(ref) is None]


def _ordinal(period: str) -> int | None:
    try:
        return parse_period(period).ordinal
    except OpError:
        return None


def read_extents(data: Mapping[str, Sequence[Observation]]) -> dict[str, dict[str, str]]:
    """Per indicator, per place, the last period with a value: where a replay cuts the data."""
    out: dict[str, dict[str, str]] = {}
    for indicator, observations in data.items():
        last: dict[str, tuple[int, str]] = {}
        for o in observations:
            ordinal = _ordinal(o.period) if o.value is not None else None
            if ordinal is not None and (o.geo not in last or ordinal > last[o.geo][0]):
                last[o.geo] = (ordinal, o.period)
        out[indicator] = {geo: period for geo, (_, period) in sorted(last.items())}
    return out


def cut_at(observations: Sequence[Observation], until: Mapping[str, str]) -> list[Observation]:
    """The observations up to each place's last period in `until`; a place it lacks had no
    figures then, so none of its figures are kept."""
    limits = {geo: _ordinal(period) for geo, period in until.items()}
    out = []
    for o in observations:
        limit, ordinal = limits.get(o.geo), _ordinal(o.period)
        if limit is not None and ordinal is not None and ordinal <= limit:
            out.append(o)
    return out


def _related(
    spec: IndicatorSpec | None, data: dict[str, list[Observation]], geo: str
) -> Related | None:
    """The place's values of a fetched series, or None when it was not fetched or has none."""
    if spec is None or spec.id not in data:
        return None
    try:
        return Related(spec, Series.from_observations(data[spec.id], geo, unit=spec.unit))
    except OpError:
        return None
