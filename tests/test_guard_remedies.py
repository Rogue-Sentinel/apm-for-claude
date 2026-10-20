"""A denial offers only an approval that can lift it: --path for a protected file, --command for a command."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import PLUGIN_ROOT, Project, cli_command
from apm.profile import Profile

WINDOWS = sys.platform == "win32"


def _path_approval(repo: Path, path: str) -> dict:
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    return {"path": path, "reason": "r", "cwd": str(repo), "expires_at": expires}


def _decide(repo: Path, event_extra: dict, approvals: tuple = (), protected: tuple = ()) -> Decision:
    event = {"cwd": str(repo), **event_extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=protected)
    return decide(event, project, profile, [], [], WINDOWS, list(approvals))


def _file_event(tool: str, path: Path, **extra: object) -> dict:
    return {"tool_name": tool, "tool_input": {"file_path": str(path)}, **extra}


def _bash(command: str, **extra: object) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, **extra}


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_an_outside_file_write_offers_no_approval(git_repo: Path, tool: str) -> None:
    reason = _decide(git_repo, _file_event(tool, git_repo.parent / "outside" / "x.md")).reason
    assert "approve --" not in reason
    assert "make the change themselves" in reason


def test_a_state_dir_file_write_offers_no_approval(git_repo: Path) -> None:
    reason = _decide(git_repo, _file_event("Edit", git_repo / ".apm" / "state" / "ledger.json")).reason
    assert "approve --" not in reason
    assert "only through the CLI" in reason


def test_a_protected_file_write_offers_a_path_approval_only(git_repo: Path) -> None:
    event = _file_event("Edit", git_repo / "data" / "fleet.db")
    reason = _decide(git_repo, event, protected=("data/*.db",)).reason
    assert "data/fleet.db is a protected path" in reason
    assert "approve --path" in reason
    assert "--command" not in reason


def test_a_command_denial_offers_a_command_approval_only(git_repo: Path) -> None:
    reason = _decide(git_repo, _bash("rm -rf build")).reason
    assert 'approve --command "<the exact full command>"' in reason
    assert "--path" not in reason


def test_a_path_approval_of_the_named_path_lifts_the_protected_write(git_repo: Path) -> None:
    event = _file_event("Edit", git_repo / "data" / "fleet.db")
    approvals = (_path_approval(git_repo, "data/fleet.db"),)
    assert _decide(git_repo, event, approvals, ("data/*.db",)).kind == "none"


@pytest.mark.parametrize("form", ["native", "posix", "**"])
def test_no_path_approval_lifts_an_outside_write(git_repo: Path, form: str) -> None:
    target = git_repo.parent / "outside" / "x.md"
    approved = {"native": str(target), "posix": target.as_posix(), "**": "**"}[form]
    event = _file_event("Edit", target)
    assert _decide(git_repo, event, (_path_approval(git_repo, approved),)).kind == "deny"


@pytest.mark.parametrize("kind", ["file", "command"])
def test_a_worker_denial_offers_no_remedy(git_repo: Path, kind: str) -> None:
    outside = _file_event("Edit", git_repo.parent / "outside" / "x.md", agent_id="w1")
    decision = _decide(git_repo, outside if kind == "file" else _bash("rm -rf build", agent_id="w1"))
    assert decision.kind == "deny"
    assert "Ask the user" not in decision.reason


CLI = cli_command(PLUGIN_ROOT)
COMMAND_REMEDY = (
    f'. Ask the user in chat; if they approve this exact action, record it with {CLI} approve --command '
    '"<the exact full command>" --reason "<why>", then retry. Run the approve call with the Bash tool, '
    "on its own, with the command in single quotes if it holds a double quote."
)
PROTECTED_REMEDY = (
    f'. Ask the user in chat; if they approve this exact write, record it with {CLI} approve --path '
    '"<the path named above, as written>" --reason "<why>", then retry. Run the approve call with the '
    "Bash tool, on its own."
)
OUTSIDE_REMEDY = ". No approval lifts this for a file tool. Ask the user in chat to make the change themselves."
STATE_REMEDY = (
    f". Ask the user in chat. No approval lifts this: APM state changes only through the CLI ({CLI}), "
    "never by editing its files."
)


def test_a_command_in_the_state_directory_offers_no_approval(git_repo: Path) -> None:
    state_dir = git_repo / ".apm" / "state"
    state_dir.mkdir(parents=True)
    reason = _decide(git_repo, {**_bash("touch x"), "cwd": str(state_dir)}).reason
    assert "approve --command" not in reason
    assert "No approval lifts this" in reason


def test_a_command_denial_carries_the_command_remedy_in_full(git_repo: Path) -> None:
    assert _decide(git_repo, _bash("rm -rf build")).reason.endswith(COMMAND_REMEDY)


def test_a_protected_denial_carries_the_path_remedy_in_full(git_repo: Path) -> None:
    event = _file_event("Edit", git_repo / "data" / "fleet.db")
    reason = _decide(git_repo, event, protected=("data/*.db",)).reason
    assert reason.endswith("data/fleet.db is a protected path" + PROTECTED_REMEDY)


def test_an_outside_denial_carries_the_outside_remedy_in_full(git_repo: Path) -> None:
    reason = _decide(git_repo, _file_event("Edit", git_repo.parent / "outside" / "x.md")).reason
    assert reason.endswith("is outside the project" + OUTSIDE_REMEDY)


def test_a_state_denial_carries_the_state_remedy_in_full(git_repo: Path) -> None:
    reason = _decide(git_repo, _file_event("Edit", git_repo / ".apm" / "state" / "ledger.json")).reason
    assert reason.endswith("is inside the APM state directory" + STATE_REMEDY)
