"""The claim watch (S1): compare the figures behind stored checks with the sources, and publish
an updated check where a source revised them. Code only: no model, no provider key.

Usage (from the repo root, DATABASE_URL in .env or the environment):
    make watch                      # compare and publish
    make watch ARGS="--dry-run"     # compare and print, store nothing
    make watch ARGS="--backfill"    # give checks from before plans were stored a plan: asks
                                    # the plan model once per claim (keys needed), and keeps a
                                    # plan only when it gives the figures the check showed
GitHub Actions runs `make watch` daily (.github/workflows/watch.yml).
"""

import argparse
import asyncio
from datetime import UTC, datetime

from holdsup.config import get_settings
from holdsup.pipeline.run import Pipeline
from holdsup.service.watch import MAX_PER_RUN, WATCH_DAYS, backfill, format_table, watch
from holdsup.service.wiring import build_watch


async def main(*, plan: bool, limit: int, days: int, save: bool) -> int:
    parts = build_watch(get_settings(), planner=plan)
    now = datetime.now(UTC)
    try:
        if plan:
            assert isinstance(parts.steps, Pipeline)  # noqa: S101 (build_watch(planner=True))
            rows = await backfill(
                parts.store, parts.steps, now=now, limit=limit, days=days, save=save
            )
        else:
            rows = await watch(parts.store, parts.steps, now=now, limit=limit, days=days, save=save)
    finally:
        await parts.close()
    print(format_table(rows))
    if not save:
        print("Dry run: nothing was stored.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--backfill", action="store_true", help="plan checks made before S1")
    parser.add_argument("--dry-run", action="store_true", help="print what would change only")
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN, help="checks per run")
    parser.add_argument("--days", type=int, default=WATCH_DAYS, help="watch checks this young")
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            main(plan=args.backfill, limit=args.limit, days=args.days, save=not args.dry_run)
        )
    )
