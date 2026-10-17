import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from apm.ledger import (
    LedgerError,
    active_allowlist,
    add_allow,
    add_question,
    append_log,
    empty_ledger,
    load_ledger,
    resolve_question,
    save_ledger,
    update_task,
    upsert_issue,
)


def test_missing_ledger_is_empty(tmp_path: Path) -> None:
    assert load_ledger(tmp_path / "ledger.json") == empty_ledger()


def test_corrupt_ledger_raises(tmp_path: Path) -> None:
    bad = tmp_path / "ledger.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(LedgerError):
        load_ledger(bad)
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(LedgerError):
        load_ledger(bad)


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 7, status="planning", title="Seven")
    path = tmp_path / "sub" / "ledger.json"
    save_ledger(path, ledger)
    assert load_ledger(path) == ledger
    assert path.read_text(encoding="utf-8").startswith('{\n  "issues"')


def test_upsert_issue_defaults_and_merge() -> None:
    ledger = empty_ledger()
    issue = upsert_issue(ledger, 3, status="designing")
    assert issue["tasks"] == [] and issue["allowlist"] == [] and issue["questions"] == []
    upsert_issue(ledger, 3, status="building")
    assert ledger["issues"]["3"]["status"] == "building"


def test_upsert_issue_rejects_unknown_status() -> None:
    with pytest.raises(LedgerError):
        upsert_issue(empty_ledger(), 1, status="nonsense")


def test_running_increments_attempts() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, status="building")
    update_task(ledger, 1, "t1", status="running")
    update_task(ledger, 1, "t1", status="failed")
    task = update_task(ledger, 1, "t1", status="running")
    assert task["attempts"] == 2
    assert len(ledger["issues"]["1"]["tasks"]) == 1


def test_update_task_rejects_bad_status() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, status="building")
    with pytest.raises(LedgerError):
        update_task(ledger, 1, "t1", status="bogus")


def test_update_task_unknown_issue_raises() -> None:
    with pytest.raises(LedgerError):
        update_task(empty_ledger(), 9, "t1", status="running")


def test_add_allow_requires_exactly_one_kind() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, status="building")
    with pytest.raises(LedgerError):
        add_allow(ledger, 1, path=None, command=None, reason="r")
    with pytest.raises(LedgerError):
        add_allow(ledger, 1, path="a", command="b", reason="r")
    add_allow(ledger, 1, path="a", command=None, reason="r")
    assert len(ledger["issues"]["1"]["allowlist"]) == 1


def test_active_allowlist_only_from_building_or_integrating() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, status="building")
    upsert_issue(ledger, 2, status="awaiting-approval")
    add_allow(ledger, 1, path="src/x.py", command=None, reason="needed")
    add_allow(ledger, 2, path=None, command="make", reason="later")
    entries = active_allowlist(ledger)
    assert [e["path"] for e in entries] == ["src/x.py"]


def test_question_add_and_resolve() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 1, status="blocked")
    index = add_question(ledger, 1, "Which db?", ["t1"])
    assert index == 0
    resolve_question(ledger, 1, index, "postgres")
    question = ledger["issues"]["1"]["questions"][0]
    assert question["answer"] == "postgres" and question["resolved"] is True


def test_append_log_records_utc_iso() -> None:
    ledger = empty_ledger()
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    append_log(ledger, 4, "started", now)
    append_log(ledger, None, "global", now)
    assert ledger["log"][0] == {"at": "2026-01-02T03:04:05+00:00", "issue": 4, "event": "started"}
    assert ledger["log"][1]["issue"] is None


def _write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "data",
    [
        {"issues": {"1": 5}},
        {"issues": {"1": {"status": "building", "allowlist": "x"}}},
        {"issues": {"1": {"status": "building", "tasks": {}}}},
        {"issues": {"1": {"status": "building", "questions": None}}},
        {"issues": {}, "log": {}},
        {"issues": []},
        [],
    ],
)
def test_malformed_ledger_shapes_raise(tmp_path: Path, data: object) -> None:
    with pytest.raises(LedgerError):
        load_ledger(_write(tmp_path / "ledger.json", data))


def test_missing_issue_lists_are_defaulted(tmp_path: Path) -> None:
    path = _write(tmp_path / "ledger.json", {"issues": {"1": {"status": "building"}}})
    ledger = load_ledger(path)
    issue = ledger["issues"]["1"]
    assert issue["tasks"] == [] and issue["questions"] == [] and issue["allowlist"] == []
    assert active_allowlist(ledger) == []


def test_new_issue_without_status_is_queued() -> None:
    ledger = empty_ledger()
    assert upsert_issue(ledger, 4, title="No status")["status"] == "queued"


def test_existing_issue_status_kept_when_not_passed() -> None:
    ledger = empty_ledger()
    upsert_issue(ledger, 4, status="building")
    upsert_issue(ledger, 4, title="Renamed")
    assert ledger["issues"]["4"]["status"] == "building"
