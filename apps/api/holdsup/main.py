"""FastAPI app factory: settings, logging, error handling, CORS, and the /v1 routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from holdsup import problems
from holdsup.config import get_settings, production_problems
from holdsup.logs import RequestIdMiddleware, configure_logging
from holdsup.pipeline.result import app_version
from holdsup.routes import v1
from holdsup.service.wiring import Built
from holdsup.telegram.bot import TelegramBot


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    telegram: TelegramBot | None = getattr(app.state, "telegram", None)
    if telegram is not None:  # pragma: no cover (built only with a bot token)
        await telegram.client.http.aclose()
    built: Built | None = getattr(app.state, "built", None)
    if built is not None:  # pragma: no cover (built only with Postgres + the model)
        await built.close()


def create_app() -> FastAPI:
    settings = get_settings()
    if problems_found := production_problems(settings):
        raise RuntimeError("Refusing to start in production:\n- " + "\n- ".join(problems_found))
    configure_logging(settings.log_level)
    app = FastAPI(title="HoldsUp API", version=app_version(), lifespan=lifespan)
    problems.install(app)
    # JSON compresses to about a seventh (the catalog: 56 KB). The event stream is left alone
    # (Starlette excludes text/event-stream), so each step still goes out as it happens.
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)
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
