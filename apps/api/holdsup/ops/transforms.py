"""Operations that turn one series into another: per_capita, deflate, chain_index."""

from holdsup.ops.periods import Period, parse_period, same_frequency
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


def chain_index(rates: Series, base: str) -> OpRecord:
    """A price index from changes on the previous period in % (yearly inflation rates): 100 in
    `base`, and each period `1 + rate / 100` times the one before. The rate of a period is its
    change from the period before, so the index reaches back one period before the first rate.
    Only periods joined to `base` by consecutive rates are chained; the rest are flagged."""
    start = parse_period(base)
    same_frequency(start, rates.first)
    per_year = rates.frequency.per_year
    by_ordinal = {p.ordinal: v for p, v in rates.points}
    index = {start.ordinal: 100.0}

    def factor(ordinal: int) -> float:
        growth = 1 + by_ordinal[ordinal] / 100
        if growth <= 0:
            raise OpError(f"a change of {by_ordinal[ordinal]}% leaves no price level to chain")
        return growth

    o = start.ordinal + 1
    while o in by_ordinal:  # forward: index[o] = index[o - 1] × (1 + rate[o])
        index[o] = finite(index[o - 1] * factor(o), f"the index in period {o}")
        o += 1
    o = start.ordinal
    while o in by_ordinal:  # backward: index[o - 1] = index[o] ÷ (1 + rate[o])
        index[o - 1] = finite(index[o] / factor(o), f"the index in period {o - 1}")
        o -= 1
    if len(index) == 1:
        raise OpError(f"no change in % next to the base period {base} to chain from")
    used = set(index) - {min(index)}  # the first index value needs no rate of its own
    left_out = [str(p) for p, _ in rates.points if p.ordinal not in used]
    flags = []
    if left_out:
        flags.append(
            Flag(
                code=FlagCode.MISSING_PERIODS,
                detail=f"left out (not joined to {base} by consecutive changes): "
                + ", ".join(left_out),
                items=left_out,
            )
        )
    periods = sorted(index)
    out = [
        rates.point(Period(o // per_year, o % per_year + 1, rates.frequency), index[o])
        for o in periods
    ]
    return OpRecord(
        op="chain_index",
        args={"geo": rates.geo, "base": base},
        inputs=rates.data_points(),
        series=out,
        unit=f"index, {base}=100",
        flags=flags,
    )
