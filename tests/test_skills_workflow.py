"""The workflow skills carry every heading and phrase the agents and the CLI anchor to."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill

REQUIRED = {
    "initializing": (
        "## Existing or fresh", "## Dispatching the auditors", "## The audit report",
        "## The capability coverage table", "## In-flight work", "## Overwrite versus keep",
        "## Approval, then apply", "## Debt issues", "## A fresh project",
    ),
    "running-an-issue": (
        "## Filing the issue", "## The size check", "## Splitting into sub-issues", "## Planning",
        "## The plan summary", "## Building", "## Pacing", "## A bug a worker finds",
        "## Integrating", "## Reporting", "## Lanes and the queue", "## Progress updates",
    ),
    "merge-gate": (
        "## Running the gate", "## Criterion 1: everything passes", "## Criterion 2: no debt got worse",
        "## Criterion 3: the final review is clean", "## Criterion 4: the structure the plan promised",
        "## When a criterion cannot be met",
    ),
}
REFERENCES = {
    "initializing": ("audit-report-template.md", "auditor-brief.md"),
    "running-an-issue": ("issue-body-template.md", "plan-summary-template.md"),
}
NAMED_IN_BODY = {
    "initializing": ("`<CLI> init", "`<CLI> github file", "never removed"),
    "running-an-issue": (
        "one plain line", "exactly once", "`<CLI> gate", "`<CLI> github file", "`<CLI> github close",
        "workflow.safety_critical",
    ),
    "merge-gate": ("`<CLI> gate", "`<CLI> review", "all four criteria"),
}


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_skill_has_its_named_references(name):
    for file_name in REFERENCES[name]:
        assert (SKILLS_DIR / name / "references" / file_name).is_file(), f"{name}: {file_name}"


@pytest.mark.parametrize("name", sorted(NAMED_IN_BODY))
def test_skill_names_the_phrases_it_owns(name):
    _, body = parse_skill(name)
    missing = [term for term in NAMED_IN_BODY[name] if term not in body]
    assert not missing, f"{name} does not name {missing}"
