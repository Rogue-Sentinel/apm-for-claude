"""Issue 20: where a shell write lands (Reach.resolve), a hook with no home folder, and a PowerShell `"C:\\x\\"` copy."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

import apm
import hook_pretooluse
from apm.guard import decide
from apm.guard_outside import SHELL_TEMP_ROOTS, Reach
from apm.paths import Project, to_native_path
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])
CWD = Path("/w")


def _reach(home: Path | None = Path("/h")) -> Reach:
    return Reach(Project(main_root=CWD, worktree_root=CWD), (), None, home, False, WINDOWS, False)


@pytest.mark.parametrize("word, expected", [
    ("~/x", "/h/x"),
    ("~", "/h"),
    ("$HOME/x", "/h/x"),
    ("${HOME}/x", "/h/x"),
    ("$env:USERPROFILE/x", "/h/x"),
    ("$ENV:userprofile/x", "/h/x"),
    ("$env:HOME/x", "/h/x"),
    ("$Home/x", "/h/x"),
    ("$USERPROFILE/x", "/h/x"),
    ("${USERPROFILE}/x", "/h/x"),
    ("${env:USERPROFILE}/x", "/h/x"),
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


def _decide(tmp_path: Path, tool: str, command: str, extra: dict, **options: object):
    """`decide` from `tmp_path/repo`; no shell temp root (`/tmp` holds tmp_path on Linux) unless `options` give one."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=())
    options = {"config_dir": tmp_path / "cfg", "shell_temp": (), **options}
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


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


@BOTH
def test_a_bash_read_holding_an_escaped_quote_stays_allowed(tmp_path: Path, extra: dict) -> None:
    """Bash reads `\\"` as an escaped quote; the PowerShell reading would cut at it and invent a `>14}` target."""
    other = tmp_path / "other"
    command = f"cd \"{other.as_posix()}\" && python -c \"print(\\\"it's\\\"); print(f'{{1:>14}}')\""

    assert _decide(tmp_path, "Bash", command, extra).kind == "none"


@pytest.mark.parametrize("extra, place, expected", [
    ({}, "notes.md", "deny"),
    (WORKER, "notes.md", "deny"),
    ({}, "memory", "none"),
    (WORKER, "memory", "deny"),
], ids=["main-home", "worker-home", "main-memory", "worker-memory"])
def test_git_bashs_userprofile_is_the_home_folder(tmp_path: Path, extra: dict, place: str, expected: str) -> None:
    home = tmp_path / "home"
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(tmp_path / "repo"))
    target = f".claude/projects/{slug}/memory/MEMORY.md" if place == "memory" else place
    command = f'echo x > "$USERPROFILE/{target}"'

    decision = _decide(tmp_path, "Bash", command, extra, home=home, config_dir=home / ".claude")

    assert decision.kind == expected


@BOTH
@pytest.mark.parametrize("tool, command, expected", [
    ("PowerShell", "Set-Content /tmp/x.txt y", "deny"),
    ("Bash", "echo y > /tmp/x.txt", "none"),
], ids=["powershell", "bash"])
def test_slash_tmp_is_a_temp_folder_only_for_bash(
    tmp_path: Path, extra: dict, tool: str, command: str, expected: str
) -> None:
    """Git Bash mounts `/tmp` on the temp folder; to PowerShell it is a real `C:\\tmp`, outside."""
    decision = _decide(tmp_path, tool, command, extra, shell_temp=SHELL_TEMP_ROOTS)

    assert decision.kind == expected
