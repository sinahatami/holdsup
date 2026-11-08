"""Checks: submit text, follow the live trace, read the result; and the gallery."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field, StringConstraints

from holdsup.config import get_settings
from holdsup.problems import Problem, ProblemError, not_found
from holdsup.routes.deps import Runner, Store
from holdsup.service.ratelimit import client_ip
from holdsup.service.store import CheckResult, CheckStatus
from holdsup.verdict import Label

MAX_TEXT = 2_000  # characters, after trimming whitespace
GALLERY_MAX = 24

router = APIRouter(tags=["checks"])

PROBLEM = {"model": Problem, "content": {"application/problem+json": {}}}


class CheckRequest(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXT)
    ] = Field(description="Text with one or more numeric claims.")


class CheckAccepted(BaseModel):
    id: UUID
    status: CheckStatus
    cached: bool = Field(description="True when an earlier check of the same claim answered it.")
    stream_url: str
    result_url: str


class CheckView(BaseModel):
    id: UUID
    text: str
    status: CheckStatus
    created_at: datetime
    finished_at: datetime | None
    result: CheckResult | None
    error: Problem | None


class GalleryItem(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    verdicts: list[Label]  # one per claim, in order
    indicators: list[str]  # the matched indicator names


class GalleryResponse(BaseModel):
    items: list[GalleryItem]


@router.post(
    "/checks",
    status_code=202,
    response_model=CheckAccepted,
    responses={422: PROBLEM, 429: PROBLEM},
)
async def submit_check(
    body: CheckRequest, request: Request, response: Response, runner: Runner
) -> CheckAccepted:
    submitted = await runner.submit(body.text, client_ip(request, get_settings().trusted_proxies))
    url = f"/v1/checks/{submitted.id}"
    response.headers["Location"] = url
    return CheckAccepted(
        id=submitted.id,
        status=submitted.status,
        cached=submitted.cached,
        stream_url=f"{url}/stream",
        result_url=url,
    )


async def _existing(check_id: UUID, runner: Runner) -> UUID:
    # A dependency, so a 404 is answered before the event stream starts.
    if not await runner.exists(check_id):
        raise ProblemError(not_found(f"No check {check_id}."))
    return check_id


def _after(last_event_id: str | None) -> int:
    try:
        return int(last_event_id) if last_event_id is not None else -1
    except ValueError:
        return -1


@router.get(
    "/checks/{check_id}/stream",
    response_class=EventSourceResponse,
    responses={404: PROBLEM},
    description="Server-Sent Events: `step_started` and `step_done` per pipeline step, then "
    "one `result` (a CheckResult) or `error` (a problem). Reconnects resume after "
    "Last-Event-ID.",
)
async def stream_check(
    check_id: Annotated[UUID, Depends(_existing)],
    runner: Runner,
    last_event_id: Annotated[str | None, Header()] = None,
) -> AsyncIterator[ServerSentEvent]:
    async for event in runner.events(check_id, _after(last_event_id)):
        yield ServerSentEvent(event=event.name, id=str(event.index), data=event.data)


@router.get("/checks/{check_id}", response_model=CheckView, responses={404: PROBLEM})
async def get_check(check_id: UUID, store: Store) -> CheckView:
    stored = await store.get(check_id)
    if stored is None:
        raise ProblemError(not_found(f"No check {check_id}."))
    return CheckView(
        id=stored.id,
        text=stored.text,
        status=stored.status,
        created_at=stored.created_at,
        finished_at=stored.finished_at,
        result=CheckResult.model_validate(stored.result) if stored.result else None,
        error=Problem.model_validate(stored.error) if stored.error else None,
    )


def _gallery_item(result: dict[str, Any]) -> GalleryItem:
    r = CheckResult.model_validate(result)
    return GalleryItem(
        id=r.id,
        text=r.text,
        created_at=r.created_at,
        verdicts=[c.verdict.label for c in r.claims],
        indicators=[c.indicator.name for c in r.claims if c.indicator],
    )


@router.get("/gallery", response_model=GalleryResponse)
async def gallery(
    store: Store, limit: Annotated[int, Query(ge=1, le=GALLERY_MAX)] = 12
) -> GalleryResponse:
    checks = await store.gallery(limit)
    return GalleryResponse(items=[_gallery_item(c.result) for c in checks if c.result])
