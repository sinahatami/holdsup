"""Typed errors. Provider errors are internal; callers only ever see RouterError."""

from dataclasses import dataclass, field


class ProviderError(Exception):
    """A single provider call failed."""


@dataclass
class RateLimited(ProviderError):
    """HTTP 429. `daily` means the provider's per-day quota is spent."""

    retry_after_s: float | None = None
    daily: bool = False
    message: str = ""


class ProviderTimeout(ProviderError):
    """The call exceeded the provider's timeout."""


class ProviderUnavailable(ProviderError):
    """5xx or connection failure."""


class ProviderRejected(ProviderError):
    """Other 4xx (bad key, bad request, unknown model)."""


class MalformedOutput(ProviderError):
    """The response was not valid JSON or failed the requested schema."""


@dataclass
class RouterError(Exception):
    """Every eligible provider was tried or unavailable for this call."""

    step: str
    attempts: list[str] = field(default_factory=list)
    retry_after_s: float | None = None

    def __str__(self) -> str:
        wait = f"; retry in ~{self.retry_after_s:.0f}s" if self.retry_after_s is not None else ""
        return f"no provider available for step {self.step!r}{wait} (attempts: {self.attempts})"
