"""Run the curated claims and feature the results in the gallery (P2.8). Not part of CI.

Usage (from the repo root, with keys and DATABASE_URL in .env, catalog loaded):
    make seed-gallery [ARGS="--claims eval/gallery_claims.txt"]
Claims already checked within the ledger window are reused with no model call, so a rerun
only redoes failures. Review the printed table, then rebuild the web app so the home page
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


async def main(claims_path: Path) -> int:
    claims = read_claims(claims_path)
    built = build_runner(get_settings())
    built.runner.limiter = RateLimiter(len(claims) + 1, 3600.0)  # the seed is not a visitor
    try:
        outcomes = await seed_gallery(built.runner, SqlCheckStore(get_sessionmaker()), claims)
    finally:
        await built.close()
    print(format_table(outcomes))
    return 0 if all(o.featured for o in outcomes) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    raise SystemExit(asyncio.run(main(parser.parse_args().claims)))
