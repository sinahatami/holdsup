"""Typed view of providers.yaml."""

from enum import StrEnum
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).with_name("providers.yaml")


class Use(StrEnum):
    LIVE = "live"
    OFFLINE = "offline"


class Capability(StrEnum):
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"
    TOOLS = "tools"


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requests_per_minute: PositiveInt
    requests_per_day: PositiveInt | None = None


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    base_url: str
    model: str
    api_key_env: str
    # The model's name for a reader (the receipt); empty = show the model id.
    label: str = ""
    capabilities: frozenset[Capability]
    context_window: PositiveInt
    limits: Limits
    allowed_use: Use
    timeout_s: float = Field(default=30.0, gt=0)
    # Minimum gap between calls (e.g. Mistral's ~1 request/second); 0 = no pacing.
    min_interval_s: float = Field(default=0.0, ge=0)

    def serves(self, use: Use) -> bool:
        """Live providers may also run offline jobs; offline providers never serve live traffic."""
        return use is Use.OFFLINE or self.allowed_use is Use.LIVE


class RouterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    providers: tuple[ProviderConfig, ...]
    steps: dict[str, tuple[str, ...]]

    @model_validator(mode="after")
    def _check(self) -> Self:
        names = [p.name for p in self.providers]
        if len(names) != len(set(names)):
            raise ValueError("provider names must be unique")
        for p in self.providers:
            # D003: Gemini's free tier must never serve live users.
            host = (urlparse(p.base_url).hostname or "").lower()
            is_googleapis_host = host == "googleapis.com" or host.endswith(".googleapis.com")
            is_gemini = "gemini" in p.name.lower() or is_googleapis_host
            if is_gemini and p.allowed_use is not Use.OFFLINE:
                raise ValueError(f"{p.name}: Gemini providers must be allowed_use: offline")
        for step, prefs in self.steps.items():
            unknown = set(prefs) - set(names)
            if unknown:
                raise ValueError(f"step {step!r} references unknown providers: {sorted(unknown)}")
        return self

    def provider(self, name: str) -> ProviderConfig:
        for p in self.providers:
            if p.name == name:
                return p
        raise KeyError(name)


def load_router_config(path: Path = DEFAULT_CONFIG_PATH) -> RouterConfig:
    with path.open(encoding="utf-8") as f:
        return RouterConfig.model_validate(yaml.safe_load(f))
