import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide, to_hook_output
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
PLUGIN_CLI = (Path(__file__).resolve().parent.parent / "scripts" / "apm_cli.py").as_posix()
BUILD = "python tools/build_fleet_db.py --out data/fleet.db"


def _profile() -> Profile:
    return Profile(framework_version="0.1.0", protected_paths=("data/*.db",))


def _event(repo: Path, tool: str = "Bash", **extra: object) -> dict:
    return {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": BUILD}, **extra}


def _file_event(repo: Path, tool: str, key: str, value: str, cwd: Path | None = None) -> dict:
    return {"tool_name": tool, "cwd": str(cwd or repo), "tool_input": {key: value}}


def _decide(event: dict, repo: Path, allowlist: list | None = None, approvals: list | None = None) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, _profile(), allowlist or [], [], WINDOWS, approvals or [])


def test_worker_violation_is_denied(git_repo: Path) -> None:
    decision = _decide(_event(git_repo, agent_id="a1"), git_repo)
    assert decision.kind == "deny"
    assert decision.reason.startswith("APM guard: ")


def test_main_session_violation_is_denied_with_instructions(git_repo: Path) -> None:
    decision = _decide(_event(git_repo), git_repo)
    assert decision.kind == "deny"
    assert decision.reason.startswith("APM guard: ")
    assert "Ask the user in chat" in decision.reason and " approve --command " in decision.reason
    assert '/scripts/apm_cli.py" approve' in decision.reason and "\n" not in decision.reason
    assert '--command "<the exact full command>"' in decision.reason


def test_worker_reason_has_no_approval_instructions(git_repo: Path) -> None:
    decision = _decide(_event(git_repo, agent_id="a1"), git_repo)
    assert "approve" not in decision.reason


def test_uninitialized_project_is_none(git_repo: Path) -> None:
    project = Project(main_root=git_repo, worktree_root=git_repo)
    assert decide(_event(git_repo), project, None, [], [], WINDOWS).kind == "none"
    assert decide(_event(git_repo), None, _profile(), [], [], WINDOWS).kind == "none"


def test_unrelated_tool_is_none(git_repo: Path) -> None:
    event = _file_event(git_repo, "Read", "file_path", "data/fleet.db")
    assert _decide(event, git_repo).kind == "none"


def test_allowlist_from_active_issue_applies(git_repo: Path) -> None:
    allow = [{"command": "python tools/build_fleet_db.py", "reason": "r"}]
    assert _decide(_event(git_repo), git_repo, allow).kind == "none"


def test_path_allowlist_applies_to_writes(git_repo: Path) -> None:
    event = _file_event(git_repo, "Write", "file_path", "data/fleet.db")
    assert _decide(event, git_repo).kind == "deny"
    allow = [{"path": "data/fleet.db", "reason": "r"}]
    assert _decide(event, git_repo, allow).kind == "none"


def test_malformed_allowlist_entries_are_ignored(git_repo: Path) -> None:
    allow = ["python", {"command": 5}, {"path": None}, {"reason": "only"}]
    assert _decide(_event(git_repo), git_repo, allow).kind == "deny"


def test_relative_write_path_resolves_against_cwd(git_repo: Path) -> None:
    event = _file_event(git_repo, "Edit", "file_path", "fleet.db", cwd=git_repo / "data")
    assert _decide(event, git_repo).kind == "deny"


def test_notebook_edit_uses_notebook_path(git_repo: Path) -> None:
    ok = _file_event(git_repo, "NotebookEdit", "notebook_path", "n.ipynb")
    assert _decide(ok, git_repo).kind == "none"
    bad = _file_event(git_repo, "NotebookEdit", "notebook_path", "data/a.db")
    assert _decide(bad, git_repo).kind == "deny"


def test_powershell_commands_are_checked(git_repo: Path) -> None:
    event = _file_event(git_repo, "PowerShell", "command", "Remove-Item x -Recurse")
    assert _decide(event, git_repo).kind == "deny"


def test_missing_tool_input_field_is_none(git_repo: Path) -> None:
    event = {"tool_name": "Write", "cwd": str(git_repo), "tool_input": {}}
    assert _decide(event, git_repo).kind == "none"


def test_hook_output_shape() -> None:
    out = to_hook_output(Decision("deny", "x"))
    assert out is not None
    assert out["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "x",
    }
    assert to_hook_output(Decision("none")) is None


def test_command_globs_expand_against_the_event_cwd(git_repo: Path) -> None:
    (git_repo / "data").mkdir()
    (git_repo / "data" / "fleet.db").write_text("x")
    event = _file_event(git_repo, "Bash", "command", "rm *.db", cwd=git_repo / "data")
    assert _decide(event, git_repo).kind == "deny"
    elsewhere = _file_event(git_repo, "Bash", "command", "rm *.db", cwd=git_repo)
    assert _decide(elsewhere, git_repo).kind == "none"


def _command(cwd: Path, command: str, tool: str = "Bash", **extra: object) -> dict:
    return {"tool_name": tool, "cwd": str(cwd), "tool_input": {"command": command}, **extra}


def _state(repo: Path) -> Path:
    state = repo / ".apm" / "state"
    state.mkdir(parents=True)
    return state


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_writing_command_in_state_dir_is_a_violation(git_repo: Path, tool: str) -> None:
    state = _state(git_repo)
    assert _decide(_command(state, "rm x", tool, agent_id="a1"), git_repo).kind == "deny"
    assert _decide(_command(state, "rm x", tool), git_repo).kind == "deny"
    assert _decide(_command(state / "sub", "touch y", tool), git_repo).kind == "deny"


@pytest.mark.parametrize("command", ["cat ledger.json", "git status && git log --oneline | grep x", "ls"])
def test_read_only_command_in_state_dir_is_allowed(git_repo: Path, command: str) -> None:
    state = _state(git_repo)
    assert _decide(_command(state, command, agent_id="a1"), git_repo).kind == "none"


def test_allowlist_does_not_exempt_state_dir_writes(git_repo: Path) -> None:
    state = _state(git_repo)
    allow = [{"command": "touch", "reason": "r"}]
    assert _decide(_command(state, "touch x", agent_id="a1"), git_repo, allow).kind == "deny"


APM_MUTATIONS = [
    "apm issue 1 --status merged",
    "apm task 1 t1 --status done",
    "apm allow 1 --path dist/** --reason r",
    "apm question 1 --text Why",
    "apm resolve 1 0 --answer yes",
    "apm setup",
    "apm approve --command 'make' --reason r",
    "echo hi && apm task 1 t1 --status done",
    '"/c/plugins/apm/bin/apm" issue 2 --title x',
]


@pytest.mark.parametrize("command", APM_MUTATIONS)
def test_worker_may_not_change_apm_state(git_repo: Path, command: str) -> None:
    decision = _decide(_command(git_repo, command, agent_id="a1"), git_repo)
    assert decision.kind == "deny" and "APM state" in decision.reason


@pytest.mark.parametrize("command", APM_MUTATIONS)
def test_main_session_may_change_apm_state(git_repo: Path, command: str) -> None:
    assert _decide(_command(git_repo, command), git_repo).kind == "none"


@pytest.mark.parametrize("command", ["apm brief", "apmx issue 1", "apm issues", 'bash -c "apm brief"'])
def test_worker_may_read_apm_state(git_repo: Path, command: str) -> None:
    assert _decide(_command(git_repo, command, agent_id="a1"), git_repo).kind == "none"


LATER = "2999-01-01T00:00:00+00:00"


def _approval(cwd: Path | str | None = None, **target: str) -> dict:
    return {**target, "reason": "user said yes", "cwd": str(cwd), "expires_at": LATER}


def test_command_approval_lets_exactly_that_command_through(git_repo: Path) -> None:
    approvals = [_approval(git_repo, command=BUILD)]
    assert _decide(_event(git_repo), git_repo, approvals=approvals).kind == "none"
    padded = _command(git_repo, f"  {BUILD}\n")
    assert _decide(padded, git_repo, approvals=approvals).kind == "none"
    shell = _command(git_repo, BUILD, "PowerShell")
    assert _decide(shell, git_repo, approvals=approvals).kind == "none"


@pytest.mark.parametrize(
    ("approved", "command"),
    [
        (BUILD, BUILD + " --force"),
        (BUILD, BUILD.replace("fleet.db", "other.db")),
        (BUILD, BUILD.replace("--out", "--out ")),
        (BUILD, f"{BUILD} && rm -rf src"),
        ("rm -rf build", "rm -rf build2"),
        ("rm -rf build", "rm -rf build/.."),
        ("rm -rf", "rm -rf build"),
    ],
)
def test_near_identical_command_is_still_denied(git_repo: Path, approved: str, command: str) -> None:
    approvals = [_approval(git_repo, command=approved)]
    assert _decide(_command(git_repo, command), git_repo, approvals=approvals).kind == "deny"


def test_command_approval_applies_only_in_the_recorded_cwd(git_repo: Path) -> None:
    approvals = [_approval(git_repo, command="rm -rf build")]
    assert _decide(_command(git_repo, "rm -rf build"), git_repo, approvals=approvals).kind == "none"
    (git_repo / "sub").mkdir()
    assert _decide(_command(git_repo / "sub", "rm -rf build"), git_repo, approvals=approvals).kind == "deny"
    assert _decide(_command(git_repo.parent, "rm -rf build"), git_repo, approvals=approvals).kind == "deny"


def test_command_approval_cwd_compares_normalized(git_repo: Path) -> None:
    recorded = git_repo.as_posix().upper() if WINDOWS else git_repo.as_posix() + "/"
    approvals = [_approval(recorded, command="rm -rf build")]
    assert _decide(_command(git_repo, "rm -rf build"), git_repo, approvals=approvals).kind == "none"


def test_command_approval_without_a_cwd_is_ignored(git_repo: Path) -> None:
    approvals = [{"command": "rm -rf build", "reason": "r", "expires_at": LATER}]
    assert _decide(_command(git_repo, "rm -rf build"), git_repo, approvals=approvals).kind == "deny"


def test_command_approval_does_not_override_the_state_dir_rule(git_repo: Path) -> None:
    state = _state(git_repo)
    approvals = [_approval(state, command="rm -rf build")]
    assert _decide(_command(state, "rm -rf build"), git_repo, approvals=approvals).kind == "deny"
    approvals = [_approval(state, command="touch x")]
    assert _decide(_command(state, "touch x"), git_repo, approvals=approvals).kind == "deny"


def test_command_approval_does_not_help_a_worker(git_repo: Path) -> None:
    approvals = [_approval(git_repo, command=BUILD)]
    assert _decide(_event(git_repo, agent_id="a1"), git_repo, approvals=approvals).kind == "deny"


def test_path_approval_allows_a_protected_write_in_the_main_session_only(git_repo: Path) -> None:
    approvals = [_approval(git_repo, path="data/*.db")]
    event = _file_event(git_repo, "Write", "file_path", "data/fleet.db")
    assert _decide(event, git_repo, approvals=approvals).kind == "none"
    assert _decide({**event, "agent_id": "a1"}, git_repo, approvals=approvals).kind == "deny"
    other = _file_event(git_repo, "Write", "file_path", "data/other.db")
    assert _decide(other, git_repo, approvals=[_approval(git_repo, path="data/fleet.db")]).kind == "deny"


def test_path_approval_does_not_cover_a_command(git_repo: Path) -> None:
    approvals = [_approval(git_repo, path="data/*.db"), _approval(git_repo, path=BUILD)]
    assert _decide(_event(git_repo), git_repo, approvals=approvals).kind == "deny"


def test_malformed_approvals_are_ignored(git_repo: Path) -> None:
    approvals = ["x", {"command": 5}, {"path": None}, {"reason": "only"}]
    assert _decide(_event(git_repo), git_repo, approvals=approvals).kind == "deny"


CLI = f'python "{PLUGIN_CLI}"'
RECORDS = [
    f'{CLI} approve --command "rm -rf build" --reason "user said yes"',
    f"{CLI} approve --path 'data/*.db' --reason 'regenerate the fleet db'",
    f'{CLI} task 1 t1 --status done --evidence "rm -rf build; git reset --hard | ok"',
    f'{CLI} allow 1 --command "git clean -fdx" --reason "plan step 3"',
    f"python3 '{PLUGIN_CLI}' approve --command 'touch data/fleet.db' --reason r",
    f'py "{PLUGIN_CLI.replace("/scripts/", "/scripts/../scripts/")}" approve --command "rm -rf build" --reason r',
]


@pytest.mark.parametrize("command", RECORDS)
def test_main_session_may_record_any_action_as_data(git_repo: Path, command: str) -> None:
    assert _decide(_command(git_repo, command), git_repo).kind == "none"


@pytest.mark.parametrize(
    "command",
    [
        f'{CLI} approve --command "rm -rf build" --reason r && rm -rf build',
        f'{CLI} approve --command x --reason r; rm -rf build',
        f'{CLI} approve --command "$(rm -rf build)" --reason r',
        f"{CLI} approve --command `rm -rf build` --reason r",
        f'{CLI} approve --command \\" ; rm -rf build ; \\" --reason r',
        f'{CLI} approve --command "rm -rf build --reason r',
        f'{CLI} approve --command x --reason r > data/fleet.db',
        'echo apm approve --command "rm -rf build"',
        'python tools/apm_cli.py.bak approve --command "rm -rf build" --reason r',
        'rm -rf build # apm approve',
        'python "/c/other/plugin/scripts/apm_cli.py" approve --command "rm -rf build" --reason r',
        f'python "{PLUGIN_CLI.replace("/scripts/", "/tools/")}" approve --command "rm -rf build" --reason r',
        '/tmp/apm approve --command "rm -rf build" --reason r',
        'apm allow 1 --command "git clean -fdx" --reason "plan step 3"',
    ],
)
def test_record_exemption_needs_a_single_plain_cli_call(git_repo: Path, command: str) -> None:
    assert _decide(_command(git_repo, command), git_repo).kind == "deny"


def test_record_exemption_is_bash_only_and_main_session_only(git_repo: Path) -> None:
    command = RECORDS[0]
    assert _decide(_command(git_repo, command, "PowerShell"), git_repo).kind == "deny"
    assert _decide(_command(git_repo, command, agent_id="a1"), git_repo).kind == "deny"


CLI_MUTATIONS = [
    'python "C:/Users/me/.claude/plugins/cache/rogue-sentinel/apm/0.1.0/scripts/apm_cli.py" issue 1 --status merged',
    "python3 /c/plugins/apm/scripts/apm_cli.py task 1 t1 --status done",
    r"python 'C:\plugins\apm\scripts\apm_cli.py' allow 1 --path x --reason r",
    'py -3 "C:/my plugins/apm/scripts/apm_cli.py" approve --command x --reason r',
    "echo hi && python scripts/apm_cli.py setup",
    "python apm_cli.py question 1 --text Why",
    'cd /x; python.exe "./scripts/apm_cli.py" resolve 1 0 --answer yes',
    '"C:/Python313/python.exe" "C:/x/scripts/apm_cli.py" "issue" 1',
    r'C:\plugins\apm\bin\apm approve --command x --reason r',
    "python scripts/APM_CLI.PY issue 1 --title x",
    'python "C:/x/Scripts/Apm_Cli.py" approve --command x --reason r',
    "python scripts/apm_cli.py -- task 1 t1 --status done",
    "apm -- issue 1 --title x",
    f'bash -c "python {PLUGIN_CLI} issue 1 --title x"',
    f"sh -c 'python3 \"{PLUGIN_CLI}\" task 1 t1 --status done'",
    'sh -c "apm task 1 t1"',
    "bash -c 'apm issue 1 --status merged'",
    'bash -lc "apm approve --command x --reason r"',
    'sh -c "echo hi; apm task 1 t1"',
    'powershell -Command "apm issue 1 --title x"',
    'cmd /c "apm task 1 t1"',
    f'bash -c "python \\"{PLUGIN_CLI}\\" issue 1 --title x"',
]


@pytest.mark.parametrize("command", CLI_MUTATIONS)
def test_worker_may_not_change_apm_state_through_apm_cli_py(git_repo: Path, command: str) -> None:
    decision = _decide(_command(git_repo, command, agent_id="a1"), git_repo)
    assert decision.kind == "deny" and "APM state" in decision.reason


@pytest.mark.parametrize(
    "command",
    ['python "C:/x/scripts/apm_cli.py" brief', "python scripts/apm_cli.py --help", "cat scripts/apm_cli.py",
     "python tools/my_apm_cli.py issue 1", "python scripts/apm_cli.py issues"],
)
def test_worker_may_read_apm_state_through_apm_cli_py(git_repo: Path, command: str) -> None:
    assert _decide(_command(git_repo, command, agent_id="a1"), git_repo).kind == "none"
