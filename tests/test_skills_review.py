"""The review scorecard and the audit carry every heading, band and format the old ones had."""
import re

import pytest

from skill_helpers import (
    SKILLS_DIR, assert_sections, parse_skill, prose_lines, section, sections,
)

DIMENSIONS = (
    "Type and contract safety", "State management", "Module architecture",
    "Entry points and routing", "Styling and presentation", "Testing", "Error handling",
    "External integration", "Accessibility", "Code duplication",
    "Developer experience and maintainability",
)
UI_SCOPED = ("Entry points and routing", "Styling and presentation", "Accessibility")
NO_UI_REASON = "N/A (no user interface)"
UI_WHERE = "(where there is a user interface)"
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
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
# An escape pair, or a bracket expression: an optional ^, an optional leading ], then
# character classes or any character but ], up to the closing ].
_ERE_TOKEN = re.compile(r"\\.|(\[\^?\]?(?:\[:[a-z]+:\]|[^\]])*\])")


def _reference(name: str) -> str:
    return (SKILLS_DIR / "branch-review" / "references" / name).read_text(encoding="utf-8")


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
    text = section(body, f"### {dimension}")
    missing = [band for band in BANDS if f"| {band} |" not in text]
    assert not missing, f"{dimension} lacks bands {missing}"


def _band(text: str, band: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(f"| {band} |"))


def _bad_bracket_expressions(text: str) -> list[str]:
    """Code spans holding a bracket expression that ends in a backslash.

    In POSIX ERE a backslash inside brackets is literal, so `[a\\]]` is `[a\\]` and then a `]`.
    """
    spans = [span for line in prose_lines(text) for span in _CODE_SPAN.findall(line)]
    found = [(span, token) for span in spans for token in _ERE_TOKEN.findall(span)]
    return [span for span, token in found if token.endswith("\\]")]


@pytest.mark.parametrize("dimension", UI_SCOPED)
def test_ui_scoped_dimensions_give_na_with_its_reason_without_a_ui(dimension):
    _, body = parse_skill("branch-review")
    assert NO_UI_REASON in section(body, f"### {dimension}"), dimension


def test_entry_points_are_still_scored_without_a_ui():
    _, body = parse_skill("branch-review")
    assert "entry points are still scored" in section(body, "### Entry points and routing")


def test_the_profile_ui_key_decides_the_ui_scoped_dimensions():
    _, review = parse_skill("branch-review")
    _, audit = parse_skill("clean-code-audit")
    assert "`standard.ui`" in section(review, "## Gather evidence")
    assert "`standard.ui`" in section(audit, "## Scan")


def test_testing_can_reach_the_top_band_without_a_ui():
    _, body = parse_skill("branch-review")
    assert UI_WHERE in _band(section(body, "### Testing"), "9-10")
    assert UI_WHERE in section(_reference("scoring-evidence-guide.md"), "## Testing")


def test_duplication_counts_shared_modules_as_well_as_components():
    _, body = parse_skill("branch-review")
    assert "shared components or shared modules" in section(body, "### Code duplication")


def test_branch_review_gathers_measured_and_project_evidence():
    _, body = parse_skill("branch-review")
    evidence = section(body, "## Gather evidence")
    needles = ("`apm metrics`", "`apm debt check", "`standard.review_patterns`", "`standard.limits`")
    for needle in needles:
        assert needle in evidence, needle
    assert "`apm debt baseline`" in body


def test_report_keeps_the_old_new_and_previous_review_formats():
    _, body = parse_skill("branch-review")
    for line in SCORECARD_FORMATS:
        assert line in body, line
    assert "`BRANCH_REVIEW.md`" in section(body, "## Previous reviews")


def test_scoring_honestly_keeps_greenfield_and_the_weighting_rule():
    _, body = parse_skill("branch-review")
    honesty = section(body, "## Scoring honestly")
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


def test_evidence_patterns_have_well_formed_bracket_expressions():
    bad = _bad_bracket_expressions(_reference("evidence-by-language.md"))
    assert not bad, bad


def test_bracket_check_catches_an_escaped_closing_bracket():
    text = r"`[a-z\]]!` and `[]a-z]!` and `\[x\]` and `[[:space:]]`"
    assert _bad_bracket_expressions(text) == [r"[a-z\]]!"]


def test_credits_name_both_review_skills():
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    for name in ("branch-review", "clean-code-audit"):
        assert f"| `{name}` |" in credits, name


def test_audit_measures_against_the_profile_limits():
    _, body = parse_skill("clean-code-audit")
    measure = section(body, "## Measure")
    assert "`apm metrics`" in measure and "`standard.limits`" in measure
    assert "20 lines" not in body


def test_audit_report_keeps_the_summary_scores_and_top_five():
    _, body = parse_skill("clean-code-audit")
    report = section(body, "## Report format")
    for needle in ("Overall health", "Files scanned", "Issues found", "(score: X/10)", "Top 5"):
        assert needle in report, needle
