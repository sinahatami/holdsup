"""The per-IP sliding window and the client address behind proxies."""

from starlette.requests import Request

from holdsup.service import ratelimit
from holdsup.service.ratelimit import RateLimiter, client_ip
from tests.router.fakes import FakeClock


def test_limit_per_key_in_a_sliding_window() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, 3600.0, clock=clock.now)
    assert limiter.hit("a") is None
    clock.advance(600)
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 3000.0  # until the first hit leaves the window
    assert limiter.hit("b") is None  # other addresses are counted apart
    clock.advance(3000)
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 600.0


def test_idle_keys_are_forgotten(monkeypatch: object) -> None:
    clock = FakeClock()
    limiter = RateLimiter(1, 10.0, clock=clock.now)
    setattr(ratelimit, "MAX_KEYS", 2)  # noqa: B010
    try:
        limiter.hit("a")
        limiter.hit("b")
        clock.advance(11)
        limiter.hit("c")
        assert set(limiter._hits) == {"c"}
    finally:
        setattr(ratelimit, "MAX_KEYS", 10_000)  # noqa: B010


def request(client: str | None, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    scope = {"type": "http", "headers": headers, "client": (client, 1234) if client else None}
    return Request(scope)


def test_client_ip() -> None:
    # No trusted proxy: the socket address; X-Forwarded-For is the caller's to forge.
    assert client_ip(request("1.1.1.1", "6.6.6.6"), 0) == "1.1.1.1"
    assert client_ip(request(None), 0) == "unknown"
    # One proxy appends what it saw: the last entry.
    assert client_ip(request("10.0.0.1", "6.6.6.6, 2.2.2.2"), 1) == "2.2.2.2"
    # Two proxies (web app, then the host): the second to last.
    assert client_ip(request("10.0.0.1", "6.6.6.6, 2.2.2.2, 3.3.3.3"), 2) == "2.2.2.2"
    # Fewer entries than proxies: every entry came from a proxy; the first is the caller.
    assert client_ip(request("10.0.0.1", "2.2.2.2"), 2) == "2.2.2.2"
    assert client_ip(request("10.0.0.1"), 1) == "10.0.0.1"
