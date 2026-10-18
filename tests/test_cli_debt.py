import json
from datetime import datetime
from pathlib import Path

import pytest

import apm_cli
from apm.cli_debt import render_comparison
from apm.debt import Comparison
from conftest import run_git

DEBT = ".apm/debt.json"


def _body(lines: int) -> str:
    return "def big():\n" + "".join(f"    x{i} = {i}\n" for i in range(lines))


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    """An initialized project holding one 20-line function."""
    (git_repo / ".apm").mkdir()
    profile = {"framework_version": "0.2.0"}
    (git_repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (git_repo / "big.py").write_text(_body(20), encoding="utf-8")
    run_git(git_repo, "add", "-A")
    run_git(git_repo, "commit", "-m", "code")
    monkeypatch.chdir(git_repo)
    return git_repo


def _debt(*args: str) -> int:
    return apm_cli.main(["debt", *args])


def _baseline(repo: Path) -> dict:
    return json.loads((repo / DEBT).read_text(encoding="utf-8"))


def _grow(repo: Path, lines: int) -> None:
    (repo / "big.py").write_text(_body(lines), encoding="utf-8")


def test_debt_baseline_then_check_passes(repo: Path, capsys) -> None:
    assert _debt("baseline") == 0
    assert _baseline(repo)["functions"] == {"big.py::big": 20}

    assert _debt("check") == 0


def test_check_fails_after_growing_the_function(repo: Path, capsys) -> None:
    _debt("baseline")
    _grow(repo, 21)
    capsys.readouterr()

    assert _debt("check") == 1

    out = capsys.readouterr().out
    assert "big.py::big" in out and "20 → 21" in out


def test_baseline_refuses_worse_without_accept(repo: Path, capsys) -> None:
    _debt("baseline")
    before = (repo / DEBT).read_text(encoding="utf-8")
    _grow(repo, 25)
    capsys.readouterr()

    assert _debt("baseline") == 1

    assert "20 → 25" in capsys.readouterr().out
    assert (repo / DEBT).read_text(encoding="utf-8") == before


@pytest.mark.parametrize("reason", ["", "   "])
def test_a_blank_accept_does_not_bypass_the_refusal(repo: Path, reason: str) -> None:
    _debt("baseline")
    _grow(repo, 25)

    assert _debt("baseline", "--accept", reason) == 1

    assert _baseline(repo)["functions"] == {"big.py::big": 20}


def test_baseline_with_accept_records_reason(repo: Path) -> None:
    _debt("baseline")
    _grow(repo, 25)

    assert _debt("baseline", "--accept", "the parser needs it") == 0

    data = _baseline(repo)
    assert data["functions"] == {"big.py::big": 25}
    assert [entry["reason"] for entry in data["accepted"]] == ["the parser needs it"]
    assert datetime.fromisoformat(data["accepted"][0]["at"]).utcoffset().total_seconds() == 0
    assert _debt("check") == 0


def test_accepting_twice_keeps_the_history(repo: Path) -> None:
    _debt("baseline")
    _grow(repo, 25)
    _debt("baseline", "--accept", "first")
    _grow(repo, 30)

    _debt("baseline", "--accept", "second")

    assert [entry["reason"] for entry in _baseline(repo)["accepted"]] == ["first", "second"]


def test_baseline_tightens_after_shrinking(repo: Path, capsys) -> None:
    _debt("baseline")
    _grow(repo, 10)
    capsys.readouterr()

    assert _debt("check") == 0
    assert "baseline" in capsys.readouterr().out

    assert _debt("baseline") == 0

    data = _baseline(repo)
    assert data["functions"] == {} and data["totals"]["long_functions"] == 0


def test_growing_again_after_tightening_fails(repo: Path) -> None:
    _debt("baseline")
    _grow(repo, 10)
    _debt("baseline")
    _grow(repo, 20)

    assert _debt("check") == 1


def test_check_without_baseline_exits_2(repo: Path, capsys) -> None:
    assert _debt("check") == 2

    assert "apm debt baseline" in capsys.readouterr().err


def test_check_with_an_unknown_base_exits_2(repo: Path, capsys) -> None:
    _debt("baseline")

    assert _debt("check", "--base", "nope") == 2

    assert "unknown ref nope" in capsys.readouterr().err


def test_check_with_a_corrupt_baseline_exits_2(repo: Path, capsys) -> None:
    (repo / DEBT).write_text('{"version": 1, "functions": {"big.py::big": "20"}}', encoding="utf-8")

    assert _debt("check") == 2

    assert "debt.json" in capsys.readouterr().err


def test_baseline_over_a_corrupt_baseline_exits_2(repo: Path) -> None:
    (repo / DEBT).write_text("{oops", encoding="utf-8")

    assert _debt("baseline") == 2


def test_check_passes_when_the_base_has_no_baseline(repo: Path) -> None:
    _debt("baseline")

    assert _debt("check", "--base", "main") == 0


def _commit_baseline_on_main_then_branch(repo: Path) -> None:
    _debt("baseline")
    run_git(repo, "add", DEBT)
    run_git(repo, "commit", "-m", "baseline")
    run_git(repo, "checkout", "-b", "feature")


def test_check_fails_when_branch_loosened_baseline_without_acceptance(repo: Path, capsys) -> None:
    _commit_baseline_on_main_then_branch(repo)
    data = _baseline(repo)
    data["functions"]["big.py::big"] = 30
    (repo / DEBT).write_text(json.dumps(data), encoding="utf-8")
    capsys.readouterr()

    assert _debt("check") == 1

    out = capsys.readouterr().out
    assert "looser than the baseline at main" in out and "20 → 30" in out


def test_loosening_through_a_hand_edit_that_also_lowers_the_totals_still_fails(repo: Path) -> None:
    _commit_baseline_on_main_then_branch(repo)
    data = _baseline(repo)
    data["limits"]["function"] = 40
    (repo / DEBT).write_text(json.dumps(data), encoding="utf-8")

    assert _debt("check") == 1


def test_check_passes_after_recorded_acceptance_on_branch(repo: Path) -> None:
    _commit_baseline_on_main_then_branch(repo)
    _grow(repo, 25)
    assert _debt("check") == 1

    assert _debt("baseline", "--accept", "the parser needs it") == 0

    assert _debt("check") == 0


def test_a_baseline_that_only_tightened_passes_against_the_base(repo: Path) -> None:
    _commit_baseline_on_main_then_branch(repo)
    _grow(repo, 10)
    _debt("baseline")

    assert _debt("check") == 0


def test_check_compares_with_a_given_base(repo: Path) -> None:
    _commit_baseline_on_main_then_branch(repo)
    data = _baseline(repo)
    data["functions"]["big.py::big"] = 30
    (repo / DEBT).write_text(json.dumps(data), encoding="utf-8")
    run_git(repo, "commit", "-am", "loosen")

    assert _debt("check", "--base", "main") == 1
    assert _debt("check", "--base", "HEAD") == 0


def _profile(repo: Path, standard: dict) -> None:
    profile = {"framework_version": "0.2.0", "standard": standard}
    (repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")


def test_declared_sources_are_part_of_the_ratchet(repo: Path, capsys) -> None:
    (repo / "n.txt").write_text("3", encoding="utf-8")
    command = "python -c \"print('errors:', open('n.txt').read().strip())\""
    _profile(repo, {"debt_sources": [{"name": "lint", "command": command, "numbers": {"errors": r"errors: (\d+)"}}]})
    _debt("baseline")
    assert _baseline(repo)["sources"] == {"lint": {"errors": 3}}
    (repo / "n.txt").write_text("4", encoding="utf-8")
    capsys.readouterr()

    assert _debt("check") == 1

    assert "lint.errors 3 → 4" in capsys.readouterr().out


def test_a_source_that_does_not_match_exits_2(repo: Path, capsys) -> None:
    command = "python -c \"print('nothing')\""
    _profile(repo, {"debt_sources": [{"name": "lint", "command": command, "numbers": {"errors": r"errors: (\d+)"}}]})

    assert _debt("baseline") == 2

    assert "lint: no match for errors" in capsys.readouterr().err


def test_tightening_a_limit_needs_no_acceptance(repo: Path) -> None:
    _debt("baseline")
    _profile(repo, {"limits": {"function": 10}})

    assert _debt("check") == 0
    assert _debt("baseline") == 0

    data = _baseline(repo)
    assert data["limits"]["function"] == 10 and data["accepted"] == []
    assert _debt("check") == 0


def test_loosening_a_limit_in_the_profile_fails_the_check(repo: Path) -> None:
    _debt("baseline")
    _profile(repo, {"limits": {"function": 30}})

    assert _debt("check") == 1


def test_narrowing_the_scope_in_the_profile_fails_the_check(repo: Path) -> None:
    _debt("baseline")
    _profile(repo, {"metrics": {"include": ["src/**"]}})

    assert _debt("check") == 1


def test_debt_needs_an_initialized_project(git_repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(git_repo)

    assert _debt("check") == 2

    assert "not an initialized APM project" in capsys.readouterr().err


def test_debt_works_from_a_subdirectory(repo: Path, monkeypatch) -> None:
    (repo / "sub").mkdir()
    monkeypatch.chdir(repo / "sub")

    assert _debt("baseline") == 0

    assert (repo / DEBT).exists() and _debt("check") == 0


def test_debt_needs_a_subcommand(repo: Path) -> None:
    assert _debt() == 2


def test_the_report_lists_regressions_then_moves_then_improvements_then_the_hint() -> None:
    result = Comparison(("grew: a.py::f 18 → 19",), ("fixed: b.py::g (20 lines)",), ("moved: c.py::h → d.py::h",))

    lines = render_comparison(result).splitlines()
    order = [next(i for i, line in enumerate(lines) if text in line)
             for text in ("grew: a.py::f", "moved: c.py::h", "fixed: b.py::g")]

    assert order == sorted(order)
    assert not any("apm debt baseline" in line for line in lines)


def test_the_hint_appears_only_when_nothing_is_worse() -> None:
    better = Comparison((), ("fixed: b.py::g (20 lines)",))

    assert render_comparison(better).splitlines()[-1].endswith("to record these improvements")
    assert render_comparison(Comparison((), ())) == "debt: nothing worse than the baseline"
