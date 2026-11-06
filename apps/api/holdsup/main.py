"""FastAPI app factory. All routes live under /v1."""

from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from holdsup.config import get_settings
from holdsup.routes import indicators


class HealthResponse(BaseModel):
    status: Literal["ok"]


v1 = APIRouter(prefix="/v1")


@v1.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HoldsUp API", version="0.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(v1)
    app.include_router(indicators.router, prefix="/v1")
    return app


app = create_app()
