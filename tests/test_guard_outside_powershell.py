"""Issue 20, PowerShell tool: a cmdlet or redirect that writes outside the project is denied; routine work stays."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])


@dataclass(frozen=True)
class World:
    """A project folder with an `other` folder beside it; placeholders in a command name them."""

    repo: Path
    other: Path
    scratch: Path
    cfg: Path

    @classmethod
    def build(cls, tmp_path: Path) -> World:
        world = cls(tmp_path / "repo", tmp_path / "other", tmp_path / "scratch", tmp_path / "cfg")
        world.repo.mkdir()
        world.other.mkdir()
        return world

    def text(self, command: str) -> str:
        """Fill @R @O @S @C with posix paths and @N with the native path of `other`."""
        names = {"@R": self.repo, "@O": self.other, "@S": self.scratch, "@C": self.cfg}
        for key, path in names.items():
            command = command.replace(key, path.as_posix())
        return command.replace("@N", str(self.other))

    def decide(self, command: str, extra: dict) -> Decision:
        body = {"tool_name": "PowerShell", "cwd": str(self.repo), "tool_input": {"command": self.text(command)}}
        profile = Profile(framework_version="0.3.0", protected_paths=())
        project = Project(main_root=self.repo, worktree_root=self.repo)
        return decide({**body, **extra}, project, profile, [], [self.scratch], WINDOWS, [], config_dir=self.cfg,
                      shell_temp=())


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World.build(tmp_path)


@BOTH
@pytest.mark.parametrize("command", [
    "Set-Content -Path @O/a.md -Value x",
    "Set-Content @O/a.md x",
    "Add-Content @O/a.md x",
    "'x' | Out-File @O/a.md",
    "'x' | Out-File -FilePath @O/a.md -Append",
    "'x' | Tee-Object -FilePath @O/a.md",
    "Copy-Item README.md -Destination @O/r.md",
    "Copy-Item README.md @O/r.md",
    "Move-Item a.txt -Destination @O/a.txt",
    "New-Item -ItemType File -Path @O/n.md",
    "New-Item -ItemType Directory @O/d",
    "Remove-Item @O/old.md",
    "python x.py > @O/out.log",
    "python x.py *> @O/all.log",
    "Set-Location @O; git commit -am x",
    "cd @O; Set-Content f.md x",
    'Set-Content -Path "@N\\a.md" -Value x',
    "Copy-Item README.md @N\\r.md",
])
def test_a_powershell_write_outside_the_project_is_denied(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "deny"


@BOTH
@pytest.mark.parametrize("command", [
    "git fetch origin *>$null",
    "python x.py > $null",
    "python x.py 2>&1",
    "Set-Content -Path docs/a.md -Value x",
    "Copy-Item @O/x.md -Destination docs/",
    "Get-Content @O/x.md",
    "Set-Content -Path @S/body.md -Value x",
    "New-Item -ItemType Directory -Force @S/d",
    "Set-Location docs; Set-Content a.md x",
    'Set-Content -Path docs/a.md -Value "see @O/x"',
])
def test_a_routine_powershell_command_stays_allowed(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"
