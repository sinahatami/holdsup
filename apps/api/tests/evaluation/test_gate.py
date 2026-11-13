"""The regression gate: more than 5 points below the baseline fails; too little to judge is
its own outcome, never a pass."""

from pathlib import Path

import pytest
from scripts.evaluation.gate import (
    Baseline,
    Outcome,
    baseline_of,
    check,
    first_choices_spent,
    read_baseline,
    write_baseline,
)
from scripts.evaluation.meter import Call

from tests.evaluation.helpers import make_report


def baseline(accuracy: float = 0.8, **over: object) -> Baseline:
    fields: dict[str, object] = {
        "eval": "0.1.0",
        "benchmark": "smoke_claims.jsonl",
        "claims": 20,
        "written": "2026-11-12",
        "verdict_accuracy": accuracy,
        "match_top1": 1.0,
        "extraction_recall": 1.0,
    } | over
    return Baseline.model_validate(fields)


def test_the_baseline_is_taken_from_a_report() -> None:
    b = baseline_of(make_report(16, 20))

    assert (b.verdict_accuracy, b.claims, b.eval, b.written) == (0.8, 20, "0.1.0", "2026-11-12")
    assert (b.match_top1, b.extraction_recall) == (1.0, 1.0)


def test_a_run_that_judged_nothing_cannot_be_a_baseline() -> None:
    with pytest.raises(ValueError, match="no judged claim"):
        baseline_of(make_report(0, 0, not_run=3))


def test_a_run_with_many_claims_dropped_out_is_not_a_baseline_worth_keeping() -> None:
    with pytest.raises(ValueError, match="33% of the claims dropped out"):
        baseline_of(make_report(8, 8, not_run=4))


def test_a_baseline_survives_a_round_trip_and_a_missing_one_is_none(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    assert read_baseline(path) is None

    write_baseline(path, baseline())

    assert read_baseline(path) == baseline()


def test_the_same_accuracy_passes() -> None:
    gate = check(make_report(16, 20), baseline(0.8))

    assert gate.outcome is Outcome.PASS and "no change" in gate.message


def test_a_better_run_passes() -> None:
    gate = check(make_report(18, 20), baseline(0.8))

    assert gate.outcome is Outcome.PASS and "up 10.0 points" in gate.message


def test_a_drop_of_exactly_five_points_is_not_more_than_five() -> None:
    gate = check(make_report(15, 20), baseline(0.8))  # 75% against 80%

    assert gate.outcome is Outcome.PASS and "down 5.0 points" in gate.message


def test_a_drop_of_more_than_five_points_is_a_regression() -> None:
    gate = check(make_report(14, 20), baseline(0.8))

    assert gate.outcome is Outcome.REGRESSION
    assert "down 10.0 points, more than 5" in gate.message
    assert "70.0% against a baseline of 80.0%" in gate.message


def test_one_claim_in_fifteen_is_more_than_five_points() -> None:
    gate = check(make_report(13, 15), baseline(round(14 / 15, 4)))

    assert gate.outcome is Outcome.REGRESSION  # 6.7 points: small sets are coarse


def test_the_allowed_drop_can_be_widened() -> None:
    gate = check(make_report(14, 20), baseline(0.8), max_drop=10.0)

    assert gate.outcome is Outcome.PASS


def test_no_baseline_cannot_be_judged() -> None:
    gate = check(make_report(16, 20), None)

    assert gate.outcome is Outcome.INCONCLUSIVE and "--update-baseline" in gate.message


def test_a_run_where_too_many_claims_dropped_out_cannot_be_judged() -> None:
    gate = check(make_report(8, 8, not_run=4), baseline(0.8))  # a third of them not run

    assert gate.outcome is Outcome.INCONCLUSIVE and "33% of the claims dropped out" in gate.message


def test_a_few_claims_dropping_out_is_tolerated() -> None:
    gate = check(make_report(16, 16, not_run=2), baseline(0.8))  # 11%

    assert gate.outcome is Outcome.PASS


def test_a_run_that_judged_no_claim_cannot_be_judged() -> None:
    gate = check(make_report(0, 0), baseline(0.8))

    assert gate.outcome is Outcome.INCONCLUSIVE and "No claim was judged" in gate.message


@pytest.mark.parametrize(
    ("version", "benchmark"), [("0.2.0", "smoke_claims.jsonl"), ("0.1.0", "claims.jsonl")]
)
def test_a_baseline_for_another_benchmark_cannot_be_compared(version: str, benchmark: str) -> None:
    gate = check(make_report(16, 20, eval=version, benchmark=benchmark), baseline(0.8))

    assert gate.outcome is Outcome.INCONCLUSIVE and "--update-baseline" in gate.message


def spent(provider: str = "fake", step: str = "match") -> list[Call]:
    """A daily-limit failure from `provider` in `step`, then the next choice answering."""
    return [
        Call(step, provider, "m", False, 50.0, error="RateLimited", daily_limit=True),
        Call(step, "spare", "m", True, 900.0),
    ]


def test_a_run_whose_first_choice_reached_its_daily_limit_cannot_be_judged() -> None:
    gate = check(make_report(14, 20, calls=spent()), baseline(0.8))  # else a 10-point drop

    assert gate.outcome is Outcome.INCONCLUSIVE
    assert "Daily limit reached by fake (first choice for match)" in gate.message
    assert "once the limits reset" in gate.message


def test_only_the_steps_that_called_a_model_are_named() -> None:
    report = make_report(16, 20, calls=[*spent(step="extract"), *spent(step="plan")])

    assert first_choices_spent(report) == {"fake": ["extract", "plan"]}


def test_a_fallback_reaching_its_daily_limit_is_judged_as_usual() -> None:
    gate = check(make_report(14, 20, calls=spent(provider="spare")), baseline(0.8))

    assert gate.outcome is Outcome.REGRESSION


def test_a_run_whose_first_choice_reached_its_daily_limit_is_not_a_baseline() -> None:
    with pytest.raises(ValueError, match="Daily limit reached by fake"):
        baseline_of(make_report(16, 20, calls=spent()))


def test_the_exit_codes_are_the_documented_ones() -> None:
    assert (int(Outcome.PASS), int(Outcome.REGRESSION), int(Outcome.INCONCLUSIVE)) == (0, 1, 3)
