"""Both check stores against the same expectations. The Postgres one runs only with
TEST_DATABASE_URL set (a `pgvector/pgvector` container migrated with `alembic upgrade head`)."""

import math
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from holdsup.db.models import Check, ClaimRow, OperationRow
from holdsup.db.url import to_async_url
from holdsup.pipeline.ledger import Ledger, LedgerEntry
from holdsup.problems import at_capacity
from holdsup.service.store import (
    CheckResult,
    CheckStatus,
    CheckStore,
    InMemoryCheckStore,
    ReportKind,
    SqlCheckStore,
    StoredCheck,
    StoredReport,
)
from tests.service.fakes import EMBEDDER, TEXT, happy_script, make_pipeline

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
T0 = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


async def a_result(check_id: object, created: datetime = T0) -> CheckResult:
    pipeline, _, _ = make_pipeline(happy_script())

    async def emit(event: object) -> None:
        pass

    out = await pipeline.run(TEXT, emit)
    return CheckResult(
        id=check_id, text=TEXT, created_at=created, finished_at=created + timedelta(seconds=9),
        claims=out.claims, versions=out.versions, models=out.models,
    )  # fmt: skip


@pytest.fixture(params=["memory", "postgres"])
async def store(request: pytest.FixtureRequest) -> AsyncIterator[CheckStore]:
    if request.param == "memory":
        yield InMemoryCheckStore()
        return
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    engine = create_async_engine(to_async_url(TEST_DATABASE_URL))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def clear() -> None:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(Check))

    await clear()
    try:
        yield SqlCheckStore(sessionmaker)
    finally:
        await clear()
        await engine.dispose()


async def test_lifecycle(store: CheckStore) -> None:
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
    got = await store.get(check_id)
    assert got is not None and got.status is CheckStatus.QUEUED and got.result is None
    await store.mark_running(check_id)
    assert (await store.get(check_id)).status is CheckStatus.RUNNING  # type: ignore[union-attr]

    result = await a_result(check_id)
    await store.finish(result, None)
    got = await store.get(check_id)
    assert got is not None and got.status is CheckStatus.DONE
    assert got.finished_at == result.finished_at
    assert CheckResult.model_validate(got.result) == result
    assert await store.get(uuid4()) is None


async def test_fail(store: CheckStore) -> None:
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
    await store.fail(check_id, at_capacity(120), T0)
    got = await store.get(check_id)
    assert got is not None and got.status is CheckStatus.FAILED
    assert got.error is not None and got.error["retry_after"] == 120 and "errors" not in got.error


async def test_gallery_is_featured_finished_checks_newest_first(store: CheckStore) -> None:
    ids = [uuid4() for _ in range(4)]
    for i, check_id in enumerate(ids):
        created = T0 + timedelta(minutes=i)
        await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, created))
        if i < 3:
            await store.finish(await a_result(check_id, created), None)
        await store.set_featured(check_id, i != 1)
    # 0 and 2 are featured and done; 3 is featured but unfinished; 1 is not featured.
    assert [c.id for c in await store.gallery(10)] == [ids[2], ids[0]]
    assert [c.id for c in await store.gallery(1)] == [ids[2]]


async def test_ledger_reads_reusable_original_checks(store: CheckStore) -> None:
    ledger = Ledger(store, EMBEDDER, now=lambda: T0 + timedelta(hours=1))
    original, copy = uuid4(), uuid4()
    await store.create(StoredCheck(original, TEXT, CheckStatus.QUEUED, T0))
    result = await a_result(original)
    entry = await ledger.entry(TEXT, result.model_dump(mode="json"))
    await store.finish(result, entry)
    # A cached copy is stored done, but never becomes a ledger entry itself.
    await store.create(
        StoredCheck(copy, TEXT, CheckStatus.DONE, T0 + timedelta(minutes=5),
                    result=result.model_dump(mode="json"), cached_from=original)
    )  # fmt: skip

    hit = await ledger.lookup(TEXT.upper())
    assert hit is not None and hit.similarity == 1.0
    assert CheckResult.model_validate(hit.entry.result).id == original

    nearest = await store.nearest(entry.embedding, T0 - timedelta(days=1), k=5)
    assert len(nearest) == 1 and math.isclose(nearest[0][1], 1.0, abs_tol=1e-6)
    assert await store.exact(entry.normalized, T0 + timedelta(seconds=1)) is None  # too old
    assert await store.nearest(entry.embedding, T0 + timedelta(seconds=1), k=5) == []


async def test_a_result_saved_without_an_entry_is_not_reusable(store: CheckStore) -> None:
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
    await store.finish(await a_result(check_id), None)
    ledger = Ledger(store, EMBEDDER, now=lambda: T0)
    assert await ledger.lookup(TEXT) is None


async def test_add_stores_a_finished_check_from_an_entry(store: CheckStore) -> None:
    check_id = uuid4()
    result = await a_result(check_id)
    ledger = Ledger(store, EMBEDDER, now=lambda: T0)
    await ledger.remember(TEXT, result.model_dump(mode="json"))
    got = await store.get(check_id)
    assert got is not None and got.status is CheckStatus.DONE
    hit = await ledger.lookup(TEXT)
    assert hit is not None and CheckResult.model_validate(hit.entry.result).id == check_id


async def test_finished_results_are_the_computed_ones(store: CheckStore) -> None:
    """Unfinished checks and cached copies are left out, so a claim asked twice counts once."""
    done, unfinished, copy = uuid4(), uuid4(), uuid4()
    result = await a_result(done)
    await store.create(StoredCheck(done, TEXT, CheckStatus.QUEUED, T0))
    await store.finish(result, None)
    await store.create(StoredCheck(unfinished, TEXT, CheckStatus.QUEUED, T0))
    await store.create(
        StoredCheck(copy, TEXT, CheckStatus.DONE, T0, result=result.model_dump(mode="json"),
                    cached_from=done)
    )  # fmt: skip
    got = await store.finished_results()
    assert [CheckResult.model_validate(r).id for r in got] == [done]


async def test_reports_are_kept_newest_first(store: CheckStore) -> None:
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
    assert await store.reports(10) == []
    older = StoredReport(uuid4(), check_id, 0, ReportKind.WRONG_SERIES, "wrong series", T0)
    newer = StoredReport(uuid4(), check_id, None, ReportKind.OTHER, "", T0 + timedelta(minutes=5))
    await store.add_report(older)
    await store.add_report(newer)
    assert await store.reports(10) == [newer, older]
    assert await store.reports(1) == [newer]


# --- the claim watch (S1) --------------------------------------------------------------------


VERSIONS = make_pipeline(happy_script())[0].versions()


async def finished(store: CheckStore, created: datetime, *, featured: bool = False) -> UUID:
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, created))
    await store.finish(await a_result(check_id, created), None)
    if featured:
        await store.set_featured(check_id, True)
    return check_id


async def test_the_watch_reads_recent_and_featured_computed_checks(store: CheckStore) -> None:
    since = T0 - timedelta(days=90)
    recent = await finished(store, T0)
    older = await finished(store, T0 - timedelta(days=1))
    old_featured = await finished(store, T0 - timedelta(days=200), featured=True)
    await finished(store, T0 - timedelta(days=200))  # too old, not featured
    unfinished, copy = uuid4(), uuid4()
    await store.create(StoredCheck(unfinished, TEXT, CheckStatus.QUEUED, T0))
    await store.create(
        StoredCheck(copy, TEXT, CheckStatus.DONE, T0, result={"x": 1}, cached_from=recent)
    )
    # Never compared first, oldest first; then the ones compared longest ago.
    assert [c.id for c in await store.watchable(since, 10, VERSIONS)] == [
        old_featured,
        older,
        recent,
    ]
    await store.mark_watched([old_featured], T0 + timedelta(hours=1))
    await store.mark_watched([older], T0 + timedelta(hours=2))
    assert [c.id for c in await store.watchable(since, 10, VERSIONS)] == [
        recent,
        old_featured,
        older,
    ]
    assert [c.id for c in await store.watchable(since, 1, VERSIONS)] == [recent]
    got = await store.get(older)
    assert got is not None and got.watched_at == T0 + timedelta(hours=2)
    await store.mark_watched([], T0)  # nothing to do


async def test_the_watch_reads_only_checks_it_can_replay_with_today_s_rules(
    store: CheckStore,
) -> None:
    planned = await finished(store, T0)
    result = (await a_result(uuid4())).model_dump(mode="json")
    unplanned, older_rules, unmatched = uuid4(), uuid4(), uuid4()
    no_plan = {**result, "claims": [{**c, "plan": None} for c in result["claims"]]}
    old_rules = {**result, "versions": {**result["versions"], "tolerances": 1}}
    nothing = {**no_plan, "claims": [{**c, "indicator": None} for c in no_plan["claims"]]}
    for check_id, doc in ((unplanned, no_plan), (older_rules, old_rules), (unmatched, nothing)):
        await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
        await store.finish(CheckResult.model_validate({**doc, "id": str(check_id)}), None)
    assert [c.id for c in await store.watchable(T0, 10, VERSIONS)] == [planned]
    # The backfill's: matched and checked, but no stored plan (from before S1).
    assert [c.id for c in await store.watchable(T0, 10, VERSIONS, planned=False)] == [unplanned]


async def test_an_update_takes_the_old_check_s_place(store: CheckStore) -> None:
    ledger = Ledger(store, EMBEDDER, now=lambda: T0 + timedelta(days=30))
    old = uuid4()
    await store.create(StoredCheck(old, TEXT, CheckStatus.QUEUED, T0))
    first = await a_result(old)
    await store.finish(first, await ledger.entry(TEXT, first.model_dump(mode="json")))
    await store.set_featured(old, True)
    earlier, copy = await finished(store, T0 - timedelta(days=5)), uuid4()
    await store.create(
        StoredCheck(copy, TEXT, CheckStatus.DONE, T0, result=first.model_dump(mode="json"),
                    cached_from=old)
    )  # fmt: skip
    # Pretend `old` was itself the update of an earlier check, which points at it.
    if isinstance(store, InMemoryCheckStore):
        store.checks[earlier] = replace(store.checks[earlier], updated_by=old)
    else:
        assert isinstance(store, SqlCheckStore)
        async with store._sessionmaker() as s, s.begin():  # the store has no setter for this
            await s.execute(sa_update(Check).where(Check.id == earlier).values(updated_by=old))

    later = T0 + timedelta(days=30)
    new = await a_result(uuid4(), later)
    await store.supersede(old, new)

    got = await store.get(new.id)
    assert got is not None and got.status is CheckStatus.DONE and got.featured
    assert got.text == TEXT and got.watched_at == new.finished_at and got.updated_by is None
    for pointing in (old, copy, earlier):
        c = await store.get(pointing)
        assert c is not None and c.updated_by == new.id, pointing
    assert [c.id for c in await store.gallery(10)] == [new.id]
    # The ledger answers a repeated claim with the update, and only with it.
    hit = await ledger.lookup(TEXT)
    assert hit is not None and CheckResult.model_validate(hit.entry.result).id == new.id
    assert [CheckResult.model_validate(r).id for r in await store.finished_results()] == [new.id]
    assert [c.id for c in await store.watchable(T0, 10, VERSIONS)] == [new.id]


async def test_set_result_replaces_the_stored_result(store: CheckStore) -> None:
    ledger = Ledger(store, EMBEDDER, now=lambda: T0)
    check_id = uuid4()
    await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
    result = await a_result(check_id)
    await store.finish(result, await ledger.entry(TEXT, result.model_dump(mode="json")))
    noted = result.model_copy(update={"notes": ["a plan was added"]})
    await store.set_result(check_id, noted)
    got = await store.get(check_id)
    assert got is not None and got.result is not None
    assert CheckResult.model_validate(got.result).notes == ["a plan was added"]
    # The ledger answers with the result as it is now.
    hit = await ledger.lookup(TEXT)
    assert hit is not None
    assert CheckResult.model_validate(hit.entry.result).notes == ["a plan was added"]


async def test_an_unknown_check_cannot_be_superseded(store: CheckStore) -> None:
    with pytest.raises(KeyError):
        await store.supersede(uuid4(), await a_result(uuid4()))


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")
async def test_postgres_rows_for_claims_and_operations() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(to_async_url(TEST_DATABASE_URL))
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    store = SqlCheckStore(sessionmaker)
    check_id = uuid4()
    try:
        await store.create(StoredCheck(check_id, TEXT, CheckStatus.QUEUED, T0))
        result = await a_result(check_id)
        entry = LedgerEntry("x", EMBEDDER.embed(["x"])[0], {}, T0)
        await store.finish(result, entry)
        async with sessionmaker() as s:
            check = await s.get(Check, check_id)
            claims = (await s.scalars(select(ClaimRow).where(ClaimRow.check_id == check_id))).all()
            ops = (
                await s.scalars(select(OperationRow).where(OperationRow.claim_id == claims[0].id))
            ).all()
        assert check is not None and check.providers == ["fake"]
        assert check.normalized_text == "x" and check.input_embedding is not None
        assert [(c.position, c.indicator_id, c.verdict) for c in claims] == [
            (0, "unemployment_rate", "supported")
        ]
        assert claims[0].spec["geo"] == "IT" and claims[0].explanation
        assert [(o.position, o.name) for o in ops] == [(0, "change")]
        assert ops[0].inputs["args"]["kind"] == "percentage_points"
        assert [p["period"] for p in ops[0].inputs["points"]] == ["2015", "2023"]
        assert math.isclose(ops[0].output["value"], -4.2)
        assert set(ops[0].output) == {"value", "extras", "series", "unit", "flags"}
        # Deleting a check removes its claims and operations.
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(Check).where(Check.id == check_id))
        async with sessionmaker() as s:
            assert (
                await s.scalars(select(ClaimRow).where(ClaimRow.check_id == check_id))
            ).all() == []
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(delete(Check).where(Check.id == check_id))
        await engine.dispose()
