"""The check store in Postgres: `checks`, `claims` and `operations`."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.db.models import Check, ClaimRow, OperationRow
from holdsup.pipeline.ledger import LedgerEntry
from holdsup.problems import Problem
from holdsup.service.store.model import CheckResult, CheckStatus, StoredCheck, add_entry


def _stored(row: Check) -> StoredCheck:
    return StoredCheck(
        id=row.id,
        text=row.input_text,
        status=CheckStatus(row.status),
        created_at=row.created_at,
        finished_at=row.finished_at,
        result=row.result,
        error=row.error,
        cached_from=row.cached_from,
        featured=row.featured,
    )


def _entry(row: Check) -> LedgerEntry:
    # Only rows selected by _LEDGER_ROWS reach here: both columns are set.
    assert row.normalized_text is not None  # noqa: S101
    assert row.input_embedding is not None and row.result is not None  # noqa: S101
    return LedgerEntry(
        normalized=row.normalized_text,
        embedding=[float(x) for x in row.input_embedding],
        result=row.result,
        created_at=row.created_at,
    )


OUTPUT_FIELDS = {"value", "extras", "series", "unit", "flags"}


def _claim_rows(result: CheckResult) -> Sequence[tuple[ClaimRow, list[OperationRow]]]:
    out = []
    for c in result.claims:
        claim = ClaimRow(
            check_id=result.id,
            position=c.index,
            spec=c.claim.model_dump(mode="json"),
            indicator_id=c.indicator.id if c.indicator else None,
            verdict=str(c.verdict.label),
            explanation=c.explanation,
        )
        ops = [
            OperationRow(
                position=i,
                name=r.op,
                inputs={
                    "args": r.args,
                    "points": [p.model_dump(mode="json") for p in r.inputs],
                },
                output=r.model_dump(mode="json", include=OUTPUT_FIELDS),
            )
            for i, r in enumerate(c.operations)
        ]
        out.append((claim, ops))
    return out


class SqlCheckStore:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def create(self, check: StoredCheck) -> None:
        async with self._sessionmaker() as session, session.begin():
            session.add(
                Check(
                    id=check.id,
                    input_text=check.text,
                    status=str(check.status),
                    created_at=check.created_at,
                    finished_at=check.finished_at,
                    providers=[],
                    result=check.result,
                    error=check.error,
                    cached_from=check.cached_from,
                    featured=check.featured,
                )
            )

    async def mark_running(self, check_id: UUID) -> None:
        async with self._sessionmaker() as session, session.begin():
            await session.execute(
                update(Check).where(Check.id == check_id).values(status=str(CheckStatus.RUNNING))
            )

    async def finish(self, result: CheckResult, ledger: LedgerEntry | None) -> None:
        values: dict[str, Any] = {
            "status": str(CheckStatus.DONE),
            "finished_at": result.finished_at,
            "providers": result.providers(),
            "result": result.model_dump(mode="json"),
        }
        if ledger is not None:
            values |= {"normalized_text": ledger.normalized, "input_embedding": ledger.embedding}
        async with self._sessionmaker() as session, session.begin():
            await session.execute(update(Check).where(Check.id == result.id).values(**values))
            for claim, ops in _claim_rows(result):
                session.add(claim)
                await session.flush()  # claim.id for its operations
                for op in ops:
                    op.claim_id = claim.id
                session.add_all(ops)

    async def fail(self, check_id: UUID, error: Problem, at: datetime) -> None:
        async with self._sessionmaker() as session, session.begin():
            await session.execute(
                update(Check)
                .where(Check.id == check_id)
                .values(
                    status=str(CheckStatus.FAILED),
                    finished_at=at,
                    error=error.model_dump(mode="json", exclude_none=True),
                )
            )

    async def get(self, check_id: UUID) -> StoredCheck | None:
        async with self._sessionmaker() as session:
            row = await session.get(Check, check_id)
        return None if row is None else _stored(row)

    async def gallery(self, limit: int) -> list[StoredCheck]:
        stmt = (
            select(Check)
            .where(Check.featured.is_(True), Check.status == str(CheckStatus.DONE))
            .order_by(Check.created_at.desc())
            .limit(limit)
        )
        async with self._sessionmaker() as session:
            rows = (await session.scalars(stmt)).all()
        return [_stored(r) for r in rows]

    async def set_featured(self, check_id: UUID, featured: bool) -> None:
        async with self._sessionmaker() as session, session.begin():
            await session.execute(
                update(Check).where(Check.id == check_id).values(featured=featured)
            )

    async def finished_results(self) -> list[dict[str, Any]]:
        stmt = select(Check.result).where(
            Check.status == str(CheckStatus.DONE),
            Check.cached_from.is_(None),
            Check.result.is_not(None),
        )
        async with self._sessionmaker() as session:
            return [r for r in (await session.scalars(stmt)).all() if r is not None]

    # LedgerStore: finished, reusable, original checks.
    @staticmethod
    def _ledger_rows(since: datetime) -> Any:  # Any: a Select over Check
        return select(Check).where(
            Check.status == str(CheckStatus.DONE),
            Check.cached_from.is_(None),
            Check.normalized_text.is_not(None),
            Check.input_embedding.is_not(None),
            Check.created_at >= since,
        )

    async def exact(self, normalized: str, since: datetime) -> LedgerEntry | None:
        stmt = (
            self._ledger_rows(since)
            .where(Check.normalized_text == normalized)
            .order_by(Check.created_at.desc())
            .limit(1)
        )
        async with self._sessionmaker() as session:
            row = await session.scalar(stmt)
        return None if row is None else _entry(row)

    async def nearest(
        self, embedding: list[float], since: datetime, k: int
    ) -> list[tuple[LedgerEntry, float]]:
        distance = Check.input_embedding.cosine_distance(embedding)
        stmt = self._ledger_rows(since).add_columns(distance).order_by(distance).limit(k)
        async with self._sessionmaker() as session:
            rows = (await session.execute(stmt)).all()
        return [(_entry(row), 1.0 - float(d)) for row, d in rows]

    async def add(self, entry: LedgerEntry) -> None:
        await add_entry(self, entry)
