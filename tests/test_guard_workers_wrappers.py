"""A worker's apm state change is caught behind a wrapper or a substitution, and plain reads stay allowed."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
CLI = f'python "{(Path(__file__).resolve().parent.parent / "scripts" / "apm_cli.py").as_posix()}"'


def _worker(repo: Path, command: str) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    event = {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": command}, "agent_id": "w1"}
    return decide(event, project, Profile(framework_version="0.2.0"), [], [], WINDOWS)


WRAPPED_MUTATIONS = [
    "env apm note 1",
    "sudo apm issue 3 --status done",
    "xargs apm note 1",
    "x=$(apm review 1)",
    "(apm github close 3)",
    "command apm task 1 2",
    "env FOO=1 apm note 1",
    "sudo -u bob apm note 1",
    "echo `apm review 1`",
    "if true; then apm note 1; fi",
    "exec apm gate",
    "time apm init",
    "xargs -I {} apm note {}",
    "nohup apm issue 1 --status done",
    "apm.exe note 1",
    "APM.EXE note 1",
    r"C:\bin\apm.exe note 1",
    "env apm debt baseline",
    "(apm debt)",
    "ls | xargs apm task 1 t1",
    'x=$(python "/c/p/scripts/apm_cli.py" note 1)',
    "env python3 scripts/apm_cli.py github close 3",
    "bash -c 'FOO=1 apm note 1'",
    'env "apm" "note" 1',
    "env apm -- note 1",
]
# Runners no wrapper list named; the re-review found each one allowed.
UNLISTED_RUNNERS = [
    "eval 'apm note 1'",
    "iex 'apm note 1'",
    'Invoke-Expression "apm github close 3"',
    "cmd /c call apm note 1",
    "cmd /c start /b apm note 1",
    "timeout 30s apm issue 3 --status done",
    "timeout 1m apm note 1",
    "watch -n1 apm note 1",
    "strace -f apm note 1",
    "flock /tmp/l apm note 1",
    "uv run apm note 1",
    "busybox apm note 1",
    "parallel apm note ::: 1",
    "apm.cmd note 1",
    "Apm.Bat review 1",
    "/usr/local/bin/apm debt baseline",
]
# An expansion that is empty at run time sits between `apm` and its subcommand: the shell still runs `apm note 1`.
EMPTY_EXPANSIONS = [
    "apm $EMPTY note 1",
    "apm ${X} issue 3 --status done",
    "apm $(true) note 1",
    "apm `true` review 1",
    "apm debt $(true) baseline",
]


@pytest.mark.parametrize("command", [*WRAPPED_MUTATIONS, *UNLISTED_RUNNERS, *EMPTY_EXPANSIONS])
def test_worker_cannot_change_apm_state_behind_a_wrapper(git_repo: Path, command: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and "APM state" in decision.reason


# An `apm` word followed by a state subcommand is denied anywhere, so these text mentions are denied on purpose.
TEXT_MENTIONS = ["echo apm note", "echo env apm note 1", "ls apm note", "grep apm issue docs"]


@pytest.mark.parametrize("command", TEXT_MENTIONS)
def test_a_text_mention_of_an_apm_state_change_is_denied_and_points_to_the_grep_tool(
        git_repo: Path, command: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and "Grep tool" in decision.reason


def test_a_commit_message_that_names_an_apm_state_change_is_allowed(git_repo: Path) -> None:
    assert _worker(git_repo, 'git commit -m "Workers (apm note) are denied"').kind == "none"


def test_a_commit_message_that_runs_an_apm_state_change_is_denied(git_repo: Path) -> None:
    decision = _worker(git_repo, 'git commit -m "$(apm note 1)"')

    assert decision.kind == "deny" and "APM state" in decision.reason


WRAPPED_READS = [
    "env apm brief",
    "sudo apm metrics",
    "x=$(apm coverage)",
    "(apm audit)",
    "env apm debt check",
    "xargs apm debt check --base main",
    "git add scripts/apm note.txt",
    "cd scripts/apm",
    "apm brief",
    "apm metrics scripts/apm/guard_workers.py",
    "apm coverage",
    "apm audit scripts",
    "apm debt check --base main",
    "timeout 30s apm metrics",
    "python scripts/apm/note.py issue",
    "cat scripts/apm/guard.py",
    "apm brief && echo note",
    "env FOO=apm echo note",
    "cat apm_cli.py.bak note",
]


@pytest.mark.parametrize("command", WRAPPED_READS)
def test_worker_may_still_read_through_a_wrapper(git_repo: Path, command: str) -> None:
    assert _worker(git_repo, command).kind == "none"
