import json
from pathlib import Path

import pytest

import apm_cli
from apm.cli_debt import TRACK_HINT
from conftest import run_git

DEBT = ".apm/debt.json"
QML = "ui/Main.qml"


def _qml_text(lines: int) -> str:
    return "Item {\n" + "".join(f"    property int p{i}: {i}\n" for i in range(lines - 2)) + "}\n"


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    """An initialized project holding one committed 250-line QML file."""
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text(json.dumps({"framework_version": "0.2.0"}), encoding="utf-8")
    (git_repo / "ui").mkdir()
    (git_repo / QML).write_text(_qml_text(250), encoding="utf-8")
    run_git(git_repo, "add", "-A")
    run_git(git_repo, "commit", "-m", "code")
    monkeypatch.chdir(git_repo)
    return git_repo


def _debt(*args: str) -> int:
    return apm_cli.main(["debt", *args])


def _write_legacy_baseline(repo: Path) -> None:
    """The baseline apm 0.3.2 wrote: no language fields, and the QML file was never measured."""
    _debt("baseline")
    data = json.loads((repo / DEBT).read_text(encoding="utf-8"))
    del data["measured_languages"], data["file_languages"], data["files"][QML]
    data["totals"]["long_files"] = data["totals"]["excess_file_lines"] = 0
    (repo / DEBT).write_text(json.dumps(data), encoding="utf-8")


def test_check_passes_on_an_unchanged_long_qml_file_measured_for_the_first_time(repo: Path, capsys) -> None:
    _write_legacy_baseline(repo)
    capsys.readouterr()

    assert _debt("check") == 0

    out = capsys.readouterr().out
    assert "newly measured, not new debt:" in out and TRACK_HINT in out


def test_after_a_baseline_a_grown_qml_file_fails(repo: Path, capsys) -> None:
    _write_legacy_baseline(repo)
    _debt("baseline")
    (repo / QML).write_text(_qml_text(260), encoding="utf-8")
    capsys.readouterr()

    assert _debt("check") == 1

    assert "grew: ui/Main.qml" in capsys.readouterr().out
