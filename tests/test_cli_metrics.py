import json
from pathlib import Path

import pytest

import apm_cli
from apm.paths import find_project
from apm.state_store import init_state


def _big_function(lines: int = 20) -> str:
    return "def big():\n" + "".join(f"    x{i} = {i}\n" for i in range(lines))


@pytest.fixture
def project(git_repo: Path, monkeypatch) -> Path:
    (git_repo / "big.py").write_text(_big_function(), encoding="utf-8")
    (git_repo / "small.py").write_text("def small():\n    return 1\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    return git_repo


def _initialize(repo: Path, standard: dict) -> None:
    (repo / ".apm").mkdir()
    profile = {"framework_version": "0.2.0", "standard": standard}
    (repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")


def test_cli_metrics_outside_apm_project(project: Path, capsys) -> None:
    assert apm_cli.main(["metrics"]) == 0

    out = capsys.readouterr().out
    assert "Functions over 15 lines of logic: 1 of 2" in out
    assert "big.py:1 big -- 20 lines" in out


def test_cli_metrics_json_round_trips(project: Path, capsys) -> None:
    assert apm_cli.main(["metrics", "--json"]) == 0

    data = json.loads(capsys.readouterr().out)
    assert data["limits"] == {"function": 15, "file": 200, "public_methods": 7}
    assert {f["path"] for f in data["files"]} == {"big.py", "small.py"}
    big = next(f for f in data["files"] if f["path"] == "big.py")
    assert big["functions"] == [{"name": "big", "line": 1, "lines": 20}]


def test_cli_metrics_takes_paths_relative_to_the_current_directory(project: Path, monkeypatch, capsys) -> None:
    (project / "sub").mkdir()
    (project / "sub" / "inner.py").write_text(_big_function(30), encoding="utf-8")

    assert apm_cli.main(["metrics", "sub"]) == 0
    from_root = capsys.readouterr().out
    monkeypatch.chdir(project / "sub")
    assert apm_cli.main(["metrics", "inner.py"]) == 0
    from_sub = capsys.readouterr().out

    assert "sub/inner.py:1 big -- 30 lines" in from_root
    assert "Functions over 15 lines of logic: 1 of 1" in from_root
    assert from_sub == from_root


def test_cli_metrics_from_a_subdirectory_measures_the_whole_repo(project: Path, monkeypatch, capsys) -> None:
    (project / "sub").mkdir()
    monkeypatch.chdir(project / "sub")

    assert apm_cli.main(["metrics"]) == 0

    assert "of 2" in capsys.readouterr().out


def test_cli_metrics_path_outside_the_repo_is_an_error(project: Path, tmp_path: Path, capsys) -> None:
    assert apm_cli.main(["metrics", str(tmp_path)]) == 2

    assert "outside" in capsys.readouterr().err


def test_cli_metrics_exits_zero_even_when_over_limits(project: Path) -> None:
    assert apm_cli.main(["metrics", "big.py"]) == 0


def test_cli_metrics_outside_a_git_repository_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert apm_cli.main(["metrics"]) == 2

    assert "not inside a git repository" in capsys.readouterr().err


def test_cli_metrics_uses_the_profile_standard(project: Path, capsys) -> None:
    _initialize(project, {"limits": {"function": 30}, "metrics": {"include": ["big.py"]}})

    assert apm_cli.main(["metrics"]) == 0

    out = capsys.readouterr().out
    assert "Functions over 30 lines of logic: 0 of 1" in out


def test_cli_metrics_works_without_state_set_up(project: Path, capsys) -> None:
    _initialize(project, {})

    assert apm_cli.main(["metrics"]) == 0
    assert "Functions over 15" in capsys.readouterr().out


def test_cli_metrics_with_a_bad_profile_standard_fails(project: Path, capsys) -> None:
    _initialize(project, {"limits": {"function": 0}})

    assert apm_cli.main(["metrics"]) == 2

    assert "limits.function" in capsys.readouterr().err


def test_cli_metrics_works_when_state_is_set_up(project: Path) -> None:
    _initialize(project, {})
    init_state(find_project(project))

    assert apm_cli.main(["metrics"]) == 0


@pytest.mark.parametrize("argv", [["brief"], ["issue", "1", "--title", "T"], ["task", "1", "t1"]])
def test_other_subcommands_still_need_an_initialized_project(project: Path, argv: list[str], capsys) -> None:
    assert apm_cli.main(argv) == 2

    assert "not an initialized APM project" in capsys.readouterr().err


def test_state_subcommands_still_need_state(project: Path, capsys) -> None:
    _initialize(project, {})

    assert apm_cli.main(["issue", "1", "--title", "T"]) == 2

    assert "state is not set up" in capsys.readouterr().err


def test_setup_still_needs_only_a_repository(tmp_path: Path, monkeypatch, capsys) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert apm_cli.main(["setup"]) == 2

    assert "not inside a git repository" in capsys.readouterr().err


def test_a_none_requirement_runs_anywhere(tmp_path: Path, monkeypatch) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert apm_cli.project_for("none") is None


def test_the_requirement_table_keeps_plan_one_behavior() -> None:
    assert apm_cli.REQUIREMENTS == {"setup": "repo", "metrics": "repo", "brief": "profile", "debt": "profile", "coverage": "none"}


def test_cli_metrics_path_that_does_not_exist_is_an_error(project: Path, capsys) -> None:
    assert apm_cli.main(["metrics", "nope.py"]) == 2

    assert "nope.py does not exist" in capsys.readouterr().err


def test_an_unknown_requirement_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="requirement"):
        apm_cli.project_for("everything")
