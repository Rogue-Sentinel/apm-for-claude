"""The README and the tutorial tell the truth: real commands, working links, the promised sections."""
import json
import re
from pathlib import Path

import pytest

from apm.cli_parser import build_parser
from apm.profile import load_profile
from apm.standard_config import load_standard
from apm.workflow_config import load_workflow
from skill_helpers import SKILLS_DIR, british_spellings, local_links, prose_lines, section, sections

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TUTORIAL = ROOT / "docs" / "tutorial.md"
DOCS = (README, TUTORIAL)
HEADINGS = (
    "## 1. Install and set up", "## 2. Initialize a project", "## 3. Ask for a feature",
    "## 4. Report a bug", "## 5. When a worker finds a bug", "## 6. Ask where things stand",
    "## 7. When the guard says no", "## 8. Debt", "## 9. Settings you can change", "## 10. Troubleshooting",
)
_CLI_WORD = re.compile(r"(?:\bapm|<CLI>|apm_cli\.py\"?) ([a-z][a-z-]*)")
_CODE_SPAN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
_JSON_FENCE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """Lines inside fenced code, plus every inline code span in the prose."""
    prose = prose_lines(text)
    fenced = [line for line in text.splitlines() if line not in prose]
    return fenced + [span for line in prose for span in _CODE_SPAN.findall(line)]


def _subcommands(parser, words: list[str]) -> bool:
    """True when the words name a path through the parser's subcommands."""
    choices = next((a.choices for a in parser._actions if hasattr(a, "choices") and isinstance(a.choices, dict)), {})
    if not words or words[0] not in choices:
        return not choices or not words
    return _subcommands(choices[words[0]], words[1:])


def _named_commands(text: str) -> list[str]:
    return [word for line in _code_lines(text) for word in _CLI_WORD.findall(line)]


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_the_document_exists(path):
    assert path.is_file(), f"{path} is missing"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_every_command_it_shows_is_a_real_subcommand(path):
    named = _named_commands(_text(path))
    assert named or path == README, "no commands shown"
    bad = [word for word in named if not _subcommands(build_parser(), [word])]
    assert not bad, f"not subcommands: {bad}"


def test_subcommands_with_a_second_word_name_a_real_action():
    for line in _code_lines(_text(TUTORIAL)):
        for match in re.finditer(r"(?:\bapm|<CLI>) ((?:debt|github) [a-z-]+)", line):
            assert _subcommands(build_parser(), match.group(1).split()), match.group(1)


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_every_relative_link_resolves(path):
    missing = [t for t in local_links(_text(path)) if t and not (path.parent / t).exists()]
    assert not missing, f"broken links: {missing}"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_no_british_spelling(path):
    found = [(n, w) for n, line in enumerate(_text(path).splitlines(), 1) for w in british_spellings(line)]
    assert not found, found


def test_the_tutorial_has_the_ten_sections_in_order():
    numbered = [h for h in sections(_text(TUTORIAL)) if re.match(r"## \d+\.", h)]
    assert tuple(numbered) == HEADINGS


def test_the_readme_links_to_the_tutorial_the_spec_the_coverage_table_and_the_decisions():
    links = local_links(_text(README))
    wanted = ("docs/tutorial.md", "docs/coverage.md", "docs/adr/")
    assert all(any(link.startswith(w) for link in links) for w in wanted), links
    assert any(link.startswith("docs/specs/") for link in links), links


def test_the_readme_states_what_the_plugin_needs_and_how_to_install_it():
    text = _text(README)
    for needed in ("Python 3.12", "git", "`gh`", "rogue-sentinel", "/apm:setup"):
        assert needed in text, needed


@pytest.mark.parametrize(
    "path, heading", [(README, "## Install"), (TUTORIAL, HEADINGS[0])], ids=["README.md", "tutorial.md"]
)
def test_the_install_says_to_remove_an_old_local_marketplace_first(path, heading):
    install = section(_text(path), heading)
    remove = "/plugin marketplace remove rogue-sentinel"
    assert remove in install
    assert "claude plugin marketplace remove rogue-sentinel" in install
    assert install.index(remove) < install.index("/plugin marketplace add")


def test_troubleshooting_explains_a_failed_marketplace_add():
    troubleshooting = section(_text(TUTORIAL), HEADINGS[9])
    assert "Failed to add marketplace." in troubleshooting
    assert "/plugin marketplace remove rogue-sentinel" in troubleshooting


def test_the_example_profile_loads_and_uses_only_keys_that_exist(tmp_path):
    block = _JSON_FENCE.search(section(_text(TUTORIAL), HEADINGS[8]))
    assert block, "no json block under the settings section"
    path = tmp_path / "profile.json"
    path.write_text(block.group(1), encoding="utf-8")
    profile = load_profile(path)
    load_standard(profile), load_workflow(profile)
    assert {"standard", "workflow"} <= set(profile.extra)


def test_the_tutorial_names_every_workflow_skill():
    text = _text(TUTORIAL)
    for skill in ("initializing", "running-an-issue", "merge-gate"):
        assert (SKILLS_DIR / skill / "SKILL.md").is_file() and f"apm:{skill}" in text, skill


def test_the_test_first_cycle_runs_targeted_tests_not_the_whole_suite():
    steps = _text(SKILLS_DIR / "test-first" / "references" / "cycle-steps.md")
    assert "**whole** suite" not in steps
    assert "`<CLI> gate`" in steps


_RUNS_APM = re.compile(r"\b(?:run|type|enter|execute)\b[^.\n]*`apm ", re.IGNORECASE)
_MANAGER_RUNS = "The manager runs"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_no_python_command_line_is_shown_to_the_user(path):
    text = _text(path)
    bad = [line for line in _code_lines(text) if line.lstrip().startswith("python ")]
    assert not bad, f"the user is never asked to run python: {bad}"
    assert "apm_cli.py" not in text, "the script path belongs to the manager"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_the_user_is_never_told_to_run_apm_in_a_shell(path):
    text = _text(path)
    bad = [line for line in _code_lines(text) if line.lstrip().startswith("apm ")]
    assert not bad, f"apm in a shell: {bad}"
    assert not _RUNS_APM.findall(text), "prose tells the user to run apm"


def test_the_readme_and_tutorial_section_one_set_up_from_chat():
    assert "/apm:setup" in _text(README)
    assert "/apm:setup" in section(_text(TUTORIAL), HEADINGS[0])


def test_the_setup_slash_command_exists_with_a_quoted_description():
    path = ROOT / "commands" / "setup.md"
    assert path.is_file(), f"{path} is missing"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].strip() == "---", "no frontmatter"
    front = lines[1:lines.index("---", 1)]
    assert any(re.match(r"description: \"[^\"]+\"$", line) for line in front), front


def _cli_blocks_without_a_label(text: str) -> list[int]:
    """Line numbers of fenced blocks that start a line with <CLI> but have no label just above."""
    lines, bad, start = text.splitlines(), [], None
    for number, line in enumerate(lines):
        if not line.lstrip().startswith("```"):
            continue
        if start is None:
            start = number
            continue
        body = lines[start + 1:number]
        labeled = any(_MANAGER_RUNS in above for above in lines[max(0, start - 2):start])
        if any(row.lstrip().startswith("<CLI> ") for row in body) and not labeled:
            bad.append(start + 1)
        start = None
    return bad


def test_every_cli_block_in_the_tutorial_is_labeled_as_what_the_manager_runs():
    assert _cli_blocks_without_a_label(_text(TUTORIAL)) == []


def _front_and_body(path: Path) -> tuple[list[str], str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1:])


def test_the_branch_review_command_takes_an_optional_branch():
    path = ROOT / "commands" / "branch-review.md"
    assert path.is_file(), f"{path} is missing"
    front, body = _front_and_body(path)
    assert any(re.match(r"description: \"[^\"]+\"$", line) for line in front), front
    assert "argument-hint: \"[branch]\"" in front, front
    assert "$ARGUMENTS" in body and "apm:branch-review" in body


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_the_docs_name_the_optional_branch_review_command(path):
    assert "/apm:branch-review" in _text(path)


def test_the_branch_review_command_briefs_the_reviewer_with_the_code_review_brief():
    body = _front_and_body(ROOT / "commands" / "branch-review.md")[1]
    flat = " ".join(body.split())
    assert "apm:code-review" in flat and "references/reviewer-checklist.md" in flat
    for needed in ("exact CLI line", "its base", "limits", "`standard.ui`"):
        assert needed in flat, needed
