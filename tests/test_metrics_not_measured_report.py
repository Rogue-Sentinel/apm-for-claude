"""The metrics report lists the in-scope text files it had no language for, so an empty report never reads as clean."""
from __future__ import annotations

import json
from pathlib import Path

import apm_cli
from apm.metrics import Report, measure_tree, render_text, report_json
from apm.metrics_model import FileMetric
from apm.metrics_ref import measure_at_ref
from apm.standard_config import Limits, MetricsConfig
from conftest import run_git


def _write(repo: Path, name: str, content: str | bytes) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def _commit_all(repo: Path) -> None:
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "files")


def test_measure_tree_lists_text_files_with_no_language_as_not_measured(git_repo: Path) -> None:
    _write(git_repo, "a.py", "x = 1\n")
    _write(git_repo, "ui/Panel.qrc", "<RCC/>\n")
    _write(git_repo, "Makefile", "all:\n\techo hi\n")
    _write(git_repo, "README.md", "# Sample App\n")
    _write(git_repo, "logo.bin", b"\x00\x01")
    _write(git_repo, "marker.typed", "")

    report = measure_tree(git_repo, MetricsConfig())

    assert report.not_measured == ("Makefile", "ui/Panel.qrc")
    assert [f.path for f in report.files] == ["a.py"]


def test_the_new_size_only_languages_are_measured_not_listed(git_repo: Path) -> None:
    for name in ("ui/Main.qml", "setup.iss", "CMakeLists.txt", "cmake/deps.cmake"):
        _write(git_repo, name, "Item\n")

    report = measure_tree(git_repo, MetricsConfig())

    assert report.not_measured == ()
    assert sorted(f.path for f in report.plain()) == ["CMakeLists.txt", "cmake/deps.cmake", "setup.iss", "ui/Main.qml"]


def test_excluded_files_are_not_listed_as_not_measured(git_repo: Path) -> None:
    _write(git_repo, "vendor/lib/Tool.qrc", "<RCC/>\n")

    assert measure_tree(git_repo, MetricsConfig()).not_measured == ()


def test_files_outside_a_narrowed_include_are_not_listed_as_not_measured(git_repo: Path) -> None:
    _write(git_repo, "tools/Makefile", "all:\n")

    assert measure_tree(git_repo, MetricsConfig(include=("src/**",))).not_measured == ()


def test_paths_limit_the_not_measured_files(git_repo: Path) -> None:
    _write(git_repo, "Makefile", "all:\n")
    _write(git_repo, "sub/Makefile", "all:\n")

    assert measure_tree(git_repo, MetricsConfig(), ["sub"]).not_measured == ("sub/Makefile",)


def test_measure_at_ref_lists_the_same_not_measured_files(git_repo: Path) -> None:
    _write(git_repo, "Makefile", "all:\n")
    _write(git_repo, "ui/Panel.qrc", "<RCC/>\n")
    _write(git_repo, "logo.bin", b"\x00\x01")
    _commit_all(git_repo)
    (git_repo / "Makefile").unlink()

    report = measure_at_ref(git_repo, "HEAD", MetricsConfig())

    assert report.not_measured == ("Makefile", "ui/Panel.qrc")


def test_render_text_ends_with_the_not_measured_total_and_kinds() -> None:
    report = Report((FileMetric("a.py", "Python", 1),), ("a/Makefile", "ui/A.qrc", "ui/B.qrc"))

    lines = render_text(report, Limits()).splitlines()

    assert lines[-3:] == ["Files not measured: 3", "  .qrc: 2", "  Makefile: 1"]


def test_an_empty_report_still_says_files_were_not_measured() -> None:
    text = render_text(Report((), ("x.qrc",)), Limits())

    assert "Files over 200 lines of logic: 0 of 0" in text
    assert "Files not measured: 1" in text


def test_report_json_carries_the_not_measured_files() -> None:
    data = report_json(Report((), ("Makefile", "ui/A.qrc")), Limits())

    assert (data["files_not_measured"], data["not_measured"]) == (2, ["Makefile", "ui/A.qrc"])
    assert json.loads(json.dumps(data)) == data


def test_cli_metrics_reports_files_not_measured(git_repo: Path, monkeypatch, capsys) -> None:
    _write(git_repo, "a.py", "x = 1\n")
    _write(git_repo, "Makefile", "all:\n")
    monkeypatch.chdir(git_repo)

    apm_cli.main(["metrics"])
    text = capsys.readouterr().out
    apm_cli.main(["metrics", "--json"])
    data = json.loads(capsys.readouterr().out)

    assert "Files not measured: 1" in text
    assert "  Makefile: 1" in text
    assert data["files_not_measured"] == 1
