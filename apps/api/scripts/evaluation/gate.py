"""The regression gate: a run may not be more than 5 points below the baseline.

`eval/baseline.json` holds the figures of the last accepted smoke run. The gate fails when
end-to-end verdict accuracy drops by more than `MAX_DROP_POINTS`, and refuses to judge
(`inconclusive`) when the run is not comparable or too much of it dropped out: a provider
outage must not read as a pass. With a small smoke set one claim is worth several points, so a
single flip can trip the gate; look at the report before updating the baseline.
"""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel

from scripts.evaluation.report import Report

MAX_DROP_POINTS = 5.0
MAX_EXCLUDED_SHARE = 0.2


class Outcome(IntEnum):
    """The process exit code."""

    PASS = 0
    REGRESSION = 1
    INCONCLUSIVE = 3


class Baseline(BaseModel):
    eval: str  # eval/VERSION the figures are for
    benchmark: str
    claims: int
    written: str  # an ISO date
    verdict_accuracy: float
    match_top1: float | None
    extraction_recall: float | None


@dataclass(frozen=True)
class Gate:
    outcome: Outcome
    message: str


def baseline_of(report: Report) -> Baseline:
    m = report.metrics
    accuracy = m.verdict.accuracy.rate
    if accuracy is None:
        raise ValueError("the run has no judged claim; nothing to take as a baseline")
    if m.excluded.share is not None and m.excluded.share > MAX_EXCLUDED_SHARE:
        raise ValueError(
            f"{m.excluded.share:.0%} of the claims dropped out (a provider or a source did not "
            "answer): not a baseline worth keeping. Run it again."
        )
    return Baseline(
        eval=report.versions.eval,
        benchmark=report.benchmark,
        claims=m.labelled_claims,
        written=report.created_at.date().isoformat(),
        verdict_accuracy=accuracy,
        match_top1=m.matching.top1.rate,
        extraction_recall=m.extraction.recall.rate,
    )


def read_baseline(path: Path) -> Baseline | None:
    return Baseline.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def write_baseline(path: Path, baseline: Baseline) -> None:
    path.write_text(baseline.model_dump_json(indent=2) + "\n", encoding="utf-8")


def check(
    report: Report,
    baseline: Baseline | None,
    *,
    max_drop: float = MAX_DROP_POINTS,
    max_excluded: float = MAX_EXCLUDED_SHARE,
) -> Gate:
    m = report.metrics
    accuracy = m.verdict.accuracy.rate
    if baseline is None:
        return Gate(Outcome.INCONCLUSIVE, "No baseline: write one with --update-baseline.")
    if m.excluded.share is not None and m.excluded.share > max_excluded:
        return Gate(
            Outcome.INCONCLUSIVE,
            f"{m.excluded.share:.0%} of the claims dropped out (a provider or a source did not "
            f"answer); more than {max_excluded:.0%} is too many to judge. Run it again.",
        )
    if accuracy is None:
        return Gate(Outcome.INCONCLUSIVE, "No claim was judged.")
    if (baseline.eval, baseline.benchmark) != (report.versions.eval, report.benchmark):
        return Gate(
            Outcome.INCONCLUSIVE,
            f"The baseline is for {baseline.benchmark} at eval {baseline.eval}; this run is "
            f"{report.benchmark} at eval {report.versions.eval}. Accept the new claims with "
            "--update-baseline.",
        )
    drop = round((baseline.verdict_accuracy - accuracy) * 100, 6)
    summary = (
        f"Verdict accuracy {accuracy:.1%} against a baseline of {baseline.verdict_accuracy:.1%} "
        f"({baseline.written})"
    )
    if drop > max_drop:
        return Gate(
            Outcome.REGRESSION, f"{summary}: down {drop:.1f} points, more than {max_drop:g}."
        )
    change = "no change" if drop == 0 else f"{'down' if drop > 0 else 'up'} {abs(drop):.1f} points"
    return Gate(Outcome.PASS, f"{summary}: {change}.")
