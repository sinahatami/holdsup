"""The claim watch (S1): unchanged figures mark a check as compared, revised ones publish an
update the old check points to, a claim that cannot be computed now waits, and the backfill
keeps a new plan only when it gives the figures the check showed."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from holdsup.adapters.base import Observation
from holdsup.pipeline.result import ClaimResult, Versions
from holdsup.pipeline.run import Pipeline
from holdsup.pipeline.steps import CodeSteps, ReplayError
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from holdsup.service.site_pages import SitePages
from holdsup.service.store import (
    CheckResult,
    CheckStatus,
    FigureChange,
    InMemoryCheckStore,
    StoredCheck,
)
from holdsup.service.watch import (
    Outcome,
    Watched,
    backfill,
    checked_on,
    format_table,
    tell_site,
    watch,
)
from holdsup.verdict import Label, cant_check, load_tolerances
from tests.pipeline.test_regressions import CATALOG, TODAY, RecordedFetcher, plan, search
from tests.pipeline.test_replay import DownFetcher, EditedFetcher, fall
from tests.router.fakes import FakeClient, FakeClock, config, provider

FIRST = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)
NOW = FIRST + timedelta(days=30)


def steps(fetcher: RecordedFetcher | None = None) -> CodeSteps:
    return CodeSteps(
        catalog=CATALOG,
        fetcher=fetcher or RecordedFetcher(),
        tolerances=load_tolerances(),
        today=lambda: TODAY,
    )


def revised(o: Observation) -> Observation:
    """Eurostat revises Italy's 2023 months up by 1.5 points."""
    up = o.geo == "IT" and o.period.startswith("2023") and o.value is not None
    return replace(o, value=o.value + 1.5) if up and o.value is not None else o


async def stored(
    store: InMemoryCheckStore, *claims: ClaimResult, featured: bool = False
) -> CheckResult:
    result = CheckResult(
        id=uuid4(), text="Italy's unemployment rate fell.", created_at=FIRST,
        finished_at=FIRST + timedelta(seconds=9), claims=list(claims),
        versions=Versions(app="0.3.0", catalog=CATALOG.version,
                          tolerances=load_tolerances().version),
        models=[],
    )  # fmt: skip
    await store.create(StoredCheck(result.id, result.text, CheckStatus.QUEUED, FIRST))
    await store.finish(result, None)
    if featured:
        await store.set_featured(result.id, True)
    return result


async def test_unchanged_figures_mark_the_check_as_compared() -> None:
    store = InMemoryCheckStore()
    first = await stored(store, await fall())
    [w] = await watch(store, steps(), now=NOW)
    assert w == Watched(first.id, first.text, Outcome.UNCHANGED)
    got = await store.get(first.id)
    assert got is not None and got.watched_at == NOW and got.updated_by is None
    assert len(store.checks) == 1


async def test_revised_figures_publish_an_update_the_old_check_points_to() -> None:
    store = InMemoryCheckStore()
    claim = await fall()
    first = await stored(store, claim, featured=True)
    [w] = await watch(store, steps(EditedFetcher(revised)), now=NOW)
    assert w.outcome is Outcome.UPDATED and w.update_id is not None
    assert w.detail == "claim 1: supported → partly_supported"

    old, new = await store.get(first.id), await store.get(w.update_id)
    assert old is not None and new is not None and new.result is not None
    assert old.updated_by == w.update_id and not old.featured and new.featured
    update = CheckResult.model_validate(new.result)
    assert (update.created_at, update.text, update.cached_from) == (NOW, first.text, None)
    assert update.update_of is not None
    assert (update.update_of.check_id, update.update_of.created_at) == (first.id, FIRST)
    assert update.update_of.checked_on == FIRST.date()
    [change] = update.update_of.changes
    assert (change.index, change.before, change.after) == (0, Label.SUPPORTED,
                                                           Label.PARTLY_SUPPORTED)  # fmt: skip
    # The 2023 average and the fall it ends moved; the 2015 start did not.
    moved = {(f.name, f.period): (f.before, f.after) for f in change.figures}
    assert set(moved) == {("assertion", None), ("end value", "2023")}
    for before, after in moved.values():
        assert before is not None and after is not None and round(after - before, 6) == 1.5
    [again] = update.claims
    assert again.explanation_source == "template" and again.plan == claim.plan
    # The update itself is then watched: the same figures again leave it alone.
    [w2] = await watch(store, steps(EditedFetcher(revised)), now=NOW + timedelta(days=1))
    assert (w2.check_id, w2.outcome) == (w.update_id, Outcome.UNCHANGED)


async def test_an_update_of_an_update_reads_as_of_the_first_check() -> None:
    store = InMemoryCheckStore()
    await stored(store, await fall())
    [w] = await watch(store, steps(EditedFetcher(revised)), now=NOW)
    assert w.update_id is not None
    got = await store.get(w.update_id)
    assert got is not None and got.result is not None
    assert checked_on(CheckResult.model_validate(got.result)) == FIRST.date()


async def test_a_dry_run_stores_nothing() -> None:
    store = InMemoryCheckStore()
    first = await stored(store, await fall())
    [w] = await watch(store, steps(EditedFetcher(revised)), now=NOW, save=False)
    assert w.outcome is Outcome.UPDATED
    got = await store.get(first.id)
    assert got is not None and got.updated_by is None and got.watched_at is None
    assert len(store.checks) == 1


async def test_a_claim_that_cannot_be_computed_now_waits_for_a_later_run() -> None:
    store = InMemoryCheckStore()
    first = await stored(store, await fall())
    [w] = await watch(store, steps(DownFetcher()), now=NOW)
    assert w.outcome is Outcome.SKIPPED and "didn't answer just now" in w.detail
    got = await store.get(first.id)
    assert got is not None and got.watched_at is None  # first in line next time


async def test_a_claim_with_no_plan_is_kept_as_it_was_in_an_update() -> None:
    store = InMemoryCheckStore()
    claim = await fall()
    stopped = claim.model_copy(update={"index": 1, "plan": None, "operations": []})
    await stored(store, claim, stopped)
    [w] = await watch(store, steps(EditedFetcher(revised)), now=NOW)
    assert w.update_id is not None
    got = await store.get(w.update_id)
    assert got is not None and got.result is not None
    kept = CheckResult.model_validate(got.result).claims[1]
    assert kept == stopped


# --- the backfill ------------------------------------------------------------------------------


def planner(script: list[ChatResponse]) -> tuple[Pipeline, FakeClient]:
    client = FakeClient()
    client.script("fake", script)
    steps_ = {s: ["fake"] for s in ("extract", "match", "plan", "explain")}
    return Pipeline(
        router=Router(config(provider("fake"), steps=steps_), client, clock=FakeClock()),
        catalog=CATALOG,
        search=search,
        fetcher=RecordedFetcher(),
        tolerances=load_tolerances(),
        today=lambda: TODAY,
    ), client


SAME_PLAN = plan({"op": "change", "geo": "IT", "start": "2015", "end": "2023",
                  "kind": "percentage_points"})  # fmt: skip
OTHER_PLAN = plan({"op": "change", "geo": "IT", "start": "2016", "end": "2023",
                   "kind": "percentage_points"})  # fmt: skip


async def test_the_backfill_keeps_a_plan_that_gives_the_same_figures() -> None:
    store = InMemoryCheckStore()
    claim = await fall()
    first = await stored(store, claim.model_copy(update={"plan": None}))
    pipeline, client = planner([SAME_PLAN])
    [w] = await backfill(store, pipeline, now=NOW)
    assert (w.check_id, w.outcome, w.detail) == (first.id, Outcome.PLANNED, "")
    assert len(client.calls) == 1  # one plan call, nothing else
    got = await store.get(first.id)
    assert got is not None and got.result is not None
    [planned] = CheckResult.model_validate(got.result).claims
    assert planned.plan is not None and planned.plan.calls == claim.plan.calls  # type: ignore[union-attr]
    assert planned.operations == claim.operations and planned.explanation == claim.explanation
    # Now the watch can read it, and nothing is left to backfill.
    assert [c.id for c in await store.watchable(FIRST, 10, pipeline.versions())] == [first.id]
    assert await backfill(store, planner([])[0], now=NOW) == []


async def test_the_backfill_drops_a_plan_that_gives_other_figures() -> None:
    store = InMemoryCheckStore()
    first = await stored(store, (await fall()).model_copy(update={"plan": None}))
    [w] = await backfill(store, planner([OTHER_PLAN])[0], now=NOW)
    assert w.outcome is Outcome.SKIPPED and "other figures" in w.detail
    got = await store.get(first.id)
    assert got is not None and got.result is not None
    assert CheckResult.model_validate(got.result).claims[0].plan is None


async def test_the_backfill_stops_when_no_model_is_left() -> None:
    store = InMemoryCheckStore()
    for _ in range(2):
        await stored(store, (await fall()).model_copy(update={"plan": None}))
    rows = await backfill(store, planner([])[0], now=NOW)  # the fake has no reply left
    assert [w.outcome for w in rows] == [Outcome.SKIPPED]
    assert rows[0].detail.startswith("no model")


BAD_PLAN = plan({"op": "value_at", "geo": "XX", "period": "2023"})


async def test_the_backfill_leaves_claims_it_cannot_plan_and_says_why() -> None:
    store = InMemoryCheckStore()
    claim = await fall()
    unplanned = claim.model_copy(update={"index": 1, "plan": None})
    stopped = claim.model_copy(update={"index": 2, "plan": None, "verdict": cant_check("no data")})
    first = await stored(store, claim, unplanned, stopped)
    # Only claim 2 needs a plan; the model gets it wrong twice.
    [w] = await backfill(store, planner([BAD_PLAN, BAD_PLAN])[0], now=NOW)
    assert (w.check_id, w.outcome) == (first.id, Outcome.SKIPPED)
    assert w.detail.startswith("claim 2: ")
    got = await store.get(first.id)
    assert got is not None and got.result is not None
    assert [c.plan is None for c in CheckResult.model_validate(got.result).claims] == [
        False, True, True
    ]  # fmt: skip


async def test_planning_again_needs_a_statistic_in_today_s_catalog() -> None:
    claim = await fall()
    pipeline, client = planner([])
    unmatched = claim.model_copy(update={"indicator": None})
    with pytest.raises(ReplayError, match="no statistic matched"):
        await pipeline.plan_again(unmatched, TODAY)
    with pytest.raises(ReplayError, match="no statistic matched"):
        await pipeline.replay(unmatched, TODAY)
    assert claim.indicator is not None
    retired = claim.indicator.model_copy(update={"id": "retired_statistic"})
    with pytest.raises(ReplayError, match="no longer in the catalog"):
        await pipeline.plan_again(claim.model_copy(update={"indicator": retired}), TODAY)
    assert client.calls == []


def test_the_run_s_table_counts_each_outcome() -> None:
    a, b = uuid4(), uuid4()
    table = format_table([
        Watched(a, "Claim one.", Outcome.UNCHANGED),
        Watched(b, "Claim two.", Outcome.UPDATED, "claim 1: supported → not_supported"),
    ])  # fmt: skip
    assert table.splitlines()[-1] == "2 checks: 1 unchanged, 1 updated"
    assert str(b)[:8] in table and "Claim two." in table
    assert format_table([]) == "0 checks: nothing to compare"


def test_figure_changes_name_the_part_and_period() -> None:
    assert FigureChange(name="end value", period="2023", before=7.68, after=9.18).before == 7.68


async def test_the_site_drops_the_pages_of_checks_that_point_at_an_update() -> None:
    updated, unchanged, refused = uuid4(), uuid4(), uuid4()
    rows = [
        Watched(updated, "a", Outcome.UPDATED, "x", uuid4()),
        Watched(unchanged, "b", Outcome.UNCHANGED),
        Watched(refused, "c", Outcome.UPDATED, "y", uuid4()),
    ]
    seen: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(500 if str(refused) in str(request.url) else 204)

    pages = SitePages(httpx.AsyncClient(transport=httpx.MockTransport(answer)), "https://s.test")
    assert await tell_site(rows, pages) == [refused]
    assert seen == [
        f"https://s.test/api/checks/{updated}/refresh?gallery=1",
        f"https://s.test/api/checks/{refused}/refresh?gallery=1",
    ]
