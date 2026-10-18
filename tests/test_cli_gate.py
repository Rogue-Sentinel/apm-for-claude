import json
import subprocess
from pathlib import Path

import pytest

import apm_cli
from apm import cli_gate
from apm.paths import find_project
from apm.state_store import init_state
from conftest import run_git

PLAN = "## Structural acceptance criteria\n- The note `docs/promised.md` exists.\n"
COMMANDS = {"build": "BUILD", "test": "TEST"}


def build_project(repo: Path, monkeypatch, commands: dict, plan: bool = True) -> None:
    """A committed feature branch with a plan, a debt baseline and issue 1 reviewed at HEAD."""
    profile = {"framework_version": "0.3.0", "workflow": {"commands": commands}}
    (repo / ".apm").mkdir()
    (repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (repo / ".gitignore").write_text(".apm/state/\n.apm/tmp/\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "plan.md").write_text(PLAN, encoding="utf-8")
    (repo / "docs" / "promised.md").write_text("promised\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    init_state(find_project(repo))
    apm_cli.main(["debt", "baseline"])
    run_git(repo, "checkout", "-b", "feature")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "work")
    apm_cli.main(["issue", "1", "--title", "T", *(["--plan", "docs/plan.md"] if plan else [])])
    apm_cli.main(["review", "1", "--open", "0", "--criteria-met", "--evidence", "green"])


def fake_run(outcomes: dict[str, int]):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, outcomes.get(command, 0), f"ran {command}\n", None)

    return run


@pytest.fixture
def gated(git_repo: Path, monkeypatch) -> Path:
    build_project(git_repo, monkeypatch, COMMANDS)
    monkeypatch.setattr(cli_gate, "RUN", fake_run({}))
    return git_repo


def test_gate_passes_with_exit_0(gated: Path, capsys) -> None:
    code = apm_cli.main(["gate", "1"])

    assert code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "merge gate: passed"


def test_gate_failure_exits_1_and_prints_the_failing_check(gated: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_gate, "RUN", fake_run({"TEST": 1}))

    code = apm_cli.main(["gate", "1"])

    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL  1  test  ran TEST" in out and out.splitlines()[-1] == "merge gate: 1 failed; stop and ask"


def test_base_option_replaces_the_profile_base(gated: Path, capsys) -> None:
    code = apm_cli.main(["gate", "1", "--base", "no-such-ref"])

    assert code == 1
    assert "FAIL  1  base merged  no-such-ref is not merged into HEAD" in capsys.readouterr().out


def test_no_test_command_is_gate_error_exit_2(git_repo: Path, monkeypatch, capsys) -> None:
    build_project(git_repo, monkeypatch, {"build": "BUILD"})

    code = apm_cli.main(["gate", "1"])

    assert code == 2
    assert "no test command" in capsys.readouterr().err


def test_no_plan_is_gate_error_exit_2(git_repo: Path, monkeypatch, capsys) -> None:
    build_project(git_repo, monkeypatch, COMMANDS, plan=False)

    code = apm_cli.main(["gate", "1"])

    assert code == 2
    assert "no plan recorded" in capsys.readouterr().err


def test_unknown_issue_is_gate_error_exit_2(gated: Path, capsys) -> None:
    code = apm_cli.main(["gate", "9"])

    assert code == 2
    assert "unknown issue: 9" in capsys.readouterr().err
