from pathlib import Path

import pytest

from apm.paths import find_project, to_native_path, worktree_relative
from conftest import run_git


def test_find_project_in_plain_repo(git_repo):
    p = find_project(git_repo)
    assert p.main_root == p.worktree_root == git_repo.resolve()
    assert p.profile_path == git_repo.resolve() / ".apm" / "profile.json"
    assert p.ledger_path == git_repo.resolve() / ".apm" / "state" / "ledger.json"
    assert not p.is_initialized


def test_find_project_in_linked_worktree(git_repo):
    run_git(git_repo, "worktree", "add", "../wt", "-b", "x")
    wt = git_repo.parent / "wt"
    p = find_project(wt)
    assert p.main_root == git_repo.resolve()
    assert p.worktree_root == wt.resolve()
    assert p.state_dir == git_repo.resolve() / ".apm" / "state"


def test_find_project_outside_repo_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    assert find_project(plain) is None


@pytest.mark.parametrize(
    "raw", ["/c/repo/a.txt", "C:\\repo\\a.txt", "c:/repo/a.txt", "sub/../a.txt"]
)
def test_to_native_path_forms(raw):
    assert to_native_path(raw, Path("C:/repo"), windows=True) == Path("C:/repo/a.txt")


def test_to_native_path_posix():
    assert to_native_path("/c/x", Path("/repo"), windows=False) == Path("/c/x")
    assert to_native_path("a/../b", Path("/repo"), windows=False) == Path("/repo/b")


def test_worktree_relative(git_repo):
    target = git_repo / "data" / "fleet.db"
    assert worktree_relative(target) == (git_repo, "data/fleet.db")
