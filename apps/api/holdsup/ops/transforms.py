"""Operations that turn one series into another: per_capita, deflate."""

from holdsup.ops.periods import Period
from holdsup.ops.record import DataPoint, Flag, FlagCode, OpError, OpRecord, finite
from holdsup.ops.series import Series
from holdsup.ops.values import resolve


def _pair(
    series: Series, other: Series, role: str
) -> tuple[list[tuple[Period, float, float]], list[Flag]]:
    """(period, series value, other value) for the periods both have, plus a flag naming the
    periods only one of them has."""
    if other.geo != series.geo:
        raise OpError(f"the {role} is for {other.geo}, not {series.geo}")
    if other.frequency is not series.frequency:
        raise OpError(f"the {role} is {other.frequency} but the series is {series.frequency}")
    mine = dict(series.points)
    theirs = dict(other.points)
    shared = [(p, v, theirs[p]) for p, v in series.points if p in theirs]
    if not shared:
        raise OpError(f"the series and the {role} share no period")
    dropped = sorted(mine.keys() ^ theirs.keys(), key=lambda p: p.ordinal)
    flags = []
    if dropped:
        items = [str(p) for p in dropped]
        flags.append(
            Flag(
                code=FlagCode.MISSING_PERIODS,
                detail=f"left out (only in one of series and {role}): {', '.join(items)}",
                items=items,
            )
        )
    return shared, flags


def per_capita(
    series: Series, population: Series, scale: float = 1.0, unit: str | None = None
) -> OpRecord:
    """`series × scale ÷ population`, period by period.

    `scale` converts units (1e6 for million euros over persons); code sets it from the
    catalog's units, never the model.
    """
    rows, flags = _pair(series, population, "population")
    out: list[DataPoint] = []
    for p, value, people in rows:
        if people <= 0:
            raise OpError(f"population of {series.geo} in {p} is not positive")
        out.append(series.point(p, finite(value * scale / people, f"the value per person in {p}")))
    return OpRecord(
        op="per_capita",
        args={"geo": series.geo, "scale": scale},
        inputs=series.data_points() + population.data_points(),
        series=out,
        unit=unit,
        flags=flags,
    )


def deflate(series: Series, price_index: Series, base: str) -> OpRecord:
    """Values in prices of the `base` period: `value × index[base] ÷ index[period]`."""
    rows, flags = _pair(series, price_index, "price index")
    base_period = resolve(price_index, base)
    base_index = price_index.get(base_period)
    if base_index is None or base_index <= 0:
        raise OpError(f"the price index has no positive value for the base period {base_period}")
    out: list[DataPoint] = []
    for p, value, index in rows:
        if index <= 0:
            raise OpError(f"the price index must be positive (got {index} in {p})")
        out.append(series.point(p, finite(value * base_index / index, f"the real value in {p}")))
    unit = f"{series.unit}, {base_period} prices" if series.unit else None
    return OpRecord(
        op="deflate",
        args={"geo": series.geo, "base": base},
        inputs=series.data_points() + price_index.data_points(),
        series=out,
        unit=unit,
        flags=flags,
    )
