import json
import shutil
import subprocess
from pathlib import Path

from conftest import run_git

from apm.audit_scan import (
    audit, detect_mode, resolve_base, scan_branches, scan_docs, scan_issues, scan_worktrees,
)


def no_gh(argv, **kwargs):
    """Real git; `gh` is not installed."""
    if argv[0] == "gh":
        raise FileNotFoundError("gh")
    return subprocess.run(argv, **kwargs)


def with_gh(stdout: str, code: int = 0, stderr: str = ""):
    def run(argv, **kwargs):
        if argv[0] != "gh":
            return subprocess.run(argv, **kwargs)
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    return run


def commit(repo: Path, name: str = "work.txt") -> None:
    (repo / name).write_text(name, encoding="utf-8")
    run_git(repo, "add", name)
    run_git(repo, "commit", "-m", f"add {name}")


def add_origin(repo: Path) -> None:
    bare = repo.parent / "origin.git"
    run_git(repo.parent, "init", "--bare", str(bare))
    run_git(repo, "remote", "add", "origin", str(bare))
    run_git(repo, "push", "origin", "main")


def test_mode_fresh_and_existing() -> None:
    assert detect_mode(["README.md", "docs/notes.txt"]) == "fresh"
    assert detect_mode(["README.md", "src/app.py"]) == "existing"


def test_base_falls_back_to_master(git_repo: Path) -> None:
    run_git(git_repo, "branch", "-m", "main", "master")

    base, _ = resolve_base(git_repo, None, no_gh)

    assert base == "master"


def test_given_base_wins_over_the_default(git_repo: Path) -> None:
    run_git(git_repo, "branch", "release")

    base, _ = resolve_base(git_repo, "release", no_gh)

    assert base == "release"


def test_no_origin_is_a_note(git_repo: Path) -> None:
    base, notes = resolve_base(git_repo, None, no_gh)

    assert base == "main"
    assert len(notes) == 1 and notes[0].startswith("could not fetch origin")


def test_no_commits_is_fresh(tmp_path: Path) -> None:
    run_git(tmp_path, "init", "-b", "main")

    assert resolve_base(tmp_path, None, no_gh) == ("", ["no commits yet"])
    found, report = audit(tmp_path, None, with_gh("[]"))
    assert (found.mode, found.base, found.in_flight, report.files) == ("fresh", "", (), ())


def test_branch_ahead_and_dedup_with_origin(git_repo: Path) -> None:
    add_origin(git_repo)
    run_git(git_repo, "checkout", "-b", "feat/x")
    commit(git_repo, "a.txt")
    commit(git_repo, "b.txt")
    run_git(git_repo, "push", "origin", "feat/x")
    run_git(git_repo, "checkout", "-b", "solo", "main")
    commit(git_repo, "c.txt")
    run_git(git_repo, "checkout", "main")

    found = {item.id: item for item in scan_branches(git_repo, "origin/main", no_gh)}

    assert sorted(found) == ["branch:feat/x", "branch:solo"]
    assert found["branch:feat/x"].detail == "2 ahead, also on origin"
    assert found["branch:solo"].detail == "1 ahead"
    assert found["branch:solo"].kind == "branch"


def test_remote_only_branch_is_reported(git_repo: Path) -> None:
    add_origin(git_repo)
    run_git(git_repo, "checkout", "-b", "theirs")
    commit(git_repo)
    run_git(git_repo, "push", "origin", "theirs")
    run_git(git_repo, "checkout", "main")
    run_git(git_repo, "branch", "-D", "theirs")

    found = scan_branches(git_repo, "origin/main", no_gh)

    assert [(item.id, item.detail) for item in found] == [("branch:theirs", "1 ahead, only on origin")]


def test_worktree_dirty_and_missing(git_repo: Path) -> None:
    for name in ("dirty", "clean", "gone"):
        run_git(git_repo, "worktree", "add", str(git_repo.parent / f"wt-{name}"), "-b", name)
    (git_repo.parent / "wt-dirty" / "scratch.txt").write_text("x", encoding="utf-8")
    shutil.rmtree(git_repo.parent / "wt-gone")

    found = {Path(item.id.removeprefix("worktree:")).name: item for item in scan_worktrees(git_repo, no_gh)}

    assert {name: item.detail for name, item in found.items()} == {
        "wt-dirty": "uncommitted changes", "wt-clean": "clean", "wt-gone": "folder missing",
    }
    assert all(item.kind == "worktree" for item in found.values())


def test_docs_found() -> None:
    files = ["docs/plans/a.md", "docs/specs/b.md", "plans/c.md", "docs/plans/x.txt", "docs/guide.md", "src/plans/d.py"]

    found = scan_docs(files)

    assert [(item.id, item.kind) for item in found] == [
        ("plan:docs/plans/a.md", "plan"), ("plan:plans/c.md", "plan"), ("spec:docs/specs/b.md", "spec"),
    ]


def test_issues_and_debt_issues(git_repo: Path) -> None:
    issues = [
        {"number": 3, "title": "Add login", "labels": [{"name": "feature"}]},
        {"number": 5, "title": "[debt] split the parser", "labels": []},
        {"number": 6, "title": "Slow tests", "labels": [{"name": "tech-debt"}]},
        {"number": 8, "title": "[Debt] Old module", "labels": [{"name": "debt"}]},
    ]

    items, debt, notes = scan_issues(git_repo, with_gh(json.dumps(issues)))

    assert [item.id for item in items] == ["issue:3"]
    assert items[0].detail == "feature"
    assert (debt, notes) == ([5, 6, 8], [])


def test_gh_unavailable_is_a_note(git_repo: Path) -> None:
    items, debt, notes = scan_issues(git_repo, no_gh)

    assert (items, debt) == ([], [])
    assert notes == ["open issues not read: gh is not installed"]


def test_gh_not_signed_in_is_a_note(git_repo: Path) -> None:
    _, _, notes = scan_issues(git_repo, with_gh("", 1, "gh auth login required"))

    assert notes == ["open issues not read: gh auth login required"]


def test_audit_measures_at_base_not_the_working_tree(git_repo: Path) -> None:
    (git_repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    run_git(git_repo, "add", "app.py")
    run_git(git_repo, "commit", "-m", "app")
    (git_repo / "later.py").write_text("y = 2\n", encoding="utf-8")

    found, report = audit(git_repo, "main", with_gh("[]"))

    assert (found.mode, found.base) == ("existing", "main")
    assert [f.path for f in report.files] == ["app.py"]
