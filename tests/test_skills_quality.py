"""The debugging, verification, review, skill-writing and diagnosis skills carry what their sources did."""
import re

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
    "Request conflicts", "Cost and time", "Roles and safety",
)
REVIEW_TIERS = ("#### Must fix", "#### Suggestions")
OLD_TIERS = ("Critical", "Important", "Minor")
WORKSPACE = "apm-diagnosis/<session-id>/"
WORKSPACE_FILES = ("transcripts.md", "case-and-report.md", "export-and-redaction.md")
CLI_VERBS = (
    "metrics", "debt", "brief", "coverage", "issue", "task", "question", "resolve", "approve",
    "allow", "setup",
)
BARE_CLI = re.compile(r"(?<![\w:/<>-])apm (?:" + "|".join(CLI_VERBS) + r")\b")
WRITING_RED_FLAGS = (
    "before the test", "by hand", "tests after", "spirit", "different because",
    "delete it and start over",
)


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
    assert "one tier stronger" in text and "same model" in text


def test_the_fix_removes_the_cause_not_just_the_symptom():
    text = section(_body("systematic-debugging"), "## Reproduce it as a failing test")
    assert "simplest code" in text and "removes the cause" in text


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


def _skill_texts(name: str) -> list[tuple[str, str]]:
    return [(str(path.relative_to(SKILLS_DIR)), path.read_text(encoding="utf-8"))
            for path in sorted((SKILLS_DIR / name).rglob("*.md"))]


def test_the_reviewer_brief_has_two_tiers_and_a_verdict():
    text = _reference("code-review", "reviewer-checklist.md")
    for tier in REVIEW_TIERS:
        assert tier in text, tier
    assert "Ready to merge?" in text and "## Declined to judge" in text


@pytest.mark.parametrize("file_name", ("SKILL.md", "references/reviewer-checklist.md"))
def test_code_review_uses_only_must_fix_and_suggestion(file_name):
    text = (SKILLS_DIR / "code-review" / file_name).read_text(encoding="utf-8")
    found = [tier for tier in OLD_TIERS if re.search(rf"\*\*{tier}\b|#+ {tier}\b", text)]
    assert not found, f"{file_name} still grades with {found}"


def test_code_review_defers_suggestions_and_points_to_the_fix_loop():
    text = section(_body("code-review"), "## Requesting a review")
    assert "`apm:executing-plans`" in text and "deferred" in text
    assert "as debt" not in _body("code-review")


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_runnable_text_names_the_cli_not_bare_apm(name):
    found = [f"{where}: {match}" for where, text in _skill_texts(name)
             for match in BARE_CLI.findall(text)]
    assert not found, found


def test_the_cli_placeholder_is_glossed_where_it_is_used():
    for name in sorted(REQUIRED):
        for where, text in _skill_texts(name):
            if "`<CLI>" in text and where.endswith("SKILL.md"):
                assert "`<CLI>` is the framework's command line" in text, where


def test_writing_skills_states_the_framework_skill_contract():
    text = section(_body("writing-skills"), "## Structure")
    for heading in ("## When this applies", "## The core rule", "## Common mistakes"):
        assert heading in text, heading
    assert "-by-language.md" in text


def test_writing_skills_carries_wording_and_diagrams():
    headings = sections(_reference("writing-skills", "best-practices.md"))
    assert "## Wording that holds under pressure" in headings
    assert "## Diagrams" in headings


def test_writing_skills_has_red_flags():
    text = section(_body("writing-skills"), "## Red flags").lower()
    missing = [flag for flag in WRITING_RED_FLAGS if flag not in text]
    assert not missing, missing


def test_subagent_testing_carries_the_debugging_skill_example():
    text = _reference("writing-skills", "testing-skills-with-subagents.md")
    example = section(text, "## A worked example: bulletproofing a debugging skill")
    for needle in ("complex system", "failed first fix", "redundancy", "structural defenses"):
        assert needle in example, needle


def test_subagent_testing_carries_the_worked_campaign():
    headings = sections(_reference("writing-skills", "testing-skills-with-subagents.md"))
    assert "## A worked campaign: testing an instruction file" in headings


def test_transcripts_are_found_under_the_projects_directory():
    text = section(_body("session-diagnosis"), "## Finding the transcripts")
    assert "~/.claude/projects/" in text


@pytest.mark.parametrize("file_name", WORKSPACE_FILES)
def test_the_workspace_is_in_the_system_temp_directory(file_name):
    assert WORKSPACE in _reference("session-diagnosis", file_name), file_name


def test_the_workspace_path_is_named_and_the_old_one_is_gone():
    assert WORKSPACE in _body("session-diagnosis")
    for name in sorted(REQUIRED):
        for where, text in _skill_texts(name):
            assert ".apm/diagnosis" not in text, where


def test_analysts_are_auditors_under_the_worker_cap():
    text = section(_body("session-diagnosis"), "## Triage")
    assert "`apm:auditor`" in text and "worker cap" in text and "sonnet" in text


def test_the_scrubber_is_an_implementer_in_a_worktree():
    text = section(_reference("session-diagnosis", "export-and-redaction.md"), "## Building a bundle")
    assert "`apm:implementer`" in text and 'isolation: "worktree"' in text


def test_the_retry_rule_is_two_failures_then_one_tier_stronger_then_the_user():
    briefs = _reference("session-diagnosis", "analyst-briefs.md")
    for heading in ("## Repeated work", "## Roles and safety"):
        text = section(briefs, heading)
        assert "one tier stronger" in text and "the user" in text, heading


def test_every_analyst_dimension_has_a_brief():
    headings = sections(_reference("session-diagnosis", "analyst-briefs.md"))
    missing = [name for name in ANALYST_DIMENSIONS if f"## {name}" not in headings]
    assert not missing, f"analyst briefs lack {missing}"


def test_the_report_keeps_every_required_section():
    text = _reference("session-diagnosis", "case-and-report.md")
    for heading in ("## The case file", "## The report", "## 7. Instructions involved"):
        assert heading in text, heading


def test_diagrams_keep_the_shape_mapping_and_the_triggers_edge():
    text = section(_reference("writing-skills", "best-practices.md"), "## Diagrams")
    for needle in ("diamond", "plaintext", "ellipse", "octagon", "double circle", "dotted",
                   "triggers", "GOOD", "BAD"):
        assert needle in text, needle


def test_redaction_catches_uuids():
    text = section(_reference("session-diagnosis", "export-and-redaction.md"), "## The redaction policy")
    assert "UUIDs" in text


def test_credits_trace_the_best_practices_to_anthropic():
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert "Anthropic's skill-authoring documentation" in credits


def test_every_diagnosis_opens_its_issue_before_the_first_dispatch():
    text = section(_body("session-diagnosis"), "## When this applies")
    assert "before the first dispatch" in text and "`<CLI> issue N" in text
    for worker in ("analyst", "scrubber", "pressure run"):
        assert worker in text, worker
    assert "When the user asks for the diagnosis to be filed" not in text


def test_a_pressure_run_acts_only_by_choosing_in_its_answer():
    text = section(_reference("writing-skills", "testing-skills-with-subagents.md"),
                   "## Who runs the tests")
    assert "making the choice in the answer" in text
