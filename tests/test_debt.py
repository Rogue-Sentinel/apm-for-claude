from datetime import datetime, timezone

from apm.debt import Comparison, accept, compare, snapshot
from apm.metrics import Report
from apm.metrics_model import ClassMetric, FileMetric, FunctionMetric
from apm.standard_config import Limits

LIMITS = Limits()


def _file(path: str, lines: int = 10, funcs=(), classes=(), measured: bool = True,
          language: str = "Python") -> FileMetric:
    fns = tuple(FunctionMetric(name, 1 + i * 50, n) for i, (name, n) in enumerate(funcs))
    cls = tuple(ClassMetric(name, 1, n) for name, n in classes)
    return FileMetric(path, language, lines, fns, cls, functions_measured=measured,
                      note="" if measured else "syntax error")


def _snap(*files: FileMetric, sources=None) -> dict:
    return snapshot(Report(tuple(files)), LIMITS, sources)


def test_snapshot_lists_only_over_limit_items_and_totals() -> None:
    report = Report((
        _file("a.py", 230, [("big", 20), ("ok", 15)], [("Wide", 9), ("Slim", 3)]),
        _file("bad.py", 40, measured=False),
        _file("run.sh", 500, measured=False, language="Shell"),
    ))
    snap = snapshot(report, LIMITS, {"ruff": {"errors": 4}})

    assert snap["version"] == 1 and snap["accepted"] == []
    assert snap["limits"] == {"function": 15, "file": 200, "public_methods": 7}
    assert snap["functions"] == {"a.py::big": 20}
    assert snap["files"] == {"a.py": 230, "run.sh": 500}
    assert snap["classes"] == {"a.py::Wide": 9}
    assert snap["unmeasured"] == ["bad.py"]
    assert snap["sources"] == {"ruff": {"errors": 4}}
    assert snap["totals"] == {
        "long_functions": 1, "long_files": 2, "wide_classes": 1,
        "excess_function_lines": 5, "excess_file_lines": 30 + 300, "unmeasured_files": 1,
    }


def test_snapshot_numbers_duplicate_names_in_source_order() -> None:
    snap = _snap(_file("a.py", 60, [("it", 20), ("it", 10), ("it", 25), ("other", 30)]))

    assert snap["functions"] == {"a.py::it": 20, "a.py::it#3": 25, "a.py::other": 30}


def test_plain_language_files_count_for_size_only() -> None:
    snap = _snap(_file("run.sh", 300, measured=False, language="Shell"))

    assert snap["unmeasured"] == [] and snap["totals"]["unmeasured_files"] == 0
    assert snap["files"] == {"run.sh": 300}


def test_identical_snapshots_have_no_regressions() -> None:
    snap = _snap(_file("a.py", 210, [("f", 20)], [("C", 8)]), sources={"x": {"n": 1}})

    result = compare(snap, snap)

    assert result == Comparison((), ()) and not result.worse


def test_growing_an_over_limit_function_is_a_regression() -> None:
    base = _snap(_file("a.py", 50, [("f", 18)]))
    current = _snap(_file("a.py", 50, [("f", 19)]))

    result = compare(base, current)

    assert result.worse and "grew: a.py::f 18 → 19" in result.regressions


def test_new_over_limit_function_is_a_regression() -> None:
    base = _snap(_file("a.py", 50, [("f", 18)]))
    current = _snap(_file("a.py", 90, [("f", 18), ("g", 16)]))

    result = compare(base, current)

    assert "new over-limit function: a.py::g (16 lines)" in result.regressions


def test_pure_move_to_another_file_is_not_a_regression() -> None:
    base = _snap(_file("a.py", 50, [("load", 30)]), _file("b.py", 10))
    current = _snap(_file("a.py", 10), _file("b.py", 50, [("load", 30)]))

    result = compare(base, current)

    assert not result.worse
    assert result.moves == ("moved: a.py::load → b.py::load (30 lines)",)


def test_move_that_grows_is_a_regression() -> None:
    base = _snap(_file("a.py", 50, [("load", 30)]), _file("b.py", 10))
    current = _snap(_file("a.py", 10), _file("b.py", 50, [("load", 31)]))

    result = compare(base, current)

    assert any(r.startswith("new over-limit function: b.py::load") for r in result.regressions)
    assert result.moves == ()


def test_reordering_same_named_functions_is_not_a_regression() -> None:
    base = _snap(_file("a.py", 90, [("it", 20), ("it", 25)]))
    current = _snap(_file("a.py", 90, [("it", 25), ("it", 20)]))

    assert not compare(base, current).worse


def test_renumbering_after_a_sibling_shrinks_is_not_a_regression() -> None:
    base = _snap(_file("a.py", 90, [("it", 20), ("it", 25)]))
    current = _snap(_file("a.py", 90, [("it", 10), ("it", 25)]))

    result = compare(base, current)

    assert not result.worse and result.improvements


def test_a_sibling_crossing_the_limit_is_a_regression() -> None:
    base = _snap(_file("a.py", 90, [("it", 10), ("it", 25)]))
    current = _snap(_file("a.py", 90, [("it", 16), ("it", 25)]))

    assert compare(base, current).worse


def test_splitting_a_file_into_two_over_limit_files_is_a_regression() -> None:
    base = _snap(_file("big.py", 420))
    current = _snap(_file("one.py", 210), _file("two.py", 210))

    result = compare(base, current)

    assert "total rose: long_files 1 → 2" in result.regressions


def test_loosened_limit_is_a_regression() -> None:
    base = _snap(_file("a.py"))
    current = snapshot(Report((_file("a.py"),)), Limits(function=20))

    assert "limit loosened: function 15 → 20" in compare(base, current).regressions


def test_source_metric_rise_and_disappearance_are_regressions() -> None:
    base = _snap(sources={"ruff": {"errors": 4, "warnings": 2}, "mypy": {"errors": 1}})
    current = _snap(sources={"ruff": {"errors": 5}})

    regressions = compare(base, current).regressions

    assert "source metric rose: ruff.errors 4 → 5" in regressions
    assert "source metric disappeared: ruff.warnings" in regressions
    assert "source disappeared: mypy" in regressions


def test_newly_unmeasured_file_is_a_regression_and_measuring_again_is_an_improvement() -> None:
    clean = _snap(_file("a.py", 10))
    broken = _snap(_file("a.py", 10, measured=False))

    assert "now unmeasured: a.py" in compare(clean, broken).regressions
    assert "measures again: a.py" in compare(broken, clean).improvements


def test_shrinking_is_an_improvement_and_not_a_regression() -> None:
    base = _snap(_file("a.py", 300, [("f", 30)], [("C", 9)]), sources={"x": {"n": 3}})
    current = _snap(_file("a.py", 250, [("f", 20)], [("C", 8)]), sources={"x": {"n": 2}})

    result = compare(base, current)

    assert not result.worse and result.improvements


def test_items_leaving_are_improvements() -> None:
    base = _snap(_file("a.py", 250, [("f", 30)]))
    current = _snap(_file("a.py", 100))

    assert "fixed: a.py::f (30 lines)" in compare(base, current).improvements


def test_accept_appends_reason_and_keeps_history() -> None:
    previous = {"accepted": [{"reason": "first", "at": "2026-01-01T00:00:00+00:00"}]}
    new = _snap(_file("a.py"))
    now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)

    accepted = accept(new, previous, "split later", now)

    assert accepted["accepted"] == [
        previous["accepted"][0], {"reason": "split later", "at": "2026-10-17T12:00:00+00:00"}]
    assert new["accepted"] == []


def test_accept_without_reason_carries_history_forward() -> None:
    previous = {"accepted": [{"reason": "first", "at": "t"}]}
    now = datetime(2026, 10, 17, tzinfo=timezone.utc)

    assert accept(_snap(), previous, "", now)["accepted"] == previous["accepted"]
    assert accept(_snap(), None, "", now)["accepted"] == []
