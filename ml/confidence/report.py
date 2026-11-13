"""reports/report.json (what /eval reads) and report.md: every figure in the Markdown is
formatted from report.json by code."""

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from confidence.dataset import Dataset
from confidence.experiment import (
    BASE_RATE,
    BOOSTING,
    CLEAR_GAIN,
    FOLDS,
    SEED,
    SERVED,
    C,
    CrossValidation,
    Score,
    matrix,
)
from confidence.metrics import Threshold, calibration, coverage_curve
from holdsup.ml.confidence import EXPECTED_SIGN, FEATURES, ConfidenceModel

NAME = "holdsup-confidence"
COVERAGES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)  # rows of the coverage table
LIMITATIONS = (
    (
        "The served reranker was fine-tuned on every dev claim (P4.3), so on these rows its "
        "probabilities and margins are in-sample: higher, and more often right, than on claims it "
        "has never seen. The model may lean on them more than it should; the held-out evaluation "
        "(P4.7) is the honest check of its calibration."
    ),
    (
        "About a hundred rows, most of them right: one claim moves the figures by about a point, "
        "and the threshold can move with them."
    ),
    (
        "Rows come from the runs named above; a run on backup models (a provider at its daily "
        "limit) has more wrong verdicts and more fallback steps than a usual day."
    ),
)


class Data(BaseModel):
    reports: dict[str, str]
    eval_version: str
    catalog_version: str
    rows: int
    right: int
    wrong: int
    groups: int
    skipped: dict[str, int]
    missing: dict[str, int]  # feature -> rows without it


class ModelRow(BaseModel):
    name: str
    label: str
    brier: float
    log_loss: float
    auc: float | None


class BinRow(BaseModel):
    low: float
    high: float
    n: int
    mean_probability: float | None
    accuracy: float | None


class CoverageRow(BaseModel):
    answered: int
    coverage: float
    accuracy: float
    lowest: float


class CrossValidated(BaseModel):
    folds: int
    fold_sizes: list[int]
    grouping: str
    models: list[ModelRow]
    calibration: list[BinRow]  # the served model's, out of fold
    coverage: list[CoverageRow]  # the served model's, out of fold
    threshold: Threshold
    beats_base_rate: bool  # the served model's Brier score is below the base rate's
    boosting_clearly_better: bool  # by CLEAR_GAIN or more: then boosting should be served


class Coefficient(BaseModel):
    feature: str
    weight: float  # per standard deviation
    expected_sign: int
    as_expected: bool  # a weight of the other sign never gives an abstention reason


class Served(BaseModel):
    threshold: float
    high: float
    target_accuracy: float
    intercept: float
    coefficients: list[Coefficient]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    created: str
    seed: int
    hyperparameters: dict[str, float | int | str]
    data: Data
    cross_validation: CrossValidated
    served: Served
    limitations: list[str]


def build_report(
    data: Dataset,
    cv: CrossValidation,
    table: Sequence[Score],
    threshold: Threshold,
    model: ConfidenceModel,
    *,
    created: str,
) -> Report:
    rows = data.rows
    y = [r.right for r in rows]
    p = cv.probabilities[SERVED]
    x, _ = matrix(rows)
    by_name = {s.name: s for s in table}
    served, base, boost = by_name[SERVED], by_name[BASE_RATE], by_name[BOOSTING]
    right = sum(y)
    return Report(
        model=NAME,
        created=created,
        seed=SEED,
        hyperparameters={
            "model": "logistic regression (L2), standardized signals, mean imputation",
            "C": C,
            "folds": FOLDS,
            "clear_gain": CLEAR_GAIN,
        },
        data=Data(
            reports=data.reports,
            eval_version=data.eval_version,
            catalog_version=data.catalog_version,
            rows=len(rows),
            right=right,
            wrong=len(rows) - right,
            groups=len({r.group for r in rows}),
            skipped=data.skipped,
            missing={f: int(np.isnan(x[:, i]).sum()) for i, f in enumerate(FEATURES)},
        ),
        cross_validation=CrossValidated(
            folds=len(cv.fold_sizes),
            fold_sizes=cv.fold_sizes,
            grouping="statistic and place (a claim's rows from several runs stay in one fold)",
            models=[
                ModelRow(name=s.name, label=s.label, brier=s.brier, log_loss=s.log_loss, auc=s.auc)
                for s in table
            ],
            calibration=[BinRow(**vars(b)) for b in calibration(y, p)],
            coverage=[CoverageRow(**vars(c)) for c in coverage_curve(y, p)],
            threshold=threshold,
            beats_base_rate=served.brier < base.brier,
            boosting_clearly_better=boost.brier <= served.brier - CLEAR_GAIN,
        ),
        served=Served(
            threshold=model.threshold,
            high=model.high,
            target_accuracy=model.target_accuracy,
            intercept=model.intercept,
            coefficients=[
                Coefficient(
                    feature=f,
                    weight=w,
                    expected_sign=EXPECTED_SIGN[f],
                    as_expected=w * EXPECTED_SIGN[f] > 0,
                )
                for f, w in zip(FEATURES, model.coef, strict=True)
            ],
        ),
        limitations=list(LIMITATIONS),
    )


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _num(v: float | None, digits: int = 3) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
        *("| " + " | ".join(r) + " |" for r in rows),
        "",
    ]


def _at_coverage(points: Sequence[CoverageRow], share: float) -> CoverageRow | None:
    """The point answering the most claims without going over `share` of them."""
    fits = [c for c in points if c.coverage <= share + 1e-9]
    return max(fits, key=lambda c: c.answered) if fits else None


def markdown(r: Report) -> str:
    d, cv, s = r.data, r.cross_validation, r.served
    t = cv.threshold
    out = [
        "# Confidence model",
        "",
        (
            "How likely a verdict is to be right, from signals the check already has; below the "
            'threshold the result page says "can\'t check confidently" and why (P4.5).'
        ),
        "",
        "## Data",
        "",
        f"- Dev-split evaluation reports (eval {d.eval_version}, catalog {d.catalog_version}): "
        + ", ".join(f"`{name}` (sha256 {sha[:12]})" for name, sha in d.reports.items())
        + ".",
        (
            f"- {d.rows} claims with a verdict other than cant_check: {d.right} right, {d.wrong} "
            f"wrong, in {d.groups} groups."
        ),
        "- Not rows: " + ("; ".join(f"{why}: {n}" for why, n in d.skipped.items()) or "none") + ".",
        "- Missing signals (read as the training mean): "
        + (", ".join(f"{f} {n}" for f, n in d.missing.items() if n) or "none")
        + ".",
        "",
        "## Cross-validation",
        "",
        (
            f"{cv.folds} folds, grouped by {cv.grouping}; fold sizes "
            f"{', '.join(map(str, cv.fold_sizes))}. Every figure is out of fold."
        ),
        "",
    ]
    out += _table(
        ["Model", "Brier", "Log loss", "AUC"],
        [[m.label, _num(m.brier), _num(m.log_loss), _num(m.auc)] for m in cv.models],
    )
    out += [
        (
            f"- The served model {'beats' if cv.beats_base_rate else 'does not beat'} the base rate "
            "on the Brier score."
        ),
        (
            f"- Gradient boosting is {'clearly better (serve it instead: P4.7)' if cv.boosting_clearly_better else 'not clearly better'}"
            f" (a clear gain is a Brier score {r.hyperparameters['clear_gain']} lower)."
        ),
        "",
        "## Calibration (served model, out of fold)",
        "",
    ]
    out += _table(
        ["Probability", "Claims", "Mean probability", "Share right"],
        [
            [f"{b.low:.1f}–{b.high:.1f}", str(b.n), _num(b.mean_probability), _pct(b.accuracy)]
            for b in cv.calibration
        ],
    )
    out += ["## Accuracy against coverage (served model, out of fold)", ""]
    rows = []
    for share in COVERAGES:
        point = _at_coverage(cv.coverage, share)
        if point is not None:
            rows.append(
                [
                    f"{share:.0%}",
                    f"{point.answered} ({_pct(point.coverage)})",
                    _pct(point.accuracy),
                    _num(point.lowest),
                ]
            )
    out += _table(["Answer at most", "Answered", "Accuracy", "Lowest probability answered"], rows)
    met = "reaches" if t.met else "cannot reach; the most accurate coverage is used"
    out += [
        "## Threshold",
        "",
        f"- Target: answered verdicts right {_pct(t.target)} of the time ({met}).",
        (
            f"- Threshold {_num(t.threshold)}: answers {t.answered} of {d.rows} ({_pct(t.coverage)}), "
            f"abstains on {_pct(1 - t.coverage)}; answered accuracy {_pct(t.accuracy)} out of fold."
        ),
        (
            f"- Confidence is high at {_num(s.high, 2)} or above, medium from the threshold up, low "
            "(abstain) below it."
        ),
        "",
        "## Served coefficients (per standard deviation; trained on every row)",
        "",
    ]
    out += _table(
        ["Signal", "Weight", "Expected", "As expected"],
        [
            [
                c.feature,
                f"{c.weight:+.3f}",
                "+" if c.expected_sign > 0 else "−",
                _expected(c),
            ]
            for c in s.coefficients
        ],
    )
    out += [f"Intercept {s.intercept:+.3f}.", "", "## Limitations", ""]
    out += [f"- {line}" for line in r.limitations]
    return "\n".join(out) + "\n"


def _expected(c: Coefficient) -> str:
    if c.weight == 0:
        return "no weight (the signal never varied)"
    return "yes" if c.as_expected else "no: never a reason"


def write_report(report: Report, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / "report.json", out_dir / "report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    return json_path, md_path
