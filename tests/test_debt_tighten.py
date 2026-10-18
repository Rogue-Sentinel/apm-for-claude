"""A tighter limit than the base's is not a regression: code fine under the old limit is not new debt."""
from apm.debt import compare
from apm.standard_config import Limits
from debt_helpers import file_metric as _file, snap as _snap

LOOSE = Limits(function=20, file=300, public_methods=9)
TIGHT = Limits(function=10, file=250, public_methods=6)


def test_tightening_the_function_limit_is_not_a_regression() -> None:
    base = _snap(_file("a.py", 50, [("f", 25)]), limits=LOOSE)
    current = _snap(_file("a.py", 50, [("f", 25), ("g", 14)]), limits=Limits(function=10))

    result = compare(base, current)

    assert not result.worse, result.regressions
    assert "limit tightened: function 20 → 10" in result.improvements


def test_a_function_over_the_old_limit_still_counts_after_tightening() -> None:
    base = _snap(_file("a.py", 50, [("f", 21)]), limits=LOOSE)
    current = _snap(_file("a.py", 50, [("f", 22), ("g", 14)]), limits=Limits(function=10))

    assert "grew: a.py::f 21 → 22" in compare(base, current).regressions


def test_a_new_function_over_the_old_limit_counts_after_tightening() -> None:
    base = _snap(_file("a.py", 50, [("f", 21)]), limits=LOOSE)
    current = _snap(_file("a.py", 90, [("f", 21), ("g", 30)]), limits=Limits(function=10))

    result = compare(base, current)

    assert any("new over-limit function: a.py::g" in line for line in result.regressions)
    assert any("total rose: long_functions" in line for line in result.regressions)


def test_tightening_every_limit_projects_files_classes_and_totals() -> None:
    base = _snap(_file("a.py", 310, [("f", 25)], [("C", 9)]), limits=LOOSE)
    current = _snap(_file("a.py", 310, [("f", 25), ("g", 12)], [("C", 9), ("D", 6)]),
                    _file("b.py", 260, [("h", 11)], [("E", 7)]), limits=TIGHT)

    result = compare(base, current)

    assert not result.worse, result.regressions


def test_the_projection_leaves_the_current_snapshot_untouched() -> None:
    base = _snap(_file("a.py", 50, [("f", 25)]), limits=LOOSE)
    current = _snap(_file("a.py", 50, [("f", 25), ("g", 14)]), limits=Limits(function=10))
    before = repr(current)

    compare(base, current)

    assert repr(current) == before


def test_a_loosened_limit_is_still_a_regression_when_another_is_tightened() -> None:
    base = _snap(_file("a.py", 50), limits=Limits(function=15, file=200))
    current = _snap(_file("a.py", 50), limits=Limits(function=10, file=250))

    assert "limit loosened: file 200 → 250" in compare(base, current).regressions


def test_the_tightened_snapshot_compares_cleanly_with_itself() -> None:
    tight = _snap(_file("a.py", 50, [("f", 25), ("g", 14)]), limits=Limits(function=10))

    result = compare(tight, tight)

    assert not result.worse and not result.improvements
