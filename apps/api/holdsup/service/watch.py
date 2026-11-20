"""The claim watch (S1): compare the figures behind stored checks with the sources, and publish
a check computed again when a source revised them.

`make watch` runs it (scripts/watch.py); a GitHub Actions schedule runs that daily. Code only:
each claim's stored plan is replayed (`CodeSteps.replay`) on the data as it is now, cut where
the check read it, so a revision counts and a figure published since does not. No model is
asked, so a run needs no provider key and spends no quota.

An update is a new check (new id, `update_of` naming the one it updates); the old check stays
as it was, and its readers are pointed at the update (`updated_by`), as are its gallery place
and its ledger entry. The old receipt is never rewritten.

The backfill (`make watch ARGS=--backfill`) gives checks made before plans were stored a plan:
the plan model is asked once per claim, and the plan kept only when it gives exactly the
figures the check showed.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import structlog

from holdsup.pipeline.result import ClaimResult, Versions, app_version
from holdsup.pipeline.run import Pipeline
from holdsup.pipeline.steps import CodeSteps, ReplayError
from holdsup.router import RouterError
from holdsup.service.store import (
    CheckResult,
    CheckStore,
    ClaimChange,
    FigureChange,
    StoredCheck,
    UpdateOf,
)
from holdsup.verdict import Label

WATCH_DAYS = 90  # a check is watched this long after it was made; a featured one always
MAX_PER_RUN = 200  # checks compared per run, the ones compared longest ago first

log = structlog.get_logger(__name__)


class Outcome(StrEnum):
    UNCHANGED = "unchanged"  # the same figures: the check is marked as compared today
    UPDATED = "updated"  # revised figures: a new check, the old one pointing at it
    PLANNED = "planned"  # the backfill stored a plan that gives the same figures
    SKIPPED = "skipped"  # a claim could not be computed now (source down, data gone): later


@dataclass(frozen=True)
class Watched:
    check_id: UUID
    text: str
    outcome: Outcome
    detail: str = ""  # what changed, or why it was skipped
    update_id: UUID | None = None


def checked_on(result: CheckResult) -> date:
    """The day the claims were first checked: every replay reads as of it, updates too."""
    return result.update_of.checked_on if result.update_of else result.created_at.date()


def same_figures(old: ClaimResult, new: ClaimResult) -> bool:
    """Every number the claim's result holds is the same: the operations, the chart, the
    sweep, the change points and the framing checks. The verdict follows from them; dates,
    hashes and models are not figures."""
    return (
        old.operations == new.operations
        and old.series == new.series
        and old.sweep == new.sweep
        and old.changepoints == new.changepoints
        and old.distortion_checks == new.distortion_checks
    )


def claim_change(old: ClaimResult, new: ClaimResult) -> ClaimChange:
    """What a reader is told moved: the verdict, and each figure it read that changed."""
    before = {(p.name, p.period): p.computed for p in old.verdict.parts}
    after = {(p.name, p.period): p.computed for p in new.verdict.parts}
    figures = [
        FigureChange(name=k[0], period=k[1], before=before.get(k), after=after.get(k))
        for k in dict.fromkeys([*before, *after])
        if before.get(k) != after.get(k)
    ]
    return ClaimChange(
        index=old.index, before=old.verdict.label, after=new.verdict.label, figures=figures
    )


async def watch(
    store: CheckStore,
    steps: CodeSteps,
    *,
    now: datetime,
    limit: int = MAX_PER_RUN,
    days: int = WATCH_DAYS,
    save: bool = True,
) -> list[Watched]:
    """Compare up to `limit` checks with the sources; publish an update for each whose figures
    were revised. `save=False` reports what would change and stores nothing."""
    checks = await store.watchable(now - timedelta(days=days), limit, steps.versions())
    done = [await _watch_one(store, steps, stored, now, save) for stored in checks]
    if save:
        await store.mark_watched([w.check_id for w in done if w.outcome is Outcome.UNCHANGED], now)
    return done


async def _watch_one(
    store: CheckStore, steps: CodeSteps, stored: StoredCheck, now: datetime, save: bool
) -> Watched:
    result = CheckResult.model_validate(stored.result)
    claims: list[ClaimResult] = []
    changes: list[ClaimChange] = []
    for claim in result.claims:
        if claim.plan is None:  # stopped before a plan: nothing was computed to compare
            claims.append(claim)
            continue
        try:
            again = await steps.replay(claim, checked_on(result))
        except ReplayError as err:
            log.info("watch_skipped", check_id=str(stored.id), claim=claim.index, reason=str(err))
            return Watched(
                stored.id, stored.text, Outcome.SKIPPED, f"claim {claim.index + 1}: {err}"
            )
        if same_figures(claim, again):
            claims.append(claim)
        else:
            claims.append(again)
            changes.append(claim_change(claim, again))
    if not changes:
        return Watched(stored.id, stored.text, Outcome.UNCHANGED)
    update = result.model_copy(
        update={
            "id": uuid4(),
            "created_at": now,
            "finished_at": now,
            "cached_from": None,
            "claims": claims,
            "versions": Versions(
                app=app_version(),
                catalog=steps.catalog.version,
                tolerances=steps.tolerances.version,
            ),
            "update_of": UpdateOf(
                check_id=result.id,
                created_at=result.created_at,
                checked_on=checked_on(result),
                changes=changes,
            ),
        }
    )
    if save:
        await store.supersede(stored.id, update)
        log.info("watch_updated", check_id=str(stored.id), update_id=str(update.id))
    return Watched(stored.id, stored.text, Outcome.UPDATED, describe(changes), update.id)


def describe(changes: Sequence[ClaimChange]) -> str:
    """One line for the run's table: each changed claim's verdict, before → after."""
    return "; ".join(
        f"claim {c.index + 1}: {c.before}" + (f" → {c.after}" if c.after != c.before else " (same)")
        for c in changes
    )


async def backfill(
    store: CheckStore,
    pipeline: Pipeline,
    *,
    now: datetime,
    limit: int = MAX_PER_RUN,
    days: int = WATCH_DAYS,
    save: bool = True,
) -> list[Watched]:
    """Give the checks the watch would read, made before plans were stored, a plan: the plan
    model is asked once per matched, checked claim, and the plan kept only when it gives the
    same figures and answer the check showed. Stops at the first `RouterError` (no model
    left today), keeping what it stored."""
    since = now - timedelta(days=days)
    checks = await store.watchable(since, limit, pipeline.versions(), planned=False)
    done: list[Watched] = []
    for stored in checks:
        try:
            done.append(await _plan_one(store, pipeline, stored, save))
        except RouterError as err:
            done.append(Watched(stored.id, stored.text, Outcome.SKIPPED, f"no model: {err}"))
            break
    return done


async def _plan_one(
    store: CheckStore, pipeline: Pipeline, stored: StoredCheck, save: bool
) -> Watched:
    result = CheckResult.model_validate(stored.result)
    claims: list[ClaimResult] = []
    kept, missed = 0, []
    for claim in result.claims:
        if (
            claim.plan is not None
            or claim.indicator is None
            or claim.verdict.label is Label.CANT_CHECK
        ):
            claims.append(claim)
            continue
        try:
            adopted = await pipeline.plan_again(claim, checked_on(result))
        except ReplayError as err:
            claims.append(claim)
            missed.append(f"claim {claim.index + 1}: {err}")
            continue
        if adopted.answer == claim.answer and same_figures(claim, adopted):
            claims.append(claim.model_copy(update={"plan": adopted.plan}))
            kept += 1
        else:
            claims.append(claim)
            missed.append(f"claim {claim.index + 1}: the new plan gives other figures")
    if kept and save:
        await store.set_result(stored.id, result.model_copy(update={"claims": claims}))
    outcome = Outcome.PLANNED if kept else Outcome.SKIPPED
    return Watched(stored.id, stored.text, outcome, "; ".join(missed))


def format_table(rows: Sequence[Watched]) -> str:
    lines = [
        f"{w.outcome:9}  {str(w.check_id)[:8]}  {w.detail[:60]:60}  {w.text[:60]}" for w in rows
    ]
    counts = {o: sum(w.outcome is o for w in rows) for o in Outcome}
    summary = ", ".join(f"{n} {o}" for o, n in counts.items() if n) or "nothing to compare"
    return "\n".join([*lines, f"{len(rows)} checks: {summary}"])
