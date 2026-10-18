"""The design, planning and build process skills carry every heading the coverage inventory anchors to."""
import re

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
        "## When to review", "## Re-review after fixes", "## Recording each task",
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
    "finishing-a-branch": ("`<CLI> debt check`",),
    "parallel-dispatch": ("`max_workers`",),
    "executing-plans": ("`<CLI> task", "--status failed"),
    "worktrees": ('`isolation: "worktree"`',),
    "writing-plans": ("`<CLI> allow",),
}

LEAN_PACING_SKILLS = (
    "executing-plans", "code-review", "test-first", "worktrees", "parallel-dispatch", "writing-plans",
    "systematic-debugging", "verification",
)
BASE_CHECK_FILES = ("worktrees/SKILL.md", "executing-plans/references/implementer-brief.md")

BARE_CLI =re.compile(r"`apm (?:metrics|debt|task|issue|allow|approve|question|resolve|brief)(?!\w)")
TWO_TIERS_ONLY = ("reviewer-brief.md", "re-review-brief.md")


def _skill_texts(name):
    return [(path, path.read_text(encoding="utf-8")) for path in (SKILLS_DIR / name).rglob("*.md")]


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


@pytest.mark.parametrize("name", LEAN_PACING_SKILLS)
def test_skill_carries_the_lean_pacing_rule(name):
    text = "\n".join(text for _, text in _skill_texts(name))
    assert "`<CLI> gate`" in text, f"{name} does not name the gate as where the full suite runs"


def test_no_skill_still_reviews_after_every_task():
    stale = [str(path) for path in SKILLS_DIR.rglob("*.md") if "Review after every task" in path.read_text(encoding="utf-8")]
    assert not stale, f"old heading still referenced in {stale}"


@pytest.mark.parametrize("relative", BASE_CHECK_FILES)
def test_worktree_guidance_checks_the_base_is_an_ancestor(relative):
    text = (SKILLS_DIR / relative).read_text(encoding="utf-8")
    assert "merge-base --is-ancestor" in text and "--ff-only" in text, f"{relative} has no base check"


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_credits_name_the_skill(name):
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert f"| `{name}` |" in credits, f"CREDITS.md has no row for {name}"


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_runnable_commands_use_the_cli_placeholder(name):
    bare = [f"{path.name}: {m}" for path, text in _skill_texts(name) for m in BARE_CLI.findall(text)]
    assert not bare, f"{name} names the CLI as bare apm: {bare}"


@pytest.mark.parametrize("file_name", TWO_TIERS_ONLY)
def test_review_briefs_use_two_severity_tiers(file_name):
    text = (SKILLS_DIR / "executing-plans" / "references" / file_name).read_text(encoding="utf-8")
    assert "must fix" in text.lower() and "suggestion" in text.lower()
    assert "should fix" not in text.lower(), f"{file_name} still has a should-fix tier"
