"""The debugging, verification, review, skill-writing and diagnosis skills carry what their sources did."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill, section, sections

REQUIRED = {
    "systematic-debugging": (
        "## Root cause first", "## Reproduce it as a failing test", "## Trace backward to the source",
        "## Fix the cause, then the instruction behind it", "## After three failed fixes",
        "## Defense in depth", "## Waiting on conditions, not time",
    ),
    "verification": (
        "## Evidence before claims", "## What counts as evidence", "## Honest reporting", "## Red flags",
    ),
    "code-review": (
        "## Requesting a review", "## What the reviewer is given", "## Receiving a review",
        "## Verify before you agree", "## Pushing back", "## No performative agreement",
    ),
    "writing-skills": (
        "## A skill is tested like code", "## The description says when", "## Structure",
        "## Domain skills belong to the project", "## Testing with subagents",
    ),
    "session-diagnosis": (
        "## The problem statement", "## Finding the transcripts", "## Every finding cites evidence",
        "## From finding to fix",
    ),
}
REFERENCES = {
    "systematic-debugging": (
        "root-cause-tracing.md", "defense-in-depth.md", "condition-based-waiting.md",
    ),
    "code-review": ("reviewer-checklist.md",),
    "writing-skills": ("testing-skills-with-subagents.md", "best-practices.md"),
    "session-diagnosis": (
        "transcripts.md", "analyst-briefs.md", "case-and-report.md", "export-and-redaction.md",
    ),
}
ANALYST_DIMENSIONS = (
    "Skill timeline", "Plan adherence", "Repeated work", "Stumbles", "Quality evidence",
    "Request conflicts", "Cost and time",
)
REVIEW_SEVERITIES = ("Critical", "Important", "Minor")


def _reference(name: str, file_name: str) -> str:
    return (SKILLS_DIR / name / "references" / file_name).read_text(encoding="utf-8")


def _body(name: str) -> str:
    return parse_skill(name)[1]


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_skill_has_its_named_references(name):
    for file_name in REFERENCES[name]:
        assert (SKILLS_DIR / name / "references" / file_name).is_file(), f"{name}: {file_name}"


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_credits_name_the_skill(name):
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert f"| `{name}` |" in credits, f"CREDITS.md has no row for {name}"


def test_the_fix_includes_the_instruction_or_knowledge_behind_the_bug():
    text = section(_body("systematic-debugging"), "## Fix the cause, then the instruction behind it")
    assert "project knowledge" in text and "instruction" in text


def test_three_failed_fixes_go_back_to_the_manager():
    text = section(_body("systematic-debugging"), "## After three failed fixes")
    assert "manager" in text


def test_tracing_carries_the_polluter_search():
    assert "## Finding the test that pollutes" in sections(
        _reference("systematic-debugging", "root-cause-tracing.md"))


def test_waiting_carries_the_polling_helpers():
    text = _reference("systematic-debugging", "condition-based-waiting.md")
    for helper in ("waitFor(", "waitForEvent(", "waitForEventCount(", "waitForEventMatch("):
        assert helper in text, helper


def test_honest_reporting_keeps_red_as_red():
    assert "If something is red, it is red." in section(_body("verification"), "## Honest reporting")


def test_pushed_back_findings_are_decided_by_the_manager_or_the_user():
    text = section(_body("code-review"), "## Pushing back")
    assert "the manager decides" in text and "asks the user" in text


def test_the_reviewer_brief_keeps_its_severities_and_verdict():
    text = _reference("code-review", "reviewer-checklist.md")
    for severity in REVIEW_SEVERITIES:
        assert f"#### {severity}" in text, severity
    assert "Ready to merge?" in text and "## Declined to judge" in text


def test_writing_skills_states_the_framework_skill_contract():
    text = section(_body("writing-skills"), "## Structure")
    for heading in ("## When this applies", "## The core rule", "## Common mistakes"):
        assert heading in text, heading
    assert "-by-language.md" in text


def test_writing_skills_carries_wording_and_diagrams():
    headings = sections(_reference("writing-skills", "best-practices.md"))
    assert "## Wording that holds under pressure" in headings
    assert "## Diagrams" in headings


def test_subagent_testing_carries_the_worked_campaign():
    headings = sections(_reference("writing-skills", "testing-skills-with-subagents.md"))
    assert "## A worked campaign: testing an instruction file" in headings


def test_transcripts_are_found_under_the_projects_directory():
    text = section(_body("session-diagnosis"), "## Finding the transcripts")
    assert "~/.claude/projects/" in text


def test_every_analyst_dimension_has_a_brief():
    headings = sections(_reference("session-diagnosis", "analyst-briefs.md"))
    missing = [name for name in ANALYST_DIMENSIONS if f"## {name}" not in headings]
    assert not missing, f"analyst briefs lack {missing}"


def test_the_report_keeps_every_required_section():
    text = _reference("session-diagnosis", "case-and-report.md")
    for heading in ("## The case file", "## The report", "## 7. Instructions involved"):
        assert heading in text, heading
