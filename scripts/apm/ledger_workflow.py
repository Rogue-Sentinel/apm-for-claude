"""Decisions, concerns, sub-issues and the final review: pure functions over the ledger dict."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from apm.ledger import LedgerError, _issue

NOTE_FIELDS = {"decision": "decisions", "concern": "concerns"}


def _stamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).isoformat()


def add_note(
    ledger: dict[str, Any], number: int, kind: Literal["decision", "concern"], text: str, now: datetime
) -> bool:
    """Append a decision or concern; False, adding nothing, when the same text is already recorded."""
    notes = _issue(ledger, number).setdefault(NOTE_FIELDS[kind], [])
    if any(note.get("text") == text for note in notes):
        return False
    notes.append({"text": text, "at": _stamp(now)})
    return True


def set_parent(ledger: dict[str, Any], number: int, parent: int) -> None:
    issue = _issue(ledger, number)
    _issue(ledger, parent)
    if parent == number:
        raise LedgerError(f"issue {number} cannot be its own parent")
    issue["parent"] = parent


def children(ledger: dict[str, Any], number: int) -> list[int]:
    found = [int(key) for key, issue in ledger["issues"].items() if issue.get("parent") == number]
    return sorted(found)


def parent_progress(ledger: dict[str, Any], number: int) -> tuple[int, int]:
    """(merged, total) over the issue's sub-issues."""
    kids = children(ledger, number)
    merged = sum(1 for kid in kids if ledger["issues"][str(kid)].get("status") == "merged")
    return merged, len(kids)


def record_review(
    ledger: dict[str, Any], number: int, *, head: str, open_findings: int,
    criteria_met: bool, evidence: str, now: datetime,
) -> dict[str, Any]:
    if open_findings < 0:
        raise LedgerError("open findings cannot be negative")
    review = {
        "head": head, "open": open_findings, "criteria_met": criteria_met,
        "evidence": evidence, "at": _stamp(now),
    }
    _issue(ledger, number)["review"] = review
    return review
