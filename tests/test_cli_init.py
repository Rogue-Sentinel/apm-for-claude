import json
import shutil
import subprocess
from pathlib import Path

import pytest

import apm_cli
from apm import cli_init
from apm.coverage import INVENTORY_PATH
from apm.init_apply import AUDIT_DIR


def put(repo: Path, name: str, data: dict) -> None:
    path = repo / AUDIT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    monkeypatch.chdir(git_repo)
    return git_repo


def stage(repo: Path, in_flight=(), decisions=None) -> None:
    put(repo, "audit.json", {"mode": "existing", "base": "main", "in_flight": list(in_flight), "debt_issues": [4]})
    put(repo, "decisions.json", decisions or {})
    put(repo, "profile.json", {"framework_version": "0.1.0"})
    shutil.copy(INVENTORY_PATH, repo / AUDIT_DIR / "coverage.json")


def test_init_refuses_with_lines_and_exits_1(repo: Path, capsys) -> None:
    stage(repo, [{"id": "issue:7", "kind": "issue", "title": "T", "detail": "d"}])

    code = apm_cli.main(["init", "--issue", "1"])

    assert code == 1
    assert capsys.readouterr().out.splitlines() == ["no decision for issue:7"]
    assert not (repo / ".apm" / "profile.json").exists()


def test_init_applies_the_audit_and_a_second_run_is_quiet(repo: Path, capsys) -> None:
    stage(repo)

    first = apm_cli.main(["init", "--issue", "1"])
    out = capsys.readouterr().out
    second = apm_cli.main(["init", "--issue", "1"])

    assert (first, second) == (0, 0)
    assert "wrote .apm/profile.json" in out and "wrote .apm/debt.json" in out
    assert capsys.readouterr().out.strip() == "nothing new"
    state = json.loads((repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8"))
    assert state["debt_issues"] == [4]


def test_init_checks_merges_through_the_run_seam(repo: Path, monkeypatch, capsys) -> None:
    stage(repo, [{"id": "branch:feat", "kind": "branch", "title": "feat", "detail": "1 ahead"}], {"branch:feat": "finish"})
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "")

    monkeypatch.setattr(cli_init, "RUN", fake_run)

    code = apm_cli.main(["init", "--issue", "1"])

    assert code == 1
    assert capsys.readouterr().out.splitlines() == ["finish first: branch:feat is not merged into main yet"]
    assert ["git", "merge-base", "--is-ancestor", "feat", "main"] in calls
