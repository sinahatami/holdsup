"""The check store in memory: tests and local runs."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID

from holdsup.jsontypes import JsonObject
from holdsup.pipeline.ledger import LedgerEntry
from holdsup.problems import Problem
from holdsup.service.store.model import (
    CheckResult,
    CheckStatus,
    StoredCheck,
    StoredReport,
    add_entry,
    has_versions,
    is_planned,
    needs_plan,
)


@dataclass
class InMemoryCheckStore:
    checks: dict[UUID, StoredCheck] = field(default_factory=dict)
    ledger: dict[UUID, LedgerEntry] = field(default_factory=dict)
    saved_reports: list[StoredReport] = field(default_factory=list)

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

    async def add_report(self, report: StoredReport) -> None:
        self.saved_reports.append(report)

    async def reports(self, limit: int) -> list[StoredReport]:
        return sorted(self.saved_reports, key=lambda r: r.created_at, reverse=True)[:limit]

    async def finished_results(self) -> list[JsonObject]:
        return [
            c.result
            for c in self.checks.values()
            if c.status is CheckStatus.DONE
            and c.cached_from is None
            and c.updated_by is None
            and c.result is not None
        ]

    # The claim watch (S1)
    async def watchable(
        self,
        since: datetime,
        limit: int,
        versions: Mapping[str, object],
        *,
        planned: bool = True,
    ) -> list[StoredCheck]:
        wanted = is_planned if planned else needs_plan
        featured_copies = {c.cached_from for c in self.checks.values() if c.featured}
        found = [
            c
            for c in self.checks.values()
            if c.status is CheckStatus.DONE
            and c.result is not None
            and c.cached_from is None
            and c.updated_by is None
            and (c.featured or c.id in featured_copies or c.created_at >= since)
            and has_versions(c.result, versions)
            and wanted(c.result)
        ]
        found.sort(
            key=lambda c: (c.watched_at is not None, c.watched_at or c.created_at, c.created_at)
        )
        return found[:limit]

    async def mark_watched(self, check_ids: Sequence[UUID], at: datetime) -> None:
        for check_id in check_ids:
            self.checks[check_id] = replace(self.checks[check_id], watched_at=at)

    async def set_result(self, check_id: UUID, result: CheckResult) -> None:
        self.checks[check_id] = replace(
            self.checks[check_id], result=result.model_dump(mode="json")
        )
        if (entry := self.ledger.get(check_id)) is not None:
            self.ledger[check_id] = replace(entry, result=result.model_dump(mode="json"))

    async def supersede(self, old_id: UUID, new: CheckResult) -> None:
        old = self.checks[old_id]
        pointing = [
            check_id
            for check_id, c in self.checks.items()
            if old_id in (check_id, c.cached_from, c.updated_by)
        ]
        featured = any(self.checks[check_id].featured for check_id in pointing)
        self.checks[new.id] = StoredCheck(
            id=new.id,
            text=old.text,
            status=CheckStatus.DONE,
            created_at=new.created_at,
            finished_at=new.finished_at,
            result=new.model_dump(mode="json"),
            featured=featured,
            watched_at=new.finished_at,
        )
        for check_id in pointing:
            self.checks[check_id] = replace(
                self.checks[check_id], updated_by=new.id, featured=False
            )
        if (entry := self.ledger.pop(old_id, None)) is not None:
            self.ledger[new.id] = replace(
                entry, result=new.model_dump(mode="json"), created_at=new.created_at
            )

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
