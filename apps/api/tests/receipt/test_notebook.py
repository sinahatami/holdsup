"""The notebook export (P3.6, D027), built from whole pipeline runs on recorded data: run with
the standard library only, it reproduces every number the receipt shows, and it stops when one
of them is changed."""

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

import tests.pipeline.test_framing_checks as framing
from holdsup.pipeline.result import PipelineOutput, Versions
from holdsup.receipt import replay
from holdsup.receipt.notebook import CodeCell, MarkdownCell, Notebook, notebook
from holdsup.router.client import ChatResponse
from holdsup.service.store import CheckResult
from tests.pipeline.test_regressions import (
    C018,
    EXPLAINED,
    FALL,
    check,
    extraction,
    match,
    model_claim,
    plan,
)
from tests.receipt.run import execute, execute_standalone

ID = UUID("6f1c2d3e-4a5b-4c6d-8e7f-001122334455")


def stored(out: PipelineOutput, text: str) -> CheckResult:
    """A finished check as the store keeps it, through JSON like the database."""
    result = CheckResult(
        id=ID, text=text, created_at=datetime(2026, 11, 12, 9, 0, tzinfo=UTC),
        finished_at=datetime(2026, 11, 12, 9, 1, tzinfo=UTC), claims=out.claims,
        versions=out.versions, models=out.models,
    )  # fmt: skip
    return CheckResult.model_validate_json(result.model_dump_json())


def fall(call: dict[str, Any], **assertion: Any) -> list[ChatResponse]:  # Any: JSON a model writes
    """The r001 claim, read as `assertion` says (a trend, a yearly rate), answered by `call`."""
    stated = assertion or {"start_value": 11.9, "end_value": 7.7}
    return [
        extraction(model_claim(FALL[:-1], "unemployment rate", "2015", "2023",
                               direction="down", **stated)),
        match("unemployment_rate_monthly", ["unemployment_rate_ilo"]),
        plan(call),
        EXPLAINED,
    ]  # fmt: skip


async def r001() -> CheckResult:
    """A fall in points between yearly averages of a monthly series, with its window grid."""
    change = {"op": "change", "geo": "IT", "start": "2015", "end": "2023",
              "kind": "percentage_points"}  # fmt: skip
    out, _ = await check(FALL, fall(change))
    return stored(out, FALL)


async def c018() -> CheckResult:
    """A percent change, rerun per person by a framing check."""
    script = [
        extraction(model_claim(C018[23:], "greenhouse gas emissions", "1990", "latest",
                               type="percent", value=23, direction="down"), speaker="Renzi"),
        match("greenhouse_gas_emissions"),
        plan({"op": "change", "geo": "IT", "start": "1990", "end": "latest", "kind": "percent"}),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(C018, script)
    return stored(out, C018)


async def per_person() -> CheckResult:
    """A plan that makes a series (per person) and reads a value from it."""
    text = "Italy emitted about 6 tonnes of greenhouse gases per person in 2022."
    script = [
        extraction(model_claim(text[:-1], "greenhouse gas emissions per person", "2022", "2022",
                               unit="tonnes", value=6)),
        match("greenhouse_gas_emissions"),
        plan({"op": "per_capita", "geo": "IT", "population": "population_total"},
             {"op": "value_at", "series": "@0", "geo": "IT", "period": "2022"}, answer=[1]),
        EXPLAINED,
    ]  # fmt: skip
    out, _ = await check(text, script)
    return stored(out, text)


async def by_trend() -> CheckResult:
    """A trend through the months, and its grid of monthly windows."""
    trend = {"op": "trend", "geo": "IT", "start": "2015", "end": "2023"}
    out, _ = await check(FALL, fall(trend, type="trend", unit=None))
    return stored(out, FALL)


async def by_growth_rate() -> CheckResult:
    """A yearly growth rate ("fell 5% a year")."""
    cagr = {"op": "cagr", "geo": "IT", "start": "2015", "end": "2023"}
    out, _ = await check(FALL, fall(cagr, type="percent", value=-5))
    return stored(out, FALL)


async def below_inflation() -> CheckResult:
    """Wages deflated by consumer prices chained into an index (the after-inflation check)."""
    c, _ = await framing.run(inflation=3.0)
    out = PipelineOutput.model_validate(
        {"claims": [c], "versions": {"app": "0.0.0", "catalog": "0.8.0", "tolerances": 5},
         "models": []}
    )  # fmt: skip
    return stored(out, framing.TEXT)


RUNS = [r001, c018, per_person, by_trend, by_growth_rate, below_inflation]


def ops_in(result: CheckResult) -> list[str]:
    """Every operation the receipt records: the plan's, then each framing check's."""
    return [
        op.op
        for c in result.claims
        for op in [*c.operations, *(r for ch in c.distortion_checks for r in ch.records)]
    ]


# The notebook defines its own ReplayError (it runs without HoldsUp); it is an AssertionError.


@pytest.fixture(autouse=True)
def _fresh_tally() -> None:
    replay.CHECKED.clear()


@pytest.mark.parametrize("run", RUNS, ids=lambda f: f.__name__)
async def test_the_notebook_reproduces_every_figure(
    run: Callable[[], Awaitable[CheckResult]], tmp_path: Path
) -> None:
    result = await run()
    nb = notebook(result)
    ns = execute(nb)
    figures = ns["CHECKED"]
    c = result.claims[0]
    # Each step's headline number is among them, in the order the receipt lists the steps.
    for i, op in enumerate(c.operations):
        if op.value is not None:
            assert f"the claim, step {i + 1}" in figures
    if c.sweep is not None:
        assert "share of nearby windows" in figures or c.sweep.share is None
    # Run alone, with the standard library only, it says the same.
    printed = execute_standalone(nb, tmp_path)
    assert printed.endswith(f"All {len(figures)} figures match the receipt.\n")


async def test_the_runs_cover_every_operation_a_receipt_can_hold() -> None:
    ops = set()
    for run in RUNS:
        ops |= set(ops_in(await run()))
    # compare and rank need several places; tests/receipt/test_replay.py covers them.
    assert ops == set(replay.REPLAYS) - {"compare", "rank"}


async def test_a_changed_number_stops_the_notebook() -> None:
    result = await r001()
    op = result.claims[0].operations[0]
    op.value = (op.value or 0) + 0.01
    with pytest.raises(AssertionError, match="the claim, step 1: replayed"):
        execute(notebook(result))


async def test_a_changed_window_stops_the_notebook() -> None:
    result = await r001()
    sweep = result.claims[0].sweep
    assert sweep is not None
    sweep.values[0][-1] = (sweep.values[0][-1] or 0) * 2
    with pytest.raises(AssertionError, match=f"window {sweep.starts[0]} to {sweep.ends[-1]}"):
        execute(notebook(result))


async def test_a_changed_framing_check_stops_the_notebook() -> None:
    result = await below_inflation()
    [real] = [ch for ch in result.claims[0].distortion_checks if ch.records]
    deflated = next(r for r in real.records if r.op == "deflate")
    assert deflated.series is not None
    deflated.series[-1].value += 1
    with pytest.raises(AssertionError, match="after inflation, step 2"):
        execute(notebook(result))


async def test_the_notebook_says_what_was_checked_and_where_the_data_is() -> None:
    result = await c018()
    nb = notebook(result)
    text = "".join("".join(cell.source) for cell in nb.cells if isinstance(cell, MarkdownCell))
    c = result.claims[0]
    assert c.data is not None and c.indicator is not None
    for expected in (
        "# HoldsUp receipt", f"```text\n{C018}\n```", f"check `{ID}`",
        f"catalog {result.versions.catalog}", "**Verdict:** Does not hold up.",
        c.indicator.definition, f"dataset `{c.data.dataset}`", f"<{c.data.url}>",
        "### Step 1: `change(geo='IT', start='1990', end='latest', kind='percent'",
        "It decides the claim.", "latest is the last period published by then, 2013",
        "### Framing check: Per person (passed)", "**Also used:** Total population (Eurostat), in persons.", "**Source:** Eurostat,",
        "Step 1: `per_capita(geo='IT'",
    ):  # fmt: skip
        assert expected in text, expected


async def test_a_claim_that_could_not_be_checked_has_nothing_to_replay(tmp_path: Path) -> None:
    text = "In 2011 Italy's youth unemployment was 29%."
    script = [
        extraction(model_claim(text[:-1], "youth unemployment rate", "2011", "2011", value=29)),
        match(None),
    ]
    out, _ = await check(text, script)
    result = stored(out, text)
    result.claims[0].models = []
    nb = notebook(result)
    md = "".join("".join(cell.source) for cell in nb.cells if isinstance(cell, MarkdownCell))
    assert "**Verdict:** Can't check." in md and "Nothing to replay" in md
    assert "**Statistic:**" not in md and "**Language models:**" not in md
    assert execute_standalone(nb, tmp_path) == "No calculation to replay.\n"


def test_pasted_text_cannot_break_out_of_its_block() -> None:
    text = "Unemployment fell 4 points.\n```\n# Injected heading\n<script>x</script>"
    result = CheckResult(
        id=ID, text=text, created_at=datetime(2026, 11, 12, tzinfo=UTC),
        finished_at=datetime(2026, 11, 12, tzinfo=UTC), claims=[],
        versions=Versions(app="0.0.0", catalog="0.8.0", tolerances=5), models=[],
    )  # fmt: skip
    first = "".join(notebook(result).cells[0].source)
    assert f"````text\n{text}\n````" in first


async def test_the_file_is_a_jupyter_notebook() -> None:
    nb = notebook(await r001())
    doc = json.loads(nb.model_dump_json())
    assert (doc["nbformat"], doc["nbformat_minor"]) == (4, 5)
    assert doc["metadata"]["kernelspec"]["name"] == "python3"
    ids = [cell["id"] for cell in doc["cells"]]
    assert len(set(ids)) == len(ids)
    for cell in doc["cells"]:
        assert set(cell) >= {"id", "cell_type", "metadata", "source"}
        assert all(isinstance(line, str) for line in cell["source"])
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None and cell["outputs"] == []
        else:
            assert "outputs" not in cell and "execution_count" not in cell
    assert Notebook.model_validate(doc) == nb
    # The arithmetic is HoldsUp's replay module, whole.
    code = [c for c in nb.cells if isinstance(c, CodeCell)]
    assert "".join(code[0].source).startswith('"""Replay HoldsUp\'s calculations')
