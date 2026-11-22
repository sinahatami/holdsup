"""Delete a check whose text shows personal information, with every stored check of that text.

Usage (from the repo root, with DATABASE_URL in .env):
    make delete-check ID=<check id> [ARGS=--yes]
Shows the check, then deletes it after you type "delete" (--yes skips the question), and asks
the site at WEB_ORIGIN to drop the deleted checks' cached pages and its cached gallery. For the
live site, run it with the live database and WEB_ORIGIN=https://holdsup.vercel.app. Removal
requests from readers are listed by `make reports`.
"""

import argparse
import asyncio
from uuid import UUID

import httpx

from holdsup.config import get_settings
from holdsup.db.session import get_sessionmaker
from holdsup.service.removal import remove_check
from holdsup.service.site_pages import SitePages
from holdsup.service.store import SqlCheckStore


def show(description: str) -> bool:
    print(description)
    return True


def ask(description: str) -> bool:
    print(description)
    return input('Type "delete" to delete it and every stored check of the same text: ') == "delete"


async def main(check_id: UUID, yes: bool) -> int:
    store = SqlCheckStore(get_sessionmaker())
    async with httpx.AsyncClient() as http:
        pages = SitePages(http, get_settings().web_origin)
        message = await remove_check(store, check_id, show if yes else ask, pages)
    print(message, end="")
    return 0 if message.startswith("Deleted") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check_id", type=UUID, help="the check's id, the last part of its link")
    parser.add_argument("--yes", action="store_true", help="delete without asking")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.check_id, args.yes)))
