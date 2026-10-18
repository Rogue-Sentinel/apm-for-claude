"""A denial shows the command as typed, not the text the scan masked."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()
CLI = f'python "{PLUGIN_CLI}"'
WINDOWS = sys.platform == "win32"


def _decide(repo: Path, command: str, tool: str = "Bash", **extra: object) -> Decision:
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", protected_paths=("data/*.db",))
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [], WINDOWS, [])


def test_a_powershell_approve_call_is_denied_with_the_command_as_typed(git_repo: Path) -> None:
    command = f'{CLI} approve --command "git rm -r -q .claude/skills/x" --reason "approved in chat"'
    decision = _decide(git_repo, command, tool="PowerShell")
    assert f"destructive command (recursive rm): {command}. Ask the user in chat" in decision.reason


def test_a_chained_approve_call_is_denied_with_the_command_as_typed(git_repo: Path) -> None:
    command = f'{CLI} approve --command "rm -rf build" --reason "user said yes" && echo done'
    decision = _decide(git_repo, command)
    assert f"destructive command (recursive rm): {command}. Ask the user in chat" in decision.reason


def test_a_protected_write_is_denied_with_the_whole_command(git_repo: Path) -> None:
    command = 'cp x data/fleet.db && git commit -m "update data/fleet.db"'
    decision = _decide(git_repo, command)
    assert f"command touches a protected path (data/fleet.db): {command}." in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        'python scripts/apm_cli.py note 4 --text "remember this"',
        'gh issue create --title "Fix" --body "x"',
    ],
)
def test_a_worker_denial_ends_with_the_command_as_typed(git_repo: Path, command: str) -> None:
    decision = _decide(git_repo, command, agent_id="w1")
    assert decision.kind == "deny" and decision.reason.endswith(": " + command)
