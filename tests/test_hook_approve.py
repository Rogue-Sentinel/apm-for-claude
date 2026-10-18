"""Through the hook: record an approval for a Windows-path command and retry it; file an issue body."""
import json
import shlex
from pathlib import Path

import pytest

import apm
import apm_cli
import hook_pretooluse
from apm.paths import find_project
from apm.state_store import init_state

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()
CLI = f'python "{PLUGIN_CLI}"'
WIN_TARGET = "git rm -r -q .claude\\skills\\clean-code"


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / ".apm").mkdir()
    profile = json.dumps({"framework_version": apm.VERSION})
    (git_repo / ".apm" / "profile.json").write_text(profile, encoding="utf-8")
    init_state(find_project(git_repo))
    monkeypatch.chdir(git_repo)
    return git_repo


def _event(repo: Path, command: str, tool: str = "Bash") -> str:
    return json.dumps({"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}})


def test_the_approve_call_for_a_windows_path_passes_the_hook_and_its_retry_runs(repo: Path) -> None:
    approve = f'{CLI} approve --command "{WIN_TARGET}" --reason "approved in chat"'
    assert hook_pretooluse.run(_event(repo, approve), {}) == (0, "")
    assert apm_cli.main(shlex.split(approve)[2:]) == 0
    assert hook_pretooluse.run(_event(repo, WIN_TARGET, "PowerShell"), {}) == (0, "")


def test_an_issue_body_written_by_a_heredoc_passes_the_hook(repo: Path) -> None:
    body = "cat > body.md <<'EOF'\nThe guard denied `git rm -r -q x`.\nEOF\n"
    command = body + f"{CLI} github file --title T --body-file body.md"
    assert hook_pretooluse.run(_event(repo, command), {}) == (0, "")
