"""Issue 20: where a shell write lands (Reach.resolve), a hook with no home folder, and a PowerShell `"C:\\x\\"` copy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import apm
import hook_pretooluse
from apm.guard import decide
from apm.guard_outside import Reach
from apm.paths import Project, to_native_path
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])
CWD = Path("/w")


def _reach(home: Path | None = Path("/h")) -> Reach:
    return Reach(Project(main_root=CWD, worktree_root=CWD), (), None, home, False, WINDOWS)


@pytest.mark.parametrize("word, expected", [
    ("~/x", "/h/x"),
    ("~", "/h"),
    ("$HOME/x", "/h/x"),
    ("${HOME}/x", "/h/x"),
    ("$env:USERPROFILE/x", "/h/x"),
    ("$ENV:userprofile/x", "/h/x"),
    ("$env:HOME/x", "/h/x"),
    ("$Home/x", "/h/x"),
])
def test_home_forms_resolve_to_home(word: str, expected: str) -> None:
    assert _reach().resolve(word, CWD) == to_native_path(expected, CWD, WINDOWS)


@pytest.mark.parametrize("word", ["~user/x", "$TMPDIR/x", "$Tx/y", "$HOMEx/y"])
def test_other_names_stay_relative(word: str) -> None:
    assert _reach().resolve(word, CWD) == to_native_path(f"/w/{word}", CWD, WINDOWS)


def test_without_a_home_a_tilde_is_a_name() -> None:
    assert _reach(home=None).resolve("~/x", CWD) == to_native_path("/w/~/x", CWD, WINDOWS)


def _no_home() -> Path:
    raise RuntimeError("Could not determine home directory.")


def test_a_hook_without_a_home_still_guards(git_repo: Path, tmp_path: Path, monkeypatch) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text(json.dumps({"framework_version": apm.VERSION}), encoding="utf-8")
    monkeypatch.setattr(hook_pretooluse.tempfile, "gettempdir", lambda: str(tmp_path / "scratch"))
    monkeypatch.setattr(hook_pretooluse, "SHELL_TEMP_ROOTS", ())
    monkeypatch.setattr(Path, "home", staticmethod(_no_home))
    command = f"echo x > {(tmp_path / 'outside').as_posix()}/a.md"
    event = {"tool_name": "Bash", "cwd": str(git_repo), "tool_input": {"command": command}}

    code, out = hook_pretooluse.run(json.dumps(event), {"CLAUDE_CONFIG_DIR": str(tmp_path / "cfg")})

    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert (code, reason.startswith("APM guard: command writes outside the project")) == (0, True)


def _decide(tmp_path: Path, tool: str, command: str, extra: dict):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=())
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], config_dir=tmp_path / "cfg")


@BOTH
@pytest.mark.parametrize("source", ["README.md", '"docs\\"'], ids=["plain-source", "quoted-folder-source"])
def test_a_powershell_copy_to_a_quoted_native_folder_outside_is_denied(
    tmp_path: Path, extra: dict, source: str
) -> None:
    """Bash reads `\\"` as an escaped quote, so with a quoted folder as the source only the PowerShell reading
    sees the destination."""
    other = tmp_path / "other"

    decision = _decide(tmp_path, "PowerShell", f'Copy-Item {source} "{other}\\"', extra)

    assert decision.kind == "deny"


@BOTH
def test_a_copy_into_a_folder_outside_names_the_folder(tmp_path: Path, extra: dict) -> None:
    other = tmp_path / "other"
    command = f"cp README.md {other.as_posix()}/"

    reason = _decide(tmp_path, "Bash", command, extra).reason

    expected = to_native_path(other.as_posix(), tmp_path, WINDOWS)
    assert reason.startswith(f"APM guard: command writes outside the project and the temp folders ({expected}): ")
