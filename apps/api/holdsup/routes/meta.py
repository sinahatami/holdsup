"""GET /v1/health: the API is up. GET /v1/tolerances: how far a claim may be from the data.
GET /v1/status: the model providers behind the checks, as the router sees them now."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from holdsup.router import ProviderStatus
from holdsup.routes.deps import Runner, TolerancesDep
from holdsup.verdict import Tolerances

router = APIRouter(tags=["meta"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/tolerances", response_model=Tolerances)
async def tolerances(current: TolerancesDep) -> Tolerances:
    """What every verdict is judged by, as one version: the methodology page prints it, so
    the page cannot drift from the rules the checks used."""
    return current


class StatusResponse(BaseModel):
    checked_at: datetime
    providers: list[ProviderStatus]


@router.get("/status", response_model=StatusResponse)
async def status(runner: Runner, response: Response) -> StatusResponse:
    """Each live model provider: ready, cooling down, failing or out of today's budget, and
    the requests it has left today. Never cached: it is the state at this moment."""
    response.headers["Cache-Control"] = "no-store"
    return StatusResponse(
        checked_at=datetime.now(UTC), providers=await runner.pipeline.router.status()
    )
