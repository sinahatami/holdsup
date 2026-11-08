"""Check a model plan against the operations' signatures, the fetched data and the claim."""

from collections.abc import Sequence

from holdsup.ops import ChangeKind
from holdsup.pipeline.claim import AssertionType
from holdsup.pipeline.plan.model import (
    MAX_CALLS,
    PERIOD_ARGS,
    PERIOD_FORMAT,
    ModelPlan,
    OpCall,
    PlanContext,
    PlanInvalid,
    ValidPlan,
    source_of,
    step_of,
)
from holdsup.pipeline.plan.operations import SERIES_OPS, SIGNATURES
from holdsup.pipeline.plan.periods import frequency_of, is_reversed, period_error
from holdsup.pipeline.plan.repair import REPAIRS


def _check_call(
    i: int, call: OpCall, calls: Sequence[OpCall], ctx: PlanContext
) -> tuple[list[str], list[str]]:
    """Errors and notes for call `i`; arguments its operation does not take are dropped."""
    errors: list[str] = []
    notes: list[str] = []
    where = f"call {i} ({call.op})"
    required, optional = SIGNATURES[call.op]
    for name in sorted(required - call.given()):
        errors.append(f"{where}: missing {name}")
    for name in sorted(call.given() - required - optional):
        notes.append(f"{where}: dropped {name}, which {call.op} does not take")
        setattr(call, name, None)

    # Which series it reads, and the places that series has.
    ref = call.series
    if ref is not None and ref.startswith("@"):
        n = step_of(ref)
        if not 0 <= n < i or calls[n].op not in SERIES_OPS:
            errors.append(f"{where}: series {ref!r} must name an earlier per_capita or deflate")
            return errors, notes
        source = source_of(n, calls, ctx)
        places = frozenset({calls[n].geo or ""})
    else:
        source = ctx.info(ref)
        if source is None:
            errors.append(f"{where}: unknown series {ref!r}")
            return errors, notes
        places = source.geos
    if source is None:  # the referenced call reads an unknown series (reported there)
        return errors, notes
    info = source

    for name in ("geo", "geo_b"):
        geo = getattr(call, name)
        if geo is not None and geo not in places:
            errors.append(f"{where}: no data for {name} {geo!r} in {info.id}")
    for geo in call.geos or []:
        if geo not in places:
            errors.append(f"{where}: no data for {geo!r} in {info.id}")
    for name in PERIOD_ARGS:
        value = getattr(call, name)
        if value is not None and (problem := period_error(value, info, call.op)):
            errors.append(f"{where}: {name} {problem}")
    written = {f for f in (frequency_of(call.start), frequency_of(call.end)) if f is not None}
    if len(written) > 1:
        errors.append(
            f"{where}: start and end must both be whole years (YYYY) or both "
            f"{PERIOD_FORMAT[info.frequency]}"
        )
    elif is_reversed(call.start, call.end, info, call.op):
        errors.append(f"{where}: start must be before end")
    for name in ("population", "price_index"):
        ref_id = getattr(call, name)
        if ref_id is None:
            continue
        other = ctx.info(ref_id)
        if other is None or other is ctx.main:
            errors.append(f"{where}: {name} {ref_id!r} is not a listed indicator")
        elif other.frequency is not info.frequency:
            errors.append(f"{where}: {name} {ref_id!r} is {other.frequency}, not {info.frequency}")
    return errors, notes


def _answer_errors(plan: ModelPlan, ctx: PlanContext) -> list[str]:
    claim, calls, answer = ctx.claim, plan.calls, plan.answer
    if not answer:
        return ["answer must name at least one call"]
    if len(set(answer)) != len(answer) or not all(0 <= i < len(calls) for i in answer):
        return [f"answer {answer} must be distinct indexes of calls"]
    chosen = [calls[i] for i in answer]
    ops = [c.op for c in chosen]
    t = claim.assertion.type
    first = chosen[0]
    if claim.geo is not None and first.geo != claim.geo:
        return [f"the first answer call must be about {claim.geo}, not {first.geo}"]
    if t is AssertionType.LEVEL:
        ok = ops == ["value_at"]
    elif t is AssertionType.TREND:
        ok = ops == ["trend"]
    elif t is AssertionType.RANK:
        ok = ops == ["rank"]
    elif t is AssertionType.COMPARE:
        ok = ops == ["compare"] or (
            len(ops) >= 2
            and set(ops) == {"change"}
            and len({c.kind for c in chosen}) == 1
            and len({c.geo for c in chosen}) == len(chosen)
        )
    else:  # the four change types
        kind = ChangeKind(str(t))
        ok = (
            ops == ["value_at"]  # one value of a growth-rate series
            or (ops == ["change"] and first.kind is kind)
            or (ops == ["cagr"] and t is AssertionType.PERCENT)
        )
    if not ok:
        return [f"answer calls {ops} do not answer a {t} claim"]
    return []


def validate_plan(plan: ModelPlan, ctx: PlanContext) -> ValidPlan:
    """The plan with unused arguments dropped, or PlanInvalid listing every problem."""
    plan = plan.model_copy(deep=True)
    errors: list[str] = []
    if not plan.calls:
        raise PlanInvalid(["the plan has no calls"])
    notes = [note for repair in REPAIRS for note in repair(plan, ctx)]
    if len(plan.calls) > MAX_CALLS:
        errors.append(f"at most {MAX_CALLS} calls")
    for i, call in enumerate(plan.calls):
        e, n = _check_call(i, call, plan.calls, ctx)
        errors += e
        notes += n
    if not errors:
        errors += _answer_errors(plan, ctx)
    if errors:
        raise PlanInvalid(errors)
    return ValidPlan(calls=plan.calls, answer=plan.answer, reason=plan.reason, notes=notes)
