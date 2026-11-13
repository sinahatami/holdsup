"""The confidence model's training: rows from dev reports only, the metrics, cross-validation,
the export the API serves (scored the same as scikit-learn scores it), and the report."""

import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from confidence.dataset import DatasetError, Row, load_dataset
from confidence.experiment import (
    BASE_RATE,
    BOOSTING,
    CANDIDATES,
    LOGISTIC,
    MARGIN_ONLY,
    cross_validate,
    export,
    fit_final,
    matrix,
    scores,
)
from confidence.metrics import (
    auc,
    brier,
    calibration,
    choose_threshold,
    coverage_curve,
    log_loss,
)
from confidence.report import build_report, markdown, write_report
from holdsup.ml.confidence import FEATURES, ConfidenceModel, Signals, TrainedOn, load_confidence
from reranker.benchmark import Claim
from reranker.leakage import LeakageError

EVAL = "1.0.0"

# --- the rows --------------------------------------------------------------------------------


def outcome(
    key: str,
    *,
    verdict: str | None = "supported",
    ok: bool | None = True,
    status: str = "scored",
    signals: dict[str, Any] | None = None,  # Any: the signals as JSON
) -> dict[str, Any]:  # Any: as above
    text_id, n = key.split("#")
    return {
        "text_id": text_id,
        "index": int(n) - 1,
        "quote": "not read",
        "status": status,
        "verdict": verdict,
        "verdict_ok": ok,
        "confidence": None
        if signals is None
        else {"signals": signals, "probability": None, "abstain": False},
    }


def write(
    tmp_path: Path, name: str, outcomes: list[dict[str, Any]], split: str = "dev", eval: str = EVAL
) -> Path:  # Any: as above
    texts: dict[str, list[dict[str, Any]]] = {}  # Any: as above
    for o in outcomes:
        texts.setdefault(o["text_id"], []).append(o)
    report = {
        "name": name,
        "split": split,
        "versions": {"app": "0", "catalog": "0.1.0", "tolerances": 5, "eval": eval},
        "texts": [{"id": t, "outcomes": os} for t, os in texts.items()],
        "metrics": {},
    }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_rows_are_the_dev_claims_with_a_verdict_to_be_sure_of(
    tmp_path: Path, claims: list[Claim]
) -> None:
    path = write(
        tmp_path,
        "dev",
        [
            outcome("d1#1", signals={"rerank_margin": 0.6}),
            outcome("d2#1", ok=False, verdict="not_supported", signals={"fallback_steps": 1}),
            outcome("d2#2", verdict="cant_check", signals=None),
            outcome("d3#1", status="not_run", verdict=None, ok=None),
            outcome("d4#1", signals=None),  # a report from before P4.5
        ],
    )
    data = load_dataset([path], claims, EVAL)

    assert [(r.key, r.right) for r in data.rows] == [("d1#1", True), ("d2#1", False)]
    assert data.rows[0].signals.rerank_margin == 0.6
    assert data.rows[0].group == "unemployment_rate_monthly@IT"
    assert data.rows[0].run == "dev.json"
    assert data.skipped == {
        "cant_check (nothing to abstain from)": 1,
        "no signals (a report from before P4.5)": 1,
        "no verdict (not run, source down, or missed by extraction)": 1,
    }
    assert data.eval_version == EVAL and data.catalog_version == "0.1.0"
    assert set(data.reports) == {"dev.json"} and len(data.reports["dev.json"]) == 64


def test_one_claim_from_two_runs_is_two_rows_in_one_group(
    tmp_path: Path, claims: list[Claim]
) -> None:
    a = write(tmp_path, "dev", [outcome("d1#1", signals={})])
    b = write(tmp_path, "dev.mistral", [outcome("d1#1", ok=False, signals={})])
    rows = load_dataset([a, b], claims, EVAL).rows
    assert [(r.run, r.right) for r in rows] == [("dev.json", True), ("dev.mistral.json", False)]
    assert rows[0].group == rows[1].group


def test_a_report_of_the_test_split_or_a_held_out_claim_never_reaches_training(
    tmp_path: Path, claims: list[Claim]
) -> None:
    final = write(tmp_path, "test", [outcome("t1#1", signals={})], split="test")
    mixed = write(tmp_path, "dev", [outcome("d1#1", signals={}), outcome("t2#1", signals={})])
    invented = write(tmp_path, "dev2", [outcome("zz#1", signals={})])
    with pytest.raises(LeakageError) as err:
        load_dataset([final, mixed, invented], claims, EVAL)
    assert err.value.problems == [
        "test.json: a report of the 'test' split, not 'dev'",
        "test.json: t1#1 is a held-out claim",
        "dev.json: t2#1 is a held-out claim",
        "dev2.json: zz#1 is not a claim of the benchmark",
    ]


def test_reports_that_cannot_be_read_together_are_refused(
    tmp_path: Path, claims: list[Claim]
) -> None:
    with pytest.raises(DatasetError, match="run `make eval`"):
        load_dataset([], claims, EVAL)
    old = write(tmp_path, "old", [outcome("d1#1", signals={})], eval="0.9.0")
    with pytest.raises(DatasetError, match="old.json: eval 0.9.0"):
        load_dataset([old], claims, EVAL)
    (tmp_path / "x").mkdir()
    twin = write(tmp_path / "x", "old", [outcome("d1#1", signals={})])
    with pytest.raises(DatasetError, match="share a file name"):
        load_dataset([old, twin], claims, EVAL)


# --- the metrics -----------------------------------------------------------------------------


def test_brier_and_log_loss() -> None:
    assert brier([1, 0], [1.0, 0.0]) == 0.0
    assert brier([1, 0, 1, 1], [0.5] * 4) == pytest.approx(0.25)
    assert log_loss([1, 0], [0.5, 0.5]) == pytest.approx(math.log(2))
    assert log_loss([1], [0.0]) < 30  # clipped, not infinite
    with pytest.raises(ValueError, match="same, non-zero length"):
        brier([1, 0], [0.5])
    with pytest.raises(ValueError, match="same, non-zero length"):
        brier([], [])


def test_auc_counts_ties_as_half_and_needs_both_kinds() -> None:
    assert auc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]) == 1.0
    assert auc([1, 0], [0.5, 0.5]) == 0.5
    assert auc([1, 0, 1, 0], [0.9, 0.8, 0.3, 0.1]) == 0.75
    assert auc([1, 1], [0.2, 0.9]) is None


def test_calibration_bins_hold_every_probability_once() -> None:
    y = [1, 0, 1, 1, 0, 1]
    p = [0.05, 0.15, 0.5, 0.95, 0.9, 1.0]
    bins = calibration(y, p, bins=5)
    assert [b.n for b in bins] == [2, 0, 1, 0, 3]  # 1.0 lands in the last bin
    assert bins[0].mean_probability == pytest.approx(0.1) and bins[0].accuracy == 0.5
    assert bins[1].mean_probability is None and bins[1].accuracy is None
    assert bins[4].accuracy == pytest.approx(2 / 3)
    assert (bins[0].low, bins[4].high) == (0.0, 1.0)


def test_coverage_answers_the_most_confident_first_and_ties_together() -> None:
    curve = coverage_curve([1, 0, 1, 0], [0.9, 0.7, 0.7, 0.2])
    assert [(c.answered, c.accuracy, c.lowest) for c in curve] == [
        (1, 1.0, 0.9),
        (3, pytest.approx(2 / 3), 0.7),
        (4, 0.5, 0.2),
    ]
    assert curve[-1].coverage == 1.0


def test_the_threshold_answers_most_while_meeting_the_target() -> None:
    y = [1, 1, 1, 0, 1, 0]
    p = [0.95, 0.9, 0.85, 0.8, 0.6, 0.3]
    t = choose_threshold(y, p, 0.75)
    # Answering the top 5 gives 4/5 = 80%; all six, 4/6. Halfway between 0.6 and 0.3.
    assert (t.answered, t.met) == (5, True)
    assert t.threshold == pytest.approx(0.45) and t.accuracy == pytest.approx(0.8)
    assert t.coverage == pytest.approx(5 / 6)


def test_a_target_every_claim_meets_never_abstains() -> None:
    t = choose_threshold([1, 1, 0], [0.9, 0.8, 0.7], 0.5)
    assert (t.threshold, t.answered, t.met) == (0.0, 3, True)


def test_an_unreachable_target_answers_the_most_accurate_share_and_says_so() -> None:
    t = choose_threshold([0, 1, 0], [0.9, 0.8, 0.1], 0.99)
    assert not t.met
    assert (t.answered, t.accuracy) == (2, 0.5)
    assert t.threshold == pytest.approx(0.45)


# --- cross-validation and the export ---------------------------------------------------------


def synthetic(n: int = 80, seed: int = 3) -> list[Row]:
    """Rows where a wide margin and no fallback usually mean a right verdict; some signals are
    missing, as a re-check's reranker signals are."""
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not security
    rows = []
    for i in range(n):
        margin = rng.uniform(-0.2, 1.0)
        fallback = rng.choice([0, 0, 0, 1, 2])
        logit = 3 * margin - 1.2 * fallback + 0.5
        right = rng.random() < 1 / (1 + math.exp(-logit))
        rows.append(
            Row(
                key=f"c{i}#1",
                run="dev.json",
                group=f"g{i % 25}",
                signals=Signals(
                    rerank_probability=None if i % 9 == 0 else min(1.0, 0.3 + margin / 2),
                    rerank_margin=None if i % 9 == 0 else margin,
                    definition_mismatch=i % 11 == 0,
                    data_age_years=rng.uniform(0, 4),
                    series_length=rng.randint(5, 40),
                    boundary_distance=None if i % 4 == 0 else rng.uniform(0, 5),
                    fallback_steps=fallback,
                ),
                right=right,
            )
        )
    return rows


TRAINED = TrainedOn(
    created="2026-11-14",
    eval_version=EVAL,
    catalog_version="0.1.0",
    reports={"dev.json": "0" * 64},
    rows=80,
    seed=13,
)


def test_missing_signals_are_nan_in_the_matrix() -> None:
    x, y = matrix(synthetic(10))
    assert x.shape == (10, len(FEATURES)) and y.shape == (10,)
    assert np.isnan(x[0, FEATURES.index("rerank_margin")])  # row 0: no reranker
    assert set(np.unique(y)) <= {0.0, 1.0}


def test_every_model_is_scored_out_of_fold_and_the_signals_beat_the_base_rate() -> None:
    rows = synthetic()
    cv = cross_validate(rows, k=5, seed=13)
    assert sum(cv.fold_sizes) == len(rows) and len(cv.fold_sizes) == 5
    # A group's rows share a fold.
    by_group: dict[str, set[int]] = {}
    for r, f in zip(rows, cv.folds, strict=True):
        by_group.setdefault(r.group, set()).add(f)
    assert all(len(f) == 1 for f in by_group.values())
    assert set(cv.probabilities) == {c.name for c in CANDIDATES}
    assert all(len(p) == len(rows) for p in cv.probabilities.values())
    table = {s.name: s for s in scores(rows, cv)}
    assert table[LOGISTIC].brier < table[BASE_RATE].brier
    margin_auc = table[MARGIN_ONLY].auc
    assert margin_auc is not None and margin_auc > 0.5
    assert table[BOOSTING].brier > 0


def test_a_fold_with_one_kind_of_label_predicts_its_share() -> None:
    rows = [
        Row(key=f"c{i}#1", run="r", group=f"g{i}", signals=Signals(), right=i != 0)
        for i in range(10)
    ]
    cv = cross_validate(rows, k=5, seed=1)
    fold_of_wrong = cv.folds[0]
    # Every other fold trained on rows that include the one wrong verdict, or are all right.
    for i, f in enumerate(cv.folds):
        if f == fold_of_wrong:
            assert cv.probabilities[LOGISTIC][i] == 1.0  # trained on right verdicts only


def test_the_export_scores_exactly_as_scikit_learn_does(tmp_path: Path) -> None:
    rows = synthetic()
    pipeline = fit_final(rows)
    y = [r.right for r in rows]
    threshold = choose_threshold(y, list(pipeline.predict_proba(matrix(rows)[0])[:, 1]), 0.8)
    model = export(pipeline, threshold, TRAINED)

    x, _ = matrix(rows)
    expected = pipeline.predict_proba(x)[:, 1]
    served = [model.probability(r.signals) for r in rows]
    assert served == pytest.approx(list(expected), abs=1e-9)
    assert model.threshold == threshold.threshold
    assert model.high == max(0.85, threshold.threshold)

    # What the API loads is what was written.
    path = tmp_path / "confidence_model.json"
    path.write_text(model.model_dump_json(), encoding="utf-8")
    loaded = load_confidence(path)
    assert loaded is not None and loaded.probability(rows[0].signals) == pytest.approx(served[0])


def test_nothing_to_learn_from_one_kind_of_label() -> None:
    rows = [Row(key="a#1", run="r", group="g", signals=Signals(), right=True)] * 3
    with pytest.raises(ValueError, match="nothing to learn"):
        fit_final(rows)


# --- the report ------------------------------------------------------------------------------


def test_the_report_names_its_data_scores_threshold_and_weights(tmp_path: Path) -> None:
    from confidence.dataset import Dataset

    rows = synthetic()
    cv = cross_validate(rows)
    table = scores(rows, cv)
    y = [r.right for r in rows]
    threshold = choose_threshold(y, cv.probabilities[LOGISTIC], 0.9)
    model: ConfidenceModel = export(fit_final(rows), threshold, TRAINED)
    data = Dataset(
        rows=rows,
        reports={"dev.json": "a" * 64},
        eval_version=EVAL,
        catalog_version="0.1.0",
        skipped={"cant_check (nothing to abstain from)": 4},
    )
    report = build_report(data, cv, table, threshold, model, created="2026-11-14")

    assert report.data.rows == 80 and report.data.right + report.data.wrong == 80
    assert report.data.missing["rerank_margin"] == 9  # every ninth row, from 0
    assert report.cross_validation.beats_base_rate
    assert [m.name for m in report.cross_validation.models] == [c.name for c in CANDIDATES]
    assert len(report.served.coefficients) == len(FEATURES)
    assert sum(b.n for b in report.cross_validation.calibration) == 80
    margin = next(c for c in report.served.coefficients if c.feature == "rerank_margin")
    assert margin.as_expected and margin.weight > 0

    md = markdown(report)
    assert "`dev.json` (sha256 aaaaaaaaaaaa)" in md
    assert "80 claims with a verdict other than cant_check" in md
    assert "cant_check (nothing to abstain from): 4" in md
    assert "The served model beats the base rate on the Brier score." in md
    assert "| Logistic regression, every signal (served) |" in md
    assert f"Threshold {threshold.threshold:.3f}" in md
    assert "in-sample" in md  # the reranker caveat

    json_path, md_path = write_report(report, tmp_path / "reports")
    assert json.loads(json_path.read_text(encoding="utf-8"))["data"]["rows"] == 80
    assert md_path.read_text(encoding="utf-8") == md
