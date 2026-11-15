"""What a run returns: per claim, the indicator, the data, the operations, the verdict and the
explanation, and the versions it all came from."""

from collections.abc import Sequence
from datetime import datetime
from importlib.metadata import version
from typing import Literal

from pydantic import BaseModel, Field

from holdsup.adapters.base import FetchedSeries, Observation
from holdsup.catalog.schema import IndicatorSpec
from holdsup.checks import ChangePoints, DistortionCheck, Sweep
from holdsup.config import get_settings
from holdsup.ml.confidence import Confidence
from holdsup.ops import OpRecord, Series
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.trace import ModelUse, Step
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


class Suggestion(BaseModel):
    """A statistic HoldsUp has that is close to what a claim talks about: one a reader can
    re-check the claim with."""

    id: str
    name: str


class ExtraSource(BaseModel):
    """A series used besides the matched one: the population a per-capita figure divides by,
    the prices or the real version a real-terms check reads."""

    indicator: IndicatorRef
    data: DataRef


class SeriesPoint(BaseModel):
    period: str
    value: float


class ChartSeries(BaseModel):
    """The series the claim's deciding operation read, as it read it: yearly values made from
    months, or cut at the claim's date. The result page's chart shows it, so every number
    there is one the check used."""

    geo: str
    frequency: str
    unit: str | None
    points: list[SeriesPoint]

    @classmethod
    def of(cls, series: Series) -> "ChartSeries":
        return cls(
            geo=series.geo,
            frequency=str(series.frequency),
            unit=series.unit,
            points=[SeriesPoint(period=str(p), value=v) for p, v in series.points],
        )


class ClaimResult(BaseModel):
    index: int
    claim: ClaimSpec
    indicator: IndicatorRef | None = None
    alternatives: list[str] = Field(default_factory=list)
    # Statistics to re-check with: the match's alternatives, or the closest when none matched.
    suggestions: list[Suggestion] = Field(default_factory=list)
    match_reason: str = ""
    data: DataRef | None = None
    extra_sources: list[ExtraSource] = Field(default_factory=list)
    plan_reason: str | None = None
    operations: list[OpRecord] = Field(default_factory=list)
    answer: list[int] = Field(default_factory=list)  # which operations decide the claim
    # The claim's place's series as the first answer read it (the chart); None if not run.
    series: ChartSeries | None = None
    # The claim's direction over every time window (the cherry-pick sweep); None when the
    # claim picked no window (a level, a rank, a comparison, no direction).
    sweep: Sweep | None = None
    # Breaks in the trend of the series the answer read, and a start or end that leans on one.
    changepoints: ChangePoints | None = None
    # The distortion checks that applied (P3.4): per person, after inflation, percent or
    # points, definition, stale data, the start and end. A flagged one is a framing caveat.
    distortion_checks: list[DistortionCheck] = Field(default_factory=list)
    verdict: Verdict
    # How sure the check is of the verdict, and whether it abstains (P4.5); None for a claim
    # with no verdict to be sure of (cant_check).
    confidence: Confidence | None = None
    explanation: str
    explanation_source: Literal["model", "template"] = "template"
    models: list[ModelUse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # what code dropped, fixed or rejected
    # cant_check because something was briefly unavailable: worth checking again later.
    retryable: bool = False
    # cant_check: the step the claim stopped at, so a reader can be told why (no statistic
    # matched, the source has no figures, the kind of claim cannot be recomputed).
    stopped_at: Step | None = None


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
    """The package version, with the build's commit when known ("0.0.0+d264e60"): until the
    first release the package version alone says nothing about which code answered."""
    commit = get_settings().app_commit.strip()[:7]
    base = version("holdsup")
    return f"{base}+{commit}" if commit else base
