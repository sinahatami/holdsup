"""Errors as RFC 9457 problem details (`application/problem+json`).

Problem types are relative URI references under /problems/ (allowed by RFC 9457 §3.1.1);
`about:blank` is used for plain HTTP errors whose status code says it all.
"""

import math
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

MEDIA_TYPE = "application/problem+json"


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    # Extension members.
    retry_after: int | None = None  # seconds, also sent as the Retry-After header
    errors: list[dict[str, Any]] | None = None  # field errors of a 422


class ProblemError(Exception):
    def __init__(self, problem: Problem) -> None:
        super().__init__(problem.detail or problem.title)
        self.problem = problem


def _seconds(wait_s: float | None) -> int | None:
    return None if wait_s is None else max(1, math.ceil(wait_s))


def not_found(what: str) -> Problem:
    return Problem(type="/problems/not-found", title="Not found", status=404, detail=what)


def rate_limited(wait_s: float) -> Problem:
    return Problem(
        type="/problems/rate-limited",
        title="Too many new checks",
        status=429,
        detail="This address has started too many new checks this hour. Claims that were "
        "checked before still load straight away.",
        retry_after=_seconds(wait_s),
    )


def reports_limited(wait_s: float) -> Problem:
    return Problem(
        type="/problems/rate-limited",
        title="Too many reports",
        status=429,
        detail="This address has sent too many reports this hour. Please try again later.",
        retry_after=_seconds(wait_s),
    )


def unknown_claim(index: int) -> Problem:
    return Problem(
        type="/problems/unknown-claim",
        title="Unknown claim",
        status=422,
        detail=f"This check has no claim {index + 1}.",
    )


def at_capacity(wait_s: float | None) -> Problem:
    wait = _seconds(wait_s)
    minutes = f" Try again in about {math.ceil(wait / 60)} minutes." if wait else ""
    return Problem(
        type="/problems/at-capacity",
        title="At capacity",
        status=503,
        detail="Every free model provider is busy or out of quota." + minutes,
        retry_after=wait,
    )


def internal_error() -> Problem:
    return Problem(
        type="/problems/internal",
        title="Internal error",
        status=500,
        detail="The check failed unexpectedly.",
    )


def interrupted() -> Problem:
    return Problem(
        type="/problems/interrupted",
        title="Check interrupted",
        status=503,
        detail="The server restarted while this check was running. Submit it again.",
    )


def problem_response(problem: Problem, instance: str | None = None) -> JSONResponse:
    if problem.instance is None and instance is not None:
        problem = problem.model_copy(update={"instance": instance})
    headers: Mapping[str, str] | None = None
    if problem.retry_after is not None:
        headers = {"Retry-After": str(problem.retry_after)}
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=problem.status,
        headers=headers,
        media_type=MEDIA_TYPE,
    )


async def _problem(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)  # noqa: S101 (registered for ProblemError only)
    return problem_response(exc.problem, request.url.path)


async def _http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101 (registered for it only)
    title = HTTPStatus(exc.status_code).phrase
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    response = problem_response(
        Problem(title=title, status=exc.status_code, detail=detail), request.url.path
    )
    for key, value in (exc.headers or {}).items():
        response.headers[key] = value
    return response


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101 (registered for it only)
    errors = [{k: v for k, v in e.items() if k in ("loc", "msg", "type")} for e in exc.errors()]
    return problem_response(
        Problem(
            type="/problems/invalid-request",
            title="Invalid request",
            status=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="; ".join(str(e["msg"]) for e in errors) or None,
            errors=jsonable_encoder(errors),
        ),
        request.url.path,
    )


def install(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, _problem)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(RequestValidationError, _validation)
