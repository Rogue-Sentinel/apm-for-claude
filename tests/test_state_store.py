import subprocess
from pathlib import Path

from apm.ledger import empty_ledger, load_ledger
from apm.paths import Project
from apm.state_store import STATE_BRANCH, commit_state, init_state
from conftest import run_git


def _project(repo: Path) -> Project:
    return Project(main_root=repo, worktree_root=repo)


def _out(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip()


def test_init_state_creates_orphan_branch_with_empty_ledger(git_repo: Path) -> None:
    project = _project(git_repo)
    init_state(project)
    assert _out(project.state_dir, "rev-parse", "--abbrev-ref", "HEAD") == STATE_BRANCH
    assert load_ledger(project.ledger_path) == empty_ledger()
    assert "ledger.json" not in _out(git_repo, "ls-tree", "-r", "--name-only", "main")


def test_init_state_is_idempotent(git_repo: Path) -> None:
    project = _project(git_repo)
    init_state(project)
    init_state(project)
    assert _out(git_repo, "rev-list", "--count", STATE_BRANCH) == "1"


def test_init_state_reuses_existing_branch(git_repo: Path) -> None:
    project = _project(git_repo)
    init_state(project)
    first = _out(project.state_dir, "rev-parse", "HEAD")
    run_git(git_repo, "worktree", "remove", "--force", str(project.state_dir))
    init_state(project)
    assert _out(project.state_dir, "rev-parse", "HEAD") == first


def test_init_state_tracks_branch_that_exists_only_on_origin(git_repo: Path, tmp_path: Path) -> None:
    bare = tmp_path / "origin.git"
    run_git(tmp_path, "init", "--bare", str(bare))
    run_git(git_repo, "remote", "add", "origin", str(bare))
    project = _project(git_repo)
    init_state(project)
    commit_state(project, "seed")
    first = _out(project.state_dir, "rev-parse", "HEAD")
    run_git(git_repo, "worktree", "remove", "--force", str(project.state_dir))
    run_git(git_repo, "branch", "-D", STATE_BRANCH)
    init_state(project)
    assert _out(project.state_dir, "rev-parse", "HEAD") == first


def test_commit_state_without_remote_returns_false_and_commits(git_repo: Path) -> None:
    project = _project(git_repo)
    init_state(project)
    (project.state_dir / "note.txt").write_text("hi", encoding="utf-8")
    assert commit_state(project, "add note") is False
    assert _out(project.state_dir, "log", "-1", "--format=%s") == "add note"


def test_commit_state_pushes_to_origin(git_repo: Path, tmp_path: Path) -> None:
    bare = tmp_path / "origin.git"
    run_git(tmp_path, "init", "--bare", str(bare))
    run_git(git_repo, "remote", "add", "origin", str(bare))
    project = _project(git_repo)
    init_state(project)
    (project.state_dir / "note.txt").write_text("hi", encoding="utf-8")
    assert commit_state(project, "add note") is True
    assert _out(git_repo, "ls-remote", "origin", STATE_BRANCH) != ""


def test_commit_state_push_failure_returns_false(git_repo: Path, tmp_path: Path) -> None:
    run_git(git_repo, "remote", "add", "origin", str(tmp_path / "missing.git"))
    project = _project(git_repo)
    init_state(project)
    (project.state_dir / "note.txt").write_text("hi", encoding="utf-8")
    assert commit_state(project, "add note") is False
