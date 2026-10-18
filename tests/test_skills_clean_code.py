"""The code-level Clean Code skills carry every heading the coverage inventory anchors to."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill, sections

REQUIRED = {
    "clean-code": (
        "## The limits", "## Counting lines of logic", "## Debt never grows",
        "## The boy scout rule", "## Meaningful names", "## Functions do one thing",
    ),
    "code-smells": ("## Finding smells", "## Severity", "## Reporting a smell"),
    "refactoring": (
        "## Extract before you add", "## Refactor and behavior never share a commit",
        "## Logic does not move sideways", "## Extract method", "## Rename",
        "## Replace conditional with polymorphism", "## Splitting a file",
    ),
    "test-first": (
        "## Test first", "## Red, green, refactor", "## Arrange, act, assert",
        "## A bug fix starts with a failing test", "## No test skips",
        "## No test waits on a person", "## Never weaken a test", "## Writing good tests",
    ),
    "adr": (
        "## When a decision needs an ADR", "## Writing one", "## Superseding one",
        "## Promised ADRs are acceptance criteria",
    ),
}
REFERENCES = {
    "clean-code": ("improvement-checklist.md", "naming-conventions.md"),
    "code-smells": ("smell-catalog.md",),
    "refactoring": ("extraction-heuristics.md", "polymorphism-before-after.md"),
    "test-first": (
        "cycle-steps.md", "test-first-checklist.md", "aaa-patterns.md", "writing-good-tests.md",
    ),
    "adr": ("adr-template.md",),
}
SMELL_CATALOG = {
    "## Bloaters": (
        "### Long method", "### Large class", "### Long parameter list", "### Data clumps",
        "### Primitive obsession",
    ),
    "## Couplers": (
        "### Feature envy", "### Inappropriate intimacy", "### Message chains", "### Middle man",
    ),
    "## Change preventers": (
        "### Divergent change", "### Shotgun surgery", "### Parallel inheritance hierarchies",
    ),
    "## Dispensables": (
        "### Dead code", "### Speculative generality", "### Duplicate code", "### Lazy class",
        "### Unnecessary comments",
    ),
}


def _subsections(headings: list[str], category: str) -> list[str]:
    """The headings after `category` up to the next `##`."""
    following = headings[headings.index(category) + 1:]
    ends = [i for i, heading in enumerate(following) if heading.startswith("## ")]
    return following[:ends[0]] if ends else following


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_skill_has_its_named_references(name):
    for file_name in REFERENCES[name]:
        assert (SKILLS_DIR / name / "references" / file_name).is_file(), f"{name}: {file_name}"


def test_smell_catalog_keeps_every_category_and_smell():
    text = (SKILLS_DIR / "code-smells" / "references" / "smell-catalog.md").read_text(encoding="utf-8")
    headings = sections(text)
    for category, smells in SMELL_CATALOG.items():
        assert category in headings, f"smell catalog lacks {category}"
        own = _subsections(headings, category)
        missing = [smell for smell in smells if smell not in own]
        assert not missing, f"{category} lacks {missing}"


def test_clean_code_explains_metrics_and_the_profile_override():
    _, body = parse_skill("clean-code")
    assert "`<CLI> metrics`" in body
    assert "`standard.limits`" in body


def test_adr_directory_comes_from_the_profile():
    _, body = parse_skill("adr")
    assert "`standard.adr_dir`" in body
    assert "`docs/adr/`" in body
