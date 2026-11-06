"""Circuit breaker: after N consecutive failures a provider is skipped for a cool-off period.

After the cool-off one trial call is allowed (half-open); success closes the breaker, another
failure re-opens it.
"""

from dataclasses import dataclass

FAILURE_THRESHOLD = 3
OPEN_FOR_S = 60.0


@dataclass
class _State:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, threshold: int = FAILURE_THRESHOLD, open_for_s: float = OPEN_FOR_S) -> None:
        self.threshold = threshold
        self.open_for_s = open_for_s
        self._states: dict[str, _State] = {}

    def _state(self, name: str) -> _State:
        return self._states.setdefault(name, _State())

    def wait_s(self, name: str, now: float) -> float:
        """Seconds until the provider may be tried again (0 if closed or half-open)."""
        opened_at = self._state(name).opened_at
        if opened_at is None:
            return 0.0
        return max(0.0, opened_at + self.open_for_s - now)

    def record_success(self, name: str) -> None:
        self._states[name] = _State()

    def record_failure(self, name: str, now: float) -> None:
        state = self._state(name)
        state.failures += 1
        if state.failures >= self.threshold:
            state.opened_at = now

    def is_open(self, name: str, now: float) -> bool:
        return self.wait_s(name, now) > 0
