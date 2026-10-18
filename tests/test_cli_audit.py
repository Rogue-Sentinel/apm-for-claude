import json
import subprocess
from pathlib import Path

import pytest
from conftest import run_git

import apm_cli
from apm import cli_audit
from apm.coverage import INVENTORY_PATH


def fake_run(argv, **kwargs):
    if argv[0] != "gh":
        return subprocess.run(argv, **kwargs)
    issues = [{"number": 4, "title": "[Debt] tidy", "labels": []}, {"number": 7, "title": "Feature", "labels": []}]
    return subprocess.CompletedProcess(argv, 0, json.dumps(issues), "")


def status(repo: Path) -> str:
    done = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    return done.stdout


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    run_git(git_repo, "add", "app.py")
    run_git(git_repo, "commit", "-m", "app")
    monkeypatch.chdir(git_repo)
    monkeypatch.setattr(cli_audit, "RUN", fake_run)
    return git_repo


def test_cli_audit_json_and_not_a_repo(repo: Path, capsys, tmp_path: Path, monkeypatch) -> None:
    code = apm_cli.main(["audit", "--json", "--base", "main"])

    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert (data["mode"], data["base"], data["debt_issues"]) == ("existing", "main", [4])
    assert [item["id"] for item in data["in_flight"]] == ["issue:7"]
    assert set(data) == {"mode", "base", "notes", "in_flight", "debt_issues", "totals"}
    monkeypatch.chdir(tmp_path)
    assert apm_cli.main(["audit"]) == 2


def test_cli_audit_prints_the_report_with_coverage(repo: Path, capsys) -> None:
    code = apm_cli.main(["audit", "--base", "main", "--coverage", str(INVENTORY_PATH)])

    out = capsys.readouterr().out
    assert code == 0
    assert "# Audit" in out and "## Capability coverage" in out and "Coverage of the old standard" in out


def test_cli_audit_unknown_base_is_one_line(repo: Path, capsys) -> None:
    code = apm_cli.main(["audit", "--base", "nope"])

    assert code == 2
    assert "unknown ref: nope" in capsys.readouterr().err


def test_cli_audit_changes_nothing(repo: Path) -> None:
    apm_cli.main(["audit", "--base", "main"])

    assert status(repo) == ""
    assert not (repo / ".apm").exists()
