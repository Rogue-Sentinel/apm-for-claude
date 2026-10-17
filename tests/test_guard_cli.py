"""Only one plain call of this plugin's own apm_cli.py counts as recording data."""
import sys
from pathlib import Path

import pytest

from apm.guard_cli import is_cli_call

WINDOWS = sys.platform == "win32"
ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()
CALL = f'python "{PLUGIN_CLI}" approve --command "rm -rf build" --reason r'


def _is_call(command: str, cwd: Path = ROOT) -> bool:
    return is_cli_call(command, cwd, WINDOWS)


def test_this_plugins_cli_is_a_call() -> None:
    assert _is_call(CALL)
    assert _is_call(f'python3 "{PLUGIN_CLI}" brief')
    assert _is_call("python scripts/apm_cli.py brief", cwd=ROOT)


def test_a_relative_path_resolves_against_the_cwd() -> None:
    assert not _is_call("python scripts/apm_cli.py brief", cwd=ROOT / "tests")


@pytest.mark.parametrize(
    "command",
    [
        f"{CALL} | cat",
        f"{CALL} &",
        f"{CALL} < input.txt",
        f"({CALL})",
        f"{CALL}\nrm -rf build",
        f"{CALL}\rrm -rf build",
        f"{CALL} > out.txt",
        f"{CALL}; ls",
        f"{CALL} # note",
    ],
)
def test_operators_outside_quotes_rule_the_call_out(command: str) -> None:
    assert not _is_call(command)


@pytest.mark.parametrize(
    "command",
    [
        'python "/c/other/plugin/scripts/apm_cli.py" brief',
        "apm brief",
        "/tmp/apm approve --command x --reason r",
        f'python "{PLUGIN_CLI}" bogus',
        f'python "{PLUGIN_CLI}"',
        f'node "{PLUGIN_CLI}" brief',
    ],
)
def test_other_programs_are_not_calls(command: str) -> None:
    assert not _is_call(command)
