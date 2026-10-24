"""The code-level Clean Code skills carry every heading the coverage inventory anchors to."""
import pytest

from skill_helpers import (
    SKILLS_DIR, assert_description_names, assert_sections, flat_section, parse_skill, sections,
    skill_text, trigger_cases,
)

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
    "refactoring": (
        "extraction-heuristics.md", "polymorphism-before-after.md", "examples-by-language.md",
    ),
    "test-first": (
        "cycle-steps.md", "test-first-checklist.md", "aaa-patterns.md", "writing-good-tests.md",
    ),
    "adr": ("adr-template.md",),
}
TRIGGERS = {
    "clean-code": (
        "boy scout rule", "leaving code cleaner", "continuous improvement",
        "incremental quality improvements", "improving naming", "meaningful names",
        "naming conventions", "misleading identifiers",
    ),
    "code-smells": (
        "code smells", "technical debt", "reviewing code quality",
        "systematic code quality assessment",
    ),
    "refactoring": (
        "break up a long function", "reduce method length", "decompose complex logic",
        "simplify a function", "complex branching", "long if-else or switch-case chains",
        "Open-Closed to branching",
    ),
    "test-first": (
        "TDD", "test-driven development", "writing tests first", "test-first development",
        "testable by design", "red-green-refactor", "incrementally with tests",
        "arrange-act-assert", "AAA", "given-when-then", "organizing test code",
        "test readability",
    ),
}
CLASS_SIZE_SIGNAL = ("about 200 lines", "judged by the reviewer, not measured")
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


@pytest.mark.parametrize(("name", "term"), trigger_cases(TRIGGERS))
def test_description_names_the_original_triggers(name, term):
    assert_description_names(name, term)


def test_extract_method_keeps_the_original_trigger_threshold_and_aim():
    _, body = parse_skill("refactoring")
    assert "simplify or decompose a function" in flat_section(body, "## When this applies")
    assert "about 10 lines of logic" in flat_section(body, "## When this applies")
    assert "read like prose" in flat_section(body, "## Extract method")


def test_type_checks_point_at_their_examples_by_language():
    _, body = parse_skill("refactoring")
    assert "`instanceof`" in skill_text("refactoring", "references", "examples-by-language.md")
    assert "references/examples-by-language.md" in flat_section(
        body, "## Replace conditional with polymorphism")
    others = [p for p in (SKILLS_DIR / "refactoring").rglob("*.md")
              if p.name != "examples-by-language.md"]
    assert [p.name for p in others if "instanceof" in p.read_text(encoding="utf-8")] == []


def test_a_test_that_passes_at_once_is_deleted_as_redundant():
    _, body = parse_skill("test-first")
    cycle = flat_section(body, "## Red, green, refactor")
    assert "redundant" in cycle and "delete it and pick a different behavior" in cycle
    assert "fix or delete" not in cycle
    assert "delete it and pick a different behavior" in " ".join(
        skill_text("test-first", "references", "cycle-steps.md").split())


def test_large_class_has_a_reviewer_judged_class_size_signal():
    _, body = parse_skill("code-smells")
    catalog = skill_text("code-smells", "references", "smell-catalog.md")
    for text in (flat_section(body, "## Finding smells"), flat_section(catalog, "### Large class")):
        for phrase in CLASS_SIZE_SIGNAL:
            assert phrase in text


def test_a_regression_test_that_passes_on_the_current_code_has_not_reproduced_the_bug():
    _, body = parse_skill("test-first")
    fix = flat_section(body, "## A bug fix starts with a failing test")
    assert "has not reproduced the bug" in fix


def test_finding_smells_does_not_claim_the_class_size_is_the_only_unmeasured_signal():
    _, body = parse_skill("code-smells")
    finding = flat_section(body, "## Finding smells")
    assert "One size signal it does not give" in finding
    assert "The one size signal" not in finding
