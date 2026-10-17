"""hooks/run.sh launches each hook and fails closed when python cannot run it."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from apm.paths import find_project
from apm.state_store import init_state
from conftest import run_git

ROOT = Path(__file__).resolve().parent.parent
WRAPPER = ROOT / "hooks" / "run.sh"
EVENT = json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}, "agent_id": "w1"})


def _bash(windows: bool) -> str:
    """Git Bash on Windows (never WSL's bash.exe); plain bash elsewhere."""
    if not windows:
        return "bash"
    for parent in Path(shutil.which("git")).resolve().parents:
        if (parent / "bin" / "bash.exe").is_file():
            return str(parent / "bin" / "bash.exe")
    return "bash"


def _fake_python(tmp_path: Path, code: int) -> Path:
    folder = tmp_path / f"fake-python-{code}"
    folder.mkdir()
    fake = folder / "python"
    fake.write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8", newline="\n")
    fake.chmod(0o755)
    return folder


def _run(cwd: Path, hook: str, python_dir: Path, event: str = EVENT) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": str(python_dir) + os.pathsep + os.environ["PATH"]}
    return subprocess.run(
        [_bash(os.name == "nt"), str(WRAPPER), hook], cwd=cwd, input=event, env=env,
        capture_output=True, text=True, encoding="utf-8",
    )


def _profile(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"framework_version": "0.1.0"}', encoding="utf-8")


def _at_toplevel(repo: Path) -> Path:
    _profile(repo / ".apm" / "profile.json")
    return repo


def _at_main_root(repo: Path) -> Path:
    _profile(repo / ".apm" / "profile.json")
    run_git(repo, "worktree", "add", "../wt", "-b", "wt")
    return repo.parent / "wt"


def _in_state_mirror(repo: Path) -> Path:
    init_state(find_project(repo))
    _profile(repo / ".apm" / "state" / "profile.json")
    run_git(repo, "worktree", "add", "../wt", "-b", "wt")
    return repo.parent / "wt"


@pytest.mark.parametrize("layout", [_at_toplevel, _at_main_root, _in_state_mirror])
def test_failing_python_blocks_in_an_initialized_project(git_repo: Path, tmp_path: Path, layout) -> None:
    done = _run(layout(git_repo), "pretooluse", _fake_python(tmp_path, 1))
    assert done.returncode == 2
    assert "APM guard" in done.stderr


def test_failing_python_is_silent_outside_an_initialized_project(git_repo: Path, tmp_path: Path) -> None:
    done = _run(git_repo, "pretooluse", _fake_python(tmp_path, 1))
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_session_start_never_blocks(git_repo: Path, tmp_path: Path) -> None:
    _at_toplevel(git_repo)
    for code in (1, 2):
        assert _run(git_repo, "session_start", _fake_python(tmp_path, code)).returncode == 0


def test_python_exit_2_passes_through(git_repo: Path, tmp_path: Path) -> None:
    assert _run(git_repo, "pretooluse", _fake_python(tmp_path, 2)).returncode == 2


def test_real_python_output_passes_through(git_repo: Path) -> None:
    _at_toplevel(git_repo)
    event = json.dumps({**json.loads(EVENT), "cwd": str(git_repo)})
    done = _run(git_repo, "pretooluse", Path(sys.executable).parent, event)
    assert done.returncode == 0
    assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_wrapper_has_lf_line_endings() -> None:
    assert b"\r" not in WRAPPER.read_bytes()
