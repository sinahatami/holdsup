"""Types shared by every data-source adapter."""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Observation:
    """One cell of a series. `value` is None when the source has no number for it."""

    geo: str
    period: str  # as the source writes it: "2024", "2024-Q1", "2024-03"
    value: float | None
    status: str | None = None  # source flag, e.g. Eurostat p = provisional, b = break
    dims: dict[str, str] = field(default_factory=dict)  # other dimensions, e.g. sex, age, unit


@dataclass(frozen=True)
class FetchedSeries:
    """Observations plus what a receipt needs to cite and reproduce them."""

    source: str
    dataset: str
    url: str
    retrieved_at: datetime
    raw_sha256: str
    observations: list[Observation]
    label: str = ""
    dimension_labels: dict[str, dict[str, str]] = field(default_factory=dict)
    status_labels: dict[str, str] = field(default_factory=dict)
    updated: str | None = None


class AdapterError(Exception):
    """The source could not provide the requested series."""


class SourceNotFound(AdapterError):
    """Unknown dataset/indicator, or no data for the filters."""


class SourceUnavailable(AdapterError):
    """Network failure or 5xx after retries."""


class SourceFormatError(AdapterError):
    """The response did not have the documented shape."""


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
