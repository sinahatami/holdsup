"""Errors are RFC 9457 problem details."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from holdsup import problems
from holdsup.problems import ProblemError, at_capacity, internal_error, interrupted, rate_limited


def app() -> TestClient:
    a = FastAPI()
    problems.install(a)

    @a.get("/teapot")
    async def teapot() -> None:
        raise HTTPException(418, headers={"X-Extra": "1"})

    @a.get("/busy")
    async def busy() -> None:
        raise ProblemError(at_capacity(125.2))

    @a.get("/items/{n}")
    async def item(n: int) -> int:
        return n

    return TestClient(a)


def test_http_errors_become_problems() -> None:
    r = app().get("/teapot")
    assert r.status_code == 418
    assert r.headers["content-type"] == "application/problem+json"
    assert r.headers["x-extra"] == "1"
    assert r.json() == {
        "type": "about:blank", "title": "I'm a Teapot", "status": 418, "instance": "/teapot",
    }  # fmt: skip
    assert app().get("/nowhere").json()["title"] == "Not Found"


def test_problem_errors_carry_retry_after() -> None:
    r = app().get("/busy")
    assert r.status_code == 503 and r.headers["retry-after"] == "126"
    body = r.json()
    assert body["type"] == "/problems/at-capacity" and body["retry_after"] == 126
    assert body["detail"].endswith("Try again in about 3 minutes.")


def test_validation_errors_list_the_fields() -> None:
    r = app().get("/items/abc")
    assert r.status_code == 422
    body = r.json()
    assert body["type"] == "/problems/invalid-request"
    assert body["errors"][0]["loc"] == ["path", "n"]


def test_problem_builders() -> None:
    assert rate_limited(0.2).retry_after == 1
    assert at_capacity(None).retry_after is None
    assert at_capacity(None).detail == "Every free model provider is busy or out of quota."
    assert internal_error().status == 500
    assert interrupted().type == "/problems/interrupted"
