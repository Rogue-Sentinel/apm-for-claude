"""A line continuation joins two lines into one command, so the guard reads them as one."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.guard_commands import check_command
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
BACKSLASH_NEWLINE = chr(92) + chr(10)
BACKSLASH_CRLF = chr(92) + chr(13) + chr(10)
BACKTICK_NEWLINE = "`" + chr(10)


def _worker(repo: Path, command: str) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    event = {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": command}, "agent_id": "w1"}
    return decide(event, project, Profile(framework_version="0.2.0"), [], [], WINDOWS)


WORKER_SPLITS = [
    ("gh api repos/o/r/issues " + BACKSLASH_NEWLINE + "-X POST -f title=x", "GitHub"),
    ("gh api " + BACKSLASH_NEWLINE + "repos/o/r/issues -f title=x", "GitHub"),
    ("gh " + BACKSLASH_CRLF + "issue create", "GitHub"),
    ("python scripts/apm_cli.py " + BACKSLASH_NEWLINE + "note 4 --text x", "APM state"),
    ("apm " + BACKTICK_NEWLINE + "note 4", "APM state"),
]


@pytest.mark.parametrize(("command", "reason"), WORKER_SPLITS)
def test_a_worker_command_split_by_a_continuation_is_still_denied(
        git_repo: Path, command: str, reason: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and reason in decision.reason


DESTRUCTIVE_SPLITS = [
    "rm " + BACKSLASH_NEWLINE + "-rf build",
    "rm -r " + BACKSLASH_CRLF + "-f build",
    "git push " + BACKSLASH_NEWLINE + "--force origin main",
    "git reset " + BACKSLASH_NEWLINE + "--hard",
    "Remove-Item build " + BACKTICK_NEWLINE + "-Recurse -Force",
    "Remove-Item build `" + chr(13) + chr(10) + "-Recurse -Force",
]


@pytest.mark.parametrize("command", DESTRUCTIVE_SPLITS)
def test_a_destructive_command_split_by_a_continuation_is_denied(command: str) -> None:
    reason = check_command(command, [], [])

    assert reason is not None and "destructive" in reason


def test_a_backtick_substitution_across_lines_never_makes_its_contents_exempt() -> None:
    command = "echo " + BACKTICK_NEWLINE + "rm -rf x" + chr(10) + "`"

    assert check_command(command, [], ["echo"]) is not None


def test_a_continued_line_of_a_harmless_command_is_still_allowed() -> None:
    assert check_command("ls -la " + BACKSLASH_NEWLINE + "build", [], []) is None
