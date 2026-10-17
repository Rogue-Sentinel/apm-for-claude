"""Commands that once slipped past the guard, and the ones that must stay allowed."""
import time

import pytest

import apm.guard_commands as gc
from apm.guard_commands import check_command, destructive_reason

SPACED = "C:/Users/darby/source/repos/VirtualAirline Plugin for XP12"
GIT_DESTRUCTIVE = ("reset --hard", "clean -fdx", "push --force", "worktree remove ../wt", "checkout -- .")
GIT_PREFIXES = (
    f'git -C "{SPACED}"',
    f"git -C '{SPACED}'",
    f'git -C="{SPACED}"',
    f'git --git-dir="{SPACED}/.git"',
    f'git --work-tree="{SPACED}" -c core.x=1',
    f'git -c "user.name=A B" -C "{SPACED}"',
)

BLOCKED = [
    *(f"{prefix} {action}" for prefix in GIT_PREFIXES for action in GIT_DESTRUCTIVE),
    "git.exe reset --hard",
    "GIT.EXE -C sub clean -fd",
    "find . -name '*.db' | xargs rm",
    "ls data/*.db | xargs rm -f",
    "ls | xargs -0 /bin/rm",
    "dir | xargs del",
    "gci | xargs Remove-Item",
    "git push origin --delete main",
    "git push -d origin main",
    "git push origin :main",
    "git push --mirror",
    "git branch --delete --force feat",
    "git branch -d -f feat",
    "git branch -df feat",
    "cmd //c rd //s //q build",
    "cmd //c del //s //q build",
    "dropdb mydb",
    'rm "-rf" build',
    "rm '-r' build",
    'rm -r"f" build',
    'git "reset" --hard',
]
ALLOWED = [
    "git push origin feat",
    "git push -u origin feat",
    "git push origin feat:main",
    "git branch -d feat",
    "git branch -d feat-fix",
    "rm build/tmp.o",
    "rm -f build/tmp.o",
    f'git -C "{SPACED}" status',
    f'git -C "{SPACED}" log --oneline',
    "ls | xargs echo",
    "rd //q build",
]


@pytest.mark.parametrize("command", BLOCKED)
def test_former_bypasses_are_blocked(command: str) -> None:
    assert check_command(command, [], []) is not None


@pytest.mark.parametrize("command", ALLOWED)
def test_ordinary_commands_stay_allowed(command: str) -> None:
    assert check_command(command, [], []) is None


@pytest.mark.parametrize("unit", ["-c x=y ", "-c -c ", "--foo ", '-C "a" ', "-c 'a b' "])
def test_git_option_prefix_is_linear(unit: str) -> None:
    command = "git " + unit * 40 + "status"
    start = time.perf_counter()
    destructive_reason(command)
    assert time.perf_counter() - start < 0.5


@pytest.mark.parametrize("marker", ["$(rm -rf build)", "`rm -rf build`", "<(rm -rf build)", ">(rm -rf build)"])
def test_substitutions_are_never_exempt(marker: str) -> None:
    prefix = "python tools/build_fleet_db.py"
    assert check_command(f"{prefix} {marker}", [], [prefix]) is not None


@pytest.mark.parametrize("marker", ["<(cat x)", ">(tee y)"])
def test_process_substitution_cancels_an_allowed_prefix(marker: str) -> None:
    prefix = "python tools/build_fleet_db.py"
    command = f"{prefix} --out data/fleet.db {marker}"
    assert check_command(command, ["data/*.db"], [prefix]) is not None


def test_all_read_only() -> None:
    assert gc.all_read_only("cat ledger.json && git status | grep x")
    assert not gc.all_read_only("cat ledger.json && rm x")
    assert not gc.all_read_only("cat a > b")
