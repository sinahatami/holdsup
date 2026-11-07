"""The trend operation: a straight line through a window of a series."""

import math
from dataclasses import dataclass

from holdsup.ops.record import Flag, FlagCode, OpError, OpRecord, finite
from holdsup.ops.series import Series
from holdsup.ops.values import resolve


@dataclass(frozen=True)
class LinearFit:
    slope: float
    intercept: float
    r2: float | None  # None when every y is equal

    def at(self, x: float) -> float:
        return self.intercept + self.slope * x


def linear_fit(xs: list[float], ys: list[float]) -> LinearFit:
    """Ordinary least squares, with x centred for numerical stability."""
    n = len(xs)
    if n != len(ys) or n < 2:
        raise OpError("a linear fit needs at least two points")
    mx, my = math.fsum(xs) / n, math.fsum(ys) / n
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise OpError("a linear fit needs at least two different times")
    sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = finite(sxy / sxx, "the slope")
    intercept = my - slope * mx
    ss_tot = math.fsum((y - my) ** 2 for y in ys)
    # Exact test first: rounding in `my` can leave ss_tot tiny instead of 0 for equal values;
    # ss_tot can also underflow to 0 for values that differ by almost nothing.
    if min(ys) == max(ys) or ss_tot == 0:
        return LinearFit(slope, intercept, None)
    ss_res = math.fsum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    return LinearFit(slope, intercept, max(0.0, 1 - ss_res / ss_tot))


def trend(series: Series, start: str, end: str) -> OpRecord:
    """Slope per year of a least-squares line through every value from `start` to `end`."""
    lo, hi = resolve(series, start), resolve(series, end)
    if lo.ordinal >= hi.ordinal:
        raise OpError(f"{series.geo}: the window {lo}..{hi} is empty or reversed")
    window = [(p, v) for p, v in series.points if lo.ordinal <= p.ordinal <= hi.ordinal]
    if len(window) < 2:
        raise OpError(f"{series.geo} has fewer than two values from {lo} to {hi}")
    fit = linear_fit([p.time for p, _ in window], [v for _, v in window])

    flags: list[Flag] = []
    first, last = window[0][0], window[-1][0]
    if first != lo or last != hi:
        flags.append(
            Flag(
                code=FlagCode.WINDOW_NOT_COVERED,
                detail=f"{series.geo} has values from {first} to {last} in {lo}..{hi}",
                requested=f"{lo}..{hi}",
                used=f"{first}..{last}",
            )
        )
    if len(window) == 2:
        flags.append(Flag(code=FlagCode.FEW_POINTS, detail="a line through two points"))
    extras = {
        "n": float(len(window)),
        "fitted_start": fit.at(first.time),
        "fitted_end": fit.at(last.time),
    }
    if fit.r2 is None:
        flags.append(Flag(code=FlagCode.CONSTANT_SERIES, detail="every value is equal"))
    else:
        extras["r2"] = fit.r2
    unit = f"{series.unit} per year" if series.unit else None
    return OpRecord(
        op="trend",
        args={"geo": series.geo, "start": start, "end": end},
        inputs=[series.point(p, v) for p, v in window],
        value=fit.slope,
        extras=extras,
        unit=unit,
        flags=flags,
    )
