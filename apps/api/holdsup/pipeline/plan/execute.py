"""Run a validated plan over the fetched data: code computes every number."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from holdsup.adapters.base import Observation
from holdsup.ops import (
    LATEST,
    AnnualValue,
    Flag,
    FlagCode,
    Frequency,
    OpError,
    OpRecord,
    Series,
    annual,
    annual_flag,
    latest_year_flag,
    published_by,
)
from holdsup.pipeline.claim import VAGUE_YEARS, Basis
from holdsup.pipeline.plan.model import (
    PERIOD_ARGS,
    OpCall,
    PlanContext,
    SeriesInfo,
    ValidPlan,
    source_of,
    step_of,
)
from holdsup.pipeline.plan.operations import OPERATIONS, SeriesReader, run_call
from holdsup.pipeline.plan.periods import frequency_of
from holdsup.verdict.rules import Tolerances


@dataclass
class Execution:
    records: list[OpRecord]
    error: str | None  # an OpError message: the claim can't be checked with this data
    unit: str | None  # the unit of the series the first answer call reads


def execute_plan(
    plan: ValidPlan,
    ctx: PlanContext,
    data: Mapping[str, Sequence[Observation]],
    tolerances: Tolerances,
) -> Execution:
    """Run a validated plan over the fetched observations (keyed by indicator id)."""
    cache: dict[tuple[str, str], Series] = {}
    records: list[OpRecord] = []
    units: list[str | None] = []

    def native(ref: str | None, geo: str) -> Series:
        if ref is not None and ref.startswith("@"):
            return Series.from_record(records[step_of(ref)])
        info = ctx.info(ref)
        assert info is not None  # noqa: S101 (validated)
        key = (info.id, geo)
        if key not in cache:
            cache[key] = Series.from_observations(data[info.id], geo, unit=info.unit)
        return cache[key]

    def unit_of(call: OpCall) -> str | None:
        """The unit of the series a call reads, or of the series it makes."""
        if OPERATIONS[call.op].makes_series:
            return records[-1].unit
        if call.series is not None and call.series.startswith("@"):
            return units[step_of(call.series)]
        info = ctx.info(call.series)
        return None if info is None else info.unit

    try:
        for i, call in enumerate(plan.calls):
            source = source_of(i, plan.calls, ctx)
            how = _yearly(call, source)
            read, cut = _as_of(call, source, native, ctx)
            if how is None:
                record = run_call(call, read, ctx, tolerances)
            else:
                record = _run_yearly(call, read, how, ctx, tolerances)
            records.append(
                record.model_copy(
                    update={"flags": [*record.flags, *cut(), *_window_flags(call, ctx)]}
                )
            )
            units.append(unit_of(call))
    except OpError as exc:
        return Execution(records, str(exc), None)
    return Execution(records, None, units[plan.answer[0]])


def _as_of(
    call: OpCall, source: SeriesInfo | None, native: SeriesReader, ctx: PlanContext
) -> tuple[SeriesReader, Callable[[], list[Flag]]]:
    """For a dated claim, "latest" is the last period published by its date: series are cut
    there. Returns the reader and, after the call ran, the receipt's note (if anything was cut).
    """
    if ctx.as_of is None or source is None or LATEST not in (call.period, call.start, call.end):
        return native, list
    as_of, lag = ctx.as_of, source.lag_months
    cuts: dict[str, tuple[Series, Series]] = {}

    def read(ref: str | None, geo: str) -> Series:
        s = native(ref, geo)
        last = published_by(s.frequency, as_of, lag)
        cut = s.until(last) if last.ordinal < s.last.ordinal else s
        cuts.setdefault(geo, (cut, s))
        return cut

    def flags() -> list[Flag]:
        cut, full = cuts.get(call.geo or "", (None, None))
        if cut is None or full is None or cut.last == full.last:
            return []
        months = f"{lag} month{'s' if lag != 1 else ''}"
        return [
            Flag(
                code=FlagCode.AS_OF,
                detail=f"claim date {ctx.claim.said_on}: latest is the last period published by "
                f"then, {cut.last} (a release about {months} after a period ends); its value is "
                "today's revised figure, which may differ from the one first published",
                requested="latest",
                used=str(cut.last),
            )
        ]

    return read, flags


def _window_flags(call: OpCall, ctx: PlanContext) -> list[Flag]:
    """Say so when a call's window is the one code assumed for "for years" or "recently"."""
    claim = ctx.claim
    if claim.start_basis is not Basis.ASSUMED or claim.start is None or call.start is None:
        return []
    if call.start[:4] != claim.start[:4]:
        return []
    return [
        Flag(
            code=FlagCode.ASSUMED_WINDOW,
            detail=f"the claim gives no dates: the window is the {VAGUE_YEARS} years before the "
            f"claim date ({claim.said_on or 'today'}), from {claim.start}",
            requested=claim.start,
        )
    ]


def _yearly(call: OpCall, source: SeriesInfo | None) -> AnnualValue | None:
    """How to make yearly values when a call names whole years on a monthly or quarterly
    series; None when it reads the series as it is (a trend widens years to their months)."""
    if source is None or source.frequency is Frequency.ANNUAL or source.annual is None:
        return None
    spec = OPERATIONS[call.op]
    if spec.reads_months or spec.makes_series:
        return None
    named = (getattr(call, name) for name in PERIOD_ARGS)
    return source.annual if Frequency.ANNUAL in map(frequency_of, named) else None


def _run_yearly(
    call: OpCall, native: SeriesReader, how: AnnualValue, ctx: PlanContext, tol: Tolerances
) -> OpRecord:
    """Run `call` on yearly values made from its monthly or quarterly series; the record says
    how they were made, and which year "latest" is."""
    made: dict[str, tuple[Series, Series]] = {}

    def read(ref: str | None, geo: str) -> Series:
        if geo not in made:
            base = native(ref, geo)
            made[geo] = (annual(base, how), base)
        return made[geo][0]

    record = run_call(call, read, ctx, tol)
    yearly, base = made[call.geo or ""]
    years = sorted({p.period for p in record.inputs})
    flags = [annual_flag(base.frequency, how, years)]
    if LATEST in (call.period, call.start, call.end):
        flags.append(latest_year_flag(yearly, base))
    return record.model_copy(update={"flags": [*record.flags, *flags]})
