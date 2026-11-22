"""Telling the site that a check changed, so it drops the page it cached for it.

The site (apps/web) keeps a finished check's page whole in its cache, so a reader gets the
receipt in the first paint. What changes a check after that happens here: the runner finishes
or fails it, the removal script deletes it, the claim watch points it at an update. Each then
asks the site to drop the check's cached reads and pages (`POST /api/checks/<id>/refresh`;
`?gallery=1` also drops the cached featured checks). The site needs no secret for it: a
refresh only makes the next visit render the way an uncached one does.

A refresh that fails is logged and reported, never raised: the site's cache lets a settled
check lag a day at most (the web's readCheck), and the removal script prints the command
that retries it.
"""

from dataclasses import dataclass
from uuid import UUID

import httpx
import structlog

REFRESH_TIMEOUT_S = 10.0

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SitePages:
    http: httpx.AsyncClient
    origin: str  # the site's address, WEB_ORIGIN

    def refresh_url(self, check_id: UUID, *, gallery: bool = False) -> str:
        query = "?gallery=1" if gallery else ""
        return f"{self.origin.rstrip('/')}/api/checks/{check_id}/refresh{query}"

    async def refresh(self, check_id: UUID, *, gallery: bool = False) -> bool:
        """Ask the site to drop the check's cached pages; True when it said it did."""
        url = self.refresh_url(check_id, gallery=gallery)
        try:
            response = await self.http.post(url, timeout=REFRESH_TIMEOUT_S)
        except httpx.HTTPError as exc:
            log.warning("site_refresh_failed", check_id=str(check_id), error=type(exc).__name__)
            return False
        if response.status_code != httpx.codes.NO_CONTENT:
            log.warning("site_refresh_refused", check_id=str(check_id), status=response.status_code)
            return False
        return True
