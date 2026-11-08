"""The check store in memory: tests and local runs."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from holdsup.pipeline.ledger import LedgerEntry
from holdsup.problems import Problem
from holdsup.service.store.model import CheckResult, CheckStatus, StoredCheck, add_entry


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

    async def finished_results(self) -> list[dict[str, Any]]:
        return [
            c.result
            for c in self.checks.values()
            if c.status is CheckStatus.DONE and c.cached_from is None and c.result is not None
        ]

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
        await add_entry(self, entry)
