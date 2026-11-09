"""Both check stores against the same expectations. The Postgres one runs only with
TEST_DATABASE_URL set (a `pgvector/pgvector` container migrated with `alembic upgrade head`)."""

import math
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
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
