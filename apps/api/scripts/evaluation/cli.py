"""`make eval-smoke` and `make eval`: read the benchmark, run it, write the report, gate it.

A run keeps each finished text in `<name>.partial.jsonl` until the report is written; one that
stops part-way is continued with --resume (checkpoint.py).

Exit codes: 0 done (and, with --gate, within 5 points of the baseline); 1 the gate found a
regression; 2 the command could not run (bad file, wrong flags, a partial run of something
else to resume); 3 the gate could not judge
(no baseline, a different benchmark version, too many claims dropped out, or a step's
first-choice model reached its daily limit).
"""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from holdsup.catalog.schema import Catalog, CatalogError, load_catalog
from holdsup.config import REPO_ROOT, get_settings
from holdsup.pipeline.result import app_version
from holdsup.router import RouterConfig, Use, load_router_config
from holdsup.verdict import Tolerances, load_tolerances
from scripts.evaluation import gate
from scripts.evaluation.benchmark import (
    BenchmarkError,
    BenchmarkText,
    Selection,
    check_indicators,
    load_benchmark,
    select,
)
from scripts.evaluation.checkpoint import Checkpoint, CheckpointError, Header, checkpoint_path
from scripts.evaluation.report import ROUTER, Report, Stamp, build_report, write_report
from scripts.evaluation.run import (
    DEFAULT_RETRIES,
    OnText,
    Rig,
    TextRun,
    evaluate,
    live_rig,
    only_provider,
)
from scripts.evaluation.score import summarize

DEFAULT_CLAIMS = Path("eval/claims.jsonl")
DEFAULT_OUT = Path("eval/reports")
SPLITS: tuple[Selection, ...] = ("dev", "test", "all")

# How the live rig is made; tests pass a rig of fakes instead.
RigFactory = Callable[[Catalog, RouterConfig, Tolerances, Use], AbstractAsyncContextManager[Rig]]


class UsageError(Exception):
    """The command cannot run as asked; the message says why."""


def _resolve(path: Path) -> Path:
    """Relative paths are relative to the repo root (make runs scripts from apps/api)."""
    return path if path.is_absolute() else REPO_ROOT / path


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="make eval ARGS=...")
    p.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS, help="the benchmark (jsonl)")
    p.add_argument("--split", choices=SPLITS, default="dev", help="which texts to run")
    p.add_argument(
        "--final",
        action="store_true",
        help="allow the held-out test split: for the final report only (P4.7), never for tuning",
    )
    p.add_argument("--limit", type=int, default=None, help="only the first N texts")
    p.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="times to wait out a rate-limited router and retry a text before dropping it",
    )
    p.add_argument("--provider", default=None, help="force every step onto this one provider")
    p.add_argument("--use", choices=[u.value for u in Use], default=Use.LIVE.value)
    p.add_argument("--catalog", type=Path, default=None, help="default: packages/catalog")
    p.add_argument("--name", default=None, help="report file name; default: the split")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--baseline", type=Path, default=None, help="default: baseline.json by --claims")
    p.add_argument("--gate", action="store_true", help="fail on a drop of more than 5 points")
    p.add_argument("--max-drop", type=float, default=gate.MAX_DROP_POINTS)
    p.add_argument("--update-baseline", action="store_true", help="accept this run as baseline")
    p.add_argument(
        "--resume",
        action="store_true",
        help="continue the partial run a stopped run of the same name left; otherwise start over",
    )
    return p


def _check_flags(args: argparse.Namespace) -> None:
    if args.split in ("test", "all") and not args.final:
        raise UsageError(
            "the test split is held out for the final report: pass --final (P4.7), never to tune"
        )
    if args.gate and args.update_baseline:
        raise UsageError("use --gate or --update-baseline, not both")
    if (args.gate or args.update_baseline) and (args.provider or args.limit):
        raise UsageError(
            "--gate and --update-baseline compare whole router runs: no --provider or --limit"
        )


def _config(args: argparse.Namespace) -> RouterConfig:
    config = load_router_config()
    if args.provider is None:
        return config
    try:
        provider = config.provider(args.provider)
    except KeyError:
        known = ", ".join(p.name for p in config.providers)
        raise UsageError(f"unknown provider {args.provider!r}; known: {known}") from None
    if not provider.serves(Use(args.use)):
        raise UsageError(f"{provider.name} may only run offline jobs: pass --use offline")
    return only_provider(config, provider.name)


def _eval_version(claims: Path) -> str:
    version = claims.parent / "VERSION"
    if not version.exists():
        raise UsageError(f"{version} not found: the benchmark needs a version")
    return version.read_text(encoding="utf-8").strip()


def _pct(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def summary(report: Report) -> str:
    m = report.metrics
    return (
        f"{m.labelled_claims} claims in {m.texts} texts: "
        f"verdict accuracy {_pct(m.verdict.accuracy.rate)}, "
        f"extraction recall {_pct(m.extraction.recall.rate)}, "
        f"match top-1 {_pct(m.matching.top1.rate)}, recall@8 {_pct(m.matching.recall_at_8.rate)}, "
        f"{m.cost.model_calls} model calls, {m.cost.seconds:.0f} s"
    )


def _stderr(line: str) -> None:
    print(line, file=sys.stderr)


async def _evaluate(
    texts: Sequence[BenchmarkText],
    catalog: Catalog,
    config: RouterConfig,
    tolerances: Tolerances,
    use: Use,
    factory: RigFactory,
    retries: int,
    on_text: OnText,
) -> list[TextRun]:
    runs: list[TextRun] = []

    def keep(run: TextRun) -> None:
        on_text(run)
        runs.append(run)

    async with factory(catalog, config, tolerances, use) as rig:
        await evaluate(rig, texts, _stderr, retries=retries, on_text=keep)
    return runs


def _checkpoint(path: Path, header: Header, resume: bool) -> Checkpoint:
    if resume:
        return Checkpoint.resume(path, header)
    if path.exists():
        _stderr(f"starting over: replacing the partial run in {path.name} (--resume continues it)")
    return Checkpoint.start(path, header)


def main(argv: Sequence[str], factory: RigFactory = live_rig) -> int:
    args = _parser().parse_args(argv)
    claims = _resolve(args.claims)
    try:
        _check_flags(args)
        catalog = load_catalog(
            _resolve(args.catalog) if args.catalog else get_settings().catalog_dir
        )
        benchmark = load_benchmark(claims)
        check_indicators(benchmark, catalog)
        version = _eval_version(claims)
        config = _config(args)
    except (UsageError, BenchmarkError, CatalogError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 2
    texts = select(benchmark, args.split)[: args.limit]
    if not texts:
        print(f"no texts in the {args.split} split of {claims.name}", file=sys.stderr)
        return 2

    use = Use(args.use)
    tolerances = load_tolerances()
    out_dir = _resolve(args.out_dir)
    suffix = f".{args.provider}" if args.provider else ""
    header = Header(
        name=(args.name or args.split) + suffix,
        benchmark=claims.name,
        split=args.split,
        provider=args.provider or ROUTER,
        use=args.use,
        versions=Stamp(
            app=app_version(), catalog=catalog.version, tolerances=tolerances.version, eval=version
        ),
    )
    try:
        checkpoint = _checkpoint(checkpoint_path(out_dir, header.name), header, args.resume)
    except CheckpointError as exc:
        print(exc, file=sys.stderr)
        return 2
    done = {t.id: checkpoint.done[t.id] for t in texts if t.id in checkpoint.done}
    todo = [t for t in texts if t.id not in done]
    if done:
        _stderr(f"resuming {checkpoint.path.name}: {len(done)} of {len(texts)} texts already ran")
    ran = (
        asyncio.run(
            _evaluate(
                todo, catalog, config, tolerances, use, factory, args.retries, checkpoint.record
            )
        )
        if todo
        else []
    )

    by_id = done | {run.outcome.id: run for run in ran}
    runs = [by_id[t.id] for t in texts]
    metrics = summarize(
        [run.outcome for run in runs],
        [call for run in runs for call in run.calls],
        series_requests=sum(run.series_requests for run in runs),
        series_fetches=sum(run.series_fetches for run in runs),
    )
    report = build_report(
        name=header.name,
        benchmark=header.benchmark,
        split=header.split,
        provider=header.provider,
        use=header.use,
        versions=header.versions,
        config=config,
        metrics=metrics,
        texts=[run.outcome for run in runs],
    )
    json_path, md_path = write_report(report, out_dir)
    checkpoint.remove()
    print(summary(report))
    print(f"wrote {json_path} and {md_path.name}")

    baseline = _resolve(args.baseline) if args.baseline else claims.parent / "baseline.json"
    if args.update_baseline:
        try:
            gate.write_baseline(baseline, gate.baseline_of(report))
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"wrote {baseline}")
    if args.gate:
        verdict = gate.check(report, gate.read_baseline(baseline), max_drop=args.max_drop)
        print(f"gate: {verdict.message}", file=sys.stderr if verdict.outcome else sys.stdout)
        return int(verdict.outcome)
    return 0
