"""Run the curated claims and feature the results in the gallery (P2.8). Not part of CI.

Usage (from the repo root, with keys and DATABASE_URL in .env, catalog loaded):
    make seed-gallery [ARGS="--claims eval/gallery_claims.txt --force"]
Claims already checked within the ledger window (with the current catalog and tolerance
versions) are reused with no model call, so a rerun only redoes failures. --force checks
every claim again, e.g. after a pipeline fix that changed no version. Review the printed table, then rebuild the web app so the home page
pre-renders the new gallery.
"""

import argparse
import asyncio
from pathlib import Path

from holdsup.config import REPO_ROOT, get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.seed import format_table, read_claims, seed_gallery
from holdsup.service.store import SqlCheckStore
from holdsup.service.wiring import build_runner

DEFAULT_CLAIMS = REPO_ROOT / "eval" / "gallery_claims.txt"


async def main(claims_path: Path, force: bool = False) -> int:
    claims = read_claims(claims_path)
    built = build_runner(get_settings())
    built.runner.limiter = RateLimiter(len(claims) + 1, 3600.0)  # the seed is not a visitor
    try:
        outcomes = await seed_gallery(
            built.runner, SqlCheckStore(get_sessionmaker()), claims, force=force
        )
    finally:
        await built.close()
    print(format_table(outcomes))
    return 0 if all(o.featured for o in outcomes) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument(
        "--force", action="store_true", help="check every claim again, ignoring the ledger"
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.claims, args.force)))
