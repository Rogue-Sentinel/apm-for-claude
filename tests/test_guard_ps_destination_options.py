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


def _decide(tmp_path: Path, command: str, extra: dict):
    """`decide` for a PowerShell command run from `tmp_path/repo`, with no shell temp root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    event = {"tool_name": "PowerShell", "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    profile = Profile(framework_version="0.3.0", protected_paths=())
    options = {"config_dir": tmp_path / "cfg", "shell_temp": ()}
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


@BOTH
@pytest.mark.parametrize("template", [
    'Copy-Item build\\x.xpl "{O}\\x.xpl" -Force -ErrorAction Stop',
    'Copy-Item build\\x.xpl "{O}\\x.xpl" -Force -EA SilentlyContinue',
    'Copy-Item build\\x.xpl "{O}\\x.xpl" -WarningAction SilentlyContinue',
    'Copy-Item build\\x.xpl "{O}\\x.xpl" -ErrorVariable err',
    'Move-Item a.txt "{O}\\a.txt" -ErrorAction Stop',
    'Copy-Item build\\* "{O}" -Include *.dll',
    'Copy-Item build\\* "{O}" -Filter *.xpl',
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
    segment = 'Copy-Item build\\x.xpl "D:\\X-Plane 12\\x.xpl" -Force -ErrorAction Stop'

    assert write_targets(segment, powershell=True) == ["D:/X-Plane 12/x.xpl"]
