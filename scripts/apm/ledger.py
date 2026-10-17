"""The manager's ledger: pure functions over a plain dict, plus atomic load and save."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ISSUE_STATUSES = (
    "designing", "planning", "awaiting-approval", "building",
    "integrating", "merged", "blocked", "queued",
)
TASK_STATUSES = ("pending", "running", "done", "failed", "blocked")
ALLOWLIST_STATUSES = ("building", "integrating")


class LedgerError(Exception):
    """The ledger is unreadable or an update is invalid."""


def empty_ledger() -> dict[str, Any]:
    return {"issues": {}, "log": []}


def _normalize_issue(key: str, issue: Any) -> None:
    if not isinstance(issue, dict):
        raise LedgerError(f"issue {key} is not an object")
    for name in ("tasks", "allowlist", "questions"):
        if not isinstance(issue.setdefault(name, []), list):
            raise LedgerError(f"issue {key} field {name!r} is not a list")


def _validate(ledger: Any, path: Path) -> dict[str, Any]:
    if not isinstance(ledger, dict) or not isinstance(ledger.get("issues"), dict):
        raise LedgerError(f"ledger {path} has no 'issues' mapping")
    if not isinstance(ledger.setdefault("log", []), list):
        raise LedgerError(f"ledger {path} 'log' is not a list")
    for key, issue in ledger["issues"].items():
        _normalize_issue(key, issue)
    return ledger


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise LedgerError(f"cannot read ledger {path}: {err}") from err
    return _validate(raw, path)


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    text = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temp, path)


def _check_status(fields: dict[str, Any], allowed: tuple[str, ...], kind: str) -> None:
    if "status" in fields and fields["status"] not in allowed:
        raise LedgerError(f"unknown {kind} status: {fields['status']!r}")


def _issue(ledger: dict[str, Any], number: int) -> dict[str, Any]:
    issue = ledger["issues"].get(str(number))
    if issue is None:
        raise LedgerError(f"unknown issue: {number}")
    return issue


def upsert_issue(ledger: dict[str, Any], number: int, **fields: Any) -> dict[str, Any]:
    _check_status(fields, ISSUE_STATUSES, "issue")
    issue = ledger["issues"].setdefault(
        str(number), {"status": "queued", "tasks": [], "allowlist": [], "questions": []}
    )
    issue.update(fields)
    return issue


def update_task(
    ledger: dict[str, Any], number: int, task_id: str, **fields: Any
) -> dict[str, Any]:
    _check_status(fields, TASK_STATUSES, "task")
    tasks = _issue(ledger, number)["tasks"]
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        task = {"id": task_id, "status": "pending", "attempts": 0}
        tasks.append(task)
    if fields.get("status") == "running" and task["status"] != "running":
        task["attempts"] += 1
    task.update(fields)
    return task


def add_allow(
    ledger: dict[str, Any], number: int, *, path: str | None, command: str | None, reason: str
) -> None:
    if (path is None) == (command is None):
        raise LedgerError("an allowlist entry needs exactly one of path or command")
    entry = {"path": path, "command": command, "reason": reason}
    _issue(ledger, number)["allowlist"].append(entry)


def add_question(ledger: dict[str, Any], number: int, text: str, blocks: list[str]) -> int:
    questions = _issue(ledger, number)["questions"]
    questions.append({"text": text, "blocks": blocks, "answer": None, "resolved": False})
    return len(questions) - 1


def resolve_question(ledger: dict[str, Any], number: int, index: int, answer: str) -> None:
    questions = _issue(ledger, number)["questions"]
    if not 0 <= index < len(questions):
        raise LedgerError(f"issue {number} has no question {index}")
    questions[index].update(answer=answer, resolved=True)


def append_log(ledger: dict[str, Any], number: int | None, event: str, now: datetime) -> None:
    stamp = now.astimezone(timezone.utc).isoformat()
    ledger["log"].append({"at": stamp, "issue": number, "event": event})


def active_allowlist(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    live = (i for i in ledger["issues"].values() if i.get("status") in ALLOWLIST_STATUSES)
    return [entry for issue in live for entry in issue["allowlist"]]
