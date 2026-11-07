"""FastAPI app factory. All routes live under /v1."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from holdsup import problems
from holdsup.config import get_settings
from holdsup.logs import RequestIdMiddleware, configure_logging
from holdsup.routes import checks, indicators
from holdsup.service.wiring import Built


class HealthResponse(BaseModel):
    status: Literal["ok"]


v1 = APIRouter(prefix="/v1")


@v1.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    built: Built | None = getattr(app.state, "built", None)
    if built is not None:  # pragma: no cover (built only with Postgres + the model)
        await built.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="HoldsUp API", version="0.0.0", lifespan=lifespan)
    problems.install(app)
    # Only the web app's origin may call the API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID", "X-Request-ID"],
        expose_headers=["Location", "Retry-After", "X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(v1)
    app.include_router(indicators.router, prefix="/v1")
    app.include_router(checks.router, prefix="/v1")
    return app


app = create_app()
