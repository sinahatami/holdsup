"""POST /v1/checks, the SSE stream, GET /v1/checks/{id} and /v1/gallery, over HTTP, with
fake providers, a fake data source and the in-memory store."""

import json
import os
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from holdsup.db.models import Check
from holdsup.db.url import to_async_url
from holdsup.main import create_app
from holdsup.routes.checks import MAX_TEXT
from holdsup.routes.deps import get_runner, get_store
from holdsup.service.runner import CheckRunner
from holdsup.service.store import InMemoryCheckStore, SqlCheckStore
from tests.router.fakes import FakeClient
from tests.service.fakes import TEXT, happy_script, make_runner

WEB = "http://localhost:3000"


@pytest.fixture
def api() -> Iterator[tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore]]:
    runner, client, store = make_runner(happy_script() * 3, limit=3)
    app = create_app()
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_store] = lambda: store
    # The context manager keeps one event loop alive, so background checks can finish.
    with TestClient(app) as http:
        yield http, runner, client, store


def sse(body: str) -> list[dict[str, Any]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith(":"):
                continue
            key, _, value = line.partition(": ")
            fields[key] = json.loads(value) if key == "data" else value
        if fields:
            events.append(fields)
    return events


def stream(http: TestClient, check_id: str, **headers: str) -> list[dict[str, Any]]:
    with http.stream("GET", f"/v1/checks/{check_id}/stream", headers=headers) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        return sse("".join(r.iter_text()))


def test_submit_stream_and_stored_result(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, _, client, _ = api
    r = http.post("/v1/checks", json={"text": TEXT})
    assert r.status_code == 202
    accepted = r.json()
    check_id = accepted["id"]
    assert accepted == {
        "id": check_id, "status": "queued", "cached": False,
        "stream_url": f"/v1/checks/{check_id}/stream", "result_url": f"/v1/checks/{check_id}",
    }  # fmt: skip
    assert r.headers["location"] == f"/v1/checks/{check_id}"

    events = stream(http, check_id)
    sequence = [(e["event"], e["data"].get("step")) for e in events]
    steps = ["ledger", "extract", "match", "fetch", "plan", "execute", "verdict", "explain"]
    assert sequence == [
        *((name, step) for step in steps for name in ("step_started", "step_done")),
        ("result", None),
    ]
    assert [int(e["id"]) for e in events] == list(range(len(events)))
    result = events[-1]["data"]
    assert result["id"] == check_id
    assert result["claims"][0]["verdict"]["label"] == "supported"
    assert len(client.calls) == 4

    stored = http.get(f"/v1/checks/{check_id}")
    assert stored.status_code == 200
    body = stored.json()
    assert body["status"] == "done" and body["error"] is None
    assert body["result"] == result
    assert body["text"] == TEXT and body["finished_at"] is not None


def test_a_repeated_claim_is_cached(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, _, client, _ = api
    first = http.post("/v1/checks", json={"text": TEXT}).json()
    stream(http, first["id"])
    calls = len(client.calls)

    again = http.post("/v1/checks", json={"text": TEXT.upper()}).json()
    assert again["cached"] is True and again["status"] == "done"
    events = stream(http, again["id"])
    assert [e["event"] for e in events] == ["step_started", "step_done", "result"]
    assert events[-1]["data"]["cached_from"] == first["id"]
    assert len(client.calls) == calls


def test_reconnect_with_last_event_id(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    check_id = http.post("/v1/checks", json={"text": TEXT}).json()["id"]
    everything = stream(http, check_id)
    assert stream(http, check_id, **{"Last-Event-ID": "14"}) == everything[15:]
    assert stream(http, check_id, **{"Last-Event-ID": "junk"}) == everything


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_TEXT + 1)])
def test_input_is_required_and_capped(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore], text: str
) -> None:
    http, *_ = api
    r = http.post("/v1/checks", json={"text": text})
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["type"] == "/problems/invalid-request"


def test_exactly_the_cap_is_accepted(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    text = "Unemployment fell 4 points. " + "x" * (MAX_TEXT - 28)
    assert len(text) == MAX_TEXT
    assert http.post("/v1/checks", json={"text": f"  {text}  "}).status_code == 202


def test_rate_limit_per_address(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    for i in range(3):
        assert (
            http.post("/v1/checks", json={"text": f"Claim {i}: rates fell 4 points"}).status_code
            == 202
        )
    r = http.post("/v1/checks", json={"text": "One more: rates fell 4 points"})
    assert r.status_code == 429
    assert r.headers["content-type"] == "application/problem+json"
    assert r.headers["retry-after"] == "3600"
    assert r.json()["type"] == "/problems/rate-limited"


def test_unknown_and_malformed_ids(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    missing = uuid4()
    for path in (f"/v1/checks/{missing}", f"/v1/checks/{missing}/stream"):
        r = http.get(path)
        assert r.status_code == 404
        assert r.json()["type"] == "/problems/not-found" and r.json()["instance"] == path
    assert http.get("/v1/checks/not-a-uuid").status_code == 422


def test_a_failed_check_shows_its_problem(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, runner, _, _ = api
    from holdsup.router.errors import ProviderUnavailable

    runner.pipeline.router._client.scripts["fake"].clear()  # type: ignore[attr-defined]
    runner.pipeline.router._client.script("fake", [ProviderUnavailable("down")])  # type: ignore[attr-defined]
    check_id = http.post("/v1/checks", json={"text": TEXT}).json()["id"]
    assert stream(http, check_id)[-1]["event"] == "error"
    body = http.get(f"/v1/checks/{check_id}").json()
    assert body["status"] == "failed" and body["result"] is None
    assert body["error"]["type"] == "/problems/at-capacity"


def test_gallery_lists_featured_checks(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, _, _, store = api
    assert http.get("/v1/gallery").json() == {"items": []}
    check_id = http.post("/v1/checks", json={"text": TEXT}).json()["id"]
    stream(http, check_id)
    http.portal.call(store.set_featured, UUID(check_id), True)  # type: ignore[union-attr]

    items = http.get("/v1/gallery").json()["items"]
    assert items == [
        {
            "id": check_id, "text": TEXT, "created_at": items[0]["created_at"],
            "verdicts": ["supported"], "indicators": ["Unemployment rate"],
        }
    ]  # fmt: skip
    assert http.get("/v1/gallery", params={"limit": 0}).status_code == 422
    assert http.get("/v1/gallery", params={"limit": 25}).status_code == 422


def test_cors_allows_only_the_web_origin(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    preflight = {"Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type"}  # fmt: skip
    ok = http.options("/v1/checks", headers={"Origin": WEB, **preflight})
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == WEB
    bad = http.options("/v1/checks", headers={"Origin": "https://evil.example", **preflight})
    assert bad.status_code == 400
    assert "access-control-allow-origin" not in bad.headers
    simple = http.get("/v1/gallery", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_openapi_documents_the_routes(
    api: tuple[TestClient, CheckRunner, FakeClient, InMemoryCheckStore],
) -> None:
    http, *_ = api
    paths = http.get("/openapi.json").json()["paths"]
    assert {"/v1/checks", "/v1/checks/{check_id}", "/v1/checks/{check_id}/stream",
            "/v1/gallery"} <= set(paths)  # fmt: skip
    assert (
        "text/event-stream"
        in paths["/v1/checks/{check_id}/stream"]["get"]["responses"]["200"]["content"]
    )


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_end_to_end_on_postgres() -> None:
    engine = create_async_engine(to_async_url(os.environ["TEST_DATABASE_URL"]))
    store = SqlCheckStore(async_sessionmaker(engine, expire_on_commit=False))
    runner, client, _ = make_runner(happy_script(), store=store)  # type: ignore[arg-type]
    app = create_app()
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as http:
        try:
            first = http.post("/v1/checks", json={"text": TEXT}).json()
            result = stream(http, first["id"])[-1]["data"]
            assert http.get(f"/v1/checks/{first['id']}").json()["result"] == result
            calls = len(client.calls)
            again = http.post("/v1/checks", json={"text": TEXT}).json()
            assert again["cached"] is True and len(client.calls) == calls
            assert (
                http.get(f"/v1/checks/{again['id']}").json()["result"]["cached_from"]
                == (first["id"])
            )
        finally:

            async def clear() -> None:
                async with store._sessionmaker() as s, s.begin():
                    await s.execute(delete(Check))
                await engine.dispose()

            assert http.portal is not None
            http.portal.call(clear)
