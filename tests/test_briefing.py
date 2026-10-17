from apm.briefing import render_briefing
from apm.ledger import (
    add_question, append_log, empty_ledger, update_task, upsert_issue,
)
from datetime import datetime, timezone

HEADINGS = ["Waiting on you", "Blocked", "In progress", "Queued", "Recently merged"]


def _at(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


def _full_ledger() -> dict:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, title="Login page", status="building")
    for task_id, status in (("t1", "done"), ("t2", "done"), ("t3", "running")):
        update_task(ledger, 1, task_id, status=status)
    update_task(ledger, 1, "t3", worker="w7", model="sonnet")
    upsert_issue(ledger, 2, title="Export CSV", status="blocked")
    upsert_issue(ledger, 3, title="Dark mode", status="queued")
    upsert_issue(ledger, 4, title="Fix typo", status="merged")
    add_question(ledger, 2, "Which delimiter?", [])
    append_log(ledger, 4, "issue 4 status merged", _at(2))
    return ledger


def _headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line in HEADINGS]


def test_sections_appear_in_order() -> None:
    assert _headings(render_briefing(_full_ledger(), None)) == HEADINGS


def test_key_lines() -> None:
    text = render_briefing(_full_ledger(), None)
    assert "#2 question 0: Which delimiter?" in text
    assert "#2 Export CSV" in text
    assert "#1 Login page [building] 2/3 tasks done" in text
    assert "running t3: w7 (sonnet)" in text
    assert "#3 Dark mode" in text
    assert "#4 Fix typo" in text


def test_empty_sections_are_omitted() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 3, title="Dark mode", status="queued")
    assert _headings(render_briefing(ledger, None)) == ["Queued"]


def test_resolved_question_is_not_listed() -> None:
    ledger = _full_ledger()
    ledger["issues"]["2"]["questions"][0]["resolved"] = True
    assert "Waiting on you" not in render_briefing(ledger, None)


def test_empty_ledger() -> None:
    assert render_briefing(empty_ledger(), None) == "No work recorded yet."


def test_error_leads_the_output() -> None:
    assert render_briefing(None, "bad json") == "State unavailable: bad json"
    text = render_briefing(_full_ledger(), "stale")
    assert text.startswith("State unavailable: stale")


def test_recently_merged_newest_log_first_and_capped_at_five() -> None:
    ledger = empty_ledger()
    for number in range(1, 8):
        upsert_issue(ledger, number, title=f"Issue {number}", status="merged")
    for number, day in ((1, 9), (2, 8), (3, 7), (4, 6), (5, 5), (6, 4), (7, 3)):
        append_log(ledger, number, f"issue {number} status merged", _at(day))
    append_log(ledger, 7, "issue 7 note", _at(1))
    lines = render_briefing(ledger, None).splitlines()[1:]
    assert lines == [f"- #{n} Issue {n}" for n in (1, 2, 3, 4, 5)]


def test_merged_ordered_by_latest_log_entry_not_issue_number() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, title="Old", status="merged")
    upsert_issue(ledger, 2, title="New", status="merged")
    append_log(ledger, 1, "issue 1 status merged", _at(5))
    append_log(ledger, 2, "issue 2 status merged", _at(3))
    append_log(ledger, 2, "issue 2 status merged", _at(9))
    assert render_briefing(ledger, None).splitlines()[1:] == ["- #2 New", "- #1 Old"]


def test_untitled_issue_and_running_task_without_worker() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 5, status="planning")
    update_task(ledger, 5, "t1", status="running")
    text = render_briefing(ledger, None)
    assert "- #5 [planning] 0/1 tasks done" in text and "running t1: unassigned" in text
