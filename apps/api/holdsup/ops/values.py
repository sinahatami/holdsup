"""Operations that read values at given periods: value_at, change, cagr, compare, rank."""

import math
from collections.abc import Sequence

from holdsup.ops.change import ChangeKind, change_between, compound_rate
from holdsup.ops.periods import LATEST, Period, parse_period, same_frequency, years_between
from holdsup.ops.record import DataPoint, Flag, FlagCode, OpError, OpRecord
from holdsup.ops.series import Series

_CHANGE_UNITS = {
    ChangeKind.PERCENT: "%",
    ChangeKind.PERCENTAGE_POINTS: "percentage points",
    ChangeKind.RATIO: None,
}


def resolve(series: Series, period: str) -> Period:
    """The requested period in the series' frequency; `latest` is its last period."""
    if period == LATEST:
        return series.last
    p = parse_period(period)
    if p.frequency is not series.frequency:
        raise OpError(
            f"{period} is {p.frequency} but the {series.geo} series is {series.frequency}"
        )
    return p


def lookup(
    series: Series, period: str, max_distance: int | None = None
) -> tuple[DataPoint, list[Flag]]:
    """The value at `period`, else at the nearest period (the earlier one on a tie), flagged."""
    wanted = resolve(series, period)
    value = series.get(wanted)
    if value is not None:
        return series.point(wanted, value), []
    used, value = min(
        series.points, key=lambda pv: (abs(pv[0].ordinal - wanted.ordinal), pv[0].ordinal)
    )
    distance = abs(used.ordinal - wanted.ordinal)
    if max_distance is not None and distance > max_distance:
        raise OpError(
            f"{series.geo} has no value within {max_distance} periods of {wanted} "
            f"(nearest is {used})"
        )
    flag = Flag(
        code=FlagCode.NEAREST_PERIOD,
        detail=f"{series.geo} has no value for {wanted}; used {used}",
        requested=str(wanted),
        used=str(used),
        distance=distance,
    )
    return series.point(used, value), [flag]


def value_at(series: Series, period: str, max_distance: int | None = None) -> OpRecord:
    point, flags = lookup(series, period, max_distance)
    return OpRecord(
        op="value_at",
        args={"geo": series.geo, "period": period, "max_distance": max_distance},
        inputs=[point],
        value=point.value,
        unit=series.unit,
        flags=flags,
    )


def _window(
    series: Series, start: str, end: str, max_distance: int | None
) -> tuple[DataPoint, DataPoint, list[Flag]]:
    a, flags_a = lookup(series, start, max_distance)
    b, flags_b = lookup(series, end, max_distance)
    if parse_period(a.period).ordinal >= parse_period(b.period).ordinal:
        raise OpError(f"{series.geo}: the window resolves to {a.period}..{b.period}")
    return a, b, flags_a + flags_b


def change(
    series: Series, start: str, end: str, kind: ChangeKind, max_distance: int | None = None
) -> OpRecord:
    a, b, flags = _window(series, start, end, max_distance)
    unit = _CHANGE_UNITS.get(kind, series.unit)
    return OpRecord(
        op="change",
        args={
            "geo": series.geo,
            "start": start,
            "end": end,
            "kind": str(kind),
            "max_distance": max_distance,
        },
        inputs=[a, b],
        value=change_between(a.value, b.value, kind),
        unit=unit,
        flags=flags,
    )


def cagr(series: Series, start: str, end: str, max_distance: int | None = None) -> OpRecord:
    a, b, flags = _window(series, start, end, max_distance)
    years = years_between(parse_period(a.period), parse_period(b.period))
    return OpRecord(
        op="cagr",
        args={"geo": series.geo, "start": start, "end": end, "max_distance": max_distance},
        inputs=[a, b],
        value=compound_rate(a.value, b.value, years),
        extras={"years": years},
        unit="% per year",
        flags=flags,
    )


def compare(a: Series, b: Series, period: str, max_distance: int | None = None) -> OpRecord:
    """`a` minus `b`, and `a` divided by `b`, at the same period."""
    if a.frequency is not b.frequency:
        raise OpError(f"{a.geo} is {a.frequency} but {b.geo} is {b.frequency}")
    if a.unit and b.unit and a.unit != b.unit:
        raise OpError(f"{a.geo} is in {a.unit} but {b.geo} is in {b.unit}")
    pa, flags_a = lookup(a, period, max_distance)
    pb, flags_b = lookup(b, period, max_distance)
    flags = flags_a + flags_b
    extras: dict[str, float] = {}
    ratio = pa.value / pb.value if pb.value != 0 else math.inf
    if math.isfinite(ratio):
        extras["ratio"] = ratio
    else:
        flags.append(
            Flag(code=FlagCode.ZERO_DENOMINATOR, detail=f"{b.geo} is 0 or too small for a ratio")
        )
    return OpRecord(
        op="compare",
        args={"geo_a": a.geo, "geo_b": b.geo, "period": period, "max_distance": max_distance},
        inputs=[pa, pb],
        value=pa.value - pb.value,
        extras=extras,
        unit=a.unit or b.unit,
        flags=flags,
    )


def rank(series: Sequence[Series], geo: str, period: str, highest_first: bool = True) -> OpRecord:
    """Position of `geo` among the places with a value for exactly `period` (1 = first).

    Equal values share a position (1, 2, 2, 4). Places without a value for the period are
    left out and flagged, never filled from a neighbouring period.
    """
    geos = [s.geo for s in series]
    if len(set(geos)) != len(geos):
        raise OpError("rank: a place appears twice")
    by_geo = {s.geo: s for s in series}
    if geo not in by_geo:
        raise OpError(f"rank: {geo} is not among the places")
    target = by_geo[geo]
    wanted = resolve(target, period)
    present: list[DataPoint] = []
    missing: list[str] = []
    for s in series:
        same_frequency(wanted, s.first)
        value = s.get(wanted)
        if value is None:
            missing.append(s.geo)
        else:
            present.append(s.point(wanted, value))
    if geo in missing:
        raise OpError(f"rank: {geo} has no value for {wanted}")
    sign = -1.0 if highest_first else 1.0
    present.sort(key=lambda p: (sign * p.value, p.geo))
    mine = next(p.value for p in present if p.geo == geo)
    position = 1 + sum(1 for p in present if sign * p.value < sign * mine)
    flags: list[Flag] = []
    tied = [p.geo for p in present if p.value == mine and p.geo != geo]
    if tied:
        flags.append(
            Flag(code=FlagCode.TIE, detail=f"{geo} ties with {', '.join(tied)}", items=tied)
        )
    if missing:
        flags.append(
            Flag(
                code=FlagCode.MISSING_GEOS,
                detail=f"no value for {wanted}: {', '.join(missing)}",
                items=missing,
            )
        )
    return OpRecord(
        op="rank",
        args={"geos": geos, "geo": geo, "period": period, "highest_first": highest_first},
        inputs=present,
        value=float(position),
        extras={"of": float(len(present))},
        unit=None,
        flags=flags,
    )
