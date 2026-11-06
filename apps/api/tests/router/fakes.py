"""Fake providers and clock for router fault-injection tests (no network)."""

from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from holdsup.router.client import ChatRequest, ChatResponse
from holdsup.router.config import ProviderConfig, RouterConfig
from holdsup.router.errors import ProviderError

Outcome = ChatResponse | ProviderError | Callable[[ChatRequest], ChatResponse]

T0 = 1_793_966_400.0  # 2026-11-06 12:00:00 UTC


class FakeClock:
    def __init__(self, start: float = T0) -> None:
        self.t = start

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@dataclass
class FakeClient:
    """Each provider replays a script of outcomes; when a script runs out it returns `default`."""

    default: ChatResponse = field(default_factory=lambda: ChatResponse(content='{"ok": true}'))
    keys: set[str] | None = None  # provider names with an API key; None = all
    scripts: dict[str, deque[Outcome]] = field(default_factory=lambda: defaultdict(deque))
    calls: list[tuple[str, ChatRequest]] = field(default_factory=list)

    def script(self, provider: str, outcomes: Iterable[Outcome]) -> None:
        self.scripts[provider].extend(outcomes)

    def has_key(self, provider: ProviderConfig) -> bool:
        return self.keys is None or provider.name in self.keys

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse:
        self.calls.append((provider.name, request))
        script = self.scripts[provider.name]
        outcome = script.popleft() if script else self.default
        if isinstance(outcome, ProviderError):
            raise outcome
        if callable(outcome):
            return outcome(request)
        return outcome

    def called(self) -> list[str]:
        return [name for name, _ in self.calls]


def provider(
    name: str,
    *,
    rpm: int = 1000,
    rpd: int | None = None,
    use: str = "live",
    capabilities: tuple[str, ...] = ("json_object", "json_schema", "tools"),
    base_url: str = "https://example.invalid/v1",
) -> dict[str, object]:
    limits: dict[str, int] = {"requests_per_minute": rpm}
    if rpd is not None:
        limits["requests_per_day"] = rpd
    return {
        "name": name,
        "base_url": base_url,
        "model": f"{name}-model",
        "api_key_env": f"{name.upper().replace('-', '_')}_KEY",
        "capabilities": list(capabilities),
        "context_window": 8192,
        "limits": limits,
        "allowed_use": use,
    }


def config(
    *providers: dict[str, object], steps: dict[str, list[str]] | None = None
) -> RouterConfig:
    names = [str(p["name"]) for p in providers]
    return RouterConfig.model_validate(
        {"providers": list(providers), "steps": steps or {"extract": names}}
    )
