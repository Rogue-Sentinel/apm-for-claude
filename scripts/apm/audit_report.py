"""Render an audit: the JSON that `apm init` consumes, and the report the user approves."""
from __future__ import annotations

from dataclasses import asdict

from apm.audit_scan import Audit
from apm.coverage import render_table
from apm.debt import snapshot
from apm.metrics import Report
from apm.standard_config import Limits

DECISIONS = "finish first / adopt / leave"
_MODE_TEXT = {
    "existing": "existing: the repository already has code in a language the framework measures.",
    "fresh": "fresh: no measurable code yet, so there is nothing to bring under the standard.",
}


def audit_json(audit: Audit, report: Report, limits: Limits) -> dict:
    return {
        "mode": audit.mode, "base": audit.base, "notes": list(audit.notes),
        "in_flight": [asdict(item) for item in audit.in_flight],
        "debt_issues": list(audit.debt_issues),
        "totals": snapshot(report, limits)["totals"],
    }


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _table(audit: Audit) -> list[str]:
    if not audit.in_flight:
        return ["Nothing in flight."]
    rows = [
        f"| {_cell(i.title)} | {i.kind} | {_cell(i.detail)} | {DECISIONS} |" for i in audit.in_flight
    ]
    return ["| Item | Kind | Detail | Decision |", "|---|---|---|---|", *rows]


def _totals(totals: dict) -> list[str]:
    return [f"- {name.replace('_', ' ')}: {count}" for name, count in totals.items()]


def _coverage(coverage: dict | None) -> list[str]:
    if coverage is None:
        return ["Not inventoried yet."]
    return ["##" + line if line.startswith("#") else line for line in render_table(coverage).splitlines()]


def render_audit(audit: Audit, report: Report, limits: Limits, coverage: dict | None) -> str:
    debt = ", ".join(f"#{number}" for number in audit.debt_issues) or "None."
    sections = [
        ["# Audit"],
        ["## Mode", "", _MODE_TEXT[audit.mode]],
        [f"## Measured at {audit.base or '(no commits yet)'}", "", *_totals(audit_json(audit, report, limits)["totals"])],
        ["## In-flight work", "", *_table(audit)],
        ["## Debt issues", "", debt],
        ["## Capability coverage", "", *_coverage(coverage)],
        ["## Notes", "", *(f"- {note}" for note in audit.notes or ("None.",))],
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"
