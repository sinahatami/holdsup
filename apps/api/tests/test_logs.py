"""Request IDs: kept or made, returned, and bound to log lines."""

import json
import logging

import pytest
import structlog
from fastapi.testclient import TestClient

from holdsup.logs import configure_logging, request_id_from
from holdsup.main import create_app


def test_request_id_from() -> None:
    assert request_id_from("abc-123_x.y") == "abc-123_x.y"
    for bad in (None, "", "has space", "x" * 65, "new\nline"):
        made = request_id_from(bad)
        assert len(made) == 32 and made != bad


def test_the_id_is_kept_or_made_and_returned() -> None:
    http = TestClient(create_app())
    assert http.get("/v1/health", headers={"X-Request-ID": "web-42"}).headers["x-request-id"] == (
        "web-42"
    )
    made = http.get("/v1/health").headers["x-request-id"]
    assert len(made) == 32


def test_logs_are_json_with_the_bound_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    structlog.contextvars.bind_contextvars(request_id="r-1")
    try:
        structlog.get_logger("holdsup.test").info("hello", n=1)
        logging.getLogger("library").warning("from stdlib")
    finally:
        structlog.contextvars.clear_contextvars()
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]["event"] == "hello" and lines[0]["request_id"] == "r-1"
    assert lines[0]["n"] == 1 and lines[0]["level"] == "info" and "timestamp" in lines[0]
    assert lines[1]["event"] == "from stdlib" and lines[1]["level"] == "warning"
