"""The notebook's arithmetic (`holdsup/receipt/replay.py`) against HoldsUp's own operations: a
record made by `holdsup.ops` and replayed from its inputs gives the same numbers."""

import ast
import sys
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from holdsup.ops import (
    ChangeKind,
    OpRecord,
    Series,
    cagr,
    chain_index,
    change,
    compare,
    deflate,
    per_capita,
    rank,
    trend,
    value_at,
)
from holdsup.receipt import replay
from holdsup.receipt.notebook import REPLAY_SOURCE


def step(record: OpRecord) -> dict[str, Any]:  # Any: the record as JSON data
    return record.model_dump(mode="json")


@pytest.fixture(autouse=True)
def _fresh_tally() -> None:
    replay.CHECKED.clear()


def test_it_imports_the_standard_library_only() -> None:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(REPLAY_SOURCE)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported and imported <= sys.stdlib_module_names, imported


@pytest.mark.parametrize(
    ("text", "parts", "time"),
    [("2024", (2024, 1, 1), 2024.0), ("2024-S2", (2024, 2, 2), 2024.5),
     ("2024-Q3", (2024, 3, 4), 2024.5), ("2024-03", (2024, 3, 12), 2024 + 2 / 12)],
)  # fmt: skip
def test_periods(text: str, parts: tuple[int, int, int], time: float) -> None:
    assert replay.period(text) == parts
    assert replay.time_of(text) == pytest.approx(time)
    assert replay.label(*parts) == text
    assert replay.years_between(text, text) == 0


def test_every_operation_on_a_few_values() -> None:
    it = Series.from_values("IT", {"2015": 10.0, "2016": 12.0, "2017": 11.0, "2019": 15.0}, "%")
    de = Series.from_values("DE", {"2015": 5.0, "2016": 6.0, "2017": 11.0, "2019": 4.0}, "%")
    fr = Series.from_values("FR", {"2017": 11.0, "2019": 9.0}, "%")
    records = [
        value_at(it, "2018", max_distance=1),  # the nearest period, 2017
        *(change(it, "2015", "2019", kind) for kind in ChangeKind),
        cagr(it, "2015", "latest"),
        trend(it, "2015", "2019"),
        compare(it, de, "2019"),
        compare(it, Series.from_values("ES", {"2019": 0.0}, "%"), "2019"),  # no ratio
        rank([it, de, fr], "IT", "2017"),  # a tie: 1, 1, 1
        rank([it, de, fr], "DE", "2019", highest_first=False),
    ]
    for r in records:
        replay.check(step(r))
    assert "compare ratio" in replay.CHECKED and "rank of" in replay.CHECKED


def test_series_it_makes() -> None:
    money = Series.from_values("IT", {"2014": 90.0, "2015": 100.0, "2016": 104.0, "2017": 107.0},
                               "million euro")  # fmt: skip
    people = Series.from_values("IT", {"2015": 60e6, "2016": 59.5e6, "2017": 59e6, "2018": 58e6})
    rates = Series.from_values("IT", {"2014": 0.2, "2015": 0.1, "2016": -0.1, "2017": 1.2,
                                      "2019": 0.6})  # fmt: skip
    index = chain_index(rates, "2015")  # 2019 is not joined to 2015: left out
    prices = Series.from_record(index)
    for r in (
        per_capita(money, people, scale=1e6),
        index,
        deflate(money, prices, "2015"),
        deflate(money, prices, "latest"),  # the index's last period
    ):
        replay.check(step(r))
    assert "chain_index 2013" in replay.CHECKED  # one period before the first rate


def test_a_difference_names_the_figure() -> None:
    record = step(change(Series.from_values("IT", {"2015": 1.0, "2016": 2.0}), "2015", "2016",
                         ChangeKind.PERCENT))  # fmt: skip
    record["value"] = 101.0
    with pytest.raises(replay.ReplayError, match="change: replayed 100.0, the receipt has 101.0"):
        replay.check(record)
    record["value"], record["extras"] = 100.0, {"years": 1.0}
    with pytest.raises(replay.ReplayError, match=r"replayed \[\], not \['years'\]"):
        replay.check(record)
    made = step(per_capita(Series.from_values("IT", {"2015": 1.0}),
                           Series.from_values("IT", {"2015": 2.0})))  # fmt: skip
    made["series"].append({"geo": "IT", "period": "2016", "value": 1.0})
    with pytest.raises(replay.ReplayError, match="replayed periods"):
        replay.check(made)


def test_same_needs_both_or_neither() -> None:
    replay.same("empty", None, None)
    with pytest.raises(replay.ReplayError):
        replay.same("one side", None, 1.0)
    assert replay.CHECKED == []


@pytest.mark.parametrize(
    ("op", "kind", "start", "end", "expected"),
    [
        ("change", "percent", "2016", "2015", None),  # reversed
        ("change", "percent", "2015", "2018", None),  # no value for 2018
        ("change", "percent", "2017", "2019", None),  # a percent change from 0
        ("cagr", None, "2017", "2019", None),  # growth from 0
        ("trend", None, "2017", "2018", None),  # one value in the window
        ("change", "absolute", "2015", "2019", 3.0),
        ("cagr", None, "2015", "2016", 100.0),
        ("trend", None, "2015", "2016", 1.0),
    ],
)  # fmt: skip
def test_a_window_with_no_answer(
    op: str, kind: str | None, start: str, end: str, expected: float | None
) -> None:
    points = [("2015", 1.0), ("2016", 2.0), ("2017", 0.0), ("2019", 4.0)]
    assert replay.window_value(op, kind, dict(points), start, end, points) == expected


def test_the_window_grid_and_its_nearby_share() -> None:
    series = [{"period": p, "value": v} for p, v in (("2015", 3.0), ("2016", 2.0), ("2017", 2.5))]
    years = ["2015", "2016", "2017"]
    sweep: dict[str, Any] = {
        "op": "change", "kind": "absolute", "starts": years, "ends": years,
        "values": [[None, -1.0, -0.5], [None, None, 0.5], [None, None, None]],
        "holds": [[None, True, True], [None, None, False], [None, None, None]],
        "near_starts": ["2015", "2016"], "near_ends": ["2016", "2017"],
        "counted": 3, "held": 2, "share": 2 / 3,
    }  # fmt: skip
    replay.check_sweep(sweep, series)
    assert replay.CHECKED[-3:] == [
        "nearby windows counted", "nearby windows where it holds", "share of nearby windows",
    ]  # fmt: skip
    with pytest.raises(replay.ReplayError, match="nearby windows where it holds"):
        replay.check_sweep({**sweep, "held": 3}, series)
    with pytest.raises(replay.ReplayError, match="window 2016 to 2017"):
        replay.check_sweep({**sweep, "values": [[None, -1.0, -0.5], [None, None, 0.6],
                                                [None, None, None]]}, series)  # fmt: skip


values = st.floats(min_value=0.5, max_value=1e6, allow_nan=False, allow_infinity=False)


@settings(max_examples=60, deadline=None)
@given(
    st.lists(values, min_size=3, max_size=12),
    st.sampled_from(["", "-S", "-Q", "-M"]),
    st.lists(st.floats(min_value=-20, max_value=40), min_size=3, max_size=12),
)
def test_replays_match_the_operations(numbers: list[float], freq: str, rates: list[float]) -> None:
    per_year = {"": 1, "-S": 2, "-Q": 4, "-M": 12}[freq]
    periods = [replay.label(2000 + i // per_year, i % per_year + 1, per_year)
               for i in range(len(numbers))]  # fmt: skip
    s = Series.from_values("IT", dict(zip(periods, numbers, strict=True)), "euro")
    first, last = periods[0], periods[-1]
    records = [
        *(change(s, first, last, kind) for kind in ChangeKind),
        cagr(s, first, last),
        trend(s, first, last),
        per_capita(s, Series.from_values("IT", dict(zip(periods[1:], numbers[1:], strict=True)))),
    ]
    if freq == "":
        n = min(len(numbers), len(rates))
        r = Series.from_values("IT", dict(zip(periods[:n], rates[:n], strict=True)))
        index = chain_index(r, periods[n // 2])
        records += [index, deflate(s, Series.from_record(index), periods[n // 2])]
    for record in records:
        replay.check(step(record))
