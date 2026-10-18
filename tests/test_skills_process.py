"""The design, planning and build process skills carry every heading the coverage inventory anchors to."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill

REQUIRED = {
    "design-first": (
        "## Nothing is built before an approved design", "## One question at a time",
        "## Goals, non-goals and anti-goals", "## Approaches and tradeoffs", "## The design document",
        "## The builder check", "## Splitting into issues",
    ),
    "writing-plans": (
        "## Before writing", "## The plan header", "## File structure", "## Tasks",
        "## Interfaces between tasks", "## Structural acceptance criteria", "## Extract before you add",
        "## Allowlisted actions", "## Review focus", "## Self-review",
    ),
    "executing-plans": (
        "## One task at a time", "## Briefing a worker", "## Verify it yourself",
        "## Review after every task", "## Re-review after fixes", "## Recording each task",
        "## When to stop and ask",
    ),
    "parallel-dispatch": (
        "## When work can run in parallel", "## Disjoint files only", "## The worker cap",
        "## Writing each brief", "## Integrating the results",
    ),
    "worktrees": (
        "## Every builder works in its own worktree", "## Creating one",
        "## Never remove a worktree yourself", "## Integrating a worktree branch",
    ),
    "finishing-a-branch": (
        "## Merge main in first", "## Verify everything", "## The debt check", "## The pull request",
        "## The project's merge style", "## Never discard work",
    ),
}
REFERENCES = {
    "design-first": ("builder-check-brief.md",),
    "executing-plans": ("implementer-brief.md", "reviewer-brief.md", "re-review-brief.md"),
}
NAMED_IN_BODY = {
    "finishing-a-branch": ("`apm debt check`", "`<CLI> debt check`"),
    "parallel-dispatch": ("`max_workers`",),
    "executing-plans": ("`<CLI> task",),
    "worktrees": ('`isolation: "worktree"`',),
    "writing-plans": ("`<CLI> allow",),
}


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_skill_has_its_named_references(name):
    for file_name in REFERENCES[name]:
        assert (SKILLS_DIR / name / "references" / file_name).is_file(), f"{name}: {file_name}"


@pytest.mark.parametrize("name", sorted(NAMED_IN_BODY))
def test_skill_names_the_framework_mechanism_it_relies_on(name):
    _, body = parse_skill(name)
    missing = [term for term in NAMED_IN_BODY[name] if term not in body]
    assert not missing, f"{name} does not name {missing}"


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_credits_name_the_skill(name):
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert f"| `{name}` |" in credits, f"CREDITS.md has no row for {name}"
