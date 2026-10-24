"""Issue 20: routine shell work stays allowed in both sessions, and existing denials keep their reasons."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apm.guard import PREFIX, Decision, decide
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
    def build(cls, tmp_path: Path, repo_name: str = "repo") -> World:
        world = cls(tmp_path / repo_name, tmp_path / "other", tmp_path / "scratch", tmp_path / "cfg")
        world.repo.mkdir()
        world.other.mkdir()
        return world

    def text(self, command: str) -> str:
        """Fill @R @O @S @C with posix paths."""
        for key, path in {"@R": self.repo, "@O": self.other, "@S": self.scratch, "@C": self.cfg}.items():
            command = command.replace(key, path.as_posix())
        return command

    def decide(self, command: str, extra: dict, *, approvals: Sequence[dict] = (),
               allowlist: Sequence[dict] = (), protected: tuple = ()) -> Decision:
        body = {"tool_name": "Bash", "cwd": str(self.repo), "tool_input": {"command": self.text(command)}}
        profile = Profile(framework_version="0.3.0", protected_paths=protected)
        project = Project(main_root=self.repo, worktree_root=self.repo)
        return decide({**body, **extra}, project, profile, list(allowlist), [self.scratch], WINDOWS,
                      list(approvals), config_dir=self.cfg, shell_temp=())


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World.build(tmp_path)


def _stays_allowed(*commands: str):
    return pytest.mark.parametrize("command", commands)


@BOTH
@_stays_allowed("echo x > @S/body.md", "cat > @S/b.md <<'EOF'\nx\nEOF", "mkdir -p @S/probe && cp a @S/probe/",
                "tee @S/log.txt", "cd @S && echo x > f")
def test_writing_the_temp_folder_stays_allowed(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("python x.py >/dev/null", "python x.py 2>/dev/null", "python x.py >/dev/null 2>&1",
                "python x.py > NUL", "pytest -q 2>&1 | tail -5", "echo x >&2", "echo x 1>&2", "tee /dev/stderr",
                "cp x /dev/null", "x=$(git rev-parse HEAD 2>/dev/null)", "x=`git rev-parse HEAD 2>/dev/null`")
def test_a_device_or_a_descriptor_is_not_a_file_write(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("echo x > docs/a.md", "cp a b", "mkdir -p build/x", "cd docs && echo x > a.md",
                "cd docs && cd .. && touch x", "cd sub/dir && git add . && git commit -m x", "git -C docs status",
                "echo x > @R/docs/a.md")
def test_writing_inside_the_project_stays_allowed(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("cd {root}/docs && git add a.md", "echo x > my\\ notes.md")
def test_an_escaped_blank_in_a_bash_path_is_read_as_bash_reads_it(tmp_path: Path, extra: dict, command: str) -> None:
    spaced = World.build(tmp_path, "my repo")
    escaped = spaced.repo.as_posix().replace(" ", "\\ ")

    assert spaced.decide(command.replace("{root}", escaped), extra).kind == "none"


@BOTH
@_stays_allowed("cd \"{root}/docs\" && git add a.md && git commit -m x", "cd \"{native}\\docs\" && git commit -am x",
                "git -C \"{root}\" commit -am x", "echo x > \"{root}/docs/a.md\"")
def test_a_quoted_absolute_path_with_blanks_inside_the_project_stays_allowed(
    tmp_path: Path, extra: dict, command: str
) -> None:
    spaced = World.build(tmp_path, "my repo")
    filled = command.replace("{root}", spaced.repo.as_posix()).replace("{native}", str(spaced.repo))

    assert spaced.decide(filled, extra).kind == "none"


@BOTH
@_stays_allowed("sed -i 's|#include <a>|#include <a>\\n#include <b>|' src/x.cpp", "grep -E 'a|b>c' docs",
                "grep '>' @O/x.md", 'grep "a > b" @O/x.md', 'git commit -m "write > ~/x"', 'echo "a > @O/x"',
                "echo 'see ../x > y'")
def test_a_quoted_pipe_or_redirect_sign_is_not_a_write(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("python - <<'PY'\nif a > b: print(a)\nopen('/x') > 0\nPY",
                "cat > docs/n.md <<'EOF'\n> quoted ../x\nEOF",
                "cat > docs/n.md <<EOF\n> /etc/x is quoted here\nEOF", "python - <<'PY'\nx > /y\nPY",
                "git commit -m \"$(cat <<'EOF'\n> see /etc/x\nEOF\n)\"")
def test_a_heredoc_body_no_shell_runs_is_not_read_as_commands(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("git commit -am x", "git push origin HEAD", "git fetch", "git config --global user.name x",
                "pip install -e .")
def test_programs_that_write_on_their_own_stay_allowed(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@BOTH
@_stays_allowed("cat @O/x.md", "ls ..", "grep -r foo @O", "git -C @O log --oneline", "git -C @O status",
                "cd @O && git status", "cd @O && ls", "cp @O/x.md docs/", "diff @O/a docs/a")
def test_reading_outside_the_project_stays_allowed(world: World, extra: dict, command: str) -> None:
    assert world.decide(command, extra).kind == "none"


@_stays_allowed("gh pr create --title t --body-file @S/b.md", "gh issue list > @S/issues.txt",
                "gh issue create --title t --body \"$(cat <<'EOF'\n> see /etc/x\nEOF\n)\"")
def test_gh_calls_the_main_session_makes_stay_allowed(world: World, command: str) -> None:
    """A worker may not write to GitHub at all (guard_github), so these pins are for the main session."""
    assert world.decide(command, {}).kind == "none"


@pytest.mark.parametrize("extra, expected", [({}, "none"), (WORKER, "deny")], ids=["main", "worker"])
def test_an_approval_lifts_an_outside_write_only_in_the_main_session(
    world: World, extra: dict, expected: str
) -> None:
    command = "echo x >> @O/notes.md"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    approval = {"command": world.text(command), "reason": "r", "cwd": str(world.repo), "expires_at": expires}

    assert world.decide(command, extra, approvals=[approval]).kind == expected


@BOTH
def test_a_plan_allowlist_prefix_lifts_an_outside_write(world: World, extra: dict) -> None:
    allowlist = [{"command": world.text("cp dist/app.zip @O/")}]

    assert world.decide("cp dist/app.zip @O/", extra, allowlist=allowlist).kind == "none"


@pytest.mark.parametrize("extra, command, protected, reason", [
    ({}, "rm -rf @O", (), "destructive command (recursive rm)"),
    (WORKER, "rm -rf @O", (), "destructive command (recursive rm)"),
    ({}, "echo x > data/x.db", ("data/*.db",), "command touches a protected path"),
    (WORKER, "echo x > data/x.db", ("data/*.db",), "command touches a protected path"),
    ({}, "echo x > .apm/state/s.json", (), "command touches a protected path"),
    (WORKER, "echo x > .apm/n.md", (), "workers do not write .apm/ or the Claude settings"),
], ids=["main-rm", "worker-rm", "main-protected", "worker-protected", "main-state", "worker-apm"])
def test_an_existing_denial_keeps_its_reason(
    world: World, extra: dict, command: str, protected: tuple, reason: str
) -> None:
    decision = world.decide(command, extra, protected=protected)

    assert decision.reason.startswith(PREFIX + reason)
