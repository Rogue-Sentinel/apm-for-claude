"""The agents point at the workflows and the lean pacing."""
import pytest
from test_agents import AGENTS, SKILLS_DIR, _section, parse


def test_manager_paces_lean_and_talks_plainly():
    _, body = parse(AGENTS / "manager.md")
    assert "exactly once" in _section(body, "## Verifying work")
    assert "`<CLI> gate`" in _section(body, "## Verifying work")
    talking = _section(body, "## Talking to the user")
    assert "one plain line" in talking and "rough time left" in talking
    assert "whole-branch review" in body and "workflow.safety_critical" in body
    assert "workflow.merge_style" in body and "plan approval" in body


def test_manager_lets_workers_read_the_audit_everywhere_it_lists_their_commands():
    _, body = parse(AGENTS / "manager.md")
    assert "`<CLI> metrics`, `<CLI> debt check`, `<CLI> coverage` and `<CLI> audit`" in body
    assert "`metrics`, `debt check`, `coverage` and `audit`" in body


def test_auditor_reports_the_audit_and_measures_at_the_base():
    _, body = parse(AGENTS / "auditor.md")
    assert "`<CLI> audit --json`" in body and "`<CLI> metrics --json --ref <base>`" in body
    for needle in ("draft profile", "lanes", "coverage.json", "never remove anything"):
        assert needle in body, needle


def test_debugger_follows_the_bug_flow_and_fixes_only_named_instructions():
    _, body = parse(AGENTS / "debugger.md")
    assert "`apm:running-an-issue`" in body
    assert "profile fact" in body and "for the manager to record" in body


def test_reviewer_defaults_to_the_whole_branch_and_counts_findings():
    _, body = parse(AGENTS / "reviewer.md")
    assert "whole-branch" in body
    assert "open findings" in body and "`<CLI> review`" in body
    assert "met or unmet" in body


def test_planner_names_targeted_commands_and_ends_on_the_gate():
    _, body = parse(AGENTS / "planner.md")
    assert "targeted test command" in body
    assert "`<CLI> gate`" in body


def test_implementer_runs_targeted_tests_and_the_full_suite_only_when_told():
    _, body = parse(AGENTS / "implementer.md")
    assert "targeted tests" in body
    assert "full suite only if your brief says so" in body


@pytest.mark.parametrize("path", (
    "test-first/references/test-first-checklist.md", "code-review/references/reviewer-checklist.md",
))
def test_reference_checklists_use_lean_pacing(path):
    text = (SKILLS_DIR / path).read_text(encoding="utf-8")
    assert "whole suite still passes" not in text and "Does the whole suite pass" not in text
    assert "`<CLI> gate`" in text
