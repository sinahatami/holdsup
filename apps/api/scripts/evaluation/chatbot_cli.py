"""`make eval-chatbot`: the plain-chatbot baseline over the benchmark, as a report.

The same benchmark file, split and report folder as `make eval`; the report is named
`<split>.chatbot.<provider>` and is `kind: chatbot`. One model answers every text: the first
provider of the router's `baseline` step unless --provider names another. Failing over down
that step would hand texts to weaker models whenever the first is rate-limited, and a baseline
made of several models measures none of them (D033). The held-out test split needs --final,
as for the pipeline (P4.7).

Exit codes: 0 done; 2 the command could not run (bad file, wrong flags, a partial run of
something else to resume).
"""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from holdsup.catalog.schema import Catalog, CatalogError, load_catalog
from holdsup.config import get_settings
from holdsup.pipeline.result import app_version
from holdsup.router import RouterConfig, Use, load_router_config
from holdsup.verdict import load_tolerances
from scripts.evaluation.benchmark import (
    BenchmarkError,
    BenchmarkText,
    check_indicators,
    load_benchmark,
    select,
)
from scripts.evaluation.chatbot import STEP, ChatRig, evaluate_chatbot, live_chat_rig
from scripts.evaluation.checkpoint import Checkpoint, CheckpointError, Header, checkpoint_path
from scripts.evaluation.cli import (
    DEFAULT_CLAIMS,
    DEFAULT_OUT,
    SPLITS,
    UsageError,
    _checkpoint,
    _config,
    _eval_version,
    _pct,
    _resolve,
    _stderr,
)
from scripts.evaluation.patient import BUDGET_S
from scripts.evaluation.report import Report, Stamp, build_report, write_report
from scripts.evaluation.run import TextRun
from scripts.evaluation.score import summarize


def summary(report: Report) -> str:
    m = report.metrics
    return (
        f"{m.labelled_claims} claims in {m.texts} texts: "
        f"verdict accuracy {_pct(m.verdict.accuracy.rate)}, {m.cost.model_calls} model calls, "
        f"{m.cost.seconds:.0f} s"
    )


# How the live rig is made (config, seconds the run may spend waiting out rate limits).
ChatRigFactory = Callable[[RouterConfig, float], AbstractAsyncContextManager[ChatRig]]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="make eval-chatbot ARGS=...")
    p.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS, help="the benchmark (jsonl)")
    p.add_argument("--split", choices=SPLITS, default="dev", help="which texts to run")
    p.add_argument(
        "--final",
        action="store_true",
        help="allow the held-out test split: for the final report only (P4.7), never for tuning",
    )
    p.add_argument("--limit", type=int, default=None, help="only the first N texts")
    p.add_argument(
        "--provider",
        default=None,
        help="the one provider whose model answers; default: the first of the baseline step",
    )
    # Offline tooling, so the offline-only provider (Gemini) may answer; D003 is about live users.
    p.add_argument("--use", choices=[u.value for u in Use], default=Use.OFFLINE.value)
    p.add_argument("--catalog", type=Path, default=None, help="default: packages/catalog")
    p.add_argument("--name", default=None, help="report file name; default: <split>.chatbot")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--resume", action="store_true", help="continue a stopped run of this name")
    p.add_argument(
        "--wait-budget",
        type=float,
        default=BUDGET_S,
        metavar="SECONDS",
        help=(
            "in all, wait at most this long for rate limits before leaving texts not run "
            f"(default {BUDGET_S:.0f}); a provider held to about a call a minute needs hours"
        ),
    )
    return p


async def _run(
    config: RouterConfig, factory: ChatRigFactory, texts: Sequence[BenchmarkText], use: Use,
    checkpoint: Checkpoint, wait_budget_s: float,
) -> list[TextRun]:  # fmt: skip
    runs: list[TextRun] = []

    def keep(run: TextRun) -> None:
        checkpoint.record(run)
        runs.append(run)

    async with factory(config, wait_budget_s) as rig:
        await evaluate_chatbot(rig, texts, use, _stderr, on_text=keep)
    return runs


def main(argv: Sequence[str], factory: ChatRigFactory = live_chat_rig) -> int:
    args = _parser().parse_args(argv)
    if args.wait_budget < 0:
        print("--wait-budget cannot be negative", file=sys.stderr)
        return 2
    claims = _resolve(args.claims)
    try:
        if args.split in ("test", "all") and not args.final:
            raise UsageError(
                "the test split is held out for the final report: pass --final (P4.7), never to tune"
            )
        catalog: Catalog = load_catalog(
            _resolve(args.catalog) if args.catalog else get_settings().catalog_dir
        )
        benchmark = load_benchmark(claims)
        check_indicators(benchmark, catalog)
        version = _eval_version(claims)
        if args.provider is None:  # one model for every text, never a fall-over mix (D033)
            args.provider = load_router_config().steps[STEP][0]
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
    header = Header(
        name=f"{args.name or f'{args.split}.chatbot'}.{args.provider}",
        benchmark=claims.name,
        split=args.split,
        provider=args.provider,
        use=args.use,
        versions=Stamp(
            app=app_version(), catalog=catalog.version, tolerances=tolerances.version, eval=version
        ),
    )
    out_dir = _resolve(args.out_dir)
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
        asyncio.run(_run(config, factory, todo, use, checkpoint, args.wait_budget)) if todo else []
    )

    by_id = done | {run.outcome.id: run for run in ran}
    runs = [by_id[t.id] for t in texts]
    metrics = summarize([run.outcome for run in runs], [call for run in runs for call in run.calls])
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
        kind="chatbot",
    )
    json_path, md_path = write_report(report, out_dir)
    checkpoint.remove()
    print(summary(report))
    print(f"wrote {json_path} and {md_path.name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
