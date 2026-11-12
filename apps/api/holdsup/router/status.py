"""What the /status page shows about each live provider: whether it can take a call now, and
how many requests it has left today under the router's own cap (90% of the published limit)."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ProviderState(StrEnum):
    READY = "ready"
    COOLING_DOWN = "cooling_down"  # it asked us to slow down (HTTP 429), or a minute is full
    FAILING = "failing"  # recent calls failed: skipped for a short while (circuit breaker)
    OUT_OF_BUDGET = "out_of_budget"  # today's requests are used up; back at midnight UTC
    NOT_CONFIGURED = "not_configured"  # no API key on this server


class ProviderStatus(BaseModel):
    name: str
    label: str  # the model's name for a reader
    model: str
    state: ProviderState
    wait_s: float = Field(ge=0, description="Seconds until it may be called again; 0 if ready.")
    remaining_today: int | None = Field(
        description="Requests left today under the router's cap; null when it has no daily limit."
    )
    daily_cap: int | None = Field(description="The router's daily cap: 90% of the published limit.")
    steps: list[str] = Field(description="The pipeline steps it serves, in the router's order.")
