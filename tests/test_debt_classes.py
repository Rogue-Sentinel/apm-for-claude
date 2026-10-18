import pytest

from apm.cli_errors import DebtError
from apm.debt import compare
from apm.debt_store import validate
from debt_helpers import file_metric, snap


def _legacy(snapshot: dict) -> dict:
    return {k: v for k, v in snapshot.items() if k not in ("class_scanners", "class_languages")}


def _cpp(*classes, path: str = "db.h"):
    return file_metric(path, classes=classes, language="C++")


def test_snapshot_records_the_scanned_languages_and_the_language_of_each_wide_class_file() -> None:
    result = snap(_cpp(("Database", 7)), file_metric("a.py", classes=[("Slim", 3)]))

    assert result["class_scanners"] == ["C++", "Python"]
    assert result["class_languages"] == {"db.h": "C++"}


def test_a_legacy_baseline_does_not_count_newly_measured_cpp_classes_as_debt() -> None:
    base = _legacy(snap(_cpp()))

    result = compare(base, snap(_cpp(("Database", 7))))

    assert not result.worse
    assert result.newly_measured == (
        "newly measured: db.h::Database (7 public methods; the baseline did not measure C++ classes)",)
    assert not [line for line in result.regressions if "wide_classes" in line]


def test_a_new_wide_python_class_is_still_a_regression_against_a_legacy_baseline() -> None:
    base = _legacy(snap(_cpp()))

    result = compare(base, snap(_cpp(), file_metric("a.py", classes=[("Wide", 8)])))

    assert "new wide class: a.py::Wide (8 public methods)" in result.regressions


def test_once_recorded_a_cpp_class_that_grows_is_a_regression() -> None:
    result = compare(snap(_cpp(("Database", 7))), snap(_cpp(("Database", 9))))

    assert "grew: db.h::Database 7 → 9" in result.regressions
    assert result.newly_measured == ()


def test_a_new_cpp_class_against_a_baseline_that_scanned_cpp_is_a_regression() -> None:
    result = compare(snap(_cpp()), snap(_cpp(("Database", 7))))

    assert "new wide class: db.h::Database (7 public methods)" in result.regressions


def test_dropping_a_scanner_from_the_current_snapshot_is_a_regression() -> None:
    current = {**snap(_cpp()), "class_scanners": ["Python"]}

    result = compare(snap(_cpp()), current)

    assert "class scanner missing: C++" in result.regressions


def test_a_wide_class_with_no_recorded_language_is_judged_as_measured() -> None:
    current = {**snap(_cpp(("Database", 7))), "class_languages": {}}

    result = compare(_legacy(snap(_cpp())), current)

    assert "new wide class: db.h::Database (7 public methods)" in result.regressions


def test_a_class_the_base_already_lists_is_never_newly_measured_whatever_the_language_label() -> None:
    base = snap(_cpp(("Database", 7)))
    relabeled = snap(file_metric("db.h", classes=[("Database", 9)], language="Rust"))
    current = {**relabeled, "class_languages": {"db.h": "Rust"}}

    result = compare(base, current)

    assert "grew: db.h::Database 7 → 9" in result.regressions
    assert result.newly_measured == ()


@pytest.mark.parametrize("field, value", [("class_scanners", "C++"), ("class_languages", {"db.h": 3})])
def test_a_baseline_with_malformed_class_fields_is_rejected(field: str, value: object) -> None:
    data = {**snap(_cpp()), field: value}

    with pytest.raises(DebtError, match=f"{field} has the wrong shape"):
        validate(data, "baseline")
