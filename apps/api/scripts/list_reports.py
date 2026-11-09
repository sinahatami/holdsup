"""List the newest reports of a wrong match, with a link to each check.

Usage (from the repo root, with DATABASE_URL in .env):
    make reports [ARGS="--top 50"]
Reads the stored reports; nothing is written.
"""

import argparse
import asyncio

from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.service.reports import format_reports
from holdsup.service.store import SqlCheckStore


async def main(top: int) -> int:
    reports = await SqlCheckStore(get_sessionmaker()).reports(top)
    print(format_reports(reports, get_settings().web_origin), end="")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=20, help="how many reports to list (default 20)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.top)))
