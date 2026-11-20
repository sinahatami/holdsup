"""The regression gate: a run may not be more than 5 points below the baseline.

`eval/baseline.json` holds the figures of the last accepted smoke run and which of its claims
came out right. The gate compares the two runs on the claims both of them judged, so a claim
that dropped out of either run moves neither figure, and it names each claim that changed. It
fails when end-to-end verdict accuracy on those claims drops by more than `MAX_DROP_POINTS`,
and refuses to judge (`inconclusive`) when the run is not comparable or too much of it dropped
out: a provider outage must not read as a pass. A run in which a step's first-choice model
reached its daily limit is not comparable either: the fallback models answered, and the
baseline is a measure of the first choices. Nor is one in which a per-minute limit sent a step
to a fallback that then answered. A fallback that answers after the first choice's output was
rejected still counts: that is the first choice failing, which the gate is there to catch.
With a small smoke set one claim is worth several points, so a single flip can trip the gate;
look at the claims it names before updating the baseline.
"""

from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel

from scripts.evaluation.report import Report, claim_name
from scripts.evaluation.score import CallStats

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
    # Each claim the run judged ("c001#1") and whether its verdict was right; a claim that
    # dropped out is not here.
    judged: dict[str, bool]


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
    if spent := first_choices_spent(report):
        raise ValueError(f"{_spent(spent)}: not a baseline worth keeping. Run it again.")
    if limited := fallbacks_after_limits(report):
        raise ValueError(f"{_limited(limited)}: not a baseline worth keeping. Run it again.")
    return Baseline(
        eval=report.versions.eval,
        benchmark=report.benchmark,
        claims=m.labelled_claims,
        written=report.created_at.date().isoformat(),
        verdict_accuracy=accuracy,
        match_top1=m.matching.top1.rate,
        extraction_recall=m.extraction.recall.rate,
        judged=judged_claims(report),
    )


def judged_claims(report: Report) -> dict[str, bool]:
    """Each claim the run judged, and whether its verdict was right: the claims behind its
    end-to-end verdict accuracy."""
    return {
        claim_name(o): o.verdict_ok
        for t in report.texts
        for o in t.outcomes
        if o.status == "scored" and o.verdict_ok is not None
    }


def first_choices_spent(report: Report) -> dict[str, list[str]]:
    """Each first-choice provider that reached its daily limit in the run, with the steps it is
    first choice for. Only steps that called a model count."""
    spent = set(report.metrics.cost.daily_limited)
    called = {s.step for s in report.metrics.cost.by_step_provider}
    out: dict[str, list[str]] = {}
    for step, models in report.steps.items():  # models: "provider/model", first choice first
        if step in called and models and (first := models[0].split("/", 1)[0]) in spent:
            out.setdefault(first, []).append(step)
    return out


def fallbacks_after_limits(report: Report) -> dict[str, list[str]]:
    """Each first-choice provider a rate limit turned away in a step where another provider
    then answered, with those steps: the answers there came from a fallback model."""
    by_step: dict[str, dict[str, CallStats]] = defaultdict(dict)
    for stats in report.metrics.cost.by_step_provider:
        by_step[stats.step][stats.provider] = stats
    out: dict[str, list[str]] = {}
    for step, models in report.steps.items():  # models: "provider/model", first choice first
        if not models or not (seen := by_step.get(step)):
            continue
        first = models[0].split("/", 1)[0]
        limited = first in seen and seen[first].rate_limited > 0
        answered = any(p != first and s.calls > s.failed for p, s in seen.items())
        if limited and answered:
            out.setdefault(first, []).append(step)
    return out


def _limited(limited: dict[str, list[str]]) -> str:
    named = "; ".join(f"{p} (first choice for {', '.join(s)})" for p, s in limited.items())
    return f"Rate limits turned away {named}, so fallback models answered"


def _spent(spent: dict[str, list[str]]) -> str:
    named = "; ".join(f"{p} (first choice for {', '.join(steps)})" for p, steps in spent.items())
    return f"Daily limit reached by {named}, so fallback models answered"


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
    if spent := first_choices_spent(report):
        return Gate(
            Outcome.INCONCLUSIVE,
            f"{_spent(spent)}; the baseline measures the first choices, so this run cannot be "
            "compared with it. Run it again once the limits reset.",
        )
    if limited := fallbacks_after_limits(report):
        return Gate(
            Outcome.INCONCLUSIVE,
            f"{_limited(limited)}; the baseline measures the first choices, so this run cannot "
            "be compared with it. Run it again once the limits reset.",
        )
    return _compare(judged_claims(report), baseline, max_drop)


def _compare(now: dict[str, bool], baseline: Baseline, max_drop: float) -> Gate:
    """This run against the baseline on the claims both judged, naming the ones that changed."""
    then = baseline.judged
    both = sorted(now.keys() & then.keys())
    if not both:
        return Gate(Outcome.INCONCLUSIVE, "No claim was judged in both this run and the baseline.")
    right_then, right_now = sum(then[c] for c in both), sum(now[c] for c in both)
    before, after = right_then / len(both), right_now / len(both)
    drop = round((right_then - right_now) * 100 / len(both), 6)
    summary = (
        f"Verdict accuracy {after:.1%} against a baseline of {before:.1%} ({baseline.written}), "
        f"on the {len(both)} claims both runs judged"
    )
    notes = [
        f"{label}: {', '.join(names)}."
        for label, names in (
            ("Right in the baseline, wrong now", [c for c in both if then[c] and not now[c]]),
            ("Wrong in the baseline, right now", [c for c in both if now[c] and not then[c]]),
            ("Judged in one run only, so not compared", sorted(now.keys() ^ then.keys())),
        )
        if names
    ]
    tail = "".join(f" {n}" for n in notes)
    if drop > max_drop:
        return Gate(
            Outcome.REGRESSION,
            f"{summary}: down {drop:.1f} points, more than {max_drop:g}.{tail}",
        )
    change = "no change" if drop == 0 else f"{'down' if drop > 0 else 'up'} {abs(drop):.1f} points"
    return Gate(Outcome.PASS, f"{summary}: {change}.{tail}")
