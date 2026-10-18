import json
from pathlib import Path

import pytest

from apm.debt_store import DEBT_FILE, DebtError, baseline_at, current_snapshot, load_baseline, write_baseline
from apm.standard_config import DebtSource, Limits, MetricsConfig, Standard
from conftest import run_git
from debt_helpers import file_metric as _file, snap as _snap

GOOD = _snap(_file("a.py", 50, [("f", 20)]), sources={"ruff": {"errors": 4}})


def test_debt_file_is_under_the_apm_directory() -> None:
    assert DEBT_FILE == ".apm/debt.json"


def test_write_then_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / ".apm" / "debt.json"

    write_baseline(path, GOOD)

    assert load_baseline(path) == GOOD
    text = path.read_text(encoding="utf-8")
    assert text.endswith("}\n") and '\n  "accepted"' in text
    assert text.index('"accepted"') < text.index('"version"')


def test_missing_baseline_is_none(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "nope.json") is None


@pytest.mark.parametrize("text", ["{not json", "[]", "5", ""])
def test_corrupt_baseline_raises(tmp_path: Path, text: str) -> None:
    path = tmp_path / "debt.json"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(DebtError, match="debt.json"):
        load_baseline(path)


def _bad(**change: object) -> dict:
    return {**json.loads(json.dumps(GOOD)), **change}


@pytest.mark.parametrize(
    "change",
    [
        {"version": "1"}, {"limits": []}, {"limits": {"function": "15"}}, {"limits": {"function": True}},
        {"totals": {"long_functions": 1.5}}, {"functions": {"a.py::f": "20"}}, {"functions": []},
        {"files": {"a.py": None}}, {"classes": {"a.py::C": [8]}}, {"unmeasured": "a.py"},
        {"unmeasured": [1]}, {"sources": {"ruff": 4}}, {"sources": {"ruff": {"errors": "4"}}},
        {"accepted": {"reason": "x"}}, {"accepted": ["x"]}, {"accepted": [{"reason": 5, "at": "t"}]},
        {"scope": {"include": "a"}}, {"scope": {"exclude": [1]}}, {"scope": {"builtin": "yes"}}, {"scope": []},
    ],
    ids=lambda change: next(iter(change)) + "=" + json.dumps(next(iter(change.values())))[:20],
)
def test_a_hand_edited_bad_shape_raises_instead_of_crashing_compare(tmp_path: Path, change: dict) -> None:
    path = tmp_path / "debt.json"
    path.write_text(json.dumps(_bad(**change)), encoding="utf-8")

    with pytest.raises(DebtError, match="debt.json"):
        load_baseline(path)


def test_a_baseline_without_optional_sections_still_loads(tmp_path: Path) -> None:
    path = tmp_path / "debt.json"
    path.write_text(json.dumps({"version": 1, "limits": {"function": 15}}), encoding="utf-8")

    assert load_baseline(path) == {"version": 1, "limits": {"function": 15}}


def _commit_baseline(repo: Path, snapshot: dict) -> None:
    write_baseline(repo / DEBT_FILE, snapshot)
    run_git(repo, "add", DEBT_FILE)
    run_git(repo, "commit", "-m", "baseline")


def test_baseline_at_ref_reads_the_committed_file(git_repo: Path) -> None:
    _commit_baseline(git_repo, GOOD)
    write_baseline(git_repo / DEBT_FILE, _snap())

    assert baseline_at(git_repo, "main") == GOOD
    assert baseline_at(git_repo, "HEAD") == GOOD


def test_baseline_at_ref_missing_file_is_none(git_repo: Path) -> None:
    assert baseline_at(git_repo, "main") is None


def test_baseline_at_unknown_ref_raises(git_repo: Path) -> None:
    with pytest.raises(DebtError, match="unknown ref nope"):
        baseline_at(git_repo, "nope")


def test_baseline_at_a_ref_that_looks_like_an_option_raises(git_repo: Path) -> None:
    with pytest.raises(DebtError, match="unknown ref"):
        baseline_at(git_repo, "--output=x")


def test_baseline_at_ref_with_a_corrupt_file_raises(git_repo: Path) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / DEBT_FILE).write_text("{oops", encoding="utf-8")
    run_git(git_repo, "add", DEBT_FILE)
    run_git(git_repo, "commit", "-m", "bad")

    with pytest.raises(DebtError, match="main:.apm/debt.json"):
        baseline_at(git_repo, "main")


def _two_files(repo: Path) -> None:
    (repo / "big.py").write_text("def big():\n" + "".join(f"    x{i} = 1\n" for i in range(20)), encoding="utf-8")
    run_git(repo, "add", "big.py")


def test_current_snapshot_measures_and_records_scope_and_limits(git_repo: Path) -> None:
    _two_files(git_repo)

    snap = current_snapshot(git_repo, Standard(Limits(), MetricsConfig(), ()))

    assert snap["functions"] == {"big.py::big": 20}
    assert snap["scope"]["builtin"] is True and snap["limits"]["function"] == 15


def test_current_snapshot_with_builtin_off_measures_nothing_and_says_so(git_repo: Path) -> None:
    _two_files(git_repo)

    snap = current_snapshot(git_repo, Standard(Limits(), MetricsConfig(builtin=False), ()))

    assert snap["functions"] == {} and snap["scope"]["builtin"] is False


def test_current_snapshot_adds_every_declared_source(git_repo: Path) -> None:
    command = "python -c \"print('errors: 3')\""
    source = DebtSource("lint", command, {"errors": r"errors: (\d+)"})

    snap = current_snapshot(git_repo, Standard(Limits(), MetricsConfig(), (source,)))

    assert snap["sources"] == {"lint": {"errors": 3}}


def test_current_snapshot_uses_the_projects_real_scope(git_repo: Path) -> None:
    _two_files(git_repo)

    snap = current_snapshot(git_repo, Standard(Limits(), MetricsConfig(include=("src/**",)), ()))

    assert snap["scope"]["include"] == ["src/**"] and snap["functions"] == {}
