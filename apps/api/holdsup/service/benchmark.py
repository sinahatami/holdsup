"""What the /eval page shows, read from the reports committed in the repository.

`make eval` and `make eval-chatbot` write `eval/reports/<name>.json`, and the ML code writes
`ml/<model>/reports/report.json`. Nothing here runs a model or recomputes a verdict: it reads
those files, counts claims both runs answered, and sets the figures side by side. A report this
code cannot read is skipped with a warning (an old schema, a half-written file), never an error
on the page.

The head-to-head joins a split's pipeline run (`<split>.json`) and its chatbot run on the claims
both could be scored on, so a text one of them could not be served for does not tilt the
comparison. A split can have several chatbot runs (`<split>.chatbot.json` on the router,
`<split>.chatbot.<provider>.json` on one provider): the one that answered the most claims is
used, and a run that answered none is no comparison at all. Every run is still listed.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field, ValidationError

log = structlog.get_logger(__name__)

SKIPPED_REPORTS = {"smoke"}  # the CI smoke subset is a gate, not a benchmark result
TOP_CAUSES = 3
MAX_LOSSES = 40
MARGIN_SKIP = 0.5  # reranker.margin at which matching skips the model (D030)


class Rate(BaseModel):
    """`hits` of `total`; `rate` is None when there was nothing to measure."""

    hits: int
    total: int
    rate: float | None


# --- the reports as files (only what the page needs; unknown keys are ignored) ----------------


class _Call(BaseModel):
    step: str
    provider: str
    model: str
    calls: int


class _Cost(BaseModel):
    calls_per_claim: float | None = None
    seconds_per_claim: float | None = None
    by_step_provider: list[_Call] = Field(default_factory=list)


class _Verdict(BaseModel):
    accuracy: Rate
    labels: list[str]
    confusion: dict[str, dict[str, int]]
    per_label: dict[str, Rate]


class _Excluded(BaseModel):
    claims_not_run: int
    claims_verdict_unavailable: int


class _Metrics(BaseModel):
    texts: int
    labelled_claims: int
    excluded: _Excluded
    verdict: _Verdict
    cost: _Cost
    failures: dict[str, int] = Field(default_factory=dict)


class _Outcome(BaseModel):
    text_id: str
    index: int
    quote: str
    expected: str
    status: str = "scored"
    verdict: str | None = None
    verdict_ok: bool | None = None
    reason: str = ""
    failed_step: str | None = None


class _Text(BaseModel):
    outcomes: list[_Outcome]


class _Versions(BaseModel):
    app: str
    catalog: str
    eval: str


class _Report(BaseModel):
    kind: Literal["pipeline", "chatbot"] = "pipeline"
    name: str
    created_at: datetime
    split: str
    provider: str
    versions: _Versions
    metrics: _Metrics
    texts: list[_Text]

    def outcomes(self) -> dict[tuple[str, int], _Outcome]:
        return {(o.text_id, o.index): o for t in self.texts for o in t.outcomes}


# --- what the page gets ----------------------------------------------------------------------


class ModelUsed(BaseModel):
    provider: str
    model: str
    label: str  # the readable name, or the model id when the provider is no longer configured
    calls: int


class FailureCause(BaseModel):
    step: str
    wrong: int
    share: float  # of the run's wrong verdicts


class Run(BaseModel):
    """One evaluation run: a split of the benchmark, answered by the pipeline or a chatbot."""

    name: str  # the report's file name without .json
    kind: Literal["pipeline", "chatbot"]
    split: str
    provider: str  # "router" (each step's preference list) or the one provider forced
    created_at: datetime
    app_version: str
    catalog_version: str
    eval_version: str
    models: list[ModelUsed]  # who answered, most calls first
    texts: int
    labelled_claims: int
    left_out: int  # claims not counted in the accuracy: no provider could serve them, or no data
    accuracy: Rate
    labels: list[str]
    confusion: dict[str, dict[str, int]]  # confusion[expected][answered]
    per_label: dict[str, Rate]
    failure_causes: list[FailureCause]  # the steps that broke first, most common first
    calls_per_claim: float | None
    seconds_per_claim: float | None


class Loss(BaseModel):
    """A claim HoldsUp got wrong and the chatbot got right."""

    text_id: str
    index: int
    quote: str
    expected: str
    holdsup: str  # the verdict it gave, or "missed" when the extractor never found the claim
    chatbot: str
    broke_at: str | None  # the step that went wrong
    reason: str  # HoldsUp's verdict reason, written by code


class Comparison(BaseModel):
    """HoldsUp and the chatbot on the same split, over the claims both could be scored on."""

    split: str
    holdsup: Run
    chatbot: Run
    claims: int
    holdsup_right: Rate
    chatbot_right: Rate
    both_right: int
    both_wrong: int
    only_holdsup_right: int
    only_chatbot_right: int
    losses: list[Loss]  # only_chatbot_right, at most MAX_LOSSES


class Table(BaseModel):
    columns: list[str]
    rows: list[list[str]]


class ModelReport(BaseModel):
    """A trained model's headline figures, from its committed report."""

    id: str
    title: str
    created: str
    table: Table
    notes: list[str]


class Benchmark(BaseModel):
    eval_version: str | None
    comparisons: list[Comparison]
    runs: list[Run]  # every pipeline and chatbot run, for the per-provider table
    models: list[ModelReport]


# --- reading ---------------------------------------------------------------------------------


def _read(path: Path) -> _Report | None:
    try:
        return _Report.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        log.warning("benchmark_report_unreadable", path=path.name, error=str(exc)[:200])
        return None


def _run(report: _Report, labels: dict[str, str]) -> Run:
    m = report.metrics
    calls: Counter[tuple[str, str]] = Counter()
    for c in m.cost.by_step_provider:
        calls[c.provider, c.model] += c.calls
    wrong = sum(m.failures.values())
    return Run(
        name=report.name,
        kind=report.kind,
        split=report.split,
        provider=report.provider,
        created_at=report.created_at,
        app_version=report.versions.app,
        catalog_version=report.versions.catalog,
        eval_version=report.versions.eval,
        models=[
            ModelUsed(provider=p, model=model, label=labels.get(p) or model, calls=n)
            for (p, model), n in calls.most_common()
        ],
        texts=m.texts,
        labelled_claims=m.labelled_claims,
        left_out=m.excluded.claims_not_run + m.excluded.claims_verdict_unavailable,
        accuracy=m.verdict.accuracy,
        labels=m.verdict.labels,
        confusion=m.verdict.confusion,
        per_label=m.verdict.per_label,
        failure_causes=[
            FailureCause(step=step, wrong=n, share=round(n / wrong, 4))
            for step, n in sorted(m.failures.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_CAUSES]
        ],
        calls_per_claim=m.cost.calls_per_claim,
        seconds_per_claim=m.cost.seconds_per_claim,
    )


def _rate(hits: int, total: int) -> Rate:
    return Rate(hits=hits, total=total, rate=round(hits / total, 4) if total else None)


def _compare(split: str, holdsup: _Report, chatbot: _Report, labels: dict[str, str]) -> Comparison:
    ours, theirs = holdsup.outcomes(), chatbot.outcomes()
    shared = [
        key
        for key in ours
        if key in theirs and ours[key].status == "scored" and theirs[key].status == "scored"
    ]
    both = only_ours = only_theirs = neither = 0
    losses: list[Loss] = []
    for key in shared:
        a, b = ours[key], theirs[key]
        if a.verdict_ok and b.verdict_ok:
            both += 1
        elif a.verdict_ok:
            only_ours += 1
        elif b.verdict_ok:
            only_theirs += 1
            losses.append(
                Loss(
                    text_id=a.text_id,
                    index=a.index,
                    quote=a.quote,
                    expected=a.expected,
                    holdsup=a.verdict or "missed",
                    chatbot=b.verdict or "missed",
                    broke_at=a.failed_step,
                    reason=a.reason,
                )
            )
        else:
            neither += 1
    return Comparison(
        split=split,
        holdsup=_run(holdsup, labels),
        chatbot=_run(chatbot, labels),
        claims=len(shared),
        holdsup_right=_rate(both + only_ours, len(shared)),
        chatbot_right=_rate(both + only_theirs, len(shared)),
        both_right=both,
        both_wrong=neither,
        only_holdsup_right=only_ours,
        only_chatbot_right=only_theirs,
        losses=losses[:MAX_LOSSES],
    )


def _answered(report: _Report) -> int:
    """The claims the run could score: those that were not left out."""
    m = report.metrics
    return m.labelled_claims - m.excluded.claims_not_run - m.excluded.claims_verdict_unavailable


def _chatbot_for(reports: list[_Report], split: str) -> _Report | None:
    """The chatbot run of a split that answered the most claims; the router's run on a tie."""
    answered = [r for r in reports if r.kind == "chatbot" and r.split == split and _answered(r) > 0]
    return min(answered, key=lambda r: (-_answered(r), r.name), default=None)


def read_runs(reports_dir: Path, labels: dict[str, str]) -> tuple[list[_Report], list[Run]]:
    reports = [
        r
        for path in sorted(reports_dir.glob("*.json"))
        if path.stem not in SKIPPED_REPORTS and (r := _read(path)) is not None
    ]
    reports.sort(key=lambda r: (r.split, r.kind != "pipeline", r.name))
    return reports, [_run(r, labels) for r in reports]


def read_benchmark(reports_dir: Path, ml_dir: Path, labels: dict[str, str]) -> Benchmark:
    """Everything the /eval page shows. `labels` maps a provider's name to its readable name."""
    reports, runs = read_runs(reports_dir, labels)
    by_name = {r.name: r for r in reports}
    comparisons = [
        _compare(split, ours, theirs, labels)
        for split in sorted({r.split for r in reports})
        if (ours := by_name.get(split)) is not None
        and ours.kind == "pipeline"
        and (theirs := _chatbot_for(reports, split)) is not None
    ]
    version = reports_dir.parent / "VERSION"
    return Benchmark(
        eval_version=version.read_text(encoding="utf-8").strip() if version.exists() else None,
        comparisons=comparisons,
        runs=runs,
        models=[m for m in (_reranker(ml_dir), _confidence(ml_dir)) if m is not None],
    )


# --- the trained models' reports -------------------------------------------------------------


def _json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("model_report_unreadable", path=str(path), error=str(exc)[:200])
        return None
    return data if isinstance(data, dict) else None


def _pct(value: object) -> str:
    return f"{value * 100:.1f}%" if isinstance(value, int | float) else "n/a"


def _num(value: object, digits: int = 3) -> str:
    return f"{value:.{digits}f}" if isinstance(value, int | float) else "n/a"


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _reranker(ml_dir: Path) -> ModelReport | None:
    report = _json(ml_dir / "reranker" / "reports" / "report.json")
    if report is None:
        return None
    cv = _dict(report.get("cross_validation"))
    rows = []
    for key, name in (
        ("embedding", "Embedding search alone"),
        ("base", "Cross-encoder before fine-tuning"),
        ("reranker", "Fine-tuned reranker"),
    ):
        # Unseen: claims whose statistic and place were held out of that fold's training.
        unseen = _dict(_dict(cv.get(key)).get("unseen"))
        everything = _dict(_dict(cv.get(key)).get("all"))
        rows.append(
            [
                name,
                _pct(everything.get("top1")),
                _pct(unseen.get("top1")),
                _pct(everything.get("recall_at_8")),
                _num(everything.get("mrr_at_8")),
            ]
        )
    notes = [
        (
            "Cross-validated on the dev split in five folds grouped by statistic and place: "
            "each claim is scored by a model that never trained on it. The held-out claims are "
            "not used until the final evaluation."
        ),
    ]
    margin = next(
        (m for m in map(_dict, _list(report.get("margins"))) if m.get("threshold") == MARGIN_SKIP),
        None,
    )
    if margin is not None:
        notes.append(
            f"When the top statistic leads by at least {MARGIN_SKIP}, matching skips the model: "
            f"that covers {_pct(margin.get('coverage'))} of dev claims, and the top pick is right "
            f"for {_pct(margin.get('accuracy'))} of them."
        )
    return ModelReport(
        id="reranker",
        title="Indicator reranker",
        created=str(report.get("created", "")),
        table=Table(
            columns=["Matching", "Top-1", "Top-1, unseen statistics", "Recall@8", "MRR@8"],
            rows=rows,
        ),
        notes=notes,
    )


def _confidence(ml_dir: Path) -> ModelReport | None:
    report = _json(ml_dir / "confidence" / "reports" / "report.json")
    if report is None:
        return None
    cv = _dict(report.get("cross_validation"))
    rows = [
        [
            str(m.get("label", m.get("name", ""))),
            _num(m.get("brier"), 4),
            _num(m.get("log_loss"), 4),
            _num(m.get("auc"), 3),
        ]
        for m in map(_dict, _list(cv.get("models")))
    ]
    data = _dict(report.get("data"))
    notes = [
        (
            f"{data.get('rows', '?')} dev verdicts, {data.get('wrong', '?')} of them wrong; "
            "cross-validated in folds grouped by statistic and place. Lower Brier score is "
            "better; a model that does not beat the base rate has learned nothing."
        ),
    ]
    if cv.get("beats_base_rate") is False:
        notes.append(
            "Not served: the logistic regression did not beat the base rate, so no result "
            "shows a confidence score and no verdict is held back."
        )
        if cv.get("boosting_clearly_better") is True:
            notes.append(
                "Gradient boosting did clearly better in cross-validation; it is planned for "
                "the final evaluation."
            )
    notes += [str(n) for n in _list(report.get("limitations"))]
    return ModelReport(
        id="confidence",
        title="Confidence model",
        created=str(report.get("created", "")),
        table=Table(columns=["Model", "Brier score", "Log loss", "AUC"], rows=rows),
        notes=notes,
    )
