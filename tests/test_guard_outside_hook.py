"""Issue 20, through the hook: home-folder forms, the memory folder via `~`, `/tmp`, and a linked worktree.

Nothing here touches the real home folder or the real temp folder: HOME, USERPROFILE and the temp root
are moved under pytest's tmp_path, and a command is only decided, never run."""
import json
import re
from pathlib import Path

import pytest

import apm
import hook_pretooluse
from apm.paths import find_project
from conftest import run_git

WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])


def _init(repo: Path) -> None:
    (repo / ".apm").mkdir(exist_ok=True)
    (repo / ".apm" / "profile.json").write_text(json.dumps({"framework_version": apm.VERSION}), encoding="utf-8")


def _run(cwd: Path, command: str, tool: str = "Bash", **extra: object) -> str:
    event = {"tool_name": tool, "cwd": str(cwd), "tool_input": {"command": command}, **extra}
    code, out = hook_pretooluse.run(json.dumps(event), {})
    assert code == 0
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "none"


def _slug(repo: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(find_project(repo).main_root))


@pytest.fixture
def home_only(tmp_path: Path, monkeypatch) -> None:
    """The home folder and the temp root are under tmp_path; the real `/tmp` rule is left as it is."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(hook_pretooluse.tempfile, "gettempdir", lambda: str(tmp_path / "scratch"))


@pytest.fixture
def isolated(home_only: None, monkeypatch) -> None:
    """Also no shell temp root, so `/tmp` (which holds tmp_path on Linux) opens nothing."""
    monkeypatch.setattr(hook_pretooluse, "SHELL_TEMP_ROOTS", (), raising=False)


@pytest.fixture
def repo(git_repo: Path) -> Path:
    _init(git_repo)
    return git_repo


@BOTH
@pytest.mark.parametrize("tool, command", [
    ("Bash", "echo x >> ~/notes.md"),
    ("Bash", "echo x >> $HOME/notes.md"),
    ("Bash", 'echo x >> "${HOME}/notes.md"'),
    ("Bash", "cp README.md ~/"),
    ("PowerShell", "Add-Content $env:USERPROFILE/notes.md x"),
    ("PowerShell", "Add-Content $HOME\\notes.md x"),
], ids=["tilde", "home", "braced-home", "cp-to-tilde", "userprofile", "home-backslash"])
def test_a_write_under_home_is_denied(isolated: None, repo: Path, extra: dict, tool: str, command: str) -> None:
    assert _run(repo, command, tool, **extra) == "deny"


@BOTH
def test_the_settings_file_under_home_is_denied_for_both(isolated: None, repo: Path, extra: dict) -> None:
    assert _run(repo, "echo {} > ~/.claude/settings.json", **extra) == "deny"


@pytest.mark.parametrize("extra, expected", [({}, "none"), (WORKER, "deny")], ids=["main", "worker"])
def test_the_memory_folder_under_home_is_the_main_sessions_own(
    isolated: None, repo: Path, extra: dict, expected: str
) -> None:
    command = f"echo x >> ~/.claude/projects/{_slug(repo)}/memory/MEMORY.md"

    assert _run(repo, command, **extra) == expected


@pytest.mark.parametrize("target, expected", [("repo", "none"), ("sibling", "deny")])
def test_a_worktree_session_writes_its_main_checkout(
    isolated: None, repo: Path, target: str, expected: str
) -> None:
    run_git(repo, "worktree", "add", ".claude/worktrees/w1", "-b", "w1")
    folder = repo / "docs" if target == "repo" else repo.parent / "sibling"
    command = f"echo x > {(folder / 'a.md').as_posix()}"

    assert _run(repo / ".claude" / "worktrees" / "w1", command) == expected


@BOTH
@pytest.mark.parametrize("command", ["cat ~/.claude/settings.json", "ls ~"])
def test_reading_home_stays_allowed(isolated: None, repo: Path, extra: dict, command: str) -> None:
    assert _run(repo, command, **extra) == "none"


@BOTH
@pytest.mark.parametrize("command", ["echo x > /tmp/body.md", "cat > /tmp/b.md <<'EOF'\nx\nEOF"])
def test_a_write_under_slash_tmp_is_allowed(home_only: None, repo: Path, extra: dict, command: str) -> None:
    assert _run(repo, command, **extra) == "none"
