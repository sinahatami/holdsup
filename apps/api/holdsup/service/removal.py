"""Removing a check on request: the data behind `make delete-check`.

A reader asks for a check to be removed when its text shows personal information (the report
kind `remove`; the privacy page says how). Removing it deletes every stored check of the same
text, so no cached copy, update or identical submission keeps the text on the site.
"""

from collections.abc import Callable
from uuid import UUID

from holdsup.service.store import CheckStore, StoredCheck

PREVIEW_CHARS = 300


def describe(check: StoredCheck) -> str:
    """The check as the maintainer sees it before deciding: when, and the start of its text on
    one indented line (a stranger's text, so it cannot pass for the script's own output)."""
    text = " ".join(check.text.split())
    if len(text) > PREVIEW_CHARS:
        text = text[:PREVIEW_CHARS] + "…"
    return f"Check {check.id}, {check.created_at:%Y-%m-%d %H:%M} UTC\n  {text}\n"


async def remove_check(store: CheckStore, check_id: UUID, confirm: Callable[[str], bool]) -> str:
    """Show the check, ask `confirm`, then delete it and its copies; what happened, as text."""
    check = await store.get(check_id)
    if check is None:
        return f"No check {check_id}.\n"
    if not confirm(describe(check)):
        return "Nothing deleted.\n"
    gone = await store.remove(check_id)
    lines = [f"Deleted {len(gone)} check{'s' if len(gone) != 1 else ''} of this text:"]
    lines += [f"  {i}" for i in gone]
    lines.append(
        "Their pages are gone now. A featured one leaves the cached gallery within 15 minutes."
    )
    return "\n".join(lines) + "\n"
