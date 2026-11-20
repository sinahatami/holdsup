"""The regression gate: more than 5 points below the baseline fails; too little to judge is
its own outcome, never a pass."""

from pathlib import Path

import pytest
from scripts.evaluation.gate import (
    Baseline,
    Outcome,
    baseline_of,
    check,
    fallbacks_after_limits,
    first_choices_spent,
    read_baseline,
    write_baseline,
)
from scripts.evaluation.meter import Call

from tests.evaluation.helpers import make_report


def baseline(right: int = 16, total: int = 20, **over: object) -> Baseline:
    """The baseline `make_report(right, total)` gives: t0#1 … right first, then wrong ones."""
    fields: dict[str, object] = {
        "eval": "0.1.0",
        "benchmark": "smoke_claims.jsonl",
        "claims": total,
        "written": "2026-11-12",
        "verdict_accuracy": round(right / total, 4),
        "match_top1": 1.0,
        "extraction_recall": 1.0,
        "judged": {f"t{i}#1": i < right for i in range(total)},
    } | over
    return Baseline.model_validate(fields)


def test_the_baseline_is_taken_from_a_report() -> None:
    b = baseline_of(make_report(16, 20))

    assert (b.verdict_accuracy, b.claims, b.eval, b.written) == (0.8, 20, "0.1.0", "2026-11-12")
    assert (b.match_top1, b.extraction_recall) == (1.0, 1.0)
    assert b == baseline()


def test_the_baseline_keeps_only_the_claims_its_run_judged() -> None:
    b = baseline_of(make_report(3, 4, not_run=1))

    assert b.judged == {"t0#1": True, "t1#1": True, "t2#1": True, "t3#1": False}


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
    gate = check(make_report(16, 20), baseline())

    assert gate.outcome is Outcome.PASS and "no change" in gate.message


def test_a_better_run_passes() -> None:
    gate = check(make_report(18, 20), baseline())

    assert gate.outcome is Outcome.PASS and "up 10.0 points" in gate.message


def test_a_drop_of_exactly_five_points_is_not_more_than_five() -> None:
    gate = check(make_report(15, 20), baseline())  # 75% against 80%

    assert gate.outcome is Outcome.PASS and "down 5.0 points" in gate.message


def test_a_drop_of_more_than_five_points_is_a_regression() -> None:
    gate = check(make_report(14, 20), baseline())

    assert gate.outcome is Outcome.REGRESSION
    assert "down 10.0 points, more than 5" in gate.message
    assert "70.0% against a baseline of 80.0%" in gate.message


def test_one_claim_in_fifteen_is_more_than_five_points() -> None:
    gate = check(make_report(13, 15), baseline(14, 15))

    assert gate.outcome is Outcome.REGRESSION  # 6.7 points: small sets are coarse


def test_only_the_claims_both_runs_judged_are_compared() -> None:
    # The baseline run lost t2 (its plan failed); this run judged it, and right. Compared as
    # rates, 3 of 4 against 3 of 3 hides that t3 went from right to wrong.
    then = baseline(judged={"t0#1": True, "t1#1": True, "t3#1": True})
    gate = check(make_report(3, 4), then)

    assert gate.outcome is Outcome.REGRESSION
    assert (
        "Verdict accuracy 66.7% against a baseline of 100.0% (2026-11-12), on the 3 claims "
        "both runs judged: down 33.3 points" in gate.message
    )
    assert gate.message.endswith(
        "down 33.3 points, more than 5. Right in the baseline, wrong now: t3#1. "
        "Judged in one run only, so not compared: t2#1."
    )


def test_the_claims_that_changed_are_named_either_way() -> None:
    then = baseline(judged={"t0#1": False, "t1#1": True})
    gate = check(make_report(1, 2), then)  # t0 right now, t1 wrong now

    assert gate.outcome is Outcome.PASS and "no change" in gate.message
    assert "Right in the baseline, wrong now: t1#1." in gate.message
    assert "Wrong in the baseline, right now: t0#1." in gate.message


def test_a_run_that_shares_no_judged_claim_with_the_baseline_cannot_be_judged() -> None:
    gate = check(make_report(2, 2), baseline(judged={"other#1": True}))

    assert gate.outcome is Outcome.INCONCLUSIVE and "both this run and the baseline" in gate.message


def test_the_allowed_drop_can_be_widened() -> None:
    gate = check(make_report(14, 20), baseline(), max_drop=10.0)

    assert gate.outcome is Outcome.PASS


def test_no_baseline_cannot_be_judged() -> None:
    gate = check(make_report(16, 20), None)

    assert gate.outcome is Outcome.INCONCLUSIVE and "--update-baseline" in gate.message


def test_a_run_where_too_many_claims_dropped_out_cannot_be_judged() -> None:
    gate = check(make_report(8, 8, not_run=4), baseline())  # a third of them not run

    assert gate.outcome is Outcome.INCONCLUSIVE and "33% of the claims dropped out" in gate.message


def test_a_few_claims_dropping_out_is_tolerated() -> None:
    gate = check(make_report(16, 16, not_run=2), baseline())  # 11%

    assert gate.outcome is Outcome.PASS


def test_a_run_that_judged_no_claim_cannot_be_judged() -> None:
    gate = check(make_report(0, 0), baseline())

    assert gate.outcome is Outcome.INCONCLUSIVE and "No claim was judged" in gate.message


@pytest.mark.parametrize(
    ("version", "benchmark"), [("0.2.0", "smoke_claims.jsonl"), ("0.1.0", "claims.jsonl")]
)
def test_a_baseline_for_another_benchmark_cannot_be_compared(version: str, benchmark: str) -> None:
    gate = check(make_report(16, 20, eval=version, benchmark=benchmark), baseline())

    assert gate.outcome is Outcome.INCONCLUSIVE and "--update-baseline" in gate.message


def spent(provider: str = "fake", step: str = "match") -> list[Call]:
    """A daily-limit failure from `provider` in `step`, then the next choice answering."""
    return [
        Call(step, provider, "m", False, 50.0, error="RateLimited", daily_limit=True),
        Call(step, "spare", "m", True, 900.0),
    ]


def test_a_run_whose_first_choice_reached_its_daily_limit_cannot_be_judged() -> None:
    gate = check(make_report(14, 20, calls=spent()), baseline())  # else a 10-point drop

    assert gate.outcome is Outcome.INCONCLUSIVE
    assert "Daily limit reached by fake (first choice for match)" in gate.message
    assert "once the limits reset" in gate.message


def test_only_the_steps_that_called_a_model_are_named() -> None:
    report = make_report(16, 20, calls=[*spent(step="extract"), *spent(step="plan")])

    assert first_choices_spent(report) == {"fake": ["extract", "plan"]}


def test_a_fallback_reaching_its_daily_limit_is_judged_as_usual() -> None:
    gate = check(make_report(14, 20, calls=spent(provider="spare")), baseline())

    assert gate.outcome is Outcome.REGRESSION


def test_a_run_whose_first_choice_reached_its_daily_limit_is_not_a_baseline() -> None:
    with pytest.raises(ValueError, match="Daily limit reached by fake"):
        baseline_of(make_report(16, 20, calls=spent()))


def turned_away(error: str = "RateLimited", step: str = "match") -> list[Call]:
    """The first choice refusing a call in `step` (a per-minute limit by default), then the
    next choice answering."""
    return [
        Call(step, "fake", "m", False, 50.0, error=error),
        Call(step, "spare", "m", True, 900.0),
    ]


def test_a_run_where_a_per_minute_limit_sent_a_step_to_a_fallback_cannot_be_judged() -> None:
    gate = check(make_report(14, 20, calls=turned_away()), baseline())  # else a 10-point drop

    assert gate.outcome is Outcome.INCONCLUSIVE
    assert "Rate limits turned away fake (first choice for match)" in gate.message
    assert "once the limits reset" in gate.message


def test_a_fallback_answering_after_a_rejected_reply_is_judged_as_usual() -> None:
    gate = check(make_report(14, 20, calls=turned_away(error="ProviderRejected")), baseline())

    assert gate.outcome is Outcome.REGRESSION


def test_a_limit_the_first_choice_waited_out_is_judged_as_usual() -> None:
    calls = [Call("match", "fake", "m", False, 50.0, error="RateLimited")]
    calls.append(Call("match", "fake", "m", True, 900.0))

    assert fallbacks_after_limits(make_report(14, 20, calls=calls)) == {}
    assert check(make_report(14, 20, calls=calls), baseline()).outcome is Outcome.REGRESSION


def test_a_run_where_a_fallback_answered_after_a_limit_is_not_a_baseline() -> None:
    with pytest.raises(ValueError, match="Rate limits turned away fake"):
        baseline_of(make_report(16, 20, calls=turned_away()))


def test_the_exit_codes_are_the_documented_ones() -> None:
    assert (int(Outcome.PASS), int(Outcome.REGRESSION), int(Outcome.INCONCLUSIVE)) == (0, 1, 3)
