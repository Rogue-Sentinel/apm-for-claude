"""Workers never change APM state or write to GitHub; the main session still may."""
import argparse
import sys
from pathlib import Path

import pytest

from apm.cli_parser import build_parser
from apm.guard import Decision, decide
from apm.guard_cli import is_cli_call
from apm.guard_github import gh_write_reason
from apm.guard_workers import WORKER_READ_ONLY
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
ROOT = Path(__file__).resolve().parent.parent
CLI = f'python "{(ROOT / "scripts" / "apm_cli.py").as_posix()}"'
NEW_SUBCOMMANDS = ("audit", "init", "github", "gate", "review", "note")


def _decide(repo: Path, command: str, **extra: object) -> Decision:
    project = Project(main_root=repo, worktree_root=repo)
    event = {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": command}, **extra}
    return decide(event, project, Profile(framework_version="0.2.0"), [], [], WINDOWS)


def _worker(repo: Path, command: str) -> Decision:
    return _decide(repo, command, agent_id="w1")


def _choices(parser: argparse.ArgumentParser) -> dict:
    action = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
    return dict(action.choices) if action else {}


def _parser_commands() -> list[str]:
    """Each subcommand, and each action of a subcommand that has actions (`debt check`)."""
    commands: list[str] = []
    for name, sub in _choices(build_parser()).items():
        commands += [f"{name} {action}" for action in _choices(sub)] or [name]
    return commands


@pytest.mark.parametrize("command", _parser_commands())
def test_every_subcommand_is_classified(git_repo: Path, command: str) -> None:
    expected = "none" if command in WORKER_READ_ONLY else "deny"

    assert _worker(git_repo, f"apm {command} 1").kind == expected
    assert _worker(git_repo, f"{CLI} {command} 1").kind == expected


@pytest.mark.parametrize("call", ["debt", "debt --help", "debt -- baseline", "debt prune"])
def test_debt_is_denied_to_workers_unless_it_is_a_check(git_repo: Path, call: str) -> None:
    assert _worker(git_repo, f"apm {call}").kind == "deny"


def test_debt_baseline_is_denied_and_debt_check_is_allowed(git_repo: Path) -> None:
    assert "debt check" in WORKER_READ_ONLY
    assert _worker(git_repo, "apm debt baseline").kind == "deny"
    assert _worker(git_repo, "apm debt check").kind == "none"


def test_the_read_only_set_is_exactly_what_the_plan_names() -> None:
    assert WORKER_READ_ONLY == ("brief", "metrics", "coverage", "audit", "debt check")


@pytest.mark.parametrize("name", NEW_SUBCOMMANDS)
def test_the_new_subcommands_are_cli_calls(name: str) -> None:
    assert is_cli_call(f"{CLI} {name} 1", ROOT, WINDOWS)


@pytest.mark.parametrize("call", ["note 1", "review 1", "github file 1", "github close 3", "init", "gate"])
def test_worker_denied_new_mutations(git_repo: Path, call: str) -> None:
    assert _worker(git_repo, f"apm {call}").kind == "deny"
    assert _worker(git_repo, f"{CLI} {call}").kind == "deny"
    assert _worker(git_repo, f"ls && apm {call}").kind == "deny"


def test_worker_may_run_audit(git_repo: Path) -> None:
    assert _worker(git_repo, "apm audit").kind == "none"
    assert _worker(git_repo, f"{CLI} audit").kind == "none"


GH_WRITES = [
    "gh issue create -t x",
    "gh  pr   merge 3",
    "GH.EXE pr merge 3",
    "/usr/bin/gh issue close 2",
    r"C:\Program Files\GitHub CLI\gh.exe issue close 2",
    '"C:/Program Files/GitHub CLI/gh.exe" issue close 2',
    "ls && gh issue comment 1 -b hi",
    "ls; gh issue comment 1 -b hi",
    "echo x | gh issue comment 1 -F -",
    "false || gh pr close 4",
    "gh release create v1",
    "gh api repos/o/r/issues -X POST",
    "gh api --method=PATCH repos/o/r",
    "gh api --method DELETE repos/o/r",
    "gh api repos/o/r/issues -f title=x",
    "gh api repos/o/r/issues -F body=@f",
    "gh api repos/o/r/issues --field title=x",
    "gh api repos/o/r/issues --raw-field title=x",
    "gh api graphql --input q.json",
    "gh api -XPOST repos/o/r/issues",
    "gh api -X=PUT repos/o/r/x",
    "gh api repos/o/r/issues -ftitle=x",
    "gh api repos/o/r/issues -i -f title=x",
    "gh api repos/o/r/issues --input=body.json",
]
GH_DISGUISED = [
    'gh "issue" create',
    "gh issue 'create'",
    "g''h issue create",
    r"g\h issue create",
    "env GH_TOKEN=x gh issue create",
    "sudo gh issue create",
    "xargs gh issue close",
    "bash -c 'gh issue create -t x'",
    'sh -c "echo hi; gh pr merge 3"',
    "echo $(gh issue create -t x)",
    "gh -R o/r issue close 1",
    "gh --repo o/r pr merge 3",
    "gh issue close 1 -R o/r",
    "gh alias set mk 'issue create'",
    "gh extension install o/r",
    "gh workflow run ci.yml",
    "gh secret set TOKEN",
    "gh gist create f.txt",
    "gh repo delete o/r --yes",
    "gh label create bug",
    "gh pr update-branch 3",
    "gh release delete-asset v1 a.zip",
    "gh auth logout",
    "gh codespace create",
    "gh issue new -t x",
    "gh pr new",
    "gh repo new o/r",
    "gh gist new f.txt",
    "gh release new v1",
    "gh ext install o/r",
    "gh extensions install o/r",
    "gh cs create",
    "gh mk",
    "gh auth token",
    "gh issue frobnicate 3",
    "x=$(gh issue create)",
    "echo `gh pr ready`",
    "(gh issue create)",
    "gh pr ready>/dev/null",
    "gh issue create<body.md",
    "gh pr merge 3;",
    "{ gh issue close 3; }",
    "exec -a gh gh issue create",
    "sudo -u gh gh pr merge 3",
    "env X=gh gh issue create",
    'bash -c "exec -a gh gh issue create"',
    "gh $(echo issue) create",
    "gh $CMD create",
    "gh auth status --show-token",
    "gh auth status -t",
    "gh auth status --show-token=true",
    "gh auth status -at",
    "gh auth status -h github.com --show-token",
    "gh pr checkout 3",
]


@pytest.mark.parametrize("command", [*GH_WRITES, *GH_DISGUISED])
def test_gh_writes_denied_to_workers(git_repo: Path, command: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and "GitHub" in decision.reason


GH_READS = [
    "gh issue list",
    "gh issue view 3 --comments",
    "gh pr view 2",
    "gh pr diff 2",
    "gh pr list --state open",
    "gh pr checks 2",
    "gh api repos/o/r/pulls",
    "gh api -X GET repos/o/r",
    "gh api --method=GET repos/o/r",
    "gh api repos/o/r/issues -H 'Accept: application/json' -q '.[0]'",
    "gh auth status",
    "gh release list",
    "gh repo view o/r",
    "gh -R o/r issue list",
    "ghost issue create",
    "git commit -m 'gh issue create'",
    "ls .github && cat gh.txt",
    "gh",
    "gh --version",
    "gh help issue",
    "gh issue ls",
    "gh auth status -h github.com",
    "gh auth status --active",
    "gh auth status -hgithub.com",
    "gh run watch 3",
    "gh search issues foo",
    "gh status",
    "gh config get editor",
    "gh variable get X",
    "gh project item-list 1",
    'gh issue list --search "x y" --json number',
    "gh pr view $N",
    "echo $(gh pr view 2)",
    "x=$(gh issue list)",
    "gh issue list>out.txt",
]


@pytest.mark.parametrize("command", GH_READS)
def test_gh_reads_allowed_to_workers(git_repo: Path, command: str) -> None:
    assert _worker(git_repo, command).kind == "none"


@pytest.mark.parametrize("command", ["gh issue create -t x", "apm github close 3", "gh pr merge 3"])
def test_main_session_may_file_and_close(git_repo: Path, command: str) -> None:
    assert _decide(git_repo, command).kind == "none"


def test_a_write_reason_tells_the_worker_to_report_to_the_manager() -> None:
    reason = gh_write_reason("gh issue create -t x")

    assert reason is not None and "workers do not write to GitHub; report to the manager instead" in reason


def test_a_read_has_no_reason() -> None:
    assert gh_write_reason("gh issue list") is None


TEXT_SEARCHES = ['grep -rn "gh issue create" skills/', "rg gh pr merge docs", "grep -r 'gh issue' docs"]


@pytest.mark.parametrize("command", TEXT_SEARCHES)
def test_a_text_search_for_a_gh_write_is_denied_and_points_to_the_grep_tool(git_repo: Path, command: str) -> None:
    decision = _worker(git_repo, command)

    assert decision.kind == "deny" and "Grep tool" in decision.reason
