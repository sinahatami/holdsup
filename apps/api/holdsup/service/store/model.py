"""What the check store holds and the protocol every store meets.

The store is also the claim ledger's store: a finished check saved with a ledger entry (its
normalized text and embedding) can answer a later, identical claim. Checks that must not be
reused (a source was down) are saved without one; cached copies are never ledger entries
themselves, so a copy cannot keep an old result alive past the ledger's age limit.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from holdsup.jsontypes import JsonObject
from holdsup.pipeline.ledger import LedgerEntry, LedgerStore
from holdsup.pipeline.result import ClaimResult, Suggestion, Versions
from holdsup.pipeline.trace import ModelUse
from holdsup.problems import Problem
from holdsup.verdict import Label


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


class RecheckOf(BaseModel):
    """The claim a re-check redid with a statistic a reader chose."""

    check_id: UUID
    claim_index: int
    replaced: Suggestion | None  # the statistic the first check used, if it matched one


class FigureChange(BaseModel):
    """A figure the verdict read, as computed then and now: both by code, never a model."""

    name: str = Field(description='The verdict part: "assertion", "start value", "end value".')
    period: str | None = None
    before: float | None = None
    after: float | None = None


class ClaimChange(BaseModel):
    """A claim whose figures were revised since the check this one updates."""

    index: int
    before: Label
    after: Label
    figures: list[FigureChange] = Field(
        default_factory=list,
        description="The verdict's figures that moved; empty when only a framing check's did.",
    )


class UpdateOf(BaseModel):
    """The check this one updates (S1): the same claims, plans and statistics, computed again
    by the claim watch on the sources' revised figures. No model was asked."""

    check_id: UUID
    created_at: datetime = Field(description="When the check this one updates was made.")
    checked_on: date = Field(
        description="The day the claims were first checked: every update reads the claims' "
        "dates and the data as of it."
    )
    changes: list[ClaimChange]


class PageSource(BaseModel):
    """The web page a check's text was taken from, when the reader sent a link."""

    url: str = Field(description="The page's address, after any redirects.")
    title: str | None = Field(default=None, description="The page's own title, as it gives it.")
    read_at: datetime = Field(description="When HoldsUp read the page.")
    used: int = Field(description="Passages with figures that the checked text holds.")
    found: int = Field(
        description="Passages with figures on the page; more than `used` when the page held "
        "more than one text can."
    )


class CheckResult(BaseModel):
    """A finished check: what `GET /v1/checks/{id}` returns and the ledger stores."""

    id: UUID
    text: str
    created_at: datetime
    finished_at: datetime
    cached_from: UUID | None = None  # the check this result was first computed for
    recheck_of: RecheckOf | None = None  # a re-check: never a ledger entry
    page: PageSource | None = None  # the text came from this page, not pasted
    update_of: UpdateOf | None = None  # computed again by the claim watch (S1)
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
    result: JsonObject | None = None  # CheckResult as JSON
    error: JsonObject | None = None  # Problem as JSON
    cached_from: UUID | None = None
    featured: bool = False
    watched_at: datetime | None = None  # the claim watch last compared its figures (S1)
    updated_by: UUID | None = None  # the newest check computed again from it


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

    async def finished_results(self) -> list[JsonObject]:
        """The result (CheckResult as JSON) of every finished check that was computed, not copied
        from the ledger nor since updated, so a claim asked again is not counted twice."""
        ...

    # The claim watch (S1)

    async def watchable(
        self,
        since: datetime,
        limit: int,
        versions: Mapping[str, object],
        *,
        planned: bool = True,
    ) -> list[StoredCheck]:
        """Finished checks the watch reads: computed here (not copies), not already updated,
        featured (or with a featured cached copy, as the gallery seed makes when it reuses a
        check) or made since `since`, and judged with `versions` (the catalog and tolerances,
        as the ledger requires). `planned`: with a claim it can replay; else with a matched,
        checked claim that has no stored plan (the backfill's). The ones compared longest ago
        (or never) first."""
        ...

    async def mark_watched(self, check_ids: Sequence[UUID], at: datetime) -> None: ...

    async def set_result(self, check_id: UUID, result: CheckResult) -> None:
        """Replace a finished check's stored result in place: only to add what it lacked (the
        backfill's plans), never to change a figure a reader has seen."""
        ...

    async def supersede(self, old_id: UUID, new: CheckResult) -> None:
        """Save `new`, the check `old_id` computed again on revised figures, and make it
        the one everything pointing at `old_id` now points at: the check itself, its cached
        copies and the checks it updated (`updated_by`), its ledger entry, so a repeated claim
        gets the revised result, and the gallery place any of them held: the update is
        featured when one of them was, and none of them stays featured."""
        ...


def is_planned(result: JsonObject) -> bool:
    """A claim of this result (CheckResult as JSON) has a stored plan to replay."""
    return any(c.get("plan") for c in _claims(result))


def needs_plan(result: JsonObject) -> bool:
    """A claim of this result was matched and checked before plans were stored."""
    return any(
        c.get("indicator") and not c.get("plan") and _label(c) != "cant_check"
        for c in _claims(result)
    )


def has_versions(result: JsonObject, versions: Mapping[str, object]) -> bool:
    stamped = result.get("versions")
    return isinstance(stamped, dict) and all(
        str(stamped.get(k)) == str(v) for k, v in versions.items()
    )


def _claims(result: JsonObject) -> list[JsonObject]:
    claims = result.get("claims")
    return [c for c in claims if isinstance(c, dict)] if isinstance(claims, list) else []


def _label(claim: JsonObject) -> object:
    verdict = claim.get("verdict")
    return verdict.get("label") if isinstance(verdict, dict) else None


async def add_entry(store: CheckStore, entry: LedgerEntry) -> None:
    """Save a ledger entry added directly (not through a run) as a finished check; the entry
    carries a full CheckResult."""
    result = CheckResult.model_validate(entry.result)
    await store.create(StoredCheck(result.id, result.text, CheckStatus.QUEUED, result.created_at))
    await store.finish(result, entry)
