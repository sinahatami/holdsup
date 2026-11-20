"""GET /v1/health: the API is up. GET /v1/tolerances: how far a claim may be from the data."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from holdsup.routes.deps import TolerancesDep
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
