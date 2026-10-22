"""Issue 20: a Bash command that writes outside the project is denied, as a Write or Edit there is."""
from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from apm.guard import PREFIX, Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])
OUTSIDE_REASON = PREFIX + "command writes outside the project and the temp folders ("


@dataclass(frozen=True)
class World:
    """A project folder with an `other` folder beside it; placeholders in a command name them."""

    repo: Path
    other: Path
    scratch: Path
    cfg: Path

    @classmethod
    def build(cls, tmp_path: Path, repo_name: str = "repo") -> World:
        world = cls(tmp_path / repo_name, tmp_path / "other", tmp_path / "scratch", tmp_path / "cfg")
        world.repo.mkdir()
        world.other.mkdir()
        return world

    @property
    def memory(self) -> Path:
        return self.cfg / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(self.repo)) / "memory"

    def text(self, command: str) -> str:
        """Fill @R @O @S @C @M with posix paths and @N with the native path of `other`; @M2 is `memory2`."""
        names = {"@R": self.repo, "@O": self.other, "@S": self.scratch, "@C": self.cfg, "@M": self.memory}
        for key, path in names.items():
            command = command.replace(key, path.as_posix())
        return command.replace("@N", str(self.other))

    def decide(self, command: str, *, tool: str = "Bash", extra: dict | None = None, cwd: Path | None = None,
               approvals: Sequence[dict] = (), allowlist: Sequence[dict] = (), protected: tuple = ()) -> Decision:
        body = {"tool_name": tool, "cwd": str(cwd or self.repo), "tool_input": {"command": self.text(command)}}
        profile = Profile(framework_version="0.3.0", protected_paths=protected)
        project = Project(main_root=self.repo, worktree_root=self.repo)
        return decide({**body, **(extra or {})}, project, profile, list(allowlist), [self.scratch], WINDOWS,
                      list(approvals), config_dir=self.cfg)


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World.build(tmp_path)


@BOTH
@pytest.mark.parametrize("command", [
    "echo x >> @O/notes.md",
    "echo x>>@O/notes.md",
    "python x.py 2>@O/err.log",
    "python x.py &>@O/out.log",
    "echo x > ../outside.md",
    "cat > @O/body.md <<'EOF'\nx\nEOF",
    "git diff > @O/d.diff",
    'echo x > "@O/with space.md"',
    "pytest -q > @O/t.log 2>&1",
    "echo x > @O/a.md\r\n",
])
def test_a_redirect_outside_the_project_is_denied(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra=extra).kind == "deny"


@BOTH
@pytest.mark.parametrize("command", [
    "echo x | tee -a @O/a.md",
    "cp README.md @O/",
    "cp -r src @O/src",
    "cp -t @O a b",
    "mv a.txt @O/a.txt",
    "mkdir -p @O/new",
    "touch @O/t",
    "rm @O/old.md",
    "sed -i 's/a/b/' @O/f.md",
    "sed -i -e 's/a/b/' @O/f.md",
    "cp README.md ../../x.md",
    "touch /tmp_x.txt",
])
def test_a_program_writing_outside_the_project_is_denied(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra=extra).kind == "deny"


@BOTH
@pytest.mark.parametrize("command", [
    "git -C @O commit -am x",
    "git -C ../other add .",
    "cd @O && git commit -am x",
    "cd @O && git fetch origin",
    "cd @O && echo x > f.md",
    "cd .. && touch x",
    "cd @O; cp a b",
])
def test_git_or_cd_into_another_checkout_is_denied(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra=extra).kind == "deny"


@pytest.mark.parametrize("extra, expected", [({}, "none"), (WORKER, "deny")], ids=["main", "worker"])
@pytest.mark.parametrize("command", ["echo x >> @M/MEMORY.md", "cp notes.md @M/", "echo x | tee -a @M/MEMORY.md"])
def test_the_memory_folder_opens_only_for_the_main_session(
    world: World, extra: dict, expected: str, command: str
) -> None:
    assert world.decide(command, extra=extra).kind == expected


@BOTH
@pytest.mark.parametrize("command", [
    "echo {} > @C/settings.json",
    "echo x >> @C/CLAUDE.md",
    "echo x >> @C/projects/C--other-repo/memory/MEMORY.md",
    "echo x >> @M2/x.md",
    "mkdir -p @M",
])
def test_the_rest_of_the_config_dir_stays_denied(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra=extra).kind == "deny"


@pytest.mark.parametrize("extra, offers", [({}, True), (WORKER, False)], ids=["main", "worker"])
def test_an_outside_denial_names_the_target_and_offers_a_command_approval(
    world: World, extra: dict, offers: bool
) -> None:
    reason = world.decide("echo x >> @O/notes.md", extra=extra).reason

    assert reason.startswith(OUTSIDE_REASON)
    assert "notes.md" in reason
    assert ('approve --command "<the exact full command>"' in reason) == offers
    assert ("Ask the user" in reason) == offers
