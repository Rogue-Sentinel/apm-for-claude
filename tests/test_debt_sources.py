import subprocess
from pathlib import Path

import pytest

from apm.debt_sources import run_source
from apm.debt_store import DebtError
from apm.standard_config import DebtSource

OUTPUT = "Functions over 15 lines of logic: 41 of 900\nFiles over 200 lines of logic: 7 of 120\n"


def _fake(stdout: str, code: int = 1):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, code, stdout=stdout, stderr="")

    run.calls = calls
    return run


def _source(**numbers: str) -> DebtSource:
    default = {"long_functions": r"over 15 lines of logic: (\d+)"}
    return DebtSource("checker", "python tools/check.py", numbers or default)


def test_run_source_reads_numbers_ignoring_exit_code(tmp_path: Path) -> None:
    run = _fake(OUTPUT, code=1)
    source = _source(long_functions=r"Functions over 15 lines of logic: (\d+)",
                     long_files=r"Files over 200 lines of logic: (\d+)")

    assert run_source(source, tmp_path, run) == {"long_functions": 41, "long_files": 7}


def test_run_source_runs_the_command_in_a_shell_in_the_root(tmp_path: Path) -> None:
    run = _fake(OUTPUT)

    run_source(_source(), tmp_path, run)

    command, kwargs = run.calls[0]
    assert command == "python tools/check.py"
    assert kwargs["shell"] is True and kwargs["cwd"] == tmp_path and kwargs["capture_output"] is True


def test_run_source_no_match_raises(tmp_path: Path) -> None:
    source = _source(long_functions=r"Nothing here: (\d+)")

    with pytest.raises(DebtError, match="checker: no match for long_functions"):
        run_source(source, tmp_path, _fake(OUTPUT))


def test_run_source_a_group_that_is_not_a_whole_number_raises(tmp_path: Path) -> None:
    source = _source(long_functions=r"Functions over 15 lines of logic: (\w+)")

    with pytest.raises(DebtError, match="checker: long_functions is not a whole number"):
        run_source(source, tmp_path, _fake("Functions over 15 lines of logic: many"))


def test_run_source_a_command_that_cannot_start_raises(tmp_path: Path) -> None:
    def broken(command, **kwargs):
        raise OSError("no shell")

    with pytest.raises(DebtError, match="checker: cannot run"):
        run_source(_source(), tmp_path, broken)


def test_run_source_really_runs_a_command(tmp_path: Path) -> None:
    command = "python -c \"print('errors: 3'); raise SystemExit(1)\""
    source = DebtSource("echo", command, {"errors": r"errors: (\d+)"})

    assert run_source(source, tmp_path) == {"errors": 3}


def test_run_source_passes_its_timeout(tmp_path: Path) -> None:
    run = _fake(OUTPUT)
    source = DebtSource("checker", "python tools/check.py", {"n": r"logic: (\d+)"}, timeout=42)

    run_source(source, tmp_path, run)

    assert run.calls[0][1]["timeout"] == 42


def test_run_source_timeout_raises(tmp_path: Path) -> None:
    def hung(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    source = DebtSource("checker", "python tools/check.py", {"n": r"logic: (\d+)"}, timeout=7)

    with pytest.raises(DebtError, match=r"checker: timed out after 7s"):
        run_source(source, tmp_path, hung)
