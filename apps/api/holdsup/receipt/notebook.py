"""The receipt as a Jupyter notebook (`GET /v1/checks/{id}/notebook`).

Running the notebook repeats every calculation behind each verdict from the values it read,
and stops with an error if a number differs from the receipt. Its code is `replay.py`, copied
whole, and the recorded steps written as Python literals: it needs Python 3.10 or later and
nothing else, neither HoldsUp nor the network.

The file follows nbformat 4.5, written here as Pydantic models rather than with the nbformat
package (D027). Text a person pasted, or a model wrote, goes in fenced blocks, never as
markdown or HTML of its own.
"""

import inspect
import re
from collections.abc import Iterable
from datetime import datetime
from pprint import pformat
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from holdsup.catalog.schema import Source
from holdsup.checks import CheckKind, DistortionCheck
from holdsup.ops import OpRecord
from holdsup.pipeline.result import ClaimResult, DataRef, IndicatorRef
from holdsup.receipt import replay
from holdsup.service.store.model import CheckResult
from holdsup.verdict import Label

# The verdicts as the result page says them (apps/web/src/lib/strings.ts, `verdicts`).
LABELS = {
    Label.SUPPORTED: "Holds up",
    Label.SUPPORTED_FRAMING_MATTERS: "Holds up, but the framing matters",
    Label.NOT_SUPPORTED: "Does not hold up",
    Label.PARTLY_SUPPORTED: "Partly holds up",
    Label.CANT_CHECK: "Can't check",
}
# The framing checks as the result page names them (strings.ts, `framing.kinds`).
CHECKS = {
    CheckKind.ENDPOINTS: "Start and end",
    CheckKind.PER_CAPITA: "Per person",
    CheckKind.REAL: "After inflation",
    CheckKind.POINTS: "Percent or points",
    CheckKind.DEFINITION: "What is measured",
    CheckKind.STALE: "How recent the figures are",
}
SOURCES = {str(s): s.label.removeprefix("the ") for s in Source}
REPLAY_SOURCE = inspect.getsource(replay)


class KernelSpec(BaseModel):
    display_name: str = "Python 3"
    language: str = "python"
    name: str = "python3"


class LanguageInfo(BaseModel):
    name: str = "python"


class NotebookMetadata(BaseModel):
    kernelspec: KernelSpec = Field(default_factory=KernelSpec)
    language_info: LanguageInfo = Field(default_factory=LanguageInfo)


class MarkdownCell(BaseModel):
    cell_type: Literal["markdown"] = "markdown"
    id: str
    metadata: dict[str, str] = Field(default_factory=dict)
    source: list[str]


class CodeCell(BaseModel):
    cell_type: Literal["code"] = "code"
    id: str
    metadata: dict[str, str] = Field(default_factory=dict)
    source: list[str]
    execution_count: None = None  # never run here: the reader runs it
    outputs: list[dict[str, str]] = Field(default_factory=list)


Cell = Annotated[MarkdownCell | CodeCell, Field(discriminator="cell_type")]


class Notebook(BaseModel):
    """A Jupyter notebook, nbformat 4.5."""

    nbformat: Literal[4] = 4
    nbformat_minor: Literal[5] = 5
    metadata: NotebookMetadata = Field(default_factory=NotebookMetadata)
    cells: list[Cell]


class _Cells:
    def __init__(self) -> None:
        self.cells: list[MarkdownCell | CodeCell] = []

    def _id(self) -> str:
        return f"cell-{len(self.cells) + 1}"

    def md(self, *paragraphs: str) -> None:
        text = "\n\n".join(p for p in paragraphs if p)
        self.cells.append(MarkdownCell(id=self._id(), source=_lines(text)))

    def code(self, text: str) -> None:
        self.cells.append(CodeCell(id=self._id(), source=_lines(text.strip("\n"))))


def notebook(result: CheckResult) -> Notebook:
    """The notebook that replays every calculation of a finished check."""
    out = _Cells()
    v = result.versions
    out.md(
        "# HoldsUp receipt",
        "The text that was checked:",
        _fenced(result.text),
        f"Checked on {_moment(result.finished_at)} UTC (check `{result.id}`), with "
        f"HoldsUp {v.app}, catalog {v.catalog} and allowed gaps version {v.tolerances}.",
        "Run every cell. Each one repeats a calculation from the values it read and stops with "
        "an error if a number differs from the receipt. It needs only Python 3.10 or later: "
        "no HoldsUp and no network. The data's sources are linked below, to check the values "
        "themselves.",
    )
    out.md(
        "## The arithmetic",
        "The calculations HoldsUp runs, written out with the standard library only.",
    )
    out.code(REPLAY_SOURCE)
    for c in result.claims:
        _claim(out, c, len(result.claims))
    out.md("## Done")
    out.code(
        'print(f"All {len(CHECKED)} figures match the receipt." if CHECKED '
        'else "No calculation to replay.")'
    )
    return Notebook(cells=out.cells)


def _claim(out: _Cells, c: ClaimResult, total: int) -> None:
    name = f"claim {c.index + 1}" if total > 1 else "the claim"
    out.md(
        f"## Claim {c.index + 1}" if total > 1 else "## The claim",
        _fenced(c.claim.quote),
        f"**Verdict:** {LABELS[c.verdict.label]}. {c.verdict.reason}",
        _statistic(c.indicator, c.data),
        *(_also(e.indicator, e.data) for e in c.extra_sources),
        _models(c),
    )
    steps = [(i, op) for i, op in enumerate(c.operations) if op.op in replay.REPLAYS]
    if not steps:
        out.md("Nothing to replay: no calculation was run for this claim.")
    for i, op in steps:
        decides = " It decides the claim." if i in c.answer else ""
        out.md(f"### Step {i + 1}: `{_call(op)}`{decides}", _flags(op))
        _step(out, op, f"{name}, step {i + 1}")
    if c.sweep is not None and c.series is not None:
        out.md(
            "### Other time windows",
            "The claim's calculation over every start and end of its series, as the check "
            "read it, then the share of nearby windows where the claim's direction holds.",
        )
        series = [p.model_dump(mode="json") for p in c.series.points]
        sweep = c.sweep.model_dump(mode="json")
        out.code(
            f"series = {_literal(series)}\nsweep = {_literal(sweep)}\ncheck_sweep(sweep, series)"
        )
    for check in c.distortion_checks:
        _framing(out, check, name)


def _framing(out: _Cells, check: DistortionCheck, name: str) -> None:
    records = [r for r in check.records if r.op in replay.REPLAYS]
    if not records:
        return
    result = "flagged" if check.flagged else "passed"
    out.md(
        f"### Framing check: {CHECKS[check.kind]} ({result})",
        f"{check.text[:1].upper()}{check.text[1:]}.",
    )
    for j, r in enumerate(records):
        out.md(f"Step {j + 1}: `{_call(r)}`", _flags(r))
        _step(out, r, f"{name}, {CHECKS[check.kind].lower()}, step {j + 1}")


def _step(out: _Cells, op: OpRecord, label: str) -> None:
    step = op.model_dump(mode="json", exclude={"flags", "unit"})
    out.code(f"step = {_literal(step)}\ncheck(step, {label!r})")


def _statistic(indicator: IndicatorRef | None, data: DataRef | None) -> str:
    if indicator is None:
        return ""
    lines = [f"**Statistic:** {indicator.name}, in {indicator.unit}. {indicator.definition}"]
    if data is not None:
        lines.append(_source(data))
    return "  \n".join(lines)


def _also(indicator: IndicatorRef, data: DataRef) -> str:
    return f"**Also used:** {indicator.name}, in {indicator.unit}.  \n{_source(data)}"


def _source(data: DataRef) -> str:
    sha = f" SHA-256 of the response: `{data.raw_sha256}`." if data.raw_sha256 else ""
    return (
        f"**Source:** {_source_name(data.source)}, dataset `{data.dataset}`, retrieved "
        f"{_moment(data.retrieved_at)} UTC: <{data.url}>.{sha}"
    )


def _source_name(source: str) -> str:
    """'Eurostat', 'World Bank': the source's name, or its code if the catalog has no name."""
    return SOURCES.get(source, source)


def _moment(at: datetime) -> str:
    """'7 November 2026 at 17:29' (times are UTC)."""
    return f"{at.day} {at:%B %Y at %H:%M}"


def _models(c: ClaimResult) -> str:
    if not c.models:
        return ""
    used = ", ".join(f"{m.step}: {m.label or f'{m.provider} {m.model}'}" for m in c.models)
    return f"**Language models:** {used}. They read the claim and chose the steps; code computed every number."


def _flags(op: OpRecord) -> str:
    return "\n".join(f"- {f.detail[:1].upper()}{f.detail[1:]}." for f in op.flags)


def _call(op: OpRecord) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in op.args.items() if v is not None)
    return f"{op.op}({args})"


def _literal(value: Any) -> str:  # Any: JSON data from model_dump, written as Python
    return pformat(value, width=96, sort_dicts=False)


def _fenced(text: str) -> str:
    """Text shown as it was written: a fence longer than any run of backticks inside it."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def code_cells(nb: Notebook) -> Iterable[str]:
    """The source of every code cell, in order (what a kernel would run)."""
    return ("".join(c.source) for c in nb.cells if isinstance(c, CodeCell))
