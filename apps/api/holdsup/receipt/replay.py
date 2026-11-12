"""Replay HoldsUp's calculations from the values each one read.

This module is copied whole into every exported notebook, so it uses the standard library
only and runs on any Python 3.10 or later without HoldsUp installed. Each function repeats
the arithmetic of one operation in `holdsup/ops/`; `check(step)` replays a recorded step and
asserts that it gives the numbers the receipt shows.

A step is a recorded operation as plain data: `{"op": ..., "args": {...}, "inputs": [{"geo",
"period", "value"}, ...], "value": ..., "extras": {...}, "series": [...] or None}`. Periods
are written as sources write them: "2024", "2024-S1" (a half-year), "2024-Q3", "2024-03".
"""

import math
from typing import Any

# A recorded step or one of its points, as plain data (JSON types).
Data = dict[str, Any]
Grid = list[list[float | None]]

# How close a replayed number must be to the recorded one: the same arithmetic in the same
# order gives the same number; this only absorbs a last-digit difference on another machine.
REL_TOL = 1e-9
ABS_TOL = 1e-9

CHECKED: list[str] = []  # every figure that matched, in order


class ReplayError(AssertionError):
    """A replayed number differs from the recorded one."""


# --- periods ------------------------------------------------------------------------------


def period(text: str) -> tuple[int, int, int]:
    """(year, part of the year, parts in a year): "2024-Q3" → (2024, 3, 4), "2024" → (2024, 1, 1)."""
    year, _, rest = text.partition("-")
    if not rest:
        return int(year), 1, 1
    if rest[0] == "S":
        return int(year), int(rest[1:]), 2
    if rest[0] == "Q":
        return int(year), int(rest[1:]), 4
    return int(year), int(rest), 12


def ordinal(text: str) -> int:
    """A count of periods of the same length: consecutive periods differ by 1."""
    year, part, per_year = period(text)
    return year * per_year + part - 1


def time_of(text: str) -> float:
    """Where a period starts, in years: "2024-Q3" → 2024.5 (the x of a trend line)."""
    year, part, per_year = period(text)
    return year + (part - 1) / per_year


def years_between(start: str, end: str) -> float:
    return (ordinal(end) - ordinal(start)) / period(start)[2]


def label(year: int, part: int, per_year: int) -> str:
    """The period as sources write it, from its parts."""
    if per_year == 1:
        return str(year)
    if per_year == 2:
        return f"{year}-S{part}"
    if per_year == 4:
        return f"{year}-Q{part}"
    return f"{year}-{part:02d}"


# --- arithmetic ---------------------------------------------------------------------------


def change_between(start: float, end: float, kind: str) -> float:
    """The change from `start` to `end`: absolute and percentage points subtract, percent is
    relative to the start, ratio divides."""
    if kind in ("absolute", "percentage_points"):
        return end - start
    if start == 0:
        raise ZeroDivisionError(f"a {kind} change from 0")
    if kind == "percent":
        return (end - start) / abs(start) * 100
    return end / start


def compound_rate(start: float, end: float, years: float) -> float:
    """The constant yearly growth in % that takes `start` to `end` in `years`."""
    if years <= 0 or start <= 0 or end < 0:
        raise ValueError("compound growth needs a positive start, an end after it")
    rate: float = ((end / start) ** (1 / years) - 1) * 100  # float ** float is typed Any
    return rate


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float | None]:
    """Ordinary least squares, x centred: (slope, intercept, R²); R² is None when every y is
    equal."""
    n = len(xs)
    mx, my = math.fsum(xs) / n, math.fsum(ys) / n
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = math.fsum((y - my) ** 2 for y in ys)
    if min(ys) == max(ys) or ss_tot == 0:
        return slope, intercept, None
    ss_res = math.fsum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    return slope, intercept, max(0.0, 1 - ss_res / ss_tot)


# --- the operations -----------------------------------------------------------------------


def _paired(inputs: list[Data], at: str) -> tuple[float, float]:
    """A transform reads two series of one place, written one after the other: the series,
    then the other (population or price index). A period both have appears twice: the series'
    value first, the other's last."""
    values = [p["value"] for p in inputs if p["period"] == at]
    return values[0], values[-1]


def _shared(inputs: list[Data]) -> list[str]:
    """The periods both series have (each appears twice), in order."""
    periods = [p["period"] for p in inputs]
    return sorted({p for p in periods if periods.count(p) > 1}, key=ordinal)


def replay_value_at(step: Data) -> Data:
    return {"value": step["inputs"][0]["value"]}


def replay_change(step: Data) -> Data:
    a, b = step["inputs"]
    return {"value": change_between(a["value"], b["value"], step["args"]["kind"])}


def replay_cagr(step: Data) -> Data:
    a, b = step["inputs"]
    years = years_between(a["period"], b["period"])
    return {"value": compound_rate(a["value"], b["value"], years), "extras": {"years": years}}


def replay_trend(step: Data) -> Data:
    points = step["inputs"]
    xs = [time_of(p["period"]) for p in points]
    slope, intercept, r2 = linear_fit(xs, [p["value"] for p in points])
    extras = {
        "n": float(len(points)),
        "fitted_start": intercept + slope * xs[0],
        "fitted_end": intercept + slope * xs[-1],
    }
    if r2 is not None:
        extras["r2"] = r2
    return {"value": slope, "extras": extras}


def replay_compare(step: Data) -> Data:
    a, b = step["inputs"]
    out: Data = {"value": a["value"] - b["value"], "extras": {}}
    if b["value"] != 0 and math.isfinite(a["value"] / b["value"]):
        out["extras"]["ratio"] = a["value"] / b["value"]
    return out


def replay_rank(step: Data) -> Data:
    """The place's position among those with a value; equal values share one (1, 2, 2, 4)."""
    sign = -1.0 if step["args"]["highest_first"] else 1.0
    places = step["inputs"]
    mine = next(p["value"] for p in places if p["geo"] == step["args"]["geo"])
    position = 1 + sum(1 for p in places if sign * p["value"] < sign * mine)
    return {"value": float(position), "extras": {"of": float(len(places))}}


def replay_per_capita(step: Data) -> Data:
    """The series times the unit scale, divided by the population, period by period."""
    scale = step["args"]["scale"]
    out = []
    for at in _shared(step["inputs"]):
        value, people = _paired(step["inputs"], at)
        out.append({"period": at, "value": value * scale / people})
    return {"series": out}


def replay_deflate(step: Data) -> Data:
    """Values in prices of the base period: value × index at the base ÷ index in its period.
    "latest" is the price index's last period, which ends the inputs."""
    base = step["args"]["base"]
    if base == "latest":
        base = step["inputs"][-1]["period"]
    base_index = _paired(step["inputs"], base)[1]
    out = []
    for at in _shared(step["inputs"]):
        value, index = _paired(step["inputs"], at)
        out.append({"period": at, "value": value * base_index / index})
    return {"series": out}


def replay_chain_index(step: Data) -> Data:
    """A price index from yearly changes in %: 100 in the base period, and each period
    1 + change/100 times the one before; back from the base by dividing."""
    rates = {ordinal(p["period"]): p["value"] for p in step["inputs"]}
    per_year = period(step["inputs"][0]["period"])[2]
    start = ordinal(step["args"]["base"])
    index = {start: 100.0}
    o = start + 1
    while o in rates:
        index[o] = index[o - 1] * (1 + rates[o] / 100)
        o += 1
    o = start
    while o in rates:
        index[o - 1] = index[o] / (1 + rates[o] / 100)
        o -= 1
    out = [
        {"period": label(o // per_year, o % per_year + 1, per_year), "value": index[o]}
        for o in sorted(index)
    ]
    return {"series": out}


REPLAYS = {
    "value_at": replay_value_at,
    "change": replay_change,
    "cagr": replay_cagr,
    "trend": replay_trend,
    "compare": replay_compare,
    "rank": replay_rank,
    "per_capita": replay_per_capita,
    "deflate": replay_deflate,
    "chain_index": replay_chain_index,
}


# --- comparing with the receipt -------------------------------------------------------------


def same(what: str, got: float | None, recorded: float | None) -> None:
    """Raise unless the replayed number is the recorded one; note it when it is."""
    if got is None or recorded is None:
        if got is not recorded:
            raise ReplayError(f"{what}: replayed {got!r}, the receipt has {recorded!r}")
        return  # no answer on either side: nothing to count
    if not math.isclose(got, recorded, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        raise ReplayError(f"{what}: replayed {got!r}, the receipt has {recorded!r}")
    CHECKED.append(what)


def check(step: Data, name: str = "") -> None:
    """Replay a recorded step and compare every number it gave: its value, its other
    figures, and each period of a series it made."""
    name = name or step["op"]
    out = REPLAYS[step["op"]](step)
    if "value" in out:
        same(name, out["value"], step["value"])
    extras = out.get("extras", {})
    if extras.keys() != step["extras"].keys():
        raise ReplayError(f"{name}: replayed {sorted(extras)}, not {sorted(step['extras'])}")
    for key, value in extras.items():
        same(f"{name} {key}", value, step["extras"][key])
    if "series" in out:
        made = {p["period"]: p["value"] for p in out["series"]}
        recorded = {p["period"]: p["value"] for p in step["series"]}
        if made.keys() != recorded.keys():
            raise ReplayError(f"{name}: replayed periods {sorted(made)}, not {sorted(recorded)}")
        for at, value in recorded.items():
            same(f"{name} {at}", made[at], value)
    print(f"{name}: matches the receipt")


# --- the time-window grid -----------------------------------------------------------------


def window_value(
    op: str,
    kind: str | None,
    values: dict[str, float],
    start: str,
    end: str,
    points: list[tuple[str, float]],
) -> float | None:
    """The claim's operation over one window, or None where it has no answer: a change or a
    growth rate reads exactly the start and the end; a trend fits every value between."""
    if ordinal(end) <= ordinal(start):
        return None
    try:
        if op == "trend":
            inside = [(p, v) for p, v in points if ordinal(start) <= ordinal(p) <= ordinal(end)]
            if len(inside) < 2:
                return None
            return linear_fit([time_of(p) for p, _ in inside], [v for _, v in inside])[0]
        if start not in values or end not in values:
            return None
        if op == "cagr":
            return compound_rate(values[start], values[end], years_between(start, end))
        return change_between(values[start], values[end], kind or "percent")
    except (ArithmeticError, ValueError):
        return None


def check_sweep(sweep: Data, series: list[Data]) -> None:
    """Replay every window of the grid from the series as the check read it, then count the
    nearby windows where the claim's direction holds (whether it holds is the verdict rules'
    call, written in `holds`)."""
    points = [(p["period"], p["value"]) for p in series]
    values = dict(points)
    for i, start in enumerate(sweep["starts"]):
        for j, end in enumerate(sweep["ends"]):
            got = window_value(sweep["op"], sweep["kind"], values, start, end, points)
            got = got if got is None or math.isfinite(got) else None
            same(f"window {start} to {end}", got, sweep["values"][i][j])
    rows = [sweep["starts"].index(p) for p in sweep["near_starts"]]
    cols = [sweep["ends"].index(p) for p in sweep["near_ends"]]
    near = [sweep["holds"][i][j] for i in rows for j in cols]
    counted = sum(h is not None for h in near)
    held = sum(h is True for h in near)
    same("nearby windows counted", float(counted), float(sweep["counted"]))
    same("nearby windows where it holds", float(held), float(sweep["held"]))
    share = held / counted if rows and counted else None
    same("share of nearby windows", share, sweep["share"])
    print("every window and the nearby share match the receipt")
