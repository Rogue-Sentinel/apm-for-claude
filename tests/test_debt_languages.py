import pytest

from apm.cli_errors import DebtError
from apm.debt import compare
from apm.debt_store import validate
from debt_helpers import file_metric, snap


def _legacy(snapshot: dict) -> dict:
    return {k: v for k, v in snapshot.items() if k not in ("measured_languages", "file_languages")}


def _qml(lines: int = 250):
    return file_metric("ui/Main.qml", lines=lines, language="QML")


def test_snapshot_records_the_measured_languages_and_the_language_of_each_long_file() -> None:
    result = snap(_qml(), file_metric("a.py"))

    assert "QML" in result["measured_languages"]
    assert result["measured_languages"] == sorted(result["measured_languages"])
    assert result["file_languages"] == {"ui/Main.qml": "QML"}


def test_a_legacy_baseline_does_not_count_a_newly_measured_long_file_as_debt() -> None:
    base = _legacy(snap(file_metric("a.py")))

    result = compare(base, snap(file_metric("a.py"), _qml()))

    assert not result.worse
    assert result.newly_measured == ("newly measured: ui/Main.qml (250 lines; the baseline did not measure QML files)",)
    assert not any("long_files" in line or "excess_file_lines" in line for line in result.regressions)


def test_a_new_long_python_file_is_still_a_regression_against_a_legacy_baseline() -> None:
    base = _legacy(snap(file_metric("a.py")))

    result = compare(base, snap(file_metric("a.py"), file_metric("b.py", lines=250)))

    assert "new over-limit file: b.py (250 lines)" in result.regressions


def test_once_recorded_a_long_qml_file_that_grows_is_a_regression() -> None:
    result = compare(snap(_qml(250)), snap(_qml(260)))

    assert "grew: ui/Main.qml 250 → 260" in result.regressions
    assert result.newly_measured == ()


def test_a_new_long_qml_file_against_a_baseline_that_measured_qml_is_a_regression() -> None:
    result = compare(snap(), snap(_qml()))

    assert "new over-limit file: ui/Main.qml (250 lines)" in result.regressions


def test_dropping_a_language_from_the_current_snapshot_is_a_regression() -> None:
    current = snap()
    current["measured_languages"] = [name for name in current["measured_languages"] if name != "QML"]

    result = compare(snap(), current)

    assert "language no longer measured: QML" in result.regressions


def test_a_long_file_with_no_recorded_language_is_judged_as_measured() -> None:
    base = _legacy(snap())

    result = compare(base, {**snap(_qml()), "file_languages": {}})

    assert "new over-limit file: ui/Main.qml (250 lines)" in result.regressions


@pytest.mark.parametrize("field, value", [("measured_languages", "QML"), ("file_languages", {"a": 3})])
def test_a_hand_broken_language_field_is_rejected(field: str, value: object) -> None:
    with pytest.raises(DebtError, match="has the wrong shape"):
        validate({**snap(), field: value}, "baseline")
