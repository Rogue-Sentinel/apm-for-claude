"""The ratchet's guard rules: workers never write .apm/** or run `debt baseline`."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.guard_cli import SUBCOMMANDS, is_cli_call
from apm.paths import Project
from apm.profile import WORKER_PROTECTED, Profile

WINDOWS = sys.platform == "win32"
ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()
CLI = f'python "{PLUGIN_CLI}"'


def _decide(event: dict, repo: Path, allowlist: list | None = None, approvals: list | None = None) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, Profile(framework_version="0.2.0"), allowlist or [], [], WINDOWS, approvals or [])


def _bash(repo: Path, command: str, tool: str = "Bash", **extra: object) -> dict:
    return {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}


def _write(repo: Path, path: str, tool: str = "Write", **extra: object) -> dict:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"tool_name": tool, "cwd": str(repo), "tool_input": {key: path}, **extra}


def test_worker_protected_paths_cover_the_apm_directory() -> None:
    assert WORKER_PROTECTED == (".apm/**",)


def test_the_new_subcommands_are_cli_calls() -> None:
    assert {"metrics", "debt", "coverage"} <= set(SUBCOMMANDS)
    assert is_cli_call(f"{CLI} debt check", ROOT, WINDOWS)
    assert is_cli_call(f"{CLI} metrics --json", ROOT, WINDOWS)


@pytest.mark.parametrize("path", [".apm/debt.json", ".apm/profile.json", ".apm/anything/else.txt"])
@pytest.mark.parametrize("tool", ["Write", "Edit", "NotebookEdit"])
def test_worker_cannot_write_apm_files(git_repo: Path, path: str, tool: str) -> None:
    decision = _decide(_write(git_repo, path, tool, agent_id="w1"), git_repo)

    assert decision.kind == "deny" and ".apm" in decision.reason


def test_worker_cannot_write_apm_files_by_absolute_path(git_repo: Path) -> None:
    target = (git_repo / ".apm" / "debt.json").as_posix()

    assert _decide(_write(git_repo, target, agent_id="w1"), git_repo).kind == "deny"


def test_worker_cannot_write_apm_files_from_a_subdirectory(git_repo: Path) -> None:
    (git_repo / "sub").mkdir()
    event = {**_write(git_repo, "../.apm/debt.json", agent_id="w1"), "cwd": str(git_repo / "sub")}

    assert _decide(event, git_repo).kind == "deny"


def test_an_allowlist_does_not_open_apm_files_to_a_worker(git_repo: Path) -> None:
    allow = [{"path": ".apm/**", "reason": "r"}, {"path": ".apm/debt.json", "reason": "r"}]

    assert _decide(_write(git_repo, ".apm/debt.json", agent_id="w1"), git_repo, allow).kind == "deny"


def test_an_approval_does_not_open_apm_files_to_a_worker(git_repo: Path) -> None:
    approvals = [{"path": ".apm/**", "reason": "r", "cwd": str(git_repo), "expires_at": "2999-01-01T00:00:00+00:00"}]

    assert _decide(_write(git_repo, ".apm/debt.json", agent_id="w1"), git_repo, approvals=approvals).kind == "deny"


def test_main_session_may_write_apm_files(git_repo: Path) -> None:
    assert _decide(_write(git_repo, ".apm/debt.json"), git_repo).kind == "none"


@pytest.mark.parametrize(
    "command",
    [
        "echo {} > .apm/debt.json",
        "rm .apm/debt.json",
        "cp x.json .apm/profile.json",
        "sed -i s/20/30/ .apm/debt.json",
        "python -c \"open('.apm/debt.json','w')\" && echo .apm/debt.json",
        "tee .apm/debt.json",
        "git checkout main -- .apm/debt.json",
    ],
)
def test_worker_cannot_write_apm_files_by_command(git_repo: Path, command: str) -> None:
    assert _decide(_bash(git_repo, command, agent_id="w1"), git_repo).kind == "deny"


def test_worker_cannot_write_apm_files_by_powershell(git_repo: Path) -> None:
    event = _bash(git_repo, "Set-Content .apm/debt.json '{}'", "PowerShell", agent_id="w1")

    assert _decide(event, git_repo).kind == "deny"


def test_a_command_allowlist_does_not_open_apm_files_to_a_worker(git_repo: Path) -> None:
    allow = [{"command": "echo", "reason": "r"}]

    assert _decide(_bash(git_repo, "echo {} > .apm/debt.json", agent_id="w1"), git_repo, allow).kind == "deny"


@pytest.mark.parametrize("command", ["cat .apm/debt.json", "grep errors .apm/debt.json", "git diff main -- .apm/debt.json"])
def test_worker_may_read_apm_files(git_repo: Path, command: str) -> None:
    assert _decide(_bash(git_repo, command, agent_id="w1"), git_repo).kind == "none"


def test_main_session_may_write_apm_files_by_command(git_repo: Path) -> None:
    assert _decide(_bash(git_repo, "echo {} > .apm/debt.json"), git_repo).kind == "none"


DEBT_BASELINE = [
    f"{CLI} debt baseline",
    f'{CLI} debt baseline --accept "needed"',
    "apm debt baseline",
    "python scripts/apm_cli.py debt baseline",
    "python scripts/APM_CLI.PY debt baseline",
    "echo hi && apm debt baseline",
    '"/c/plugins/apm/bin/apm" debt baseline --accept x',
    "apm -- debt baseline",
    "apm debt  baseline",
    "apm 'debt' baseline",
]


@pytest.mark.parametrize("command", DEBT_BASELINE)
def test_worker_cannot_run_debt_baseline(git_repo: Path, command: str) -> None:
    decision = _decide(_bash(git_repo, command, agent_id="w1"), git_repo)

    assert decision.kind == "deny" and "APM state" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        f"{CLI} debt check",
        f"{CLI} debt check --base main",
        f"{CLI} metrics",
        f"{CLI} metrics --json src",
        f"{CLI} coverage",
        "apm debt check",
        "apm metrics",
        "echo debt baseline",
        "apm debt checks",
    ],
)
def test_worker_may_run_debt_check_and_metrics(git_repo: Path, command: str) -> None:
    assert _decide(_bash(git_repo, command, agent_id="w1"), git_repo).kind == "none"


@pytest.mark.parametrize("command", DEBT_BASELINE[:2])
def test_main_session_debt_baseline_is_exempt_cli_call(git_repo: Path, command: str) -> None:
    assert _decide(_bash(git_repo, command), git_repo).kind == "none"
