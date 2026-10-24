"""Issue 20: the profile's `write_roots` open folders outside the project for shell commands, and only those."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from apm.guard import _REMEDIES, Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])


def _decide(
    tmp_path: Path, command: str, extra: dict, write_roots: Sequence[str], *, tool: str = "Bash", **options: object
) -> Decision:
    """`decide` from `tmp_path/repo`. No shell temp root (`/tmp` holds tmp_path on Linux), so outside cases hold there."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    key = "file_path" if tool == "Write" else "command"
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {key: command}, **extra}
    profile = Profile(framework_version="0.3.0", write_roots=tuple(write_roots))
    options = {"config_dir": tmp_path / "cfg", "shell_temp": (), "home": tmp_path / "home", **options}
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


@BOTH
@pytest.mark.parametrize("command", [
    "echo x > {V}/build.log",
    "cmake --build {V}/c2 > {V}/c2.log 2>&1",
    "mkdir -p {V}",
    "cp a {V}/",
], ids=["redirect", "build-log", "mkdir", "copy-into"])
def test_a_named_folder_opens_for_shell_writes(tmp_path: Path, extra: dict, command: str) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, command.format(V=vab.as_posix()), extra, [vab.as_posix()])

    assert decision.kind == "none"


@BOTH
def test_the_home_form_opens_a_folder_under_home(tmp_path: Path, extra: dict) -> None:
    vab = tmp_path / "home" / "vab"

    decision = _decide(tmp_path, f"echo x > {vab.as_posix()}/build.log", extra, ["~/vab"])

    assert decision.kind == "none"


@BOTH
def test_a_relative_entry_is_read_from_the_checkout(tmp_path: Path, extra: dict) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, f"echo x > {vab.as_posix()}/build.log", extra, ["../vab"])

    assert decision.kind == "none"


@BOTH
@pytest.mark.parametrize("place", ["vab2/x", "other/x"], ids=["sibling-prefix", "unnamed-folder"])
def test_only_the_named_folder_opens(tmp_path: Path, extra: dict, place: str) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, f"echo x > {(tmp_path / place).as_posix()}", extra, [vab.as_posix()])

    assert decision.kind == "deny"


@BOTH
def test_write_roots_do_not_open_the_file_tools(tmp_path: Path, extra: dict) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, str(vab / "x.md"), extra, [vab.as_posix()], tool="Write")

    assert decision.kind == "deny"
    assert "is outside the project" in decision.reason
    assert decision.reason.endswith(_REMEDIES["outside"]) == (not extra)


@BOTH
def test_write_roots_do_not_lift_another_denial(tmp_path: Path, extra: dict) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, f"rm -rf {vab.as_posix()}/x", extra, [vab.as_posix()])

    assert decision.kind == "deny"
    assert "destructive command (recursive rm)" in decision.reason


def test_the_main_session_denial_names_write_roots(tmp_path: Path) -> None:
    reason = _decide(tmp_path, f"echo x > {(tmp_path / 'other').as_posix()}/x", {}, []).reason

    assert reason.endswith(_REMEDIES["shell_outside"])
    assert _REMEDIES["shell_outside"].endswith(
        " If the project writes there routinely, the user can list the folder under write_roots in .apm/profile.json."
    )


def test_a_worker_denial_names_no_remedy(tmp_path: Path) -> None:
    reason = _decide(tmp_path, f"echo x > {(tmp_path / 'other').as_posix()}/x", WORKER, []).reason

    assert "write_roots" not in reason


@BOTH
@pytest.mark.parametrize("command", [
    "Copy-Item -Path a -Destination {V}\\",
    'Copy-Item -Destination "{V}\\" -Path a',
], ids=["last-word", "quoted"])
def test_a_powershell_destination_ending_in_a_backslash_is_the_named_folder(
    tmp_path: Path, extra: dict, command: str
) -> None:
    vab = tmp_path / "vab"

    decision = _decide(tmp_path, command.format(V=vab), extra, [vab.as_posix()], tool="PowerShell")

    assert decision.kind == "none"
