import json
import subprocess
from pathlib import Path

import pytest

import apm_cli
from apm.paths import find_project
from apm.state_store import init_state


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    init_state(find_project(git_repo))
    monkeypatch.chdir(git_repo)
    return git_repo


def _ledger(repo: Path) -> dict:
    return json.loads((repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8"))


def _head(repo: Path) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def test_cli_note_review_parent(repo: Path) -> None:
    apm_cli.main(["issue", "1", "--title", "Big", "--status", "split"])
    apm_cli.main(["issue", "2", "--title", "Part", "--parent", "1"])

    codes = [
        apm_cli.main(["note", "2", "--decision", "use sqlite"]),
        apm_cli.main(["note", "2", "--decision", "use sqlite"]),
        apm_cli.main(["note", "2", "--concern", "slow on windows"]),
        apm_cli.main(["review", "2", "--open", "0", "--criteria-met", "--evidence", "all green"]),
    ]

    issue = _ledger(repo)["issues"]["2"]
    assert codes == [0, 0, 0, 0]
    assert issue["parent"] == 1
    assert [d["text"] for d in issue["decisions"]] == ["use sqlite"]
    assert [c["text"] for c in issue["concerns"]] == ["slow on windows"]
    assert issue["review"]["head"] == _head(repo)
    assert (issue["review"]["open"], issue["review"]["criteria_met"]) == (0, True)
    assert issue["review"]["evidence"] == "all green"


def test_review_without_criteria_flag_records_false(repo: Path) -> None:
    apm_cli.main(["issue", "3", "--title", "T"])

    apm_cli.main(["review", "3", "--open", "2", "--evidence", "two findings"])

    assert _ledger(repo)["issues"]["3"]["review"]["criteria_met"] is False


def test_issue_parent_is_validated(repo: Path, capsys) -> None:
    apm_cli.main(["issue", "4", "--title", "T"])

    code = apm_cli.main(["issue", "4", "--parent", "9"])

    assert code == 2
    assert "unknown issue: 9" in capsys.readouterr().err
    assert "parent" not in _ledger(repo)["issues"]["4"]


def test_negative_review_count_exits_2(repo: Path, capsys) -> None:
    apm_cli.main(["issue", "5", "--title", "T"])

    code = apm_cli.main(["review", "5", "--open", "-1", "--evidence", "e"])

    assert code == 2
    assert "negative" in capsys.readouterr().err


def test_note_needs_exactly_one_kind(repo: Path) -> None:
    apm_cli.main(["issue", "6", "--title", "T"])

    both = apm_cli.main(["note", "6", "--decision", "a", "--concern", "b"])
    neither = apm_cli.main(["note", "6"])

    assert (both, neither) == (2, 2)
