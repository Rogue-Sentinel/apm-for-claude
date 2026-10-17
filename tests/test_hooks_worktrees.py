"""The guard works from linked worktrees and the state worktree, not just the main checkout."""
import json
from pathlib import Path

import pytest

import hook_pretooluse
from apm.paths import find_project
from apm.state_store import init_state
from conftest import run_git


def _init_main(repo: Path) -> None:
    (repo / ".apm").mkdir(exist_ok=True)
    profile = {"framework_version": "0.1.0", "protected_paths": ["data/*.db"]}
    (repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")


def _run(cwd: Path, command: str, **extra) -> str:
    event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd), **extra}
    code, out = hook_pretooluse.run(json.dumps(event), {})
    assert code == 0
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "none"


@pytest.fixture
def agent_worktree(git_repo: Path) -> Path:
    _init_main(git_repo)
    run_git(git_repo, "worktree", "add", ".claude/worktrees/agent-1", "-b", "agent-1")
    return git_repo / ".claude" / "worktrees" / "agent-1"


def _commands(main: Path) -> list[str]:
    return ["rm -rf build", f"rm {(main / 'data' / 'fleet.db').as_posix()}", "rm -rf ../../../data"]


def test_worker_in_linked_worktree_is_guarded(agent_worktree: Path, git_repo: Path) -> None:
    assert not (agent_worktree / ".apm" / "profile.json").exists()
    for command in _commands(git_repo):
        assert _run(agent_worktree, command, agent_id="w1") == "deny", command


def test_worker_in_linked_worktree_is_guarded_by_the_state_mirror(git_repo: Path) -> None:
    init_state(find_project(git_repo))
    _init_main(git_repo)
    (git_repo / ".apm" / "profile.json").replace(git_repo / ".apm" / "state" / "profile.json")
    run_git(git_repo, "worktree", "add", "../agent-2", "-b", "agent-2")
    assert _run(git_repo.parent / "agent-2", "rm -rf build", agent_id="w1") == "deny"


@pytest.fixture
def state_dir(git_repo: Path) -> Path:
    _init_main(git_repo)
    init_state(find_project(git_repo))
    return git_repo / ".apm" / "state"


def test_write_in_state_dir_is_denied_for_worker_and_asked_for_main(state_dir: Path) -> None:
    assert _run(state_dir, "rm x", agent_id="w1") == "deny"
    assert _run(state_dir, "rm x") == "ask"


def test_read_in_state_dir_is_allowed(state_dir: Path) -> None:
    assert _run(state_dir, "cat ledger.json", agent_id="w1") == "none"
    assert _run(state_dir, "cat ledger.json") == "none"
