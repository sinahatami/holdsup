"""Cross-validation on the dev split, the final fit, the ONNX export and the report.

    make reranker-train                          # after `make ml-setup`; over an hour on CPU
    make reranker-train ARGS="--quick /tmp/rr"   # every step in minutes, on a slice

The dev split trains the model, so it cannot also score it: each of 5 folds trains on the
other folds' claims (quotes and paraphrases) and ranks its own quotes, which no model has seen.
Folds are grouped by statistic and place (benchmark.Claim.group). The embedding search alone
and the pretrained cross-encoder before fine-tuning rank the same lists, so the columns differ
only in the order. The final model then trains on every dev claim and is exported; its numbers
in the report are the cross-validated ones.
"""

import gc
import hashlib
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from holdsup.catalog.schema import Catalog
from reranker.dataset import Group, Pair, pairs
from reranker.folds import assign_folds
from reranker.metrics import Ranked, rank, sigmoid

FOLDS = 5


@dataclass(frozen=True)
class Hyper:
    base_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    epochs: int = 2  # about ten pairs a second on a laptop CPU: 3 epochs would take two hours
    learning_rate: float = 3e-5
    batch_size: int = 32
    warmup: float = 0.1
    weight_decay: float = 0.01
    max_length: int = 256
    seed: int = 13
    threads: int = 6  # physical cores on the training laptop; hyperthreads do not help


class Model(Protocol):
    def logits(self, query: str, documents: Sequence[str]) -> list[float]: ...


Fit = Callable[[Sequence[Pair]], Model]


# The rankers compared, in report order. "base" is the pretrained cross-encoder before any
# fine-tuning: it shows how much of the gain is the fine-tuning's.
EMBEDDING, BASE, RERANKER = "embedding", "base", "reranker"


@dataclass
class CrossValidation:
    rows: dict[str, list[Ranked]] = field(default_factory=dict)  # ranker -> one row per quote
    fold_sizes: list[int] = field(default_factory=list)  # quotes scored per fold
    training_pairs: list[int] = field(default_factory=list)  # per fold

    def add(self, ranker: str, row: Ranked) -> None:
        self.rows.setdefault(ranker, []).append(row)


def documents(group: Group, catalog: Catalog) -> list[str]:
    return [catalog.get(i).rerank_text() for i in group.ids]


def ranked_by(model: Model, group: Group, catalog: Catalog, *, seen: bool) -> Ranked:
    probabilities = [sigmoid(x) for x in model.logits(group.query.text, documents(group, catalog))]
    return rank(group.query.claim.key, group.gold, group.ids, probabilities, seen=seen)


def cross_validate(
    groups: Sequence[Group],
    catalog: Catalog,
    fit: Fit,
    *,
    k: int = FOLDS,
    seed: int,
    base: Model | None = None,
) -> CrossValidation:
    originals = [g for g in groups if not g.query.paraphrase]
    fold_of = assign_folds([g.query.claim.group for g in originals], k, seed)
    cv = CrossValidation()
    for fold in range(k):
        train = [g for g in groups if fold_of[g.query.claim.group] != fold]
        held = [g for g in originals if fold_of[g.query.claim.group] == fold]
        if {g.query.claim.group for g in train} & {g.query.claim.group for g in held}:
            raise RuntimeError(f"fold {fold}: a group is on both sides")  # by construction, never
        started = time.perf_counter()
        training = pairs(train, catalog)
        model = fit(training)
        seen = {g.gold for g in train if g.gold is not None}
        for g in held:
            known = g.gold in seen
            cv.add(EMBEDDING, Ranked(g.query.claim.key, g.gold, g.ids, g.similarities, known))
            if base is not None:
                cv.add(BASE, ranked_by(base, g, catalog, seen=known))
            cv.add(RERANKER, ranked_by(model, g, catalog, seen=known))
        cv.fold_sizes.append(len(held))
        cv.training_pairs.append(len(training))
        del model
        gc.collect()
        took = time.perf_counter() - started
        print(f"fold {fold + 1}/{k}: {len(held)} claims, {len(training)} pairs, {took:.0f} s",
              file=sys.stderr)  # fmt: skip
    return cv


Work = Sequence[tuple[str, Sequence[str]]]  # (claim sentence, candidate documents)


def max_logit_diff(a: Model, b: Model, work: Work) -> float:
    return max(
        (abs(x - y) for q, d in work for x, y in zip(a.logits(q, d), b.logits(q, d), strict=True)),
        default=0.0,
    )


def agreement(a: Model, b: Model, work: Work) -> tuple[float, float]:
    """The share of claims whose first candidate is the same under both models, and the
    largest difference in any candidate's probability."""
    same, worst = 0, 0.0
    for query, docs in work:
        if not docs:
            same += 1  # nothing to order, nothing to disagree on
            continue
        pa = [sigmoid(x) for x in a.logits(query, docs)]
        pb = [sigmoid(x) for x in b.logits(query, docs)]
        same += pa.index(max(pa)) == pb.index(max(pb))
        worst = max([worst, *(abs(x - y) for x, y in zip(pa, pb, strict=True))])
    return (same / len(work) if work else 1.0), worst


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def today() -> str:
    return datetime.now(UTC).date().isoformat()


QUICK_CLAIMS = 25  # --quick: this many dev claims (and their paraphrases), 2 folds, 1 epoch


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - needs `train`, the model
    import argparse

    from holdsup.catalog.embed import FastEmbedder
    from holdsup.catalog.schema import load_catalog
    from holdsup.config import get_settings
    from reranker import (
        ARTIFACTS,
        CATALOG,
        CLAIMS,
        EVAL_VERSION,
        MODEL_CARD,
        PARAPHRASES,
        REPORTS,
        train,
    )
    from reranker.benchmark import dev, load_claims
    from reranker.dataset import build_groups, embedding_search
    from reranker.paraphrase import read_rows
    from reranker.report import Export, Inputs, Variant, build_report, write_report
    from reranker.scorer import ExportMeta, OnnxReranker, measure, write_meta

    parser = argparse.ArgumentParser(prog="python -m reranker.experiment")
    parser.add_argument(
        "--quick",
        type=Path,
        metavar="DIR",
        help="a few-minute run of every step on a slice of the data, written under DIR "
        "(checks the code, not the model)",
    )
    args = parser.parse_args(argv)
    hp, k = Hyper(), FOLDS
    artifacts, reports, card = ARTIFACTS, REPORTS, MODEL_CARD
    if args.quick is not None:
        hp, k = replace(hp, epochs=1), 2
        artifacts, reports, card = (
            args.quick / "artifacts",
            args.quick / "reports",
            args.quick / "card.md",
        )

    claims = load_claims(CLAIMS)
    catalog = load_catalog(CATALOG)
    paraphrases = read_rows(PARAPHRASES)
    embedder = FastEmbedder(get_settings().fastembed_cache_path)
    groups = build_groups(claims, paraphrases, catalog, embedding_search(catalog, embedder))
    if args.quick is not None:
        keep = {c.key for c in dev(claims)[:QUICK_CLAIMS]}
        groups = [g for g in groups if g.query.claim.key in keep]
    print(f"{len(groups)} query groups", file=sys.stderr)

    cv = cross_validate(
        groups, catalog, lambda p: train.fit(p, hp), k=k, seed=hp.seed, base=train.pretrained(hp)
    )

    final_pairs = pairs(groups, catalog)
    model = train.fit(final_pairs, hp)
    model_dir, onnx_dir, int8_dir = artifacts / "model", artifacts / "onnx", artifacts / "int8"
    train.save(model, model_dir)
    pad_token, pad_id = train.export_onnx(model, onnx_dir)

    inputs = Inputs(
        hyper=asdict(hp),
        claims=claims,
        groups=groups,
        paraphrases=paraphrases,
        training_pairs=len(final_pairs),
        cv=cv,
        eval_version=EVAL_VERSION.read_text().strip(),
        catalog_version=catalog.version,
        paraphrases_sha256=sha256(PARAPHRASES),
        created=today(),
    )
    report = build_report(inputs)
    write_meta(
        onnx_dir,
        ExportMeta(
            inputs=train.INPUTS,
            max_length=hp.max_length,
            pad_id=pad_id,
            pad_token=pad_token,
            base_model=hp.base_model,
            eval_version=inputs.eval_version,
            catalog_version=inputs.catalog_version,
            paraphrases_sha256=inputs.paraphrases_sha256,
            seed=hp.seed,
            created=inputs.created,
            cv_top1=report.cross_validation[RERANKER]["all"].top1,
            cv_mrr_at_8=report.cross_validation[RERANKER]["all"].mrr_at_8,
        ),
    )
    train.quantize(onnx_dir, int8_dir)

    # The export must score as the torch model does; latency is the served path's (2 threads,
    # as on a Hugging Face Spaces CPU). int8 is smaller and faster; it is only as good as its
    # agreement with the full-precision export, since the dev split cannot score it again.
    originals = [g for g in groups if not g.query.paraphrase]
    work = [(g.query.text, documents(g, catalog)) for g in originals]
    fp32, int8 = OnnxReranker.load(onnx_dir, threads=2), OnnxReranker.load(int8_dir, threads=2)
    top1_agreement, probability_diff = agreement(fp32, int8, work)
    export = Export(
        max_abs_diff=max_logit_diff(fp32, model, work),
        variants=[
            Variant(
                name=name,
                sha256=sha256(folder / "model.onnx"),
                megabytes=round((folder / "model.onnx").stat().st_size / 1e6, 1),
                latency=measure(runner, work, threads=2),
            )
            for name, folder, runner in (("fp32", onnx_dir, fp32), ("int8", int8_dir, int8))
        ],
        int8_top1_agreement=top1_agreement,
        int8_max_probability_diff=probability_diff,
    )
    report = report.model_copy(update={"export": export})
    write_report(report, reports, card, model_dir / "README.md")
    print(f"report: {reports / 'report.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
