"""Reports: a reader says a check matched the wrong statistic or read the claim wrongly."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, StringConstraints

from holdsup.config import get_settings
from holdsup.problems import Problem, ProblemError, not_found, reports_limited, unknown_claim
from holdsup.routes.deps import ReportLimiter, Store
from holdsup.service.ratelimit import client_ip
from holdsup.service.store import ReportKind, StoredReport

MAX_NOTE = 500  # characters, after trimming whitespace

router = APIRouter(tags=["reports"])

PROBLEM = {"model": Problem, "content": {"application/problem+json": {}}}


class ReportRequest(BaseModel):
    kind: ReportKind
    claim_index: int | None = Field(
        default=None,
        ge=0,
        description="Which claim of the check the report is about, counting from 0; "
        "null for the check as a whole.",
    )
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_NOTE)] = Field(
        default="", description="What looks wrong, in the reader's words (optional)."
    )


class ReportAccepted(BaseModel):
    id: UUID


@router.post(
    "/checks/{check_id}/reports",
    status_code=201,
    response_model=ReportAccepted,
    responses={404: PROBLEM, 422: PROBLEM, 429: PROBLEM},
)
async def report_check(
    check_id: UUID,
    body: ReportRequest,
    request: Request,
    store: Store,
    limiter: ReportLimiter,
) -> ReportAccepted:
    """Record that a check went wrong. No account is needed; the sender's address is only
    counted in memory, to limit how many reports it can send in an hour."""
    wait = limiter.hit(client_ip(request, get_settings().trusted_proxies))
    if wait is not None:
        raise ProblemError(reports_limited(wait))
    stored = await store.get(check_id)
    if stored is None:
        raise ProblemError(not_found(f"No check {check_id}."))
    claims = stored.result["claims"] if stored.result else []
    if body.claim_index is not None and body.claim_index >= len(claims):
        raise ProblemError(unknown_claim(body.claim_index))
    report = StoredReport(
        id=uuid4(),
        check_id=check_id,
        claim_index=body.claim_index,
        kind=body.kind,
        note=body.note,
        created_at=datetime.now(UTC),
    )
    await store.add_report(report)
    return ReportAccepted(id=report.id)
