"""Text in a message argument is data, not a command; text given to an interpreter is code."""
import pytest

from apm.guard_commands import check_command

HEREDOC = "git commit -F - <<'EOF'\nDocument rm -rf risk\ngit clean -fd\nEOF"
DATA = [
    "git commit -m 'Block git clean in the guard'",
    'git commit -m "Document rm -rf risk"',
    'git commit -am "Never git reset --hard"',
    'git commit --message "Drop table support"',
    'git commit --message="Drop table support"',
    'gh pr create --title "Drop table support" --body "..."',
    'gh pr create --title "x" --body "Explain rm -rf and git clean -fd"',
    'apm approve --command make --reason "Avoid rm -rf"',
    'apm question 1 --text "Is rm -rf ok?"',
    'apm resolve 1 0 --answer "git push --force no"',
    'apm task 1 t1 --evidence "ran git clean -n; drop table x"',
    'git commit -m "first" -m "git stash clear"',
    HEREDOC,
    HEREDOC + "\n",
]
CODE = [
    'bash -c "rm -rf x"',
    "sh -c 'rm -rf x'",
    'sqlite3 x.db "DROP TABLE t"',
    'psql -c "drop database d"',
    'cmd /c "rd /s /q x"',
    'powershell -Command "Remove-Item x -Recurse"',
    "python -c \"import shutil; shutil.rmtree('x'); print('drop table t')\"",
    'git commit -m "x" && rm -rf build',
    'git commit -m "$(rm -rf build)"',
    'git commit -m "`rm -rf build`"',
    "git commit -F - <<EOF\n$(rm -rf build)\nEOF",
    "git commit -F - <<'EOF'\nmsg\nEOF\nrm -rf build",
    "bash -c 'echo -m \"x; rm -rf y; echo \"'",
    'git commit -m "msg" ; git clean -fd',
    # A shell takes `-m` and the like as its own options and still runs the `-c` string.
    "bash -c -m 'rm -rf x'",
    'BASH.EXE -c --title "rm -rf x"',
    "/bin/sh -lc -m 'rm -rf x'",
    '"C:/Program Files/Git/bin/bash.exe" -c -m "rm -rf x"',
    "zsh -c --body 'rm -rf x'",
    "dash -c -m 'rm -rf x'",
    "pwsh -Command -m 'Remove-Item x -Recurse'",
    "powershell.exe -c --message 'Remove-Item x -Recurse'",
    r'C:\Windows\System32\cmd.exe /c --text "rd /s /q x"',
    "cmd //c -m 'rd /s /q x'",
    "env X=1 bash -c -m 'rm -rf x'",
    "x=$(sh -c -m 'rm -rf x')",
    "ksh -c -m 'rm -rf x'",
    "mksh -c --body 'rm -rf x'",
]


@pytest.mark.parametrize("command", DATA)
def test_message_arguments_are_data(command: str) -> None:
    assert check_command(command, [], []) is None


@pytest.mark.parametrize("command", CODE)
def test_interpreter_code_stays_blocked(command: str) -> None:
    assert check_command(command, [], []) is not None


def test_message_naming_a_protected_path_is_data() -> None:
    assert check_command('git commit -m "update data/fleet.db"', ["data/*.db"], []) is None
