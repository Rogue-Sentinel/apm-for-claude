import json
from pathlib import Path

import pytest

from apm.metrics import (
    Report, measure_text, measure_tree, render_text, report_json, select_files, tracked_files,
)
from apm.metrics_model import ClassMetric, FileMetric, FunctionMetric
from apm.standard_config import DEFAULT_EXCLUDES, Limits, MetricsConfig
from conftest import run_git

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "metrics"


def _func(name: str, lines: int) -> str:
    return f"def {name}():\n" + "".join(f"    x{i} = {i}\n" for i in range(lines))


def _file(path: str, functions: tuple[FunctionMetric, ...] = (), lines: int = 5, **kw) -> FileMetric:
    return FileMetric(path, "Python", lines, functions, functions_measured=True, **kw)


def test_measure_text_dispatches_by_language_family() -> None:
    py = measure_text("a.py", _func("f", 2))
    js = measure_text("a.js", "function g() {\n  a();\n}\n")
    sh = measure_text("run.sh", "echo hi\n# note\n")

    assert (py.language, [f.name for f in py.functions]) == ("Python", ["f"])
    assert (js.language, [f.name for f in js.functions]) == ("JavaScript", ["g"])
    assert (sh.language, sh.lines, sh.functions_measured, sh.note) == ("Shell", 1, False, "")


def test_measure_text_ignores_unknown_extensions() -> None:
    assert measure_text("README.md", "# hi\n") is None


def test_select_files_include_and_exclude() -> None:
    paths = ["src/a.py", "src/vendor/b.js", "docs/readme.md", "src/c.unknown"]

    chosen = select_files(paths, MetricsConfig(include=("src/**",)))

    assert chosen == ["src/a.py"]


def test_select_files_with_empty_include_takes_every_known_language() -> None:
    paths = ["a.py", "b.md", "node_modules/x/y.js", "dist/app.js", "app.min.js", "api.generated.ts", ".apm/z.py"]

    assert select_files(paths, MetricsConfig()) == ["a.py"]


def test_select_files_exclude_replaces_defaults() -> None:
    config = MetricsConfig(exclude=("gen/**",))

    chosen = select_files(["gen/a.py", "dist/b.py"], config)

    assert chosen == ["dist/b.py"]


def test_tracked_files_lists_tracked_and_untracked_not_ignored(git_repo: Path) -> None:
    (git_repo / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (git_repo / "sub").mkdir()
    for name in ("tracked.py", "sub/new.py", "ignored.py"):
        (git_repo / name).write_text("x = 1\n", encoding="utf-8")
    run_git(git_repo, "add", "tracked.py")

    found = tracked_files(git_repo)

    assert found == [".gitignore", "sub/new.py", "tracked.py"]


def test_measure_tree_uses_tracked_and_untracked_not_ignored(git_repo: Path) -> None:
    (git_repo / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    for name in ("tracked.py", "untracked.py", "ignored.py"):
        (git_repo / name).write_text(_func("f", 3), encoding="utf-8")
    run_git(git_repo, "add", "tracked.py")

    report = measure_tree(git_repo, MetricsConfig())

    assert [f.path for f in report.files] == ["tracked.py", "untracked.py"]


def test_measure_tree_skips_a_tracked_file_that_was_deleted(git_repo: Path) -> None:
    (git_repo / "gone.py").write_text(_func("f", 1), encoding="utf-8")
    (git_repo / "kept.py").write_text(_func("f", 1), encoding="utf-8")
    run_git(git_repo, "add", ".")
    (git_repo / "gone.py").unlink()

    report = measure_tree(git_repo, MetricsConfig())

    assert [f.path for f in report.files] == ["kept.py"]


def test_measure_tree_restricts_to_given_paths(git_repo: Path) -> None:
    (git_repo / "src").mkdir()
    (git_repo / "lib").mkdir()
    for name in ("src/a.py", "src/b.py", "lib/c.py", "top.py"):
        (git_repo / name).write_text(_func("f", 1), encoding="utf-8")

    by_dir = measure_tree(git_repo, MetricsConfig(), ["src"])
    by_file = measure_tree(git_repo, MetricsConfig(), ["lib/c.py", "top.py"])

    assert [f.path for f in by_dir.files] == ["src/a.py", "src/b.py"]
    assert [f.path for f in by_file.files] == ["lib/c.py", "top.py"]


def test_measure_tree_path_prefix_does_not_match_sibling_names(git_repo: Path) -> None:
    (git_repo / "src").mkdir()
    (git_repo / "srcs").mkdir()
    for name in ("src/a.py", "srcs/b.py"):
        (git_repo / name).write_text(_func("f", 1), encoding="utf-8")

    report = measure_tree(git_repo, MetricsConfig(), ["src"])

    assert [f.path for f in report.files] == ["src/a.py"]


def test_measure_tree_reads_utf8_and_survives_undecodable_bytes(git_repo: Path) -> None:
    (git_repo / "a.py").write_text("s = 'café'\n", encoding="utf-8")
    (git_repo / "b.py").write_bytes(b"s = '\xff\xfe'\n")

    report = measure_tree(git_repo, MetricsConfig())

    assert [f.lines for f in report.files] == [1, 1]


def test_report_over_limit_lists_are_sorted_largest_first() -> None:
    small = _file("a.py", (FunctionMetric("ok", 1, 15), FunctionMetric("mid", 5, 16)), lines=100)
    big = _file("b.py", (FunctionMetric("huge", 2, 40),), lines=250)
    medium = _file("c.py", (FunctionMetric("big", 3, 20),), lines=201)

    report = Report((small, big, medium))
    limits = Limits()

    assert [(p, f.name) for p, f in report.over_functions(limits)] == [
        ("b.py", "huge"), ("c.py", "big"), ("a.py", "mid"),
    ]
    assert [f.path for f in report.over_files(limits)] == ["b.py", "c.py"]


def test_limits_are_strict_for_functions_and_files() -> None:
    at_limit = _file("a.py", (FunctionMetric("f", 1, 15),), lines=200)

    report = Report((at_limit,))

    assert report.over_functions(Limits()) == [] and report.over_files(Limits()) == []


def test_wide_classes_flag_at_the_limit_and_sort_largest_first() -> None:
    seven = _file("a.py", classes=(ClassMetric("Seven", 1, 7), ClassMetric("Six", 20, 6)))
    nine = _file("b.py", classes=(ClassMetric("Nine", 4, 9),))

    report = Report((seven, nine))

    assert [(p, c.name) for p, c in report.wide_classes(Limits())] == [("b.py", "Nine"), ("a.py", "Seven")]


def test_unmeasured_lists_files_with_a_note_largest_first() -> None:
    ok = _file("a.py")
    bad = FileMetric("b.js", "JavaScript", 50, note="unbalanced braces")
    worse = FileMetric("c.py", "Python", 90, note="syntax error: line 3")

    assert [f.path for f in Report((ok, bad, worse)).unmeasured()] == ["c.py", "b.js"]


def test_plain_files_are_kept_apart_from_real_failures() -> None:
    shell = FileMetric("run.sh", "Shell", 40)
    broken = FileMetric("b.js", "JavaScript", 50, note="unbalanced braces")
    ok = _file("a.py")

    report = Report((ok, shell, broken))

    assert [f.path for f in report.unmeasured()] == ["b.js"]
    assert [f.path for f in report.plain()] == ["run.sh"]


def test_plain_is_decided_by_the_language_table_not_the_note() -> None:
    odd_note = FileMetric("run.sh", "Shell", 40, note="syntax error: looks like a failure")
    quiet_failure = FileMetric("c.py", "Python", 9)

    report = Report((odd_note, quiet_failure))

    assert [f.path for f in report.plain()] == ["run.sh"]
    assert [f.path for f in report.unmeasured()] == ["c.py"]


def test_plain_lists_are_sorted_largest_first() -> None:
    files = (FileMetric("a.sh", "Shell", 5), FileMetric("b.sql", "SQL", 90))

    assert [f.path for f in Report(files).plain()] == ["b.sql", "a.sh"]


def test_render_text_shows_plain_files_in_their_own_section() -> None:
    files = (FileMetric("run.sh", "Shell", 40), FileMetric("b.js", "JavaScript", 10, note="unbalanced braces"))

    text = render_text(Report(files), Limits())

    assert "Files whose functions could not be measured: 1" in text
    assert "  b.js -- unbalanced braces" in text
    assert "Files measured for size only (no function scanner for the language): 1" in text
    assert "  run.sh -- 40 lines" in text


def test_render_text_summarizes_counts_and_items() -> None:
    files = (
        _file("a.py", (FunctionMetric("f", 3, 20), FunctionMetric("g", 30, 4)), lines=250,
              classes=(ClassMetric("Wide", 40, 8),)),
        FileMetric("b.js", "JavaScript", 10, note="unbalanced braces"),
    )

    text = render_text(Report(files), Limits())

    assert "Functions over 15 lines of logic: 1 of 2" in text
    assert "  a.py:3 f -- 20 lines" in text
    assert "Files over 200 lines of logic: 1 of 2" in text
    assert "  a.py -- 250 lines" in text
    assert "Review flags -- classes with 7+ public methods: 1" in text
    assert "  a.py:40 Wide -- 8 public methods" in text
    assert "Files whose functions could not be measured: 1" in text
    assert "  b.js -- unbalanced braces" in text


def test_render_text_for_a_clean_report_lists_nothing_under_the_counts() -> None:
    text = render_text(Report((_file("a.py", (FunctionMetric("f", 1, 2),)),)), Limits())

    assert text.splitlines() == [
        "Functions over 15 lines of logic: 0 of 1",
        "Files over 200 lines of logic: 0 of 1",
        "Review flags -- classes with 7+ public methods: 0",
        "Files whose functions could not be measured: 0",
        "Files measured for size only (no function scanner for the language): 0",
    ]


def test_report_json_carries_every_number() -> None:
    files = (_file("a.py", (FunctionMetric("f", 3, 20),), lines=250, classes=(ClassMetric("C", 1, 2),)),)

    data = report_json(Report(files), Limits(function=10, file=100, public_methods=5))

    assert json.loads(json.dumps(data)) == data
    assert data["limits"] == {"function": 10, "file": 100, "public_methods": 5}
    assert data["files"] == [{
        "path": "a.py", "language": "Python", "lines": 250, "functions_measured": True, "note": "", "plain": False,
        "functions": [{"name": "f", "line": 3, "lines": 20}],
        "classes": [{"name": "C", "line": 1, "public_methods": 2}],
    }]


def test_default_excludes_cover_the_plan_list() -> None:
    assert ".apm/**" in DEFAULT_EXCLUDES and "**/node_modules/**" in DEFAULT_EXCLUDES


@pytest.mark.parametrize("name", ["sample.py", "sample.c", "sample.go", "sample.rs", "sample.ts"])
def test_fixtures_measure_through_measure_text(name: str) -> None:
    metric = measure_text(name, (FIXTURES / name).read_text(encoding="utf-8"))

    assert metric is not None and metric.functions_measured and metric.functions


def test_plain_flag_in_json() -> None:
    report = Report((measure_text("run.sh", "echo hi\n"), measure_text("a.py", _func("f", 2))))

    files = {f["path"]: f for f in report_json(report, Limits())["files"]}

    assert (files["run.sh"]["plain"], files["a.py"]["plain"]) == (True, False)
