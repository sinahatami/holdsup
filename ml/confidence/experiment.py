"""Cross-validation on the dev split's evaluation rows, the final fit, the export and the report.

    make confidence-train                                  # reads eval/reports/dev.json
    make confidence-train ARGS="--report a.json --report b.json"   # several dev runs

The dev split trains the model, so it cannot also score it: each of 5 folds is scored by models
fitted on the other four, grouped by statistic and place (a sentence and its variants, and one
claim's rows from several runs, stay in one fold). Four models are compared on the same
out-of-fold rows: the base rate (every verdict gets the training share right), a logistic
regression on the reranker's margin alone, the logistic regression on every signal (the one
served), and gradient boosting (the spec's "only if cross-validation shows a clear gain").
The threshold comes from the served model's out-of-fold probabilities; the final model then
fits every row and is exported to apps/api/holdsup/ml/confidence_model.json.
"""

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from confidence.dataset import Row
from confidence.metrics import Threshold, auc, brier, choose_threshold, log_loss
from holdsup.ml.confidence import FEATURES, ConfidenceModel, TrainedOn
from reranker.folds import assign_folds

FOLDS = 5
SEED = 13
TARGET_ACCURACY = 0.90  # answered verdicts should be right this often (P4.7 tunes it)
HIGH = 0.85  # at or above: "high" confidence (never below the threshold)
C = 1.0  # inverse L2 strength: about 100 rows and 7 signals need some
# Gradient boosting replaces the logistic regression only with a Brier score at least this much
# lower out of fold (the spec: "only if cross-validation shows a clear gain").
CLEAR_GAIN = 0.01

BASE_RATE, MARGIN_ONLY, LOGISTIC, BOOSTING = "base_rate", "margin_only", "logistic", "boosting"
SERVED = LOGISTIC

Matrix = npt.NDArray[np.float64]
Vector = npt.NDArray[np.float64]


def matrix(rows: Sequence[Row]) -> tuple[Matrix, Vector]:
    """The rows' signals (missing as NaN) and labels (1: the verdict was right)."""
    x = np.array([[np.nan if v is None else v for v in r.x] for r in rows], dtype=np.float64)
    y = np.array([1.0 if r.right else 0.0 for r in rows], dtype=np.float64)
    return x.reshape(len(rows), len(FEATURES)), y


def logistic() -> Pipeline:
    # keep_empty_features: a signal missing on every row stays a column (imputed 0), so the
    # export always has one weight per feature.
    return make_pipeline(
        SimpleImputer(strategy="mean", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=C, max_iter=1000),
    )


def boosting(seed: int) -> Pipeline:
    return make_pipeline(
        SimpleImputer(strategy="mean", keep_empty_features=True),
        GradientBoostingClassifier(
            n_estimators=100, max_depth=2, learning_rate=0.05, random_state=seed
        ),
    )


# Each candidate: the columns it reads (None: all) and how to make a fresh one (None: base rate).
@dataclass(frozen=True)
class Candidate:
    name: str
    label: str
    columns: tuple[int, ...] | None
    make: Callable[[int], Pipeline] | None


CANDIDATES = (
    Candidate(BASE_RATE, "Base rate (the training share right, for every claim)", None, None),
    Candidate(
        MARGIN_ONLY,
        "Logistic regression, reranker margin only",
        (FEATURES.index("rerank_margin"),),
        lambda _: logistic(),
    ),
    Candidate(LOGISTIC, "Logistic regression, every signal (served)", None, lambda _: logistic()),
    Candidate(BOOSTING, "Gradient boosting, every signal", None, boosting),
)


def _fit_predict(
    c: Candidate, x_train: Matrix, y_train: Vector, x_test: Matrix, seed: int
) -> Vector:
    """Probabilities for `x_test`. A training fold with one kind of label (or the base rate)
    predicts its share right for every claim."""
    if c.make is None or len(np.unique(y_train)) < 2:
        return np.full(len(x_test), float(y_train.mean()))
    cols = list(c.columns) if c.columns is not None else list(range(x_train.shape[1]))
    model = c.make(seed)
    model.fit(x_train[:, cols], y_train)
    return np.asarray(model.predict_proba(x_test[:, cols])[:, 1], dtype=np.float64)


@dataclass
class CrossValidation:
    folds: list[int]  # each row's fold
    fold_sizes: list[int]
    probabilities: dict[str, list[float]] = field(default_factory=dict)  # candidate -> per row


def cross_validate(rows: Sequence[Row], k: int = FOLDS, seed: int = SEED) -> CrossValidation:
    groups = [r.group for r in rows]
    by_group = assign_folds(groups, k, seed)
    folds = [by_group[g] for g in groups]
    x, y = matrix(rows)
    cv = CrossValidation(folds=folds, fold_sizes=[folds.count(f) for f in range(k)])
    fold_arr = np.array(folds)
    for c in CANDIDATES:
        p = np.zeros(len(rows))
        for f in range(k):
            test = fold_arr == f
            p[test] = _fit_predict(c, x[~test], y[~test], x[test], seed)
        cv.probabilities[c.name] = [float(v) for v in p]
    return cv


@dataclass(frozen=True)
class Score:
    name: str
    label: str
    brier: float
    log_loss: float
    auc: float | None


def scores(rows: Sequence[Row], cv: CrossValidation) -> list[Score]:
    y = [r.right for r in rows]
    return [
        Score(
            name=c.name,
            label=c.label,
            brier=brier(y, cv.probabilities[c.name]),
            log_loss=log_loss(y, cv.probabilities[c.name]),
            # The base rate is one number per fold: it ranks nothing, so it has no AUC.
            auc=None if c.name == BASE_RATE else auc(y, cv.probabilities[c.name]),
        )
        for c in CANDIDATES
    ]


def fit_final(rows: Sequence[Row]) -> Pipeline:
    x, y = matrix(rows)
    if len(np.unique(y)) < 2:
        raise ValueError(
            "every verdict in the data was right (or every one wrong): nothing to learn"
        )
    model = logistic()
    model.fit(x, y)
    return model


def export(
    model: Pipeline, threshold: Threshold, trained_on: TrainedOn, high: float = HIGH
) -> ConfidenceModel:
    """The fitted pipeline as the API reads it."""
    imputer, scaler, lr = (
        model.named_steps[s] for s in ("simpleimputer", "standardscaler", "logisticregression")
    )
    return ConfidenceModel(
        features=list(FEATURES),
        impute=[float(v) for v in imputer.statistics_],
        center=[float(v) for v in scaler.mean_],
        scale=[float(v) for v in scaler.scale_],
        coef=[float(v) for v in lr.coef_[0]],
        intercept=float(lr.intercept_[0]),
        threshold=threshold.threshold,
        high=max(high, threshold.threshold),
        target_accuracy=threshold.target,
        trained_on=trained_on,
    )


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - reads the repo's files
    import argparse

    from confidence.dataset import DatasetError, load_dataset
    from confidence.report import build_report, write_report
    from holdsup.config import REPO_ROOT
    from reranker.benchmark import load_claims
    from reranker.leakage import LeakageError

    parser = argparse.ArgumentParser(prog="python -m confidence.experiment")
    parser.add_argument(
        "--report",
        action="append",
        type=Path,
        help="a dev-split evaluation report (repeat for several runs); default eval/reports/dev.json",
    )
    parser.add_argument("--target", type=float, default=TARGET_ACCURACY)
    parser.add_argument(
        "--model-out",
        type=Path,
        default=REPO_ROOT / "apps/api/holdsup/ml/confidence_model.json",
    )
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "ml/confidence/reports")
    args = parser.parse_args(argv)

    paths = [
        p if p.is_absolute() else REPO_ROOT / p
        for p in (args.report or [Path("eval/reports/dev.json")])
    ]
    claims = load_claims(REPO_ROOT / "eval/claims.jsonl")
    eval_version = (REPO_ROOT / "eval/VERSION").read_text(encoding="utf-8").strip()
    try:
        data = load_dataset(paths, claims, eval_version)
    except (DatasetError, LeakageError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 2
    rows = data.rows
    right = sum(r.right for r in rows)
    print(
        f"{len(rows)} rows ({right} right, {len(rows) - right} wrong) from {len(paths)} report(s)"
    )

    cv = cross_validate(rows)
    table = scores(rows, cv)
    y = [r.right for r in rows]
    threshold = choose_threshold(y, cv.probabilities[SERVED], args.target)
    served = next(s for s in table if s.name == SERVED)
    base = next(s for s in table if s.name == BASE_RATE)
    created = datetime.now(UTC).date().isoformat()
    trained_on = TrainedOn(
        created=created,
        eval_version=data.eval_version,
        catalog_version=data.catalog_version,
        reports=data.reports,
        rows=len(rows),
        seed=SEED,
        metrics={
            "brier": round(served.brier, 4),
            "base_rate_brier": round(base.brier, 4),
            **({"auc": round(served.auc, 4)} if served.auc is not None else {}),
            "coverage": round(threshold.coverage, 4),
            "answered_accuracy": round(threshold.accuracy, 4),
        },
    )
    model = export(fit_final(rows), threshold, trained_on)
    args.model_out.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")
    report = build_report(data, cv, table, threshold, model, created=created)
    json_path, md_path = write_report(report, args.report_dir)
    print(
        f"Brier {served.brier:.4f} (base rate {base.brier:.4f}); threshold {threshold.threshold:.3f} "
        f"answers {threshold.coverage:.0%} at {threshold.accuracy:.1%}"
    )
    print(f"wrote {args.model_out}, {json_path} and {md_path.name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
