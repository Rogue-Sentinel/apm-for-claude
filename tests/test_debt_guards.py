from datetime import datetime, timedelta, timezone

import pytest

from apm.debt import accept, compare
from apm.standard_config import Limits
from debt_helpers import file_metric as fm, snap


def _without_limit(snapshot: dict, name: str) -> dict:
    return {**snapshot, "limits": {k: v for k, v in snapshot["limits"].items() if k != name}}


def test_limit_missing_from_the_current_snapshot_is_a_regression() -> None:
    base = snap(fm("a.py"))

    result = compare(base, _without_limit(base, "function"))

    assert "limit missing: function" in result.regressions


def test_limit_missing_from_the_base_is_a_regression() -> None:
    current = snap(fm("a.py"))

    result = compare(_without_limit(current, "file"), current)

    assert "limit missing: file" in result.regressions


def test_base_with_no_limits_at_all_is_a_regression() -> None:
    current = snap(fm("a.py"))
    base = {k: v for k, v in current.items() if k != "limits"}

    result = compare(base, current)

    assert {"limit missing: function", "limit missing: file",
            "limit missing: public_methods"} <= set(result.regressions)


def test_unsupported_version_on_either_side_is_a_regression() -> None:
    good = snap(fm("a.py", 300))
    odd = {**good, "version": 2, "functions": {"x.py::f": 99}}

    assert compare(odd, good).regressions == ("baseline version 2 is not supported",)
    assert compare(good, odd).regressions == ("current version 2 is not supported",)
    assert compare(odd, odd).worse


def test_a_missing_version_is_unsupported() -> None:
    good = snap(fm("a.py"))
    old = {k: v for k, v in good.items() if k != "version"}

    assert compare(old, good).regressions == ("baseline version None is not supported",)


def test_loosened_file_and_public_method_limits_are_regressions() -> None:
    base = snap(fm("a.py"))
    current = snap(fm("a.py"), limits=Limits(file=250, public_methods=9))

    regressions = compare(base, current).regressions

    assert "limit loosened: file 200 → 250" in regressions
    assert "limit loosened: public_methods 7 → 9" in regressions


def test_new_wide_class_is_a_regression() -> None:
    base = snap(fm("a.py", 50, classes=[("Wide", 7)]))
    current = snap(fm("a.py", 50, classes=[("Wide", 7), ("Wider", 8)]))

    assert "new wide class: a.py::Wider (8 public methods)" in compare(base, current).regressions


def test_grown_wide_class_is_a_regression() -> None:
    base = snap(fm("a.py", 50, classes=[("Wide", 7)]))
    current = snap(fm("a.py", 50, classes=[("Wide", 9)]))

    assert "grew: a.py::Wide 7 → 9" in compare(base, current).regressions


def test_pure_file_move_is_not_a_regression() -> None:
    base = snap(fm("old/big.py", 300))
    current = snap(fm("new/big.py", 300))

    result = compare(base, current)

    assert not result.worse
    assert result.moves == ("moved: old/big.py → new/big.py (300 lines)",)


def test_accept_strips_the_reason_and_ignores_a_blank_one() -> None:
    now = datetime(2026, 10, 17, tzinfo=timezone.utc)
    previous = {"accepted": [{"reason": "first", "at": "t"}]}

    kept = accept(snap(fm("a.py")), previous, "  split later \n", now)["accepted"]
    blank = accept(snap(fm("a.py")), previous, "  \t\n", now)["accepted"]

    assert [entry["reason"] for entry in kept] == ["first", "split later"]
    assert blank == previous["accepted"]


def test_accept_requires_an_aware_time_and_records_utc() -> None:
    with pytest.raises(ValueError):
        accept(snap(fm("a.py")), None, "why", datetime(2026, 10, 17))

    plus_two = datetime(2026, 10, 17, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    entry = accept(snap(fm("a.py")), None, "why", plus_two)["accepted"][0]

    assert entry["at"] == "2026-10-17T12:00:00+00:00"
