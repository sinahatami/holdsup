"""The plan's data model: what the model writes (`ModelPlan`), what it may know about the
data (`SeriesInfo`, `PlanContext`), and what code accepts (`ValidPlan`)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from holdsup.adapters.base import Observation
from holdsup.catalog.schema import IndicatorSpec
from holdsup.ops import AnnualValue, ChangeKind, Frequency, parse_period, published_by
from holdsup.pipeline.claim import ClaimSpec

MAX_CALLS = 6

# Every operation a plan may call; each has an entry in `operations.OPERATIONS`.
OpName = Literal["value_at", "change", "cagr", "trend", "compare", "rank", "per_capita", "deflate"]

ARGS = ("series", "geo", "geo_b", "geos", "period", "start", "end", "kind", "population",
        "price_index", "base")  # fmt: skip
PERIOD_ARGS = ("period", "start", "end", "base")

PERIOD_FORMAT = {
    Frequency.ANNUAL: "YYYY",
    Frequency.QUARTERLY: "YYYY-Qn",
    Frequency.MONTHLY: "YYYY-MM",
}


class OpCall(BaseModel):
    op: OpName
    series: str | None = Field(
        default=None,
        description="null for the matched indicator; another listed indicator id; or '@N' "
        "for the series made by call N (per_capita or deflate).",
    )
    geo: str | None = Field(default=None, description="Place code, e.g. IT, EU, WORLD.")
    geo_b: str | None = Field(default=None, description="compare: the second place.")
    geos: list[str] | None = Field(default=None, description="rank: every place to rank.")
    period: str | None = Field(default=None, description="YYYY, YYYY-Qn, YYYY-MM or latest.")
    start: str | None = None
    end: str | None = None
    kind: ChangeKind | None = Field(
        default=None, description="change: absolute, percent, percentage_points or ratio."
    )
    population: str | None = Field(default=None, description="per_capita: indicator id.")
    price_index: str | None = Field(default=None, description="deflate: indicator id.")
    base: str | None = Field(default=None, description="deflate: base period.")

    def given(self) -> set[str]:
        return {name for name in ARGS if getattr(self, name) is not None}


class ModelPlan(BaseModel):
    calls: list[OpCall] = Field(description=f"At most {MAX_CALLS} operation calls, in order.")
    answer: list[int] = Field(
        description="Indexes (from 0) of the calls whose results decide the claim."
    )
    reason: str = Field(description="One sentence: why these operations answer the claim.")


@dataclass(frozen=True)
class SeriesInfo:
    """What the plan may know about one fetched indicator: no values, only their extent."""

    id: str
    name: str
    unit: str
    frequency: Frequency
    geos: frozenset[str]
    first: str | None
    last: str | None
    annual: AnnualValue | None = None  # monthly or quarterly: how a year's value is made
    lag_months: int = 0  # months from the end of a period to its release (dated claims)

    @classmethod
    def from_data(cls, spec: IndicatorSpec, observations: Sequence[Observation]) -> "SeriesInfo":
        present = [o for o in observations if o.value is not None]
        frequency = Frequency(spec.frequency.value)
        periods = sorted((parse_period(o.period) for o in present), key=lambda p: p.ordinal)
        return cls(
            id=spec.id,
            name=spec.name,
            unit=spec.unit,
            frequency=frequency,
            geos=frozenset(o.geo for o in present),
            first=str(periods[0]) if periods else None,
            last=str(periods[-1]) if periods else None,
            annual=None if spec.annual_value is None else AnnualValue(spec.annual_value.value),
            lag_months=spec.lag_months,
        )

    def years(self) -> str:
        """What a whole-year period (YYYY) means on this series."""
        if self.frequency is Frequency.ANNUAL:
            return ""
        sub = "months" if self.frequency is Frequency.MONTHLY else "quarters"
        if self.annual is AnnualValue.MEAN:
            return f" A whole year (YYYY) is the average of its {sub}."
        if self.annual is AnnualValue.END:
            return f" A whole year (YYYY) is its last {sub[:-1]}."
        return f" No yearly value: use {PERIOD_FORMAT[self.frequency]} (a trend may use YYYY)."

    def describe(self) -> str:
        return (
            f"{self.id}: {self.name}. Unit: {self.unit}. Frequency: {self.frequency}."
            f"{self.years()} Places: {', '.join(sorted(self.geos)) or 'none'}. "
            f"Periods: {self.first or '?'} to {self.last or '?'}."
        )


@dataclass(frozen=True)
class PlanContext:
    claim: ClaimSpec
    main: SeriesInfo  # the matched indicator; `series: null` in a call
    others: tuple[SeriesInfo, ...] = ()  # e.g. population or a price index, when fetched
    as_of: date | None = None  # a dated claim is checked as of this day ("latest" then)

    def published(self, info: SeriesInfo) -> str | None:
        """The last period of `info` out by the claim date, if the claim has one."""
        if self.as_of is None:
            return None
        return str(published_by(info.frequency, self.as_of, info.lag_months))

    def info(self, indicator_id: str | None) -> SeriesInfo | None:
        if indicator_id is None or indicator_id == self.main.id:
            return self.main
        return next((s for s in self.others if s.id == indicator_id), None)


class ValidPlan(BaseModel):
    calls: list[OpCall]
    answer: list[int]
    reason: str
    notes: list[str] = Field(default_factory=list)  # what code dropped or fixed


class PlanInvalid(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def step_of(ref: str) -> int:
    """N in '@N', or -1."""
    return int(ref[1:]) if ref[1:].isdigit() else -1


def source_of(n: int, calls: Sequence[OpCall], ctx: PlanContext) -> SeriesInfo | None:
    """The indicator call `n` reads, following '@' references back."""
    ref = calls[n].series
    if ref is not None and ref.startswith("@"):
        m = step_of(ref)
        return source_of(m, calls, ctx) if 0 <= m < n else None
    return ctx.info(ref)
