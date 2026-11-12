"""The cherry-pick sweep (P3.1, D023): the claim's direction over every time window.

A claim can be right for the years it names and still rest on a lucky choice of them: the
bottom of a crash, the top of a spike. The sweep reruns the claim's own operation (`change`,
`cagr` or `trend`, with the same kind) for every start and end the series allows, and asks of
each window what the claim concludes without its number: did the value rise, fall or stay flat
as claimed? The number itself is checked for the stated window only, by the verdict rules:
another window gives another number for every claim, honest or not.

Windows keep the claim's place in the year: a claim from March 2020 to September 2026 is rerun
from every March to every September, so a season never decides a cell.

The share the verdict uses counts the nearby windows only: start within `reach` years of the
claim's start, end up to `reach` years before the claim's end. Ends never move later: after
"latest" there is nothing, and an explicit end was the speaker's choice of data.
"""

from pydantic import BaseModel

from holdsup.ops import (
    ChangeKind,
    OpError,
    OpRecord,
    Period,
    Series,
    cagr,
    change,
    parse_period,
    trend,
    years_between,
)
from holdsup.ops.values import resolve
from holdsup.pipeline.claim import ClaimSpec
from holdsup.verdict.rules import direction_judge
from holdsup.verdict.tolerances import Tolerances

SWEPT_OPS = frozenset({"change", "cagr", "trend"})
# The most recent years a grid covers (more if the claim's own window is older): a series that
# starts in 1792 would otherwise give some 27,000 windows. The share never needs more.
GRID_YEARS = 50


class Sweep(BaseModel):
    """The claim recomputed over every window of its series: the heatmap's data."""

    op: str  # what each cell reruns: change, cagr or trend
    kind: str | None = None  # a change's kind: absolute, percent, percentage_points, ratio
    unit: str | None = None  # the unit of `values`
    starts: list[str]  # rows: start periods, oldest first
    ends: list[str]  # columns: end periods, oldest first
    # values[row][column]: None where the end is not after the start, or the data has no answer
    # (a missing value, a percent change from 0).
    values: list[list[float | None]]
    holds: list[list[bool | None]]  # whether the claim's direction holds in that window
    claim_start: str  # the claim's own window, as its operation read it
    claim_end: str
    near_starts: list[str]  # the rows and columns of the nearby windows the share counts
    near_ends: list[str]
    counted: int  # nearby windows with an answer
    held: int  # of which the claim's direction holds
    share: float | None  # held / counted; None for a claim window shorter than `min_years`

    @property
    def windows(self) -> int:
        """Every window with an answer."""
        return sum(v is not None for row in self.values for v in row)


def sweep(
    claim: ClaimSpec,
    record: OpRecord,
    series: Series,
    *,
    unit: str | None,
    tolerances: Tolerances,
) -> Sweep | None:
    """The sweep for a claim answered by `record`, which ran on `series`. None when the claim
    picked no window: it gives no direction, or its operation reads a single period."""
    if record.op not in SWEPT_OPS or claim.assertion.direction is None:
        return None
    try:
        start, end = _own_window(record, series)
    except OpError:
        return None
    holds = direction_judge(claim, unit=unit, tolerances=tolerances)
    reach = tolerances.sweep.reach
    first_year = max(series.first.year, min(start.year - reach, series.last.year - GRID_YEARS + 1))
    starts, ends = _axis(series, start.sub, first_year), _axis(series, end.sub, first_year)

    values: list[list[float | None]] = []
    held: list[list[bool | None]] = []
    for s in starts:
        cells = [_rerun(record, series, s, e) for e in ends]
        values.append([None if r is None else r.value for r in cells])
        held.append([None if r is None else holds(r) for r in cells])

    near_rows: list[int] = []
    near_cols: list[int] = []
    if years_between(start, end) >= tolerances.sweep.min_years:
        near_rows = [i for i, p in enumerate(starts) if abs(p.year - start.year) <= reach]
        near_cols = [j for j, p in enumerate(ends) if 0 <= end.year - p.year <= reach]
    near = [held[i][j] for i in near_rows for j in near_cols]
    counted = sum(h is not None for h in near)
    n_held = sum(h is True for h in near)
    return Sweep(
        op=record.op,
        kind=str(record.args["kind"]) if record.op == "change" else None,
        unit=record.unit,
        starts=[str(p) for p in starts],
        ends=[str(p) for p in ends],
        values=values,
        holds=held,
        claim_start=str(start),
        claim_end=str(end),
        near_starts=[str(starts[i]) for i in near_rows],
        near_ends=[str(ends[j]) for j in near_cols],
        counted=counted,
        held=n_held,
        share=n_held / counted if near_rows and counted else None,
    )


def _own_window(record: OpRecord, series: Series) -> tuple[Period, Period]:
    """The claim's window as its operation read it: the two values a change or growth rate
    used (after any nearest-period substitution), or the span a trend was asked to fit."""
    if record.op == "trend":
        return resolve(series, str(record.args["start"])), resolve(series, str(record.args["end"]))
    start, end = parse_period(record.inputs[0].period), parse_period(record.inputs[1].period)
    if start.frequency is not series.frequency:
        raise OpError(f"the record is {start.frequency} but the series is {series.frequency}")
    return start, end


def _axis(series: Series, sub: int, first_year: int) -> list[Period]:
    """One period a year, at the same place in the year (`sub`), within the series' span."""
    lo, hi = series.first.ordinal, series.last.ordinal
    periods = (Period(y, sub, series.frequency) for y in range(first_year, series.last.year + 1))
    return [p for p in periods if lo <= p.ordinal <= hi]


def _rerun(record: OpRecord, series: Series, start: Period, end: Period) -> OpRecord | None:
    """The claim's operation over another window, or None where it has no answer. A change or
    growth rate reads exactly `start` and `end`, never a neighbouring period; a trend fits the
    values between them."""
    if start.ordinal >= end.ordinal:
        return None
    a, b = str(start), str(end)
    try:
        if record.op == "change":
            return change(series, a, b, ChangeKind(str(record.args["kind"])), max_distance=0)
        if record.op == "cagr":
            return cagr(series, a, b, max_distance=0)
        return trend(series, a, b, keep_inputs=False)
    except OpError:
        return None
