"""The review scorecard and the audit carry every heading, band and format the old ones had."""
import re

import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill, sections

DIMENSIONS = (
    "Type and contract safety", "State management", "Module architecture",
    "Entry points and routing", "Styling and presentation", "Testing", "Error handling",
    "External integration", "Accessibility", "Code duplication",
    "Developer experience and maintainability",
)
UI_ONLY = ("Entry points and routing", "Styling and presentation", "Accessibility")
HEAVY = ("Type and contract safety", "Module architecture", "Testing")
BANDS = ("1-3", "4-6", "7-8", "9-10")
AUDIT_CATEGORIES = (
    "### Test-first", "### Refactoring", "### SOLID", "### Object design",
    "### Functional core", "### Architecture", "### Hygiene",
)
REQUIRED = {
    "branch-review": (
        "## Gather evidence", "## The scorecard", *(f"### {name}" for name in DIMENSIONS),
        "## Previous reviews", "## Report", "## Scoring honestly",
    ),
    "clean-code-audit": (
        "## Scan", "## Measure", *AUDIT_CATEGORIES, "## Report format", "## Priorities",
    ),
}
LANGUAGES = ("TypeScript", "Python", "C++", "C#", "Java", "Go", "Rust")
SCORECARD_FORMATS = (
    "| Dimension | Old | New | Verdict |",
    "| Dimension | Old | Previous New | Current New | Verdict |",
    "**The old code was X/10. The new code is Y/10.**",
    "**The old code was X/10. The previous new code was Y/10. The current new code is Z/10.**",
)
_FENCE = re.compile(r"\s*(`{3,}|~{3,})")


def _reference(name: str) -> str:
    return (SKILLS_DIR / "branch-review" / "references" / name).read_text(encoding="utf-8")


def _level(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def _ends_section(line: str, level: int, in_fence: bool) -> bool:
    return not in_fence and bool(sections(line)) and _level(line) <= level


def _section(text: str, heading: str) -> str:
    """The lines under `heading`, fences included, up to the next heading of its level or above."""
    lines = text.splitlines()
    kept, in_fence = [], False
    for line in lines[lines.index(heading) + 1:]:
        if _ends_section(line, _level(heading), in_fence):
            break
        in_fence ^= bool(_FENCE.match(line))
        kept.append(line)
    return "\n".join(kept)


def _subsections(text: str, heading: str) -> list[str]:
    """The `###` headings between `heading` and the next `##`."""
    headings = sections(text)
    following = headings[headings.index(heading) + 1:]
    ends = [i for i, line in enumerate(following) if line.startswith("## ")]
    return following[:ends[0]] if ends else following


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


def test_branch_review_has_its_named_references():
    for file_name in ("scoring-evidence-guide.md", "evidence-by-language.md"):
        assert (SKILLS_DIR / "branch-review" / "references" / file_name).is_file(), file_name


def test_the_scorecard_holds_the_eleven_dimensions_in_order():
    _, body = parse_skill("branch-review")
    assert _subsections(body, "## The scorecard") == [f"### {name}" for name in DIMENSIONS]


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_every_dimension_keeps_every_rubric_band(dimension):
    _, body = parse_skill("branch-review")
    text = _section(body, f"### {dimension}")
    missing = [band for band in BANDS if f"| {band} |" not in text]
    assert not missing, f"{dimension} lacks bands {missing}"


@pytest.mark.parametrize("dimension", UI_ONLY)
def test_ui_dimensions_are_scored_na_with_a_reason_without_a_ui(dimension):
    _, body = parse_skill("branch-review")
    assert "N/A" in _section(body, f"### {dimension}"), dimension


def test_branch_review_gathers_measured_and_project_evidence():
    _, body = parse_skill("branch-review")
    evidence = _section(body, "## Gather evidence")
    needles = ("`apm metrics`", "`apm debt check", "`standard.review_patterns`", "`standard.limits`")
    for needle in needles:
        assert needle in evidence, needle
    assert "`apm debt baseline`" in body


def test_report_keeps_the_old_new_and_previous_review_formats():
    _, body = parse_skill("branch-review")
    for line in SCORECARD_FORMATS:
        assert line in body, line
    assert "`BRANCH_REVIEW.md`" in _section(body, "## Previous reviews")


def test_scoring_honestly_keeps_greenfield_and_the_weighting_rule():
    _, body = parse_skill("branch-review")
    honesty = _section(body, "## Scoring honestly")
    assert "greenfield" in honesty and "N/A" in honesty
    assert "not an average" in body


def test_evidence_guide_covers_every_dimension_and_the_weighting():
    guide = _reference("scoring-evidence-guide.md")
    headings = sections(guide)
    missing = [name for name in DIMENSIONS if f"## {name}" not in headings]
    assert not missing, f"evidence guide lacks {missing}"
    assert "## Overall score weighting" in headings
    for name in HEAVY:
        assert f"| {name} | High |" in guide, name


def test_evidence_by_language_covers_each_language_and_project_patterns():
    text = _reference("evidence-by-language.md")
    headings = sections(text)
    missing = [language for language in LANGUAGES if f"## {language}" not in headings]
    assert not missing, f"evidence by language lacks {missing}"
    assert "`standard.review_patterns`" in text


def test_audit_measures_against_the_profile_limits():
    _, body = parse_skill("clean-code-audit")
    measure = _section(body, "## Measure")
    assert "`apm metrics`" in measure and "`standard.limits`" in measure
    assert "20 lines" not in body


def test_audit_report_keeps_the_summary_scores_and_top_five():
    _, body = parse_skill("clean-code-audit")
    report = _section(body, "## Report format")
    for needle in ("Overall health", "Files scanned", "Issues found", "(score: X/10)", "Top 5"):
        assert needle in report, needle
