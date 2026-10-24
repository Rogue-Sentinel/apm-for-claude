"""Issue 20: in the PowerShell reading, the names of native Unix tools are read both ways, as a bash cluster and as
PowerShell options that take a value, so `-pv` and `-iv` hide no path."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from apm.guard import decide
from apm.guard_targets import write_targets
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
BOTH = pytest.mark.parametrize("extra", [{}, {"agent_id": "w1"}], ids=["main", "worker"])


def _decide(tmp_path: Path, command: str, extra: dict):
    """`decide` through the PowerShell tool for a command run from `tmp_path/repo`, with no shell temp root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    event = {"tool_name": "PowerShell", "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=())
    options = {"config_dir": tmp_path / "cfg", "shell_temp": ()}
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


@pytest.mark.parametrize("command, target", [
    ("mkdir -pv ../o/d", "../o/d"),
    ("rm -iv ../o/f", "../o/f"),
    ("cp -pv a ../o/b", "../o/b"),
    ("mv -iv a ../o/b", "../o/b"),
    ("cp a D:\\o\\b -EA Stop", "D:/o/b"),
    ("cp a D:\\o\\b -ErrorAction Stop", "D:/o/b"),
])
def test_a_native_tool_names_its_path_read_both_ways(command: str, target: str) -> None:
    assert target in write_targets(command, powershell=True)


def test_a_cmdlet_still_skips_an_option_value() -> None:
    assert write_targets("Copy-Item a D:\\o\\b -EA Stop", powershell=True) == ["D:/o/b"]


@BOTH
@pytest.mark.parametrize("template", ["cp -pv a {O}/b", "cp a {O}\\b -EA Stop"])
def test_a_native_tool_writing_outside_is_denied(tmp_path: Path, extra: dict, template: str) -> None:
    command = template.replace("{O}", str(tmp_path / "other"))

    assert _decide(tmp_path, command, extra).kind == "deny"


@BOTH
def test_a_native_tool_writing_inside_stays_allowed(tmp_path: Path, extra: dict) -> None:
    assert _decide(tmp_path, "cp a docs\\b -EA Stop", extra).kind == "none"
