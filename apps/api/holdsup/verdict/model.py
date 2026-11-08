"""What a verdict is: a label, the reason, and every checked part with its numbers."""

from enum import StrEnum

from pydantic import BaseModel, Field

from holdsup.pipeline.claim import Operator


class Label(StrEnum):
    SUPPORTED = "supported"
    SUPPORTED_FRAMING_MATTERS = "supported_framing_matters"
    NOT_SUPPORTED = "not_supported"
    PARTLY_SUPPORTED = "partly_supported"
    CANT_CHECK = "cant_check"


class Part(BaseModel):
    """One checked piece of a claim."""

    name: str  # "assertion", "start value", "end value", "vs FR"
    holds: bool
    computed: float | None = None
    asserted: float | None = None
    tolerance: float | None = None  # the largest |computed - asserted| that holds
    period: str | None = None  # the period the computed value is for, e.g. "2026-09"
    operator: Operator = Operator.ABOUT  # how the asserted value bounds the computed one
    detail: str


class Verdict(BaseModel):
    label: Label
    reason: str
    parts: list[Part] = Field(default_factory=list)
    window_share: float | None = None  # share of windows where the claim holds (P3.1)
    framing_threshold: float | None = None
    distortions: list[str] = Field(default_factory=list)  # failed distortion checks (P3.4)
    tolerances_version: int | None = None


def cant_check(reason: str) -> Verdict:
    return Verdict(label=Label.CANT_CHECK, reason=reason)
