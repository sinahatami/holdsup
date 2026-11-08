"""What a run returns: per claim, the indicator, the data, the operations, the verdict and the
explanation, and the versions it all came from."""

from collections.abc import Sequence
from datetime import datetime
from importlib.metadata import version
from typing import Literal

from pydantic import BaseModel, Field

from holdsup.adapters.base import FetchedSeries, Observation
from holdsup.catalog.schema import IndicatorSpec
from holdsup.ops import OpRecord
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.trace import ModelUse
from holdsup.verdict import Verdict


class IndicatorRef(BaseModel):
    id: str
    name: str
    source: str
    source_code: str
    unit: str
    frequency: str
    definition: str

    @classmethod
    def of(cls, spec: IndicatorSpec) -> "IndicatorRef":
        return cls(
            id=spec.id,
            name=spec.name,
            source=str(spec.source),
            source_code=spec.source_code,
            unit=spec.unit,
            frequency=str(spec.frequency),
            definition=spec.definition,
        )


class DataRef(BaseModel):
    """Where the numbers came from: enough to cite and re-fetch them."""

    source: str
    dataset: str
    url: str
    retrieved_at: datetime
    raw_sha256: str
    label: str = ""
    updated: str | None = None
    citation: str | None = None
    places: list[str]  # claim codes with at least one value
    rows: int  # observations with a value

    @classmethod
    def of(cls, series: FetchedSeries, observations: Sequence[Observation]) -> "DataRef":
        present = [o for o in observations if o.value is not None]
        return cls(
            source=series.source,
            dataset=series.dataset,
            url=series.url,
            retrieved_at=series.retrieved_at,
            raw_sha256=series.raw_sha256,
            label=series.label,
            updated=series.updated,
            citation=series.citation,
            places=sorted({o.geo for o in present}),
            rows=len(present),
        )


class ClaimResult(BaseModel):
    index: int
    claim: ClaimSpec
    indicator: IndicatorRef | None = None
    alternatives: list[str] = Field(default_factory=list)
    match_reason: str = ""
    data: DataRef | None = None
    plan_reason: str | None = None
    operations: list[OpRecord] = Field(default_factory=list)
    answer: list[int] = Field(default_factory=list)  # which operations decide the claim
    verdict: Verdict
    explanation: str
    explanation_source: Literal["model", "template"] = "template"
    models: list[ModelUse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # what code dropped, fixed or rejected
    # cant_check because something was briefly unavailable: worth checking again later.
    retryable: bool = False


class Versions(BaseModel):
    app: str
    catalog: str
    tolerances: int


class PipelineOutput(BaseModel):
    claims: list[ClaimResult]
    versions: Versions
    models: list[ModelUse]  # check-wide model calls (extraction)
    notes: list[str] = Field(default_factory=list)

    @property
    def retryable(self) -> bool:
        return any(c.retryable for c in self.claims)


def app_version() -> str:
    return version("holdsup")
