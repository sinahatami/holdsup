"""Readers' reports of a wrong match, for the maintainer: the data behind `make reports`.

A report says a check matched the wrong statistic or read the claim wrongly. Each one is shown
with the link to the check it is about, so the receipt can be opened beside the reader's note.
"""

from collections import Counter
from collections.abc import Sequence

from holdsup.service.store import ReportKind, StoredReport

NO_NOTE = "(no note)"

_KIND_TEXT = {
    ReportKind.WRONG_SERIES: "wrong statistic",
    ReportKind.WRONG_READING: "claim read wrongly",
    ReportKind.OTHER: "other",
}


def format_reports(reports: Sequence[StoredReport], web_origin: str) -> str:
    """The reports, newest first, as plain text: a count by kind, then one block per report."""
    if not reports:
        return "No reports yet.\n"
    kinds = Counter(r.kind for r in reports)
    counts = ", ".join(f"{_KIND_TEXT[k]}: {n}" for k, n in kinds.most_common())
    lines = [f"{len(reports)} report{'s' if len(reports) != 1 else ''} ({counts})", ""]
    for r in reports:
        claim = "whole check" if r.claim_index is None else f"claim {r.claim_index + 1}"
        lines.append(f"{r.created_at:%Y-%m-%d %H:%M} UTC  {_KIND_TEXT[r.kind]}  ({claim})")
        lines.append(f"  {web_origin.rstrip('/')}/check/{r.check_id}")
        # A note is a stranger's text: one indented line each, so it cannot pass for a header.
        note = " ".join(r.note.split()) or NO_NOTE
        lines.append(f"  {note}")
        lines.append("")
    return "\n".join(lines)
