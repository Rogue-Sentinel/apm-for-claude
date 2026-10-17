import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import apm_cli
from apm.cli_parser import build_parser
from apm.guard_paths import same_path
from apm.paths import find_project
from apm.state_store import init_state

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    init_state(find_project(git_repo))
    monkeypatch.chdir(git_repo)
    return git_repo


def _state(repo: Path) -> Path:
    return repo / ".apm" / "state"


def _ledger(repo: Path) -> dict:
    return json.loads((_state(repo) / "ledger.json").read_text(encoding="utf-8"))


def _commits(repo: Path) -> int:
    done = subprocess.run(
        ["git", "-C", str(_state(repo)), "log", "--oneline"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return len(done.stdout.splitlines())


def test_issue_then_task_then_brief(repo: Path, capsys) -> None:
    assert apm_cli.main(["issue", "1", "--title", "Login page", "--status", "building"]) == 0
    assert apm_cli.main(["task", "1", "t1", "--title", "Form", "--status", "done"]) == 0
    capsys.readouterr()
    assert apm_cli.main(["brief"]) == 0
    out = capsys.readouterr().out
    assert "Login page" in out and "1/1" in out


def test_mutations_store_fields_and_log_events(repo: Path) -> None:
    argv_list = [
        ["issue", "12", "--title", "T", "--kind", "bug", "--lane", "ui", "--status", "building",
         "--branch", "issue-12", "--plan", "docs/p.md"],
        ["task", "12", "t3", "--status", "done", "--worker", "w1", "--model", "sonnet", "--evidence", "ok"],
        ["allow", "12", "--command", "python tools/x.py", "--reason", "needed"],
        ["question", "12", "--text", "Which?", "--blocks", "t3", "t4"],
        ["resolve", "12", "0", "--answer", "This"],
    ]
    for argv in argv_list:
        assert apm_cli.main(argv) == 0
    ledger = _ledger(repo)
    issue = ledger["issues"]["12"]
    assert (issue["kind"], issue["lane"], issue["branch"], issue["plan"]) == ("bug", "ui", "issue-12", "docs/p.md")
    assert issue["tasks"][0]["evidence"] == "ok" and issue["tasks"][0]["worker"] == "w1"
    assert issue["allowlist"][0]["command"] == "python tools/x.py"
    assert issue["questions"][0] == {"text": "Which?", "blocks": ["t3", "t4"], "answer": "This", "resolved": True}
    events = [entry["event"] for entry in ledger["log"]]
    assert events == [
        "issue 12 status building", "task 12/t3 done", "allow 12 command python tools/x.py",
        "question 12 #0", "resolve 12 #0",
    ]


def test_question_prints_index_and_shows_in_brief(repo: Path, capsys) -> None:
    apm_cli.main(["issue", "2", "--title", "CSV"])
    capsys.readouterr()
    apm_cli.main(["question", "2", "--text", "Delimiter?"])
    assert capsys.readouterr().out.strip() == "question 0"
    apm_cli.main(["brief"])
    assert "Delimiter?" in capsys.readouterr().out
    apm_cli.main(["resolve", "2", "0", "--answer", "comma"])
    capsys.readouterr()
    apm_cli.main(["brief"])
    assert "Delimiter?" not in capsys.readouterr().out


def test_allow_path_entry(repo: Path) -> None:
    apm_cli.main(["issue", "3", "--status", "building"])
    assert apm_cli.main(["allow", "3", "--path", "dist/**", "--reason", "build output"]) == 0
    assert _ledger(repo)["log"][-1]["event"] == "allow 3 path dist/**"


@pytest.mark.parametrize("flags", [[], ["--path", "a", "--command", "b"]])
def test_allow_requires_exactly_one_of_path_or_command(repo: Path, flags: list[str], capsys) -> None:
    assert apm_cli.main(["allow", "1", *flags, "--reason", "why"]) == 2
    assert "error" in capsys.readouterr().err


def test_mutation_commits_state(repo: Path) -> None:
    before = _commits(repo)
    assert apm_cli.main(["issue", "1", "--title", "A"]) == 0
    assert _commits(repo) == before + 1


def test_ledger_error_exits_2_with_one_line(repo: Path, capsys) -> None:
    assert apm_cli.main(["task", "99", "t1", "--status", "done"]) == 2
    err = capsys.readouterr().err
    assert "unknown issue: 99" in err and len(err.strip().splitlines()) == 1
    assert apm_cli.main(["issue", "1", "--status", "bogus"]) == 2


def test_uninitialized_project_exits_2(git_repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["brief"]) == 2
    assert "not an initialized" in capsys.readouterr().err


def test_outside_a_repo_exits_2(tmp_path: Path, monkeypatch) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    assert apm_cli.main(["brief"]) == 2


def test_missing_state_branch_exits_2(git_repo: Path, monkeypatch, capsys) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["issue", "1", "--title", "A"]) == 2
    err = capsys.readouterr().err
    assert "state" in err and f'run setup with the APM CLI: python "{ROOT.as_posix()}/scripts/apm_cli.py" setup' in err


def test_argparse_exits_become_return_codes(capsys) -> None:
    assert apm_cli.main([]) == 2
    assert apm_cli.main(["--help"]) == 0
    assert apm_cli.main(["issue", "one"]) == 2


def test_parser_knows_setup() -> None:
    assert build_parser().parse_args(["setup"]).subcommand == "setup"


def test_runs_from_a_subdirectory(repo: Path, monkeypatch) -> None:
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert apm_cli.main(["issue", "1", "--title", "A"]) == 0


def test_bin_apm_is_executable_in_git() -> None:
    script = (ROOT / "bin" / "apm").read_text(encoding="utf-8")
    assert script.splitlines()[0] == "#!/usr/bin/env bash"
    assert 'exec python "$(dirname "$0")/../scripts/apm_cli.py" "$@"' in script
    done = subprocess.run(
        ["git", "ls-files", "-s", "bin/apm"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert done.stdout.startswith("100755")


def test_new_issue_without_status_shows_as_queued_in_brief(repo: Path, capsys) -> None:
    apm_cli.main(["issue", "5", "--title", "Fresh idea"])
    capsys.readouterr()
    apm_cli.main(["brief"])
    out = capsys.readouterr().out
    assert "Queued" in out and "#5 Fresh idea" in out and "No work recorded" not in out


def test_issue_update_without_status_keeps_status(repo: Path) -> None:
    apm_cli.main(["issue", "5", "--status", "building"])
    apm_cli.main(["issue", "5", "--title", "Renamed"])
    assert _ledger(repo)["issues"]["5"]["status"] == "building"


def test_brief_on_corrupt_ledger_prints_state_unavailable_and_exits_2(repo: Path, capsys) -> None:
    (_state(repo) / "ledger.json").write_text("garbage{", encoding="utf-8")
    assert apm_cli.main(["brief"]) == 2
    assert capsys.readouterr().out.startswith("State unavailable: ")


def test_gitattributes_pins_bin_apm_to_lf() -> None:
    done = subprocess.run(
        ["git", "check-attr", "eol", "bin/apm"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip().endswith("eol: lf")
    done = subprocess.run(
        ["git", "check-attr", "eol", "tools/x.sh"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip().endswith("eol: lf")


def test_runs_from_a_linked_worktree_without_its_own_profile(repo: Path, monkeypatch, capsys) -> None:
    subprocess.run(["git", "worktree", "add", "../wt", "-b", "wt"], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(repo.parent / "wt")
    assert apm_cli.main(["issue", "1", "--title", "From a worktree"]) == 0
    assert "From a worktree" in _ledger(repo)["issues"]["1"]["title"]


def test_brief_without_state_worktree_says_state_unavailable(git_repo: Path, monkeypatch, capsys) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["brief"]) == 2
    state = find_project(git_repo).state_dir
    expected = f"State unavailable: state is not set up at {state}; run setup with the APM CLI: python \"{ROOT.as_posix()}/scripts/apm_cli.py\" setup"
    assert capsys.readouterr().out.strip() == expected


def test_approve_records_a_ten_minute_one_off_approval(repo: Path) -> None:
    before = _commits(repo)
    assert apm_cli.main(["approve", "--command", "rm -rf build", "--reason", "user said yes"]) == 0
    ledger = _ledger(repo)
    entry = ledger["approvals"][0]
    assert (entry["command"], entry["reason"]) == ("rm -rf build", "user said yes") and "path" not in entry
    assert same_path(entry["cwd"], repo)
    left = datetime.fromisoformat(entry["expires_at"]) - datetime.now(timezone.utc)
    assert timedelta(minutes=9) < left <= timedelta(minutes=10)
    assert ledger["log"][-1]["event"] == "approve command rm -rf build"
    assert ledger["log"][-1]["issue"] is None
    assert _commits(repo) == before + 1


def test_approve_path_entry(repo: Path) -> None:
    assert apm_cli.main(["approve", "--path", "data/*.db", "--reason", "regenerate"]) == 0
    assert _ledger(repo)["approvals"][0]["path"] == "data/*.db"


@pytest.mark.parametrize("flags", [[], ["--path", "a", "--command", "b"]])
def test_approve_requires_exactly_one_of_path_or_command(repo: Path, flags: list[str], capsys) -> None:
    assert apm_cli.main(["approve", *flags, "--reason", "why"]) == 2
    assert "error" in capsys.readouterr().err
    assert apm_cli.main(["approve", "--command", "x"]) == 2
