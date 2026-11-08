"""What the model answers, what a match returns, and the state one match builds up."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from holdsup.catalog.schema import IndicatorSpec
from holdsup.pipeline.claim import ClaimSpec

Confidence = Literal["low", "medium", "high"]


class MatchAnswer(BaseModel):
    indicator_id: str | None = Field(description="A candidate id, or null if none fits.")
    confidence: Confidence
    reason: str = Field(description="One sentence.")
    alternatives: list[str] = Field(
        description="Other candidate ids that could also fit (e.g. another age range); "
        "empty if none."
    )


class Candidate(BaseModel):
    id: str
    score: float


class ToolUse(BaseModel):
    name: str
    arguments: str
    ok: bool


class MatchResult(BaseModel):
    status: Literal["matched", "cant_check"]
    indicator_id: str | None
    confidence: Confidence | None
    reason: str
    alternatives: list[str]
    candidates: list[Candidate]  # the top 8 shown to the model
    excluded_by_geo: list[str]  # vector hits dropped because they do not cover the place
    tool_calls: list[ToolUse] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


@dataclass
class MatchRun:
    """State of one match: what the model has seen and done."""

    claim: ClaimSpec
    eligible: dict[str, IndicatorSpec] = field(default_factory=dict)  # ids it may pick
    tool_calls: list[ToolUse] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
