"""Where checks live: in memory (tests, local runs) or in Postgres (`checks`, `claims`,
`operations`).

The store is also the claim ledger's store: a finished check saved with a ledger entry (its
normalized text and embedding) can answer a later, identical claim. Checks that must not be
reused (a source was down) are saved without one; cached copies are never ledger entries
themselves, so a copy cannot keep an old result alive past the ledger's age limit.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.db.models import Check, ClaimRow, OperationRow
from holdsup.pipeline.ledger import LedgerEntry, LedgerStore
from holdsup.pipeline.run import ClaimResult, ModelUse, Versions
from holdsup.problems import Problem


class CheckStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class CheckResult(BaseModel):
    """A finished check: what `GET /v1/checks/{id}` returns and the ledger stores."""

    id: UUID
    text: str
    created_at: datetime
    finished_at: datetime
    cached_from: UUID | None = None  # the check this result was first computed for
    claims: list[ClaimResult]
    versions: Versions
    models: list[ModelUse]  # check-wide model calls; each claim lists its own
    notes: list[str] = Field(default_factory=list)

    def providers(self) -> list[str]:
        uses = [*self.models, *(m for c in self.claims for m in c.models)]
        return sorted({m.provider for m in uses})


@dataclass(frozen=True)
class StoredCheck:
    id: UUID
    text: str
    status: CheckStatus
    created_at: datetime
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None  # CheckResult as JSON
    error: dict[str, Any] | None = None  # Problem as JSON
    cached_from: UUID | None = None
    featured: bool = False


class CheckStore(LedgerStore, Protocol):
    async def create(self, check: StoredCheck) -> None: ...

    async def mark_running(self, check_id: UUID) -> None: ...

    async def finish(self, result: CheckResult, ledger: LedgerEntry | None) -> None: ...

    async def fail(self, check_id: UUID, error: Problem, at: datetime) -> None: ...

    async def get(self, check_id: UUID) -> StoredCheck | None: ...

    async def gallery(self, limit: int) -> list[StoredCheck]: ...

    async def set_featured(self, check_id: UUID, featured: bool) -> None: ...


def _from_entry(entry: LedgerEntry) -> CheckResult:
    """A ledger entry added directly (not through a run) carries a full CheckResult."""
    return CheckResult.model_validate(entry.result)


# --- in memory -------------------------------------------------------------------------------


@dataclass
class InMemoryCheckStore:
    checks: dict[UUID, StoredCheck] = field(default_factory=dict)
    ledger: dict[UUID, LedgerEntry] = field(default_factory=dict)

    async def create(self, check: StoredCheck) -> None:
        self.checks[check.id] = check

    async def mark_running(self, check_id: UUID) -> None:
        self.checks[check_id] = replace(self.checks[check_id], status=CheckStatus.RUNNING)

    async def finish(self, result: CheckResult, ledger: LedgerEntry | None) -> None:
        self.checks[result.id] = replace(
            self.checks[result.id],
            status=CheckStatus.DONE,
            finished_at=result.finished_at,
            result=result.model_dump(mode="json"),
        )
        if ledger is not None:
            # Dated like the Postgres store: by when the check started (≈ when data was fetched).
            self.ledger[result.id] = replace(ledger, created_at=result.created_at)

    async def fail(self, check_id: UUID, error: Problem, at: datetime) -> None:
        self.checks[check_id] = replace(
            self.checks[check_id],
            status=CheckStatus.FAILED,
            finished_at=at,
            error=error.model_dump(mode="json", exclude_none=True),
        )

    async def get(self, check_id: UUID) -> StoredCheck | None:
        return self.checks.get(check_id)

    async def gallery(self, limit: int) -> list[StoredCheck]:
        featured = [c for c in self.checks.values() if c.featured and c.status is CheckStatus.DONE]
        return sorted(featured, key=lambda c: c.created_at, reverse=True)[:limit]

    async def set_featured(self, check_id: UUID, featured: bool) -> None:
        self.checks[check_id] = replace(self.checks[check_id], featured=featured)

    # LedgerStore
    def _fresh(self, since: datetime) -> list[LedgerEntry]:
        return [e for e in self.ledger.values() if e.created_at >= since]

    async def exact(self, normalized: str, since: datetime) -> LedgerEntry | None:
        same = [e for e in self._fresh(since) if e.normalized == normalized]
        return max(same, key=lambda e: e.created_at, default=None)

    async def nearest(
        self, embedding: list[float], since: datetime, k: int
    ) -> list[tuple[LedgerEntry, float]]:
        scored = [
            (e, sum(a * b for a, b in zip(e.embedding, embedding, strict=True)))
            for e in self._fresh(since)
        ]
        return sorted(scored, key=lambda es: es[1], reverse=True)[:k]

    async def add(self, entry: LedgerEntry) -> None:
        result = _from_entry(entry)
        await self.create(
            StoredCheck(result.id, result.text, CheckStatus.QUEUED, result.created_at)
        )
        await self.finish(result, entry)


# --- Postgres --------------------------------------------------------------------------------


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
        result = _from_entry(entry)
        await self.create(
            StoredCheck(result.id, result.text, CheckStatus.QUEUED, result.created_at)
        )
        await self.finish(result, entry)
