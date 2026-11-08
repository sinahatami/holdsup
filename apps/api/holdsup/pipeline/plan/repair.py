"""Code's own fixes to a model plan, applied before it is checked.

Each repair rewrites the plan in place when the model wrote something the claim clearly means
otherwise, and returns notes for the receipt. They run in `REPAIRS` order.
"""

from collections.abc import Callable

from holdsup.ops import LATEST, ChangeKind, Frequency, Period
from holdsup.pipeline.claim import CHANGE_TYPES, AssertionType, Basis, says_now
from holdsup.pipeline.plan.model import (
    PERIOD_ARGS,
    ModelPlan,
    OpCall,
    PlanContext,
    source_of,
    step_of,
)
from holdsup.pipeline.plan.operations import OPERATIONS
from holdsup.pipeline.plan.periods import (
    claim_years,
    frequency_of,
    period_error,
    period_order,
    yearly_allowed,
)

Repair = Callable[[ModelPlan, PlanContext], list[str]]


def _whole_years(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    """Code's fix for a month or quarter the claim never named: "in 2015" on a monthly series is
    the year 2015 (its average), not 2015-01. A call is rewritten whole or not at all, so its
    start and end keep one form. Periods are rewritten in place; returns notes."""
    years = claim_years(ctx.claim)
    notes: list[str] = []
    if not years:
        return notes
    for i, call in enumerate(plan.calls):
        ref = call.series
        if ref is not None and ref.startswith("@"):
            n = step_of(ref)
            info = source_of(n, plan.calls, ctx) if 0 <= n < i else None
        else:
            info = ctx.info(ref)
        if info is None or info.frequency is Frequency.ANNUAL or not yearly_allowed(call.op, info):
            continue
        finer = {
            name: str(getattr(call, name))
            for name in PERIOD_ARGS
            if frequency_of(getattr(call, name)) not in (None, Frequency.ANNUAL)
        }
        new = {name: value[:4] for name, value in finer.items()}
        if not new or not set(new.values()) <= years:
            continue  # it also names a month or quarter the claim does name: leave it whole
        if (
            call.start is not None
            and call.end is not None
            and new.get("start", call.start) == (new.get("end", call.end))
        ):
            continue  # a change within one year: the months are what the plan means
        for name, year in new.items():
            notes.append(
                f"call {i} ({call.op}): {name} {getattr(call, name)} → {year}, "
                "the claim names the whole year"
            )
            setattr(call, name, year)
    return notes


def _assumed_start(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    """A window code assumed ("for years": the 5 years before the claim date) is the window:
    answer calls that start elsewhere start there instead."""
    claim = ctx.claim
    if claim.start_basis is not Basis.ASSUMED or claim.start is None:
        return []
    notes = []
    for i in plan.answer:
        if not 0 <= i < len(plan.calls):
            continue
        call = plan.calls[i]
        info = source_of(i, plan.calls, ctx)
        if not OPERATIONS[call.op].windowed or info is None or call.start == claim.start:
            continue
        start = claim.start
        form = frequency_of(call.end)
        if len(start) == 4 and form not in (None, Frequency.ANNUAL):
            start = str(Period(int(start), 1, form))  # the same form as the call's end
        if period_error(start, info, call.op) is None:
            notes.append(f"call {i} ({call.op}): start {call.start} → {start}, the assumed window")
            call.start = start
    return notes


def _latest_cutoff(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    """In a dated claim about the present, a call that names the claim date's last published
    period itself (2013-Q2) means "latest": written that way, the receipt gets the claim-date
    note. A period the claim itself names is left alone."""
    claim = ctx.claim
    if ctx.as_of is None or not says_now(claim):
        return []
    names = [n for n, wanted in (("start", claim.start), ("end", claim.end)) if wanted == LATEST]
    if not names and claim.end is not None and len(claim.end) == 4:
        names = ["period"]  # a level said in its own year ("is 133%"), no month or quarter named
    elif names:
        names.append("period")
    notes = []
    for i, call in enumerate(plan.calls):
        info = source_of(i, plan.calls, ctx)
        if info is None:
            continue
        for name in names:
            if getattr(call, name) == ctx.published(info):
                notes.append(
                    f"call {i} ({call.op}): {name} {getattr(call, name)} → {LATEST}, "
                    f"the last period published by the claim date {claim.said_on}"
                )
                setattr(call, name, LATEST)
    return notes


def _values_as_change(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    """A "from X to Y" change claim answered by two value_at calls (one per end) is a change:
    the two become one change call of the claim's own kind, and the calls after it move up."""
    claim = ctx.claim
    if claim.assertion.type not in CHANGE_TYPES or len(plan.answer) != 2:
        return []
    first, second = sorted(plan.answer)
    if not 0 <= first < second < len(plan.calls):
        return []
    a, b = plan.calls[first], plan.calls[second]
    if (
        a.op != "value_at"
        or b.op != "value_at"
        or a.geo != b.geo
        or a.series != b.series
        or a.period is None
        or b.period is None
    ):
        return []
    order_a, order_b = period_order(a.period), period_order(b.period)
    if order_a is None or order_b is None or order_a == order_b:
        return []
    start, end = (a.period, b.period) if order_a < order_b else (b.period, a.period)
    kind = ChangeKind(str(claim.assertion.type))
    merged = OpCall(op="change", series=a.series, geo=a.geo, start=start, end=end, kind=kind)
    plan.calls[first] = merged
    del plan.calls[second]
    for call in plan.calls[second:]:  # references to later calls shift down by one
        if (
            call.series is not None
            and call.series.startswith("@")
            and step_of(call.series) > second
        ):
            call.series = f"@{step_of(call.series) - 1}"
    plan.answer = [first]
    note = f"calls {first} and {second}: two value_at ({a.period}, {b.period}) → one change"
    return [f"{note} {start} to {end} ({kind}), the claim is about a change"]


def _level_answer(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    """A level claim is answered by one value_at; extra answer calls (a change to show the
    rise) are kept as context."""
    claim = ctx.claim
    if claim.assertion.type is not AssertionType.LEVEL or len(plan.answer) < 2:
        return []
    values = [
        i
        for i in plan.answer
        if 0 <= i < len(plan.calls)
        and plan.calls[i].op == "value_at"
        and plan.calls[i].geo == claim.geo
    ]
    if len(values) != 1:
        return []
    note = f"answer {plan.answer} → {values}: a level claim is answered by its value_at"
    plan.answer = values
    return [note]


# Order matters: merge value_at pairs first, then fix windows, then periods, then the answer.
REPAIRS: tuple[Repair, ...] = (
    _values_as_change,
    _assumed_start,
    _latest_cutoff,
    _whole_years,
    _level_answer,
)
