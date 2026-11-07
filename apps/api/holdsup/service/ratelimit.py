"""Per-IP limit on new checks (spec: about 10 an hour), in memory.

One API process serves everything (Hugging Face Spaces, one container), so a sliding window
per address in memory is enough; a restart forgets the counts, which only errs towards
letting people in. Cache hits never reach the limiter (decisions.md D017).
"""

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from starlette.requests import Request

MAX_KEYS = 10_000  # forget idle addresses beyond this many


@dataclass
class RateLimiter:
    limit: int
    window_s: float
    clock: Callable[[], float] = time.monotonic
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def hit(self, key: str) -> float | None:
        """Count one use by `key`. None if allowed, else seconds until the next one is."""
        now = self.clock()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return hits[0] + self.window_s - now
        hits.append(now)
        if len(self._hits) > MAX_KEYS:
            self._forget_idle(now)
        return None

    def _forget_idle(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= now - self.window_s]:
            del self._hits[key]


def client_ip(request: Request, trusted_proxies: int) -> str:
    """The caller's address. Behind `trusted_proxies` proxies that each append to
    X-Forwarded-For, the address the outermost trusted proxy saw; never a value the caller
    could have written themselves."""
    direct = request.client.host if request.client else "unknown"
    if trusted_proxies <= 0:
        return direct
    forwarded = [
        a.strip() for a in request.headers.get("x-forwarded-for", "").split(",") if a.strip()
    ]
    if len(forwarded) < trusted_proxies:
        return forwarded[0] if forwarded else direct
    return forwarded[-trusted_proxies]
