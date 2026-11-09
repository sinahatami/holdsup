from datetime import UTC, datetime, timedelta
from uuid import uuid4

from holdsup.service.reports import NO_NOTE, format_reports
from holdsup.service.store import ReportKind, StoredReport

T0 = datetime(2026, 11, 9, 12, 30, tzinfo=UTC)


def report(kind: ReportKind, note: str, claim: int | None = 0, minutes: int = 0) -> StoredReport:
    return StoredReport(uuid4(), uuid4(), claim, kind, note, T0 + timedelta(minutes=minutes))


def test_no_reports_says_so() -> None:
    assert format_reports([], "http://localhost:3000") == "No reports yet.\n"


def test_each_report_has_its_kind_its_claim_a_link_and_the_note() -> None:
    wrong = report(ReportKind.WRONG_SERIES, "Wrong unemployment series.", claim=1)
    text = format_reports([wrong], "http://localhost:3000/")
    assert text.splitlines()[0] == "1 report (wrong statistic: 1)"
    assert "2026-11-09 12:30 UTC  wrong statistic  (claim 2)" in text
    # The link is to the check's receipt, however the origin was written.
    assert f"  http://localhost:3000/check/{wrong.check_id}" in text
    assert "  Wrong unemployment series." in text


def test_counts_by_kind_and_marks_a_missing_note_and_the_whole_check() -> None:
    reports = [
        report(ReportKind.OTHER, "", claim=None),
        report(ReportKind.WRONG_READING, "place wrong"),
        report(ReportKind.WRONG_READING, "period wrong"),
    ]
    text = format_reports(reports, "https://holdsup.example")
    assert text.splitlines()[0] == "3 reports (claim read wrongly: 2, other: 1)"
    assert "other  (whole check)" in text
    assert f"  {NO_NOTE}" in text


def test_a_note_cannot_pass_for_a_header_or_break_the_layout() -> None:
    text = format_reports(
        [report(ReportKind.OTHER, "line one\n2026-11-09 99:99 UTC  fake\n\n\nline  two")],
        "http://x",
    )
    assert "  line one 2026-11-09 99:99 UTC fake line two" in text
