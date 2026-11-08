"""The operations a plan may call: one registry entry per operation.

Each entry holds what the model must write (its signature), how the operation treats whole
years, and how code runs it. Validation, repair and execution all read this table, so adding an
operation means one new entry here, one name in `OpName`, and a line in the prompt.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from holdsup.ops import (
    LATEST,
    ChangeKind,
    OpRecord,
    Series,
    cagr,
    change,
    compare,
    deflate,
    per_capita,
    rank,
    trend,
    unit_scale,
    value_at,
    year_window,
)
from holdsup.pipeline.claim import Direction
from holdsup.pipeline.plan.model import OpCall, OpName, PlanContext
from holdsup.verdict.rules import Tolerances

SeriesReader = Callable[[str | None, str], Series]


@dataclass(frozen=True)
class OpInput:
    """What an operation runs on: the call, the series it reads for its place, and a reader
    for any other series (a second place, a population, a price index)."""

    call: OpCall
    series: Series
    read: SeriesReader
    ctx: PlanContext
    max_gap: int | None  # how far a requested period may be from the nearest data

    @property
    def geo(self) -> str:
        return self.call.geo or ""


@dataclass(frozen=True)
class OpSpec:
    required: frozenset[str]
    run: Callable[[OpInput], OpRecord]
    optional: frozenset[str] = frozenset({"series"})
    makes_series: bool = False  # its output is a series later calls read as '@N'
    reads_months: bool = False  # a whole year means the year's months, not a yearly value

    @property
    def windowed(self) -> bool:
        """Whether it reads a start-to-end window (and so takes an assumed window)."""
        return "start" in self.required


def per_person_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    bare = re.sub(
        r"\b(thousand|million|billion|trillion|mio|bn)s?\b\s*", "", unit, flags=re.IGNORECASE
    )
    return f"{bare.strip()} per person"


def _value_at(a: OpInput) -> OpRecord:
    return value_at(a.series, a.call.period or LATEST, max_distance=a.max_gap)


def _change(a: OpInput) -> OpRecord:
    kind = a.call.kind or ChangeKind.PERCENT
    return change(a.series, a.call.start or "", a.call.end or LATEST, kind, max_distance=a.max_gap)


def _cagr(a: OpInput) -> OpRecord:
    return cagr(a.series, a.call.start or "", a.call.end or LATEST, max_distance=a.max_gap)


def _trend(a: OpInput) -> OpRecord:
    start, end = year_window(a.series, a.call.start or "", a.call.end or LATEST)
    return trend(a.series, start, end)


def _compare(a: OpInput) -> OpRecord:
    other = a.read(a.call.series, a.call.geo_b or "")
    return compare(a.series, other, a.call.period or LATEST, a.max_gap)


def _rank(a: OpInput) -> OpRecord:
    geos = list(dict.fromkeys([a.geo, *(a.call.geos or [])]))
    lowest_first = a.ctx.claim.assertion.direction is Direction.DOWN
    places = [a.read(a.call.series, g) for g in geos]
    return rank(places, a.geo, a.call.period or LATEST, not lowest_first)


def _per_capita(a: OpInput) -> OpRecord:
    population = a.read(a.call.population, a.geo)
    scale = unit_scale(a.series.unit) / unit_scale(population.unit)
    return per_capita(a.series, population, scale=scale, unit=per_person_unit(a.series.unit))


def _deflate(a: OpInput) -> OpRecord:
    return deflate(a.series, a.read(a.call.price_index, a.geo), a.call.base or LATEST)


def _needs(*names: str) -> frozenset[str]:
    return frozenset(names)


OPERATIONS: Mapping[OpName, OpSpec] = {
    "value_at": OpSpec(_needs("geo", "period"), _value_at),
    "change": OpSpec(_needs("geo", "start", "end", "kind"), _change),
    "cagr": OpSpec(_needs("geo", "start", "end"), _cagr),
    "trend": OpSpec(_needs("geo", "start", "end"), _trend, reads_months=True),
    "compare": OpSpec(_needs("geo", "geo_b", "period"), _compare),
    "rank": OpSpec(_needs("geo", "geos", "period"), _rank),
    "per_capita": OpSpec(_needs("geo", "population"), _per_capita, makes_series=True),
    "deflate": OpSpec(_needs("geo", "price_index", "base"), _deflate, makes_series=True),
}

# Required and optional arguments per operation, as the model writes them.
SIGNATURES: Mapping[OpName, tuple[frozenset[str], frozenset[str]]] = {
    name: (spec.required, spec.optional) for name, spec in OPERATIONS.items()
}
SERIES_OPS = frozenset(name for name, spec in OPERATIONS.items() if spec.makes_series)


def run_call(
    call: OpCall, read: SeriesReader, ctx: PlanContext, tolerances: Tolerances
) -> OpRecord:
    """Run one validated call, reading its own series first."""
    s = read(call.series, call.geo or "")
    gap = tolerances.max_period_gap.get(s.frequency)
    return OPERATIONS[call.op].run(OpInput(call, s, read, ctx, gap))
