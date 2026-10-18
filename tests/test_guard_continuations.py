"""A line continuation joins two lines into one command, so the guard reads them as one.

The guard reads a command twice: split as `main` splits it, and with continued lines joined. Either reading
denying denies the command, so the joining can never make the guard weaker than `main`.
"""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.guard_commands import check_command
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
BACKSLASH, BACKTICK, NEWLINE = chr(92), chr(96), chr(10)
BACKSLASH_NEWLINE = BACKSLASH + NEWLINE
BACKSLASH_CRLF = BACKSLASH + chr(13) + NEWLINE
BACKTICK_NEWLINE = BACKTICK + NEWLINE


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
    "Remove-Item build `" + chr(13) + NEWLINE + "-Recurse -Force",
]


@pytest.mark.parametrize("command", DESTRUCTIVE_SPLITS)
def test_a_destructive_command_split_by_a_continuation_is_denied(command: str) -> None:
    reason = check_command(command, [], [])

    assert reason is not None and "destructive" in reason


SUBSTITUTION_ACROSS_LINES = "echo " + BACKTICK_NEWLINE + "rm -rf x" + NEWLINE + "`"


def test_a_backtick_substitution_across_lines_never_makes_its_contents_exempt() -> None:
    assert check_command(SUBSTITUTION_ACROSS_LINES, [], ["echo"]) is not None


HARMLESS_CONTINUATION = "ls -la " + BACKSLASH_NEWLINE + "build"


def test_a_continued_line_of_a_harmless_command_is_still_allowed() -> None:
    assert check_command(HARMLESS_CONTINUATION, [], []) is None


# An even run of escapes before a newline is literal: the newline ends the command, and the next line is its own.
ESCAPED_BACKSLASH_NEWLINE = BACKSLASH * 2 + NEWLINE
ESCAPED_BACKTICK_NEWLINE = BACKTICK * 2 + NEWLINE
ESCAPED_NEWLINE_WRITES = [
    "cat x " + ESCAPED_BACKSLASH_NEWLINE + "cp y data/fleet.db",
    "cat x " + ESCAPED_BACKTICK_NEWLINE + "Copy-Item y data/fleet.db",
]


@pytest.mark.parametrize("command", ESCAPED_NEWLINE_WRITES)
def test_a_protected_write_after_an_escaped_newline_is_denied(command: str) -> None:
    assert check_command(command, ("data/*.db",), ()) is not None


ESCAPED_NEWLINE_DELETE = "npm test " + ESCAPED_BACKSLASH_NEWLINE + "rm -rf build"


def test_a_destructive_command_after_an_escaped_newline_is_not_covered_by_an_allowed_prefix() -> None:
    reason = check_command(ESCAPED_NEWLINE_DELETE, [], ["npm test"])

    assert reason is not None and "destructive" in reason


ESCAPED_NEWLINE_STATE_WRITE = "cat x " + ESCAPED_BACKSLASH_NEWLINE + "cp y .apm/state/ledger.json"


def test_a_worker_state_write_after_an_escaped_newline_is_denied(git_repo: Path) -> None:
    decision = _worker(git_repo, ESCAPED_NEWLINE_STATE_WRITE)

    assert decision.kind == "deny" and ".apm/" in decision.reason


ODD_RUN_CONTINUATION = "ls -la " + BACKSLASH * 3 + NEWLINE + "build"


def test_an_odd_run_of_backslashes_still_continues_a_harmless_command() -> None:
    assert check_command(ODD_RUN_CONTINUATION, [], []) is None


# Lines that a shell may not join at all; `main` read the second line as its own command, and so must the guard.
UNJOINED_LINES = [
    "cat x # n " + BACKSLASH_NEWLINE + "cp y {target}",  # a comment ending in a backslash
    "cat x " + BACKSLASH + BACKTICK_NEWLINE + "cp y {target}",  # a backslash-escaped backtick
    "cat x " + BACKSLASH_NEWLINE + "Copy-Item y {target}",  # no continuation in PowerShell
]
MAIN_UNJOINED = [shape.format(target="data/fleet.db") for shape in UNJOINED_LINES]
WORKER_UNJOINED = [shape.format(target=".apm/state/ledger.json") for shape in UNJOINED_LINES]
CONTINUED_DELETE = "npm test " + BACKSLASH_NEWLINE + "rm -rf build"


@pytest.mark.parametrize("command", MAIN_UNJOINED)
def test_a_protected_write_on_a_line_that_may_not_be_joined_is_denied(command: str) -> None:
    reason = check_command(command, ("data/*.db",), ())

    assert reason is not None and "protected path" in reason


@pytest.mark.parametrize("command", WORKER_UNJOINED)
def test_a_worker_state_write_on_a_line_that_may_not_be_joined_is_denied(git_repo: Path, command: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and ".apm/" in decision.reason


def test_a_continued_delete_is_not_covered_by_the_allowed_prefix_of_the_line_before() -> None:
    reason = check_command(CONTINUED_DELETE, [], ["npm test"])

    assert reason is not None and "destructive" in reason
