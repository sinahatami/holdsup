"""What the check store holds and the protocol every store meets.

The store is also the claim ledger's store: a finished check saved with a ledger entry (its
normalized text and embedding) can answer a later, identical claim. Checks that must not be
reused (a source was down) are saved without one; cached copies are never ledger entries
themselves, so a copy cannot keep an old result alive past the ledger's age limit.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from holdsup.pipeline.ledger import LedgerEntry, LedgerStore
from holdsup.pipeline.result import ClaimResult, Versions
from holdsup.pipeline.trace import ModelUse
from holdsup.problems import Problem


class CheckStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ReportKind(StrEnum):
    """What a reader says is wrong with a check."""

    WRONG_SERIES = "wrong_series"  # the statistic it was matched to is not what the claim is about
    WRONG_READING = "wrong_reading"  # the claim was read wrongly: its place, period or figure
    OTHER = "other"


@dataclass(frozen=True)
class StoredReport:
    """A reader's note that a check went wrong. It holds no one's identity: reports need no
    account, and the address that sent one is only counted in memory to limit abuse."""

    id: UUID
    check_id: UUID
    claim_index: int | None  # which claim (0-based); None = the check as a whole
    kind: ReportKind
    note: str  # free text from a stranger: shown only to maintainers, as text
    created_at: datetime


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

    async def add_report(self, report: StoredReport) -> None: ...

    async def reports(self, limit: int) -> list[StoredReport]:
        """The newest reports first."""
        ...

    async def finished_results(self) -> list[dict[str, Any]]:
        """The result (CheckResult as JSON) of every finished check that was computed, not copied
        from the ledger, so a claim asked again is not counted twice."""
        ...


async def add_entry(store: CheckStore, entry: LedgerEntry) -> None:
    """Save a ledger entry added directly (not through a run) as a finished check; the entry
    carries a full CheckResult."""
    result = CheckResult.model_validate(entry.result)
    await store.create(StoredCheck(result.id, result.text, CheckStatus.QUEUED, result.created_at))
    await store.finish(result, entry)
