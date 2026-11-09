"""Checks: submit text, follow the live trace, read the result; and the gallery."""

from collections.abc import AsyncIterator, Mapping
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field, StringConstraints

from holdsup.catalog.schema import Theme
from holdsup.config import get_settings
from holdsup.pipeline.claim import LATEST, AssertionType, Operator
from holdsup.pipeline.result import ClaimResult
from holdsup.problems import Problem, ProblemError, not_found
from holdsup.routes.deps import CatalogDep, Runner, Store
from holdsup.service.ratelimit import client_ip
from holdsup.service.store import CheckResult, CheckStatus
from holdsup.verdict import Label, Part

MAX_TEXT = 2_000  # characters, after trimming whitespace
GALLERY_MAX = 100  # the home page asks for a dozen; the recent-checks page for them all

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


class GalleryClaim(BaseModel):
    """One claim of a featured check, with the two numbers a card compares."""

    quote: str
    label: Label
    # The figure the claim states and what the official series gives for it; both null when the
    # claim has no single figure to compare (a trend, a rank) or was not checked.
    claimed: float | None = None
    official: float | None = None
    unit: str | None = None  # the unit both figures are in
    indicator: str | None = None  # the matched statistic's name
    source: str | None = None  # who publishes the series, as a source id ("eurostat")
    period: str | None = None  # the period the official figure is for
    geo: str | None = None  # the place the claim is about, as a code ("IT", "EU")
    theme: Theme | None = None  # the topic of the matched statistic, as the catalog lists it


class GalleryItem(BaseModel):
    id: UUID
    text: str
    created_at: datetime
    verdicts: list[Label]  # one per claim, in order
    indicators: list[str]  # the matched indicator names
    claims: list[GalleryClaim]  # one per claim, in order


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


def _gallery_period(c: ClaimResult, stated: str | None) -> str | None:
    """The year or window a card names: the period of the figure, else the claim's own window."""
    if stated:
        return stated
    start, end = c.claim.start, c.claim.end
    if end in (None, LATEST):
        return None
    return end if start in (None, end) else f"{start}–{end}"


def _gallery_figure(c: ClaimResult) -> tuple[Part, str | None] | None:
    """The one comparison a card can state, with the unit both numbers are in: the claim's main
    figure ("about 133%"), else the end value it states ("to 7.7%"). Bounds ("more than 5%"),
    trends and ranks have no such figure, and a figure whose unit is unknown is left out."""
    comparable = [
        p
        for p in c.verdict.parts
        if p.operator is Operator.ABOUT and p.asserted is not None and p.computed is not None
    ]
    series_unit = c.indicator.unit if c.indicator else None
    deciding = c.operations[c.answer[0]] if c.answer else None
    for name in ("assertion", "end value"):
        part = next((p for p in comparable if p.name == name), None)
        if part is None:
            continue
        if name == "end value" or deciding is None:
            return part, series_unit  # a stated level is in the series' own unit
        if deciding.unit:
            return part, deciding.unit
        if c.claim.assertion.type is AssertionType.RATIO:
            return part, "×"
    return None


def _gallery_claim(c: ClaimResult, themes: Mapping[str, Theme] | None = None) -> GalleryClaim:
    figure = _gallery_figure(c)
    part, unit = figure if figure else (None, None)
    return GalleryClaim(
        quote=c.claim.quote,
        label=c.verdict.label,
        claimed=part.asserted if part else None,
        official=part.computed if part else None,
        unit=unit,
        indicator=c.indicator.name if c.indicator else None,
        source=c.data.source if c.data else None,
        period=_gallery_period(c, part.period) if part else None,
        geo=c.claim.geo,
        theme=(themes or {}).get(c.indicator.id) if c.indicator else None,
    )


def _gallery_item(result: dict[str, Any], themes: Mapping[str, Theme]) -> GalleryItem:
    r = CheckResult.model_validate(result)
    return GalleryItem(
        id=r.id,
        text=r.text,
        created_at=r.created_at,
        verdicts=[c.verdict.label for c in r.claims],
        indicators=[c.indicator.name for c in r.claims if c.indicator],
        claims=[_gallery_claim(c, themes) for c in r.claims],
    )


@router.get("/gallery", response_model=GalleryResponse)
async def gallery(
    store: Store, catalog: CatalogDep, limit: Annotated[int, Query(ge=1, le=GALLERY_MAX)] = 12
) -> GalleryResponse:
    # A result stores the matched statistic's id but not its topic: the catalog knows it.
    themes = {i.id: i.theme for i in catalog.indicators}
    checks = await store.gallery(limit)
    return GalleryResponse(items=[_gallery_item(c.result, themes) for c in checks if c.result])
