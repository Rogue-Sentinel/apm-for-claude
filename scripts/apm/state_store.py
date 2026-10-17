"""Keep the ledger on the apm/state branch, checked out at <main_root>/.apm/state."""
from __future__ import annotations

import subprocess
from pathlib import Path

from apm.ledger import LedgerError, empty_ledger, load_ledger, save_ledger
from apm.paths import Project

STATE_BRANCH = "apm/state"


def _git(args: list[str], cwd: Path) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip()


def _ok(args: list[str], cwd: Path) -> bool:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, encoding="utf-8")
    return done.returncode == 0


def _has_origin(cwd: Path) -> bool:
    return _ok(["remote", "get-url", "origin"], cwd)


def _is_state_worktree(state_dir: Path) -> bool:
    if not (state_dir / ".git").exists():
        return False
    head = subprocess.run(
        ["git", "-C", str(state_dir), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return head.returncode == 0 and head.stdout.strip() == STATE_BRANCH


def _create_orphan(project: Project) -> None:
    root, state = project.main_root, str(project.state_dir)
    _git(["worktree", "add", "--orphan", "-b", STATE_BRANCH, state], root)
    save_ledger(project.ledger_path, empty_ledger())
    _git(["add", "-A"], project.state_dir)
    _git(["commit", "-m", "Start APM state"], project.state_dir)


def init_state(project: Project) -> None:
    if _is_state_worktree(project.state_dir):
        return
    root, state = project.main_root, str(project.state_dir)
    if _has_origin(root):
        _ok(["fetch", "origin", STATE_BRANCH], root)
    if _ok(["rev-parse", "--verify", f"refs/heads/{STATE_BRANCH}"], root):
        _git(["worktree", "add", state, STATE_BRANCH], root)
    elif _ok(["rev-parse", "--verify", f"refs/remotes/origin/{STATE_BRANCH}"], root):
        _git(["worktree", "add", state, "-b", STATE_BRANCH, f"origin/{STATE_BRANCH}"], root)
    else:
        _create_orphan(project)


def load_state(project: Project) -> dict:
    """The ledger; LedgerError when the state worktree is missing, so no one reads it as empty."""
    if not (project.state_dir / ".git").exists():
        raise LedgerError(f"state is not set up at {project.state_dir}; run 'apm setup'")
    return load_ledger(project.ledger_path)


def _push(cwd: Path) -> bool:
    return _ok(["push", "-u", "origin", STATE_BRANCH], cwd)


def commit_state(project: Project, message: str) -> bool:
    cwd = project.state_dir
    _git(["add", "-A"], cwd)
    if _git(["status", "--porcelain"], cwd):
        _git(["commit", "-m", message], cwd)
    return _has_origin(project.main_root) and _push(cwd)
