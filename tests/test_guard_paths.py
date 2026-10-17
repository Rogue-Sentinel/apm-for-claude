from pathlib import Path

from apm.guard_paths import check_write
from apm.paths import Project
from apm.state_store import init_state
from conftest import run_git

GLOBS = ("data/*.db",)


def _project(repo: Path) -> Project:
    return Project(main_root=repo, worktree_root=repo)


def test_protected_file_is_blocked(git_repo: Path) -> None:
    reason = check_write(git_repo / "data" / "fleet.db", _project(git_repo), GLOBS, [], [])
    assert reason is not None
    assert "data/fleet.db" in reason


def test_protected_file_in_linked_worktree_is_blocked(git_repo: Path) -> None:
    worktree = git_repo / ".claude" / "worktrees" / "w1"
    run_git(git_repo, "worktree", "add", str(worktree), "-b", "w1")
    reason = check_write(worktree / "data" / "fleet.db", _project(git_repo), GLOBS, [], [])
    assert reason is not None


def test_star_does_not_cross_directories(git_repo: Path) -> None:
    target = git_repo / "data" / "sub" / "x.db"
    assert check_write(target, _project(git_repo), GLOBS, [], []) is None


def test_double_star_crosses_directories(git_repo: Path) -> None:
    target = git_repo / "secrets" / "a" / "b.txt"
    assert check_write(target, _project(git_repo), ("secrets/**",), [], []) is not None


def test_git_dir_is_protected_by_default_globs(git_repo: Path) -> None:
    target = git_repo / ".git" / "config"
    assert check_write(target, _project(git_repo), (".git/**",), [], []) is not None


def test_allowlisted_protected_file_passes(git_repo: Path) -> None:
    target = git_repo / "data" / "fleet.db"
    assert check_write(target, _project(git_repo), GLOBS, ["data/fleet.db"], []) is None


def test_outside_repo_is_blocked(git_repo: Path) -> None:
    outside = git_repo.parent / "outside" / "x.txt"
    assert check_write(outside, _project(git_repo), GLOBS, [], []) is not None


def test_temp_root_is_allowed(git_repo: Path) -> None:
    scratch = git_repo.parent / "scratch"
    assert check_write(scratch / "x.txt", _project(git_repo), GLOBS, [], [scratch]) is None


def test_sibling_of_temp_root_is_blocked(git_repo: Path) -> None:
    scratch = git_repo.parent / "scratch"
    other = git_repo.parent / "scratch2" / "x.txt"
    assert check_write(other, _project(git_repo), GLOBS, [], [scratch]) is not None


def test_state_dir_is_always_protected(git_repo: Path) -> None:
    project = _project(git_repo)
    init_state(project)
    assert check_write(project.state_dir / "ledger.json", project, (), [], []) is not None


def test_ordinary_source_file_passes(git_repo: Path) -> None:
    assert check_write(git_repo / "src" / "app.py", _project(git_repo), GLOBS, [], []) is None
