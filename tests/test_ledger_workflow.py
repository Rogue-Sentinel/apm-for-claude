import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from apm.ledger import LedgerError, empty_ledger, load_ledger, upsert_issue
from apm.ledger_workflow import add_note, children, parent_progress, record_review, set_parent

NOW = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)


def _ledger() -> dict:
    ledger = empty_ledger()
    for number in (1, 2, 3):
        upsert_issue(ledger, number)
    return ledger


def test_add_note_and_no_duplicate() -> None:
    ledger = _ledger()

    first = add_note(ledger, 1, "decision", "use sqlite", NOW)
    again = add_note(ledger, 1, "decision", "use sqlite", NOW)
    add_note(ledger, 1, "concern", "slow on windows", NOW)

    assert (first, again) == (True, False)
    assert ledger["issues"]["1"]["decisions"] == [{"text": "use sqlite", "at": "2026-03-04T05:06:07+00:00"}]
    assert [c["text"] for c in ledger["issues"]["1"]["concerns"]] == ["slow on windows"]


def test_add_note_to_unknown_issue_raises() -> None:
    with pytest.raises(LedgerError, match="unknown issue: 9"):
        add_note(_ledger(), 9, "concern", "x", NOW)


def test_set_parent_rejects_self_and_unknown() -> None:
    ledger = _ledger()

    with pytest.raises(LedgerError, match="its own parent"):
        set_parent(ledger, 1, 1)
    with pytest.raises(LedgerError, match="unknown issue: 9"):
        set_parent(ledger, 1, 9)
    assert "parent" not in ledger["issues"]["1"]


def test_set_parent_records_the_parent() -> None:
    ledger = _ledger()

    set_parent(ledger, 2, 1)

    assert ledger["issues"]["2"]["parent"] == 1


def test_parent_progress() -> None:
    ledger = _ledger()
    upsert_issue(ledger, 4, status="merged")
    set_parent(ledger, 2, 1)
    set_parent(ledger, 3, 1)
    set_parent(ledger, 4, 1)
    upsert_issue(ledger, 3, status="merged")

    assert children(ledger, 1) == [2, 3, 4]
    assert parent_progress(ledger, 1) == (2, 3)
    assert parent_progress(ledger, 2) == (0, 0)


def test_record_review_stores_the_review() -> None:
    ledger = _ledger()

    review = record_review(
        ledger, 1, head="abc1234def", open_findings=2, criteria_met=True, evidence="gate output", now=NOW
    )

    assert ledger["issues"]["1"]["review"] == review
    assert review == {
        "head": "abc1234def", "open": 2, "criteria_met": True,
        "evidence": "gate output", "at": "2026-03-04T05:06:07+00:00",
    }


def test_record_review_rejects_negative() -> None:
    with pytest.raises(LedgerError, match="negative"):
        record_review(_ledger(), 1, head="a", open_findings=-1, criteria_met=False, evidence="e", now=NOW)


def test_old_ledger_without_new_fields_loads(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps({"issues": {"1": {"status": "building", "tasks": []}}}), encoding="utf-8")

    issue = load_ledger(path)["issues"]["1"]

    assert (issue["decisions"], issue["concerns"]) == ([], [])


def test_split_is_an_issue_status() -> None:
    ledger = _ledger()

    assert upsert_issue(ledger, 1, status="split")["status"] == "split"
