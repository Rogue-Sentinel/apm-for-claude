"""Render the session briefing shown at the start of an APM session."""
from __future__ import annotations

from typing import Any

from apm.ledger_workflow import parent_progress

IN_PROGRESS = ("designing", "planning", "awaiting-approval", "building", "integrating", "split")
MERGED_LIMIT = 5
EMPTY = "No work recorded yet."


def _order(key: str) -> tuple[int, str]:
    return (int(key), key) if key.isdigit() else (0, key)


def _issues(ledger: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return sorted(ledger["issues"].items(), key=lambda pair: _order(pair[0]))


def _label(key: str, issue: dict[str, Any]) -> str:
    title = issue.get("title")
    return f"#{key} {title}" if title else f"#{key}"


def _questions(ledger: dict[str, Any]) -> list[str]:
    lines = []
    for key, issue in _issues(ledger):
        for index, question in enumerate(issue.get("questions", [])):
            if not question.get("resolved"):
                lines.append(f"- #{key} question {index}: {question.get('text', '')}")
    return lines


def _with_status(ledger: dict[str, Any], statuses: tuple[str, ...]) -> list[tuple[str, dict]]:
    return [(key, i) for key, i in _issues(ledger) if i.get("status") in statuses]


def _simple(ledger: dict[str, Any], status: str) -> list[str]:
    return [f"- {_label(key, issue)}" for key, issue in _with_status(ledger, (status,))]


def _running(task: dict[str, Any]) -> str:
    worker = task.get("worker") or "unassigned"
    model = f" ({task['model']})" if task.get("model") else ""
    return f"  running {task.get('id', '?')}: {worker}{model}"


def _head(key: str, issue: dict[str, Any]) -> str:
    tasks = issue.get("tasks", [])
    if issue["status"] == "split":
        return f"- {_label(key, issue)} [split]"
    done = sum(1 for task in tasks if task.get("status") == "done")
    return f"- {_label(key, issue)} [{issue['status']}] {done}/{len(tasks)} tasks done"


def _review(issue: dict[str, Any]) -> list[str]:
    review = issue.get("review")
    if not review:
        return []
    if review.get("open"):
        return [f"  final review: {review['open']} open findings"]
    return [f"  final review: clean at {str(review.get('head', ''))[:7]}"]


def _notes(ledger: dict[str, Any], key: str, issue: dict[str, Any]) -> list[str]:
    lines = []
    if issue["status"] == "split" and key.isdigit():
        merged, total = parent_progress(ledger, int(key))
        lines.append(f"  split: {merged} of {total} sub-issues merged")
    if issue.get("concerns"):
        lines.append(f"  open concerns: {len(issue['concerns'])}")
    return lines + _review(issue)


def _progress_entry(ledger: dict[str, Any], key: str, issue: dict[str, Any]) -> list[str]:
    running = [_running(t) for t in issue.get("tasks", []) if t.get("status") == "running"]
    return [_head(key, issue)] + running + _notes(ledger, key, issue)


def _in_progress(ledger: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, issue in _with_status(ledger, IN_PROGRESS):
        lines.extend(_progress_entry(ledger, key, issue))
    return lines


def _last_event(ledger: dict[str, Any], key: str) -> str:
    stamps = [e.get("at", "") for e in ledger["log"] if str(e.get("issue")) == key]
    return max(stamps, default="")


def _merged(ledger: dict[str, Any]) -> list[str]:
    merged = _with_status(ledger, ("merged",))
    merged.sort(key=lambda pair: _last_event(ledger, pair[0]), reverse=True)
    return [f"- {_label(key, issue)}" for key, issue in merged[:MERGED_LIMIT]]


def _sections(ledger: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return [
        ("Waiting on you", _questions(ledger)),
        ("Blocked", _simple(ledger, "blocked")),
        ("In progress", _in_progress(ledger)),
        ("Queued", _simple(ledger, "queued")),
        ("Recently merged", _merged(ledger)),
    ]


def _body(ledger: dict[str, Any]) -> list[str]:
    parts = [[title, *lines] for title, lines in _sections(ledger) if lines]
    return ["\n".join(part) for part in parts] or [EMPTY]


def render_briefing(ledger: dict | None, error: str | None) -> str:
    parts = [f"State unavailable: {error}"] if error else []
    if ledger is not None:
        parts.extend(_body(ledger))
    return "\n\n".join(parts)
