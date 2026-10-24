"""Issue 20: a PowerShell copy or move whose destination is followed by an option that takes a value."""
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


def _decide(tmp_path: Path, command: str, extra: dict, tool: str = "PowerShell"):
    """`decide` for a command run from `tmp_path/repo`, with no shell temp root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=())
    options = {"config_dir": tmp_path / "cfg", "shell_temp": ()}
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


@BOTH
@pytest.mark.parametrize("template", [
    'Copy-Item build\\x.dll "{O}\\x.dll" -Force -ErrorAction Stop',
    'Copy-Item build\\x.dll "{O}\\x.dll" -Force -EA SilentlyContinue',
    'Copy-Item build\\x.dll "{O}\\x.dll" -WarningAction SilentlyContinue',
    'Copy-Item build\\x.dll "{O}\\x.dll" -ErrorVariable err',
    'Move-Item a.txt "{O}\\a.txt" -ErrorAction Stop',
    'Copy-Item build\\* "{O}" -Include *.dll',
    'Copy-Item build\\* "{O}" -Filter *.dll',
    'Move-Item a.txt "{O}" -Exclude b',
])
def test_a_destination_outside_is_denied_before_an_option_with_a_value(
    tmp_path: Path, extra: dict, template: str
) -> None:
    command = template.replace("{O}", str(tmp_path / "other"))

    assert _decide(tmp_path, command, extra).kind == "deny"


@BOTH
@pytest.mark.parametrize("command", ["Copy-Item a docs\\b -ErrorAction Stop", "Copy-Item a -ErrorAction Stop"])
def test_a_destination_inside_stays_allowed_before_an_option_with_a_value(
    tmp_path: Path, extra: dict, command: str
) -> None:
    assert _decide(tmp_path, command, extra).kind == "none"


def test_write_targets_gives_the_destination_before_an_option_with_a_value() -> None:
    segment = 'Copy-Item build\\x.dll "D:\\Shared Apps\\x.dll" -Force -ErrorAction Stop'

    assert write_targets(segment, powershell=True) == ["D:/Shared Apps/x.dll"]


@pytest.mark.parametrize("command, target", [
    ("mkdir -pv /c/other/d", "/c/other/d"),
    ("rm -iv /c/other/f", "/c/other/f"),
    ("cp -pv a /c/other/b", "/c/other/b"),
    ("mv -iv a /c/other/b", "/c/other/b"),
    ("touch -ea /c/other/f", "/c/other/f"),
])
def test_a_bash_option_cluster_is_no_value_option(command: str, target: str) -> None:
    """`-pv` is `-p -v` and `-iv` is `-i -v` in bash; only PowerShell reads them as options that take a value."""
    assert write_targets(command, powershell=False) == [target]


@BOTH
@pytest.mark.parametrize("template", ["mkdir -pv {O}/d", "cp -pv a {O}/b"])
def test_a_bash_option_cluster_before_an_outside_path_is_denied(tmp_path: Path, extra: dict, template: str) -> None:
    command = template.replace("{O}", (tmp_path / "other").as_posix())

    assert _decide(tmp_path, command, extra, tool="Bash").kind == "deny"
