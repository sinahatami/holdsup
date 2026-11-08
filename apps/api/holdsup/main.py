"""FastAPI app factory: settings, logging, error handling, CORS, and the /v1 routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from holdsup import problems
from holdsup.config import get_settings
from holdsup.logs import RequestIdMiddleware, configure_logging
from holdsup.routes import v1
from holdsup.service.wiring import Built


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
    return app


app = create_app()
