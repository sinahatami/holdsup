"""List the topics most often asked about that HoldsUp could not check.

Usage (from the repo root, with DATABASE_URL in .env):
    make missing-report [ARGS="--top 30"]
Reads the stored results of finished checks; nothing is written. Use it to decide which
statistic to add to packages/catalog next.
"""

import argparse
import asyncio

from holdsup.db.session import get_sessionmaker
from holdsup.service.missing import format_report, summarize
from holdsup.service.store import SqlCheckStore


async def main(top: int) -> int:
    results = await SqlCheckStore(get_sessionmaker()).finished_results()
    print(format_report(summarize(results, limit=top)), end="")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=20, help="how many topics to list (default 20)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.top)))
