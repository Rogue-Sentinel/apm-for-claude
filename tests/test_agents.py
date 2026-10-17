"""The plugin agent definitions carry the right frontmatter and body."""
import re
from pathlib import Path

import pytest

from apm.profile import DEFAULT_MODELS

AGENTS = Path(__file__).resolve().parent.parent / "agents"
WORKERS = tuple(DEFAULT_MODELS)
MANAGER_HEADINGS = (
    "## Your role",
    "## Talking to the user",
    "## Dispatching workers",
    "## Verifying work",
    "## Recording state",
    "## Safety",
)
REPORT_ITEMS = ("status", "files changed", "commands run", "concerns", "found elsewhere")
ALL_AGENTS = ("manager", *WORKERS)


def parse(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", f"{path.name}: no frontmatter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, "\n".join(lines[end + 1:])


def field_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@pytest.mark.parametrize("name", ALL_AGENTS)
def test_name_matches_stem_and_description_present(name):
    fields, _ = parse(AGENTS / f"{name}.md")
    assert fields["name"] == name
    assert fields.get("description", "").strip()


def test_manager_model_inherit_and_may_dispatch():
    fields, _ = parse(AGENTS / "manager.md")
    assert fields["model"] == "inherit"
    if "tools" in fields:
        assert "Agent" in field_list(fields["tools"])


@pytest.mark.parametrize("name", WORKERS)
def test_worker_model_and_cannot_dispatch(name):
    fields, _ = parse(AGENTS / f"{name}.md")
    assert fields["model"] == DEFAULT_MODELS[name]
    assert "Agent" in field_list(fields["disallowedTools"])


def test_manager_body_has_required_headings():
    _, body = parse(AGENTS / "manager.md")
    for heading in MANAGER_HEADINGS:
        assert heading in body, f"manager missing {heading}"


@pytest.mark.parametrize("name", WORKERS)
def test_worker_report_format_lists_every_item(name):
    _, body = parse(AGENTS / f"{name}.md")
    marker = "## Report format"
    assert marker in body, f"{name} missing {marker}"
    section = body[body.index(marker):].split("\n## ", 1)[0]
    for item in REPORT_ITEMS:
        assert item in section, f"{name} report format missing '{item}'"


def frontmatter_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[1:lines.index("---", 1)]


@pytest.mark.parametrize("name", ALL_AGENTS)
def test_frontmatter_unquoted_values_hold_no_colon_space(name):
    for line in frontmatter_lines(AGENTS / f"{name}.md"):
        value = line.partition(":")[2].strip()
        if value[:1] in ('"', "'"):
            assert value[-1] == value[0] and len(value) > 1, f"{name}: unterminated {line}"
        else:
            assert ": " not in value, f"{name}: unquoted value holds ': ' in {line}"


@pytest.mark.parametrize("name", ALL_AGENTS)
def test_description_is_quoted(name):
    fields, _ = parse(AGENTS / f"{name}.md")
    assert fields["description"][:1] == '"' and fields["description"][-1:] == '"'


def test_manager_isolates_workers_and_marks_tasks_running():
    _, body = parse(AGENTS / "manager.md")
    assert 'isolation: "worktree"' in body
    assert "--status running --worker" in body
    assert "attempts" in body


@pytest.mark.parametrize("name", ("implementer", "debugger"))
def test_builders_work_only_in_their_worktree(name):
    _, body = parse(AGENTS / f"{name}.md")
    assert "only in the worktree you were started in" in body


CLI_SUBCOMMANDS = ("brief", "setup", "issue", "task", "allow", "approve", "question", "resolve")


def test_manager_runs_the_cli_from_session_context_with_the_bash_tool():
    _, body = parse(AGENTS / "manager.md")
    assert "the APM CLI command from your SessionStart context (shown as `<CLI>` below)" in body
    assert "with the Bash tool" in body
    assert "Never call bare `apm`" in body
    assert 'python "<plugin root>/scripts/apm_cli.py"' in body
    assert "~/.claude/plugins/cache/rogue-sentinel/apm/<version>/" in body


@pytest.mark.parametrize("verb", CLI_SUBCOMMANDS)
def test_manager_documents_each_cli_subcommand(verb):
    _, body = parse(AGENTS / "manager.md")
    assert f"`<CLI> {verb}" in body, f"manager does not document {verb}"


def test_manager_never_shows_a_bare_apm_command():
    _, body = parse(AGENTS / "manager.md")
    assert not re.search(r"`apm [a-z]", body), re.search(r"`apm [a-z].*", body)


@pytest.mark.parametrize("name", WORKERS)
def test_workers_do_not_change_apm_state(name):
    _, body = parse(AGENTS / f"{name}.md")
    assert "Never run the APM CLI (`apm_cli.py` or `apm`); the manager records state" in body
    assert "`apm issue`" not in body


def _section(body: str, heading: str) -> str:
    return body[body.index(heading):].split("\n## ", 1)[0]


def test_manager_safety_asks_in_chat_and_records_one_off_approvals():
    _, body = parse(AGENTS / "manager.md")
    safety = _section(body, "## Safety")
    assert "A guard denial is a stop" in safety
    assert "Ask the user in chat" in safety and "approve" in safety
    assert "Never approve on your own judgment" in safety
    assert "never covers a different command" in safety
    assert "permission prompt" not in body


def test_manager_has_an_exit_when_the_approve_call_is_denied():
    _, body = parse(AGENTS / "manager.md")
    safety = _section(body, "## Safety")
    assert (
        "If the approve call is itself denied, stop and ask the user to run the command themselves; "
        "never rewrite a command to make it approvable." in safety
    )
    assert "the exact full command you will retry, not just the flagged segment" in safety
    assert "lasts 10 minutes" in safety
    assert "only in the directory it was recorded in" in safety
    assert "reusable within that window" in safety
