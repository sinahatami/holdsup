"""POST /v1/checks/{id}/reports: a reader says a check matched the wrong statistic or read the
claim wrongly. No account, no address stored; the in-memory store and a small limiter."""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from holdsup.main import create_app
from holdsup.routes.deps import get_report_limiter, get_store
from holdsup.routes.reports import MAX_NOTE
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.store import (
    CheckStatus,
    InMemoryCheckStore,
    ReportKind,
    StoredCheck,
)

T0 = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
LIMIT = 3


@pytest.fixture
def api() -> Iterator[tuple[TestClient, InMemoryCheckStore, UUID]]:
    store = InMemoryCheckStore()
    done, running = uuid4(), uuid4()
    store.checks[done] = StoredCheck(
        done, "Debt is 133%. Jobs rose 2%.", CheckStatus.DONE, T0, result={"claims": [{}, {}]}
    )
    store.checks[running] = StoredCheck(running, "Debt is 133%.", CheckStatus.RUNNING, T0)
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    limiter = RateLimiter(limit=LIMIT, window_s=3600)  # one for the test, not the process's
    app.dependency_overrides[get_report_limiter] = lambda: limiter
    with TestClient(app) as http:
        http.running = running  # type: ignore[attr-defined]
        yield http, store, done


def url(check_id: UUID | str) -> str:
    return f"/v1/checks/{check_id}/reports"


def test_a_report_is_stored_without_an_account(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, check_id = api
    r = http.post(
        url(check_id),
        json={"kind": "wrong_series", "claim_index": 1, "note": "  Wrong unemployment series.  "},
    )
    assert r.status_code == 201
    (saved,) = store.saved_reports
    assert r.json() == {"id": str(saved.id)}
    assert saved.check_id == check_id
    assert saved.claim_index == 1
    assert saved.kind is ReportKind.WRONG_SERIES
    assert saved.note == "Wrong unemployment series."  # trimmed
    assert abs((datetime.now(UTC) - saved.created_at).total_seconds()) < 60


def test_the_note_and_the_claim_are_optional(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, check_id = api
    assert http.post(url(check_id), json={"kind": "other"}).status_code == 201
    (saved,) = store.saved_reports
    assert (saved.claim_index, saved.note, saved.kind) == (None, "", ReportKind.OTHER)


def test_a_check_that_is_still_running_can_be_reported_as_a_whole(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, _ = api
    r = http.post(url(http.running), json={"kind": "other", "note": "stuck"})  # type: ignore[attr-defined]
    assert r.status_code == 201
    assert len(store.saved_reports) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "nonsense"},
        {},
        {"kind": "other", "claim_index": -1},
        {"kind": "other", "note": "x" * (MAX_NOTE + 1)},
        {"kind": "other", "note": ["not text"]},
    ],
)
def test_a_malformed_report_is_refused_and_not_stored(
    api: tuple[TestClient, InMemoryCheckStore, UUID], body: dict[str, object]
) -> None:
    http, store, check_id = api
    r = http.post(url(check_id), json=body)
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    assert store.saved_reports == []


def test_a_note_of_exactly_the_longest_length_is_kept(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, check_id = api
    assert (
        http.post(url(check_id), json={"kind": "other", "note": "x" * MAX_NOTE}).status_code == 201
    )
    assert len(store.saved_reports[0].note) == MAX_NOTE


def test_an_unknown_check_is_a_404(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, _ = api
    r = http.post(url(uuid4()), json={"kind": "other"})
    assert r.status_code == 404
    assert r.json()["type"] == "/problems/not-found"
    assert http.post(url("not-an-id"), json={"kind": "other"}).status_code == 422
    assert store.saved_reports == []


def test_a_claim_the_check_does_not_have_is_refused(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, check_id = api
    r = http.post(url(check_id), json={"kind": "other", "claim_index": 2})  # it has claims 0 and 1
    assert r.status_code == 422
    assert r.json()["type"] == "/problems/unknown-claim"
    assert r.json()["detail"] == "This check has no claim 3."
    # A check with no result yet has no claims to point at.
    r = http.post(url(http.running), json={"kind": "other", "claim_index": 0})  # type: ignore[attr-defined]
    assert r.status_code == 422
    assert store.saved_reports == []


def test_one_address_can_only_send_so_many_reports_an_hour(
    api: tuple[TestClient, InMemoryCheckStore, UUID],
) -> None:
    http, store, check_id = api
    for _ in range(LIMIT):
        assert http.post(url(check_id), json={"kind": "other"}).status_code == 201
    r = http.post(url(check_id), json={"kind": "other"})
    assert r.status_code == 429
    assert r.json()["title"] == "Too many reports"
    assert r.headers["retry-after"] == "3600"
    assert len(store.saved_reports) == LIMIT
