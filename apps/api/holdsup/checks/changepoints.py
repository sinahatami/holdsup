"""Change points (P3.3, D025): where a series' trend turns, and claims that lean on one.

Cherry-picked claims often start or end at an unusual period: the top of a spike, the bottom
of a crash. Breaks are found with PELT (ruptures) on the period-to-period changes, so a steady
trend has none and a turn in it has one; a break is named by the period the trend turns at.
Peaks and troughs come from `ops.extremes`.

The flag: the claim's start or end is a peak or a trough, or within one period of a break, and
that value carries the claim. With it replaced by the typical level around it, the claim's
change goes the other way or shrinks by more than `changepoints.shrink`. A start or end that
makes the change look smaller is never flagged, and neither is a level, a rank or a trend.
"""

import math
from typing import Literal

import numpy as np
import ruptures as rpt  # type: ignore[import-untyped]  # ships no type hints
from pydantic import BaseModel

from holdsup.fmt import fmt
from holdsup.ops import (
    ChangeKind,
    OpError,
    OpRecord,
    Period,
    Series,
    change_between,
    compound_rate,
    parse_period,
    years_between,
)
from holdsup.ops.extremes import Extreme, extreme_at, noise_scale, typical_level
from holdsup.pipeline.claim import ClaimSpec, Direction
from holdsup.verdict.tolerances import Tolerances

# Fewer values than this show no trend worth splitting.
MIN_POINTS = 6
# Operations whose answer depends on two values, so a start or end can carry it.
FLAGGED_OPS = frozenset({"change", "cagr"})
# Operations whose series the heatmap shows: their breaks are marked on its axes.
SERIES_OPS = frozenset({"change", "cagr", "trend"})

Why = Literal["peak", "trough", "break"]
WHY_TEXT: dict[Why, str] = {
    "peak": "at a peak",
    "trough": "at a trough",
    "break": "where the trend turns",
}


class EndpointFlag(BaseModel):
    """A start or end that sits on a break or an extreme and carries the claim."""

    end: Literal["start", "end"]
    period: str
    why: Why
    value: float  # the series' value there
    typical: float  # the median of its neighbours within reach
    claimed: float  # the claim's change, as computed
    shifted: float  # the change with the typical level in its place


class ChangePoints(BaseModel):
    breaks: list[str]  # the periods where the trend turns, oldest first
    flags: list[EndpointFlag]


def change_points(
    claim: ClaimSpec, record: OpRecord, series: Series, *, tolerances: Tolerances
) -> ChangePoints | None:
    """Breaks in the series the claim's answer read, and the claim's start or end leaning on
    one. None for an answer that reads no window (a level, a rank, a comparison)."""
    if record.op not in SERIES_OPS:
        return None
    breaks = find_breaks(series)
    flags = endpoint_flags(claim, record, series, breaks, tolerances=tolerances)
    return ChangePoints(breaks=[str(b) for b in breaks], flags=flags)


def find_breaks(series: Series) -> list[Period]:
    """The periods where the trend turns: PELT with a squared-error cost on the changes from
    one period to the next, and a BIC-like penalty, 2 log(n) σ², with σ the robust noise of
    those changes. A level jump turns the trend twice, just before and after it."""
    periods = [p for p, _ in series.points]
    if len(periods) < MIN_POINTS:
        return []
    diffs = np.diff(np.asarray([v for _, v in series.points], dtype=float))
    sigma = noise_scale([float(d) for d in diffs])
    floor = 1e-12 * max(1.0, float(np.max(np.abs(diffs)))) ** 2  # a noiseless series
    penalty = 2 * math.log(len(diffs)) * max(sigma**2, floor)
    starts: list[int] = rpt.Pelt(model="l2", min_size=2, jump=1).fit(diffs).predict(pen=penalty)
    # A new run of changes from diffs[i] (values[i] to values[i + 1]): the trend turns at i.
    return [periods[i] for i in starts[:-1]]


def endpoint_flags(
    claim: ClaimSpec,
    record: OpRecord,
    series: Series,
    breaks: list[Period],
    *,
    tolerances: Tolerances,
) -> list[EndpointFlag]:
    """The claim's start and end that sit on a break or an extreme and carry the claim."""
    direction = claim.assertion.direction
    if record.op not in FLAGGED_OPS or direction not in (Direction.UP, Direction.DOWN):
        return []
    start, end = parse_period(record.inputs[0].period), parse_period(record.inputs[1].period)
    if start.frequency is not series.frequency:
        return []
    reach = tolerances.sweep.reach * series.frequency.per_year
    a, b = record.inputs[0].value, record.inputs[1].value
    claimed = _rerun(record, a, b, start, end)
    flags = []
    for which, at in (("start", start), ("end", end)):
        why = _why(series, at, breaks, reach)
        typical = typical_level(series, at, reach)
        if why is None or typical is None:
            continue
        try:
            shifted = _rerun(
                record, typical if which == "start" else a, typical if which == "end" else b,
                start, end,
            )  # fmt: skip
        except OpError:
            continue
        if _carries(record, claimed, shifted, direction, tolerances.changepoints.shrink):
            flags.append(
                EndpointFlag(
                    end="start" if which == "start" else "end",
                    period=str(at),
                    why=why,
                    value=a if which == "start" else b,
                    typical=typical,
                    claimed=claimed,
                    shifted=shifted,
                )
            )
    return flags


def flag_text(flag: EndpointFlag, unit: str | None) -> str:
    """The flag as the verdict's reason says it, with numbers only from the flag."""
    verb = "starts" if flag.end == "start" else "ends"
    u = "" if not unit else unit if unit.startswith("%") else f" {unit}"
    return (
        f"it {verb} {WHY_TEXT[flag.why]} ({flag.period}): from the usual level around then, "
        f"{fmt(flag.typical)}, the change is {_signed(flag.shifted)}{u} rather than "
        f"{_signed(flag.claimed)}{u}"
    )


def _signed(x: float) -> str:
    text = fmt(x)
    return f"+{text}" if x > 0 and text != "0" else text


def _why(series: Series, at: Period, breaks: list[Period], reach: int) -> Why | None:
    extreme = extreme_at(series, at, reach)
    if extreme is not None:
        return "peak" if extreme is Extreme.PEAK else "trough"
    if any(abs(at.ordinal - b.ordinal) <= 1 for b in breaks):
        return "break"
    return None


def _rerun(record: OpRecord, a: float, b: float, start: Period, end: Period) -> float:
    """The claim's change from `a` to `b` over its own window, by its own operation."""
    if record.op == "cagr":
        return compound_rate(a, b, years_between(start, end))
    return change_between(a, b, ChangeKind(str(record.args["kind"])))


def _carries(
    record: OpRecord, claimed: float, shifted: float, direction: Direction, shrink: float
) -> bool:
    """Whether the typical level in place of the endpoint turns the change around or shrinks
    it by more than `shrink`, measured in the claimed direction. A ratio is compared on a log
    scale, so halving and doubling are the same size."""
    sign = 1.0 if direction is Direction.UP else -1.0
    if record.op == "change" and str(record.args["kind"]) == ChangeKind.RATIO:
        if claimed <= 0 or shifted <= 0:
            return False
        claimed, shifted = math.log(claimed), math.log(shifted)
    size, new = sign * claimed, sign * shifted
    if size <= 0:
        return False  # the claim's own window does not move the claimed way
    return new < (1 - shrink) * size
