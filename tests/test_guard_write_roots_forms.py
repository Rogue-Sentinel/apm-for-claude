"""Issue 20, Task 6 review: how `write_roots` entries are spelled and resolved, and where PowerShell lines join."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.guard_outside import OUTSIDE_REASON, Reach
from apm.guard_targets import command_readings
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])
TOOLS = pytest.mark.parametrize("tool", ["Bash", "PowerShell"])


def _decide(
    tmp_path: Path, command: str, extra: dict, write_roots: Sequence[str], tool: str, repo: Path | None = None
) -> Decision:
    """`decide` from `repo` (default `tmp_path/repo`), with home `tmp_path/home` and no shell temp root."""
    repo = repo or tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", write_roots=tuple(write_roots))
    options = {"config_dir": tmp_path / "cfg", "shell_temp": (), "home": tmp_path / "home"}
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [tmp_path / "scratch"], WINDOWS, [], **options)


@BOTH
@TOOLS
@pytest.mark.parametrize("entry", ["~\\out", "$HOME\\out", "$env:USERPROFILE\\out", "${env:USERPROFILE}\\out"])
def test_a_home_entry_written_with_backslashes_opens_the_folder_under_home(
    tmp_path: Path, extra: dict, tool: str, entry: str
) -> None:
    out_dir = tmp_path / "home" / "out"

    decision = _decide(tmp_path, f"echo x > {out_dir.as_posix()}/build.log", extra, [entry], tool)

    assert decision.kind == "none"


@BOTH
@TOOLS
def test_an_absolute_entry_written_with_backslashes_still_opens(tmp_path: Path, extra: dict, tool: str) -> None:
    out_dir = tmp_path / "out"
    entry = str(out_dir).replace("/", "\\")

    decision = _decide(tmp_path, f"echo x > {out_dir.as_posix()}/build.log", extra, [entry], tool)

    assert decision.kind == "none"


def test_a_share_entry_written_with_backslashes_names_the_share_folder(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = Project(main_root=repo, worktree_root=repo)
    reach = Reach(project, (), None, None, False, WINDOWS, True, ("\\\\server\\share\\out",))

    assert reach.named_roots() == [Path("//server/share/out")]


@BOTH
@TOOLS
@pytest.mark.parametrize("entry", ["~/source/repos", "~/source", "~", "..", "../..", "."])
def test_an_entry_holding_the_main_checkout_opens_nothing(tmp_path: Path, extra: dict, tool: str, entry: str) -> None:
    """`~/source/repos` holds this checkout and every other repository; it is ignored, so a sibling stays outside."""
    repos = tmp_path / "home" / "source" / "repos"
    sibling = repos / "other" / "f.md"

    decision = _decide(tmp_path, f"echo x > {sibling.as_posix()}", extra, [entry], tool, repos / "apm")

    assert decision.kind == "deny"
    assert OUTSIDE_REASON in decision.reason


@BOTH
@TOOLS
def test_a_folder_beside_the_main_checkout_still_opens(tmp_path: Path, extra: dict, tool: str) -> None:
    repos = tmp_path / "home" / "source" / "repos"
    command = f"echo x > {(repos / 'out').as_posix()}/f"

    decision = _decide(tmp_path, command, extra, ["~/source/repos/out"], tool, repos / "apm")

    assert decision.kind == "none"


@BOTH
def test_a_powershell_backslash_at_a_line_end_does_not_join_the_next_line(tmp_path: Path, extra: dict) -> None:
    """PowerShell has no `\\` continuation: the second line is its own command, and it writes outside."""
    out_dir = tmp_path / "out"
    command = f"Copy-Item a {out_dir}\\\nSet-Content ..\\o\\f x"

    decision = _decide(tmp_path, command, extra, [out_dir.as_posix()], "PowerShell")

    assert decision.kind == "deny"
    assert OUTSIDE_REASON in decision.reason


@BOTH
def test_a_bash_backslash_at_a_line_end_still_joins_the_next_line(tmp_path: Path, extra: dict) -> None:
    decision = _decide(tmp_path, "cp a \\\n../o/f", extra, [], "Bash")

    assert decision.kind == "deny"
    assert OUTSIDE_REASON in decision.reason


def test_the_powershell_reading_joins_only_backtick_lines() -> None:
    """A PowerShell `\\` at a line end is a path's last separator, read as `/`; the newline after it cuts."""
    assert command_readings("a C:\\out\\\nb `\nc", powershell=True) == [["a C:\\out/", "b ` c"]]


def test_the_bash_reading_joins_backslash_lines() -> None:
    assert command_readings("a \\\nb") == [["a  b"]]
