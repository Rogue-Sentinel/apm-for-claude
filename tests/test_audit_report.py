import json
import re

from apm.audit_report import audit_json, render_audit
from apm.audit_scan import Audit, InFlight
from apm.metrics import Report
from apm.standard_config import Limits

ITEM = InFlight("branch:feat/x", "branch", "feat/x", "2 ahead, also on origin")
AUDIT = Audit("existing", "origin/main", ("open issues not read: gh is not installed",), (ITEM,), (5, 9))
INVENTORY = {
    "sources": [{"id": "s", "title": "Source", "origin": "somewhere"}],
    "items": [{"id": "i", "source": "s", "what": "an old rule", "covered_by": [{"file": "skills/x/SKILL.md"}]}],
}


def test_json_has_exactly_the_consumed_keys() -> None:
    data = audit_json(AUDIT, Report(()), Limits())

    assert data == {
        "mode": "existing", "base": "origin/main",
        "notes": ["open issues not read: gh is not installed"],
        "in_flight": [{"id": "branch:feat/x", "kind": "branch", "title": "feat/x", "detail": "2 ahead, also on origin"}],
        "debt_issues": [5, 9],
        "totals": data["totals"],
    }
    assert data["totals"]["long_functions"] == 0
    json.dumps(data)


def test_report_has_decision_column_and_coverage() -> None:
    text = render_audit(AUDIT, Report(()), Limits(), INVENTORY)

    headings = [line for line in text.splitlines() if re.match(r"#{1,3} ", line)]
    assert headings == [
        "# Audit", "## Mode", "## Measured at origin/main", "## In-flight work", "## Debt issues",
        "## Capability coverage", "### Coverage of the old standard", "## Notes",
    ]
    assert "| Item | Kind | Detail | Decision |" in text
    assert "| feat/x | branch | 2 ahead, also on origin | finish first / adopt / leave |" in text
    assert "#5, #9" in text
    assert "an old rule" in text
    assert "- open issues not read: gh is not installed" in text


def test_empty_audit_says_so() -> None:
    empty = Audit("fresh", "", ("no commits yet",), (), ())

    text = render_audit(empty, Report(()), Limits(), None)

    assert "Not inventoried yet." in text
    assert "Nothing in flight." in text
    assert "## Measured at" in text
