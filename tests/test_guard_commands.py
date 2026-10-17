import pytest

from apm.guard_commands import (
    READ_ONLY_PREFIXES,
    check_command,
    destructive_reason,
    protected_reason,
    split_segments,
)

BLOCKED = [
    "rm -rf build",
    "rm -r -f build",
    "rm -fr x",
    "rm -R x",
    "echo hi && rm --recursive x",
    "echo $(rm -rf x)",
    "git push -f",
    "git push origin +main",
    "git push --force-with-lease",
    "git reset --hard HEAD~1",
    "ls; git clean -fdx",
    "git -C sub clean -fd",
    "git branch -D feat",
    "git worktree remove ../wt",
    "git checkout -- .",
    "git restore .",
    "sqlite3 x.db 'DROP TABLE pilots'",
    "sqlite3 x.db 'drop database fleet'",
    "sqlite3 x.db 'TRUNCATE TABLE pilots'",
    "Remove-Item -Path build -Recurse -Force",
    "Remove-Item build -r",
    "rmdir /s /q build",
    "rd /s /q build",
    "del /s /q build",
]
ALLOWED = [
    "rm build/tmp.o",
    "rm -f build/tmp.o",
    "git push origin feat",
    "git reset HEAD file",
    "git branch -d feat",
    "git status",
    "git commit -m 'clean up'",
    "rmdir build",
    "Remove-Item build/tmp.o",
]


@pytest.mark.parametrize("command", BLOCKED)
def test_destructive_commands_are_blocked(command: str) -> None:
    assert check_command(command, [], []) is not None


@pytest.mark.parametrize("command", ALLOWED)
def test_ordinary_commands_are_allowed(command: str) -> None:
    assert check_command(command, [], []) is None


def test_destructive_reason_names_the_pattern() -> None:
    assert "rm" in (destructive_reason("rm -rf build") or "")


def test_split_segments() -> None:
    parts = split_segments("a && b || c; d | e\nf")
    assert parts == ["a", "b", "c", "d", "e", "f"]


def test_split_segments_drops_empty_pieces() -> None:
    assert split_segments("a;; b ;") == ["a", "b"]


def test_read_only_prefixes_include_sqlite_readonly() -> None:
    assert "sqlite3 -readonly " in READ_ONLY_PREFIXES


GLOBS = ["data/*.db"]


@pytest.mark.parametrize(
    "command",
    [
        "cp x data/fleet.db",
        "cp x ./data/fleet.db",
        r"cp x data\fleet.db",
        "cp x /repo/data/fleet.db",
        "cat x > data/fleet.db",
        "cat x >data/fleet.db",
        "python tools/build_fleet_db.py --out data/fleet.db",
        "python tools/build_fleet_db.py --out=data/fleet.db",
        "cp 'unterminated data/fleet.db",
    ],
)
def test_writes_to_protected_paths_are_blocked(command: str) -> None:
    assert check_command(command, GLOBS, []) is not None


@pytest.mark.parametrize(
    "command",
    [
        "cat data/fleet.db",
        "sqlite3 -readonly data/fleet.db 'select 1'",
        "git log -- data/fleet.db",
        "cp x data/sub/fleet.db",
        "echo hi",
    ],
)
def test_reads_and_unrelated_commands_are_allowed(command: str) -> None:
    assert check_command(command, GLOBS, []) is None


def test_protected_reason_ignores_read_only_unless_redirected() -> None:
    assert protected_reason("cat data/fleet.db", GLOBS) is None
    assert protected_reason("cat data/fleet.db > data/other.db", GLOBS) is not None


def test_allowed_prefix_exempts_the_segment() -> None:
    command = "python tools/build_fleet_db.py --out data/fleet.db"
    assert check_command(command, GLOBS, ["python tools/build_fleet_db.py"]) is None


def test_allowed_prefix_does_not_exempt_chained_segments() -> None:
    command = "python tools/build_fleet_db.py && rm -rf build"
    assert check_command(command, GLOBS, ["python tools/build_fleet_db.py"]) is not None


def test_allowed_prefix_does_not_exempt_command_substitution() -> None:
    command = "python tools/build_fleet_db.py $(rm -rf build)"
    assert check_command(command, GLOBS, ["python tools/build_fleet_db.py"]) is not None


def test_allowed_prefix_requires_a_word_boundary() -> None:
    command = "python tools/build_fleet_db.pyevil --out data/fleet.db"
    assert check_command(command, GLOBS, ["python tools/build_fleet_db.py"]) is not None
