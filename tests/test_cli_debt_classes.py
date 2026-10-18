import json
from pathlib import Path

import pytest

import apm_cli
from apm.cli_debt import TRACK_HINT
from conftest import run_git

DEBT = ".apm/debt.json"


def _class_with(methods: int) -> str:
    return "class Database {\npublic:\n" + "".join(f"    void m{i}();\n" for i in range(methods)) + "};\n"


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    """An initialized project holding one C++ class with eight public methods."""
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text(json.dumps({"framework_version": "0.2.0"}), encoding="utf-8")
    (git_repo / "db.hpp").write_text(_class_with(8), encoding="utf-8")
    run_git(git_repo, "add", "-A")
    run_git(git_repo, "commit", "-m", "code")
    monkeypatch.chdir(git_repo)
    return git_repo


def _debt(*args: str) -> int:
    return apm_cli.main(["debt", *args])


def _read(repo: Path) -> dict:
    return json.loads((repo / DEBT).read_text(encoding="utf-8"))


def _write(repo: Path, data: dict) -> None:
    (repo / DEBT).write_text(json.dumps(data), encoding="utf-8")


def _write_legacy_baseline(repo: Path) -> None:
    """The baseline an earlier version recorded: no C++ classes, no class fields."""
    _debt("baseline")
    data = _read(repo)
    data["classes"], data["totals"]["wide_classes"] = {}, 0
    del data["class_scanners"], data["class_languages"]
    _write(repo, data)


def test_check_passes_on_unchanged_cpp_code_measured_for_the_first_time(repo: Path, capsys) -> None:
    _write_legacy_baseline(repo)
    capsys.readouterr()

    assert _debt("check") == 0

    out = capsys.readouterr().out
    assert "newly measured, not new debt:" in out and TRACK_HINT in out


def test_baseline_then_records_the_classes_and_their_growth_fails(repo: Path, capsys) -> None:
    _write_legacy_baseline(repo)

    assert _debt("baseline") == 0

    data = _read(repo)
    assert data["classes"] == {"db.hpp::Database": 8} and "C++" in data["class_scanners"]
    (repo / "db.hpp").write_text(_class_with(9), encoding="utf-8")
    capsys.readouterr()
    assert _debt("check") == 1
    assert "grew: db.hpp::Database 8 → 9" in capsys.readouterr().out


def test_a_branch_baseline_that_adds_newly_measured_classes_passes_against_main(repo: Path) -> None:
    _write_legacy_baseline(repo)
    run_git(repo, "add", DEBT)
    run_git(repo, "commit", "-m", "legacy baseline")
    run_git(repo, "checkout", "-b", "feature")
    _debt("baseline")

    assert _debt("check", "--base", "main") == 0


def test_a_branch_baseline_that_drops_a_scanner_fails_against_main(repo: Path, capsys) -> None:
    _debt("baseline")
    run_git(repo, "add", DEBT)
    run_git(repo, "commit", "-m", "baseline")
    run_git(repo, "checkout", "-b", "feature")
    data = _read(repo)
    data["class_scanners"].remove("C++")
    data["classes"], data["totals"]["wide_classes"] = {}, 0
    _write(repo, data)
    capsys.readouterr()

    assert _debt("check") == 1

    assert "class scanner missing: C++" in capsys.readouterr().out
