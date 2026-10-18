"""An approve call with a Windows path is recorded data; its chained and foreign forms stay denied."""
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
WIN_TARGET = "git rm -r -q .claude\\skills\\clean-code"
LATER = "2999-01-01T00:00:00+00:00"
APPROVE = f'{CLI} approve --command "{WIN_TARGET}" --reason "approved in chat"'


def _decide(repo: Path, command: str, tool: str = "Bash", approvals: list | None = None, **extra: object) -> Decision:
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", protected_paths=("data/*.db",))
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [], WINDOWS, approvals or [])


@pytest.mark.parametrize(
    "target",
    [
        '"git rm -r -q .claude\\skills\\clean-code"',
        "'git rm -r -q .claude\\skills\\clean-code'",
        "'Remove-Item -Recurse -Force C:\\work\\build'",
    ],
)
def test_an_approve_call_with_a_windows_path_is_data(git_repo: Path, target: str) -> None:
    command = f'{CLI} approve --command {target} --reason "approved in chat"'
    assert _decide(git_repo, command).kind == "none"


@pytest.mark.parametrize(
    "command",
    [
        f'{CLI} approve --command "{WIN_TARGET}" --reason ok; rm -rf build',
        f'{CLI} approve --command "{WIN_TARGET}" --reason ok && {WIN_TARGET}',
        f'{CLI} approve --command "{WIN_TARGET}" --reason ok > out.txt',
    ],
)
def test_a_chained_approve_call_with_a_windows_path_stays_denied(git_repo: Path, command: str) -> None:
    assert _decide(git_repo, command).kind == "deny"


def test_the_windows_approve_call_is_not_exempt_from_powershell_or_a_worker(git_repo: Path) -> None:
    assert _decide(git_repo, APPROVE, tool="PowerShell").kind == "deny"
    assert _decide(git_repo, APPROVE, agent_id="w1").kind == "deny"


def test_an_approval_of_a_windows_command_covers_exactly_its_retry(git_repo: Path) -> None:
    approvals = [{"command": WIN_TARGET, "reason": "r", "cwd": str(git_repo), "expires_at": LATER}]
    retry = _decide(git_repo, WIN_TARGET, tool="PowerShell", approvals=approvals)
    other = _decide(git_repo, "git rm -r -q .claude\\skills\\other", tool="PowerShell", approvals=approvals)
    assert (retry.kind, other.kind) == ("none", "deny")
