"""reports/report.json (what /eval and the leakage test read), report.md and the model card.

Every figure in the Markdown and the card is formatted from report.json by code, so the prose
never carries a number nobody computed.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from reranker.benchmark import Claim, dev
from reranker.dataset import Group
from reranker.experiment import BASE, EMBEDDING, RERANKER, CrossValidation
from reranker.metrics import MarginRow, Ranked, Summary, margin_table, summarize
from reranker.paraphrase import Paraphrase
from reranker.scorer import Latency

NAME = "holdsup-indicator-reranker"
HUB_OWNER = "<hub-owner>"  # set when the model is published (P4.7)
THRESHOLDS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
GROUPING = "statistic and place (a sentence and its variants stay in one fold)"
RANKER_NAMES = {
    EMBEDDING: "Embedding search alone",
    BASE: "Base cross-encoder, not fine-tuned",
    RERANKER: "Fine-tuned reranker",
}
SPLIT_NAMES = {"all": "All", "seen": "Statistic seen in training", "unseen": "Statistic not seen"}


@dataclass(frozen=True)
class Inputs:
    hyper: dict[str, Any]  # Any: a dataclass's fields (str, int, float) as asdict gives them
    claims: Sequence[Claim]
    groups: Sequence[Group]
    paraphrases: Sequence[Paraphrase]
    training_pairs: int
    cv: CrossValidation
    eval_version: str
    catalog_version: str
    paraphrases_sha256: str
    created: str


class Data(BaseModel):
    dev_claims: int
    with_indicator: int
    indicators: int
    paraphrases: int
    paraphrase_models: dict[str, int]
    queries: int
    training_pairs: int  # the final model's
    positives_added: int  # queries whose labelled indicator the search missed (training only)
    folds: int
    fold_sizes: list[int]
    grouping: str


class NoIndicator(BaseModel):
    """Claims the catalog has nothing for: the reranker's best probability should stay low."""

    claims: int
    highest_probability: float | None


class Variant(BaseModel):
    name: str  # fp32 | int8
    sha256: str
    megabytes: float
    latency: Latency


class Export(BaseModel):
    max_abs_diff: float  # fp32 ONNX vs the torch model, logits over the dev quotes
    variants: list[Variant]
    int8_top1_agreement: float  # dev quotes whose first candidate int8 and fp32 agree on
    int8_max_probability_diff: float


class Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    created: str
    eval_version: str
    catalog_version: str
    base_model: str
    hyperparameters: dict[str, Any]  # Any: see Inputs.hyper
    data: Data
    cross_validation: dict[str, dict[str, Summary]]  # ranker -> all / seen / unseen
    margins: list[MarginRow]
    no_indicator: NoIndicator
    export: Export | None = None
    paraphrases_sha256: str
    training_claims: list[str]  # every claim key the final model trained on


def _splits(rows: Sequence[Ranked]) -> dict[str, Summary]:
    return {
        "all": summarize(rows),
        "seen": summarize([r for r in rows if r.seen]),
        "unseen": summarize([r for r in rows if not r.seen]),
    }


def build_report(i: Inputs) -> Report:
    claims = dev(i.claims)
    reranked = i.cv.rows.get(RERANKER, [])
    no_indicator = [r for r in reranked if r.gold is None and r.scores]
    return Report(
        model=NAME,
        created=i.created,
        eval_version=i.eval_version,
        catalog_version=i.catalog_version,
        base_model=str(i.hyper["base_model"]),
        hyperparameters=i.hyper,
        data=Data(
            dev_claims=len(claims),
            with_indicator=sum(c.indicator is not None for c in claims),
            indicators=len({c.indicator for c in claims if c.indicator}),
            paraphrases=len(i.paraphrases),
            paraphrase_models=dict(Counter(f"{p.provider}/{p.model}" for p in i.paraphrases)),
            queries=len(i.groups),
            training_pairs=i.training_pairs,
            positives_added=sum(g.gold is not None and g.gold not in g.ids for g in i.groups),
            folds=len(i.cv.fold_sizes),
            fold_sizes=i.cv.fold_sizes,
            grouping=GROUPING,
        ),
        cross_validation={
            name: _splits(i.cv.rows[name]) for name in RANKER_NAMES if name in i.cv.rows
        },
        margins=margin_table(reranked, THRESHOLDS),
        no_indicator=NoIndicator(
            claims=sum(r.gold is None for r in reranked),
            highest_probability=(
                round(max(r.scores[0] for r in no_indicator), 4) if no_indicator else None
            ),
        ),
        paraphrases_sha256=i.paraphrases_sha256,
        training_claims=sorted({g.query.claim.key for g in i.groups}),
    )


# --- Markdown ---------------------------------------------------------------------------------


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def num(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def comparison_table(r: Report) -> list[str]:
    lines = [
        "| Claims | Ranker | n | Top-1 | Recall@8 | MRR@8 |",
        "| --- | --- | --: | --: | --: | --: |",
    ]
    for split, label in SPLIT_NAMES.items():
        for key, name in RANKER_NAMES.items():
            if key not in r.cross_validation:
                continue
            s = r.cross_validation[key][split]
            lines.append(
                f"| {label} | {name} | {s.claims} | {pct(s.top1)} | {pct(s.recall_at_8)} "
                f"| {num(s.mrr_at_8)} |"
            )
    return lines


def margin_lines(r: Report) -> list[str]:
    lines = [
        "| Margin at least | Claims answered without the model | Share | Top-1 right |",
        "| --: | --: | --: | --: |",
    ]
    for m in r.margins:
        lines.append(
            f"| {m.threshold:.1f} | {m.answered} | {pct(m.coverage)} "
            f"| {m.correct} ({pct(m.accuracy)}) |"
        )
    return lines


def export_lines(r: Report) -> list[str]:
    if r.export is None:
        return ["Not measured (no export)."]
    e = r.export
    lines = [
        "| Export | Size | Median per claim | p95 per claim |",
        "| --- | --: | --: | --: |",
    ]
    for v in e.variants:
        lines.append(
            f"| {v.name} | {v.megabytes:.1f} MB | {v.latency.p50_ms:.1f} ms "
            f"| {v.latency.p95_ms:.1f} ms |"
        )
    first = e.variants[0].latency if e.variants else None
    setup = (
        f"onnxruntime on {first.threads} CPU threads, {first.candidates_per_claim:.1f} candidates "
        f"per claim, {first.claims} claims"
        if first
        else "no variants"
    )
    return [
        *lines,
        "",
        (
            f"Measured with {setup}. The fp32 export scores as the torch model does (largest "
            f"logit difference {e.max_abs_diff:.1e}). int8 puts the same statistic first on "
            f"{pct(e.int8_top1_agreement)} of the dev quotes; its probabilities differ from "
            f"fp32's by at most {num(e.int8_max_probability_diff)}."
        ),
    ]


def data_lines(r: Report) -> list[str]:
    d = r.data
    models = ", ".join(f"{m} ({n})" for m, n in sorted(d.paraphrase_models.items())) or "none"
    return [
        (
            f"- Benchmark eval {r.eval_version}, dev split only: {d.dev_claims} claims, "
            f"{d.with_indicator} with a catalog statistic ({d.indicators} distinct), catalog "
            f"{r.catalog_version}."
        ),
        f"- {d.paraphrases} paraphrases of those claims, written offline by {models}.",
        (
            f"- {d.queries} query sentences; each is paired with the top 8 catalog entries the "
            f"search shows for its place (one positive, the rest hard negatives). "
            f"{d.positives_added} queries had their statistic outside the top 8 and get it added "
            f"as a positive for training only. {d.training_pairs} training pairs in all."
        ),
        (
            f"- {d.folds}-fold cross-validation grouped by {d.grouping}; quotes scored per fold: "
            f"{', '.join(str(n) for n in d.fold_sizes)}. Paraphrases train, never score."
        ),
        (
            "- No held-out (test split) claim, nor a paraphrase of one, is in any of it: the "
            "dataset builder refuses them and ml/tests/test_leakage.py checks this report's "
            "claim list."
        ),
    ]


def render_markdown(r: Report) -> str:
    hp = r.hyperparameters
    return "\n".join(
        [
            f"# Indicator reranker: report ({r.created})",
            "",
            (
                f"Base model `{r.base_model}` (a sentence-transformers CrossEncoder), fine-tuned "
                f"with a plain PyTorch loop; seed {hp['seed']}."
            ),
            "",
            "## Data",
            "",
            *data_lines(r),
            "",
            "## Embedding search alone vs. the reranker (cross-validated on the dev split)",
            "",
            *comparison_table(r),
            "",
            (
                "All three rank the same 8 candidates, so recall@8 is the search's ceiling and the "
                "same for each. Each claim is ranked by a model trained without its fold. A "
                "statistic is seen when some other claim about it was in that fold's training data."
            ),
            "",
            "## Margin (P4.4's skip-the-model rule)",
            "",
            (
                "Margin: the fine-tuned reranker's probability for the first candidate minus the "
                "second's. Claims with no catalog statistic count as wrong when answered."
            ),
            "",
            *margin_lines(r),
            "",
            (
                f"Claims with no catalog statistic: {r.no_indicator.claims}; the reranker's highest "
                f"first-candidate probability on them: {num(r.no_indicator.highest_probability)}."
            ),
            "",
            "## CPU latency and export",
            "",
            *export_lines(r),
            "",
            "## Hyperparameters",
            "",
            *[f"- {k}: {v}" for k, v in hp.items()],
            "",
        ]
    )


def render_card(r: Report) -> str:
    rer = r.cross_validation[RERANKER]["all"]
    emb = r.cross_validation[EMBEDDING]["all"]
    return "\n".join(
        [
            "---",
            "language: en",
            "license: apache-2.0",
            "library_name: sentence-transformers",
            "pipeline_tag: text-ranking",
            f"base_model: {r.base_model}",
            "tags: [cross-encoder, reranker, statistics, fact-checking, onnx]",
            "---",
            "",
            f"# {r.model}",
            "",
            (
                "A small cross-encoder that reranks candidate statistics for a numeric claim. Given "
                'a claim sentence ("Spain\'s youth unemployment rate was 55% in 2013") and the 8 '
                "catalog entries an embedding search found for it, it scores each pair so the "
                "statistic the claim is about comes first. It is part of HoldsUp, a statistical "
                "claim auditor, where a wide enough margin lets matching skip a language-model call."
            ),
            "",
            "## Use",
            "",
            "```python",
            "from sentence_transformers import CrossEncoder",
            "",
            f'model = CrossEncoder("{HUB_OWNER}/{r.model}")',
            "scores = model.predict([(claim, entry) for entry in entries])  # logits",
            "```",
            "",
            (
                "Scores are logits; a sigmoid turns them into 0..1. An entry is `name (unit). Also "
                "called: aliases. definition`. The ONNX exports (`model.onnx`, `tokenizer.json`, "
                "`reranker.json`) run with onnxruntime and tokenizers alone."
            ),
            "",
            "## Training data",
            "",
            *data_lines(r),
            "",
            "## Results",
            "",
            (
                f"Cross-validated on the dev split ({rer.claims} claims with a catalog statistic): "
                f"top-1 {pct(rer.top1)} against {pct(emb.top1)} for the embedding search alone, "
                f"MRR@8 {num(rer.mrr_at_8)} against {num(emb.mrr_at_8)}."
            ),
            "",
            *comparison_table(r),
            "",
            *export_lines(r),
            "",
            "## Limits",
            "",
            (
                f"- Trained on {r.data.dev_claims} English claims about European and world "
                "statistics (labour, economy, population, health, energy) and their paraphrases; it "
                f"knows the {r.data.indicators} catalog entries those claims name best. Scores on "
                "statistics it never saw in training are in the table above."
            ),
            "- It ranks what the search found; it cannot recover a statistic outside the top 8.",
            (
                "- Paraphrases come from language models and keep each claim's numbers, place and "
                "period; real phrasings are more varied."
            ),
            (
                "- The held-out test split of the benchmark was never used; the final evaluation on "
                "it is reported separately."
            ),
            "",
        ]
    )


def write_report(r: Report, reports: Path, card: Path, *copies: Path) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "report.json").write_text(r.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (reports / "report.md").write_text(render_markdown(r), encoding="utf-8")
    text = render_card(r)
    for path in (card, *copies):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
