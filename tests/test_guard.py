import sys
from pathlib import Path

from apm.guard import Decision, decide, to_hook_output
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
BUILD = "python tools/build_fleet_db.py --out data/fleet.db"


def _profile() -> Profile:
    return Profile(framework_version="0.1.0", protected_paths=("data/*.db",))


def _event(repo: Path, tool: str = "Bash", **extra: object) -> dict:
    return {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": BUILD}, **extra}


def _file_event(repo: Path, tool: str, key: str, value: str, cwd: Path | None = None) -> dict:
    return {"tool_name": tool, "cwd": str(cwd or repo), "tool_input": {key: value}}


def _decide(event: dict, repo: Path, allowlist: list | None = None) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, _profile(), allowlist or [], [], WINDOWS)


def test_worker_violation_is_denied(git_repo: Path) -> None:
    decision = _decide(_event(git_repo, agent_id="a1"), git_repo)
    assert decision.kind == "deny"
    assert decision.reason.startswith("APM guard: ")


def test_main_session_violation_is_asked(git_repo: Path) -> None:
    assert _decide(_event(git_repo), git_repo).kind == "ask"


def test_uninitialized_project_is_none(git_repo: Path) -> None:
    project = Project(main_root=git_repo, worktree_root=git_repo)
    assert decide(_event(git_repo), project, None, [], [], WINDOWS).kind == "none"
    assert decide(_event(git_repo), None, _profile(), [], [], WINDOWS).kind == "none"


def test_unrelated_tool_is_none(git_repo: Path) -> None:
    event = _file_event(git_repo, "Read", "file_path", "data/fleet.db")
    assert _decide(event, git_repo).kind == "none"


def test_allowlist_from_active_issue_applies(git_repo: Path) -> None:
    allow = [{"command": "python tools/build_fleet_db.py", "reason": "r"}]
    assert _decide(_event(git_repo), git_repo, allow).kind == "none"


def test_path_allowlist_applies_to_writes(git_repo: Path) -> None:
    event = _file_event(git_repo, "Write", "file_path", "data/fleet.db")
    assert _decide(event, git_repo).kind == "ask"
    allow = [{"path": "data/fleet.db", "reason": "r"}]
    assert _decide(event, git_repo, allow).kind == "none"


def test_malformed_allowlist_entries_are_ignored(git_repo: Path) -> None:
    allow = ["python", {"command": 5}, {"path": None}, {"reason": "only"}]
    assert _decide(_event(git_repo), git_repo, allow).kind == "ask"


def test_relative_write_path_resolves_against_cwd(git_repo: Path) -> None:
    event = _file_event(git_repo, "Edit", "file_path", "fleet.db", cwd=git_repo / "data")
    assert _decide(event, git_repo).kind == "ask"


def test_notebook_edit_uses_notebook_path(git_repo: Path) -> None:
    ok = _file_event(git_repo, "NotebookEdit", "notebook_path", "n.ipynb")
    assert _decide(ok, git_repo).kind == "none"
    bad = _file_event(git_repo, "NotebookEdit", "notebook_path", "data/a.db")
    assert _decide(bad, git_repo).kind == "ask"


def test_powershell_commands_are_checked(git_repo: Path) -> None:
    event = _file_event(git_repo, "PowerShell", "command", "Remove-Item x -Recurse")
    assert _decide(event, git_repo).kind == "ask"


def test_missing_tool_input_field_is_none(git_repo: Path) -> None:
    event = {"tool_name": "Write", "cwd": str(git_repo), "tool_input": {}}
    assert _decide(event, git_repo).kind == "none"


def test_hook_output_shape() -> None:
    out = to_hook_output(Decision("deny", "x"))
    assert out is not None
    assert out["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "x",
    }
    assert to_hook_output(Decision("none")) is None
