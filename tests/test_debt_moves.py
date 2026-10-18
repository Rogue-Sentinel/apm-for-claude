from apm.debt import compare
from debt_helpers import file_metric as fm, snap


def test_moving_one_of_two_same_named_functions_out_is_a_move() -> None:
    base = snap(fm("a.py", 90, [("it", 20), ("it", 30)]), fm("b.py"))
    current = snap(fm("a.py", 50, [("it", 20)]), fm("b.py", 50, [("it", 30)]))

    result = compare(base, current)

    assert not result.worse
    assert result.moves == ("moved: a.py::it#2 → b.py::it (30 lines)",)


def test_moving_a_same_named_function_into_a_file_that_has_one_is_a_move() -> None:
    base = snap(fm("a.py", 50, [("it", 30)]), fm("b.py", 50, [("it", 20)]))
    current = snap(fm("a.py", 10), fm("b.py", 90, [("it", 20), ("it", 30)]))

    result = compare(base, current)

    assert not result.worse
    assert result.moves == ("moved: a.py::it → b.py::it#2 (30 lines)",)


def test_moving_a_same_named_function_and_growing_it_is_a_regression() -> None:
    base = snap(fm("a.py", 90, [("it", 20), ("it", 30)]), fm("b.py"))
    current = snap(fm("a.py", 50, [("it", 20)]), fm("b.py", 50, [("it", 31)]))

    result = compare(base, current)

    assert any(r.startswith("new over-limit function: b.py::it") for r in result.regressions)


def test_moving_a_property_getter_and_setter_pair_is_a_move() -> None:
    base = snap(fm("a.py", 90, [("value", 20), ("value", 25)]), fm("b.py"))
    current = snap(fm("a.py", 10), fm("b.py", 90, [("value", 20), ("value", 25)]))

    result = compare(base, current)

    assert not result.worse and len(result.moves) == 2


def test_moving_one_overload_of_three_is_a_move() -> None:
    base = snap(fm("A.java", 120, [("add", 20), ("add", 22), ("add", 30)]), fm("B.java"))
    current = snap(fm("A.java", 90, [("add", 20), ("add", 22)]), fm("B.java", 50, [("add", 30)]))

    result = compare(base, current)

    assert not result.worse and len(result.moves) == 1


def test_growing_inside_a_renumbered_group_names_both_keys() -> None:
    base = snap(fm("b.py", 90, [("it", 10), ("it", 20)]))
    current = snap(fm("b.py", 90, [("it", 30), ("it", 10)]))

    result = compare(base, current)

    assert "grew: b.py::it (was b.py::it#2) 20 → 30" in result.regressions
    assert not any(line.startswith("new over-limit") for line in result.regressions)


def test_one_key_is_not_both_shrunk_and_fixed() -> None:
    base = snap(fm("a.py", 90, [("it", 20), ("it", 25)]))
    current = snap(fm("a.py", 90, [("it", 18), ("it", 10)]))

    improvements = compare(base, current).improvements

    assert "shrank: a.py::it (was a.py::it#2) 25 → 18" in improvements
    assert "fixed: a.py::it (20 lines)" not in improvements
    assert any(line.startswith("fixed: a.py::it ") for line in improvements)


def test_result_does_not_depend_on_dict_order() -> None:
    base = snap(fm("a.py", 90, [("it", 20), ("it", 20)]), fm("b.py", 50, [("x", 30)]))
    current = snap(fm("a.py", 90, [("it", 20), ("it", 20), ("it", 20)]), fm("c.py", 50, [("x", 30)]))
    flipped_base = {**base, "functions": dict(reversed(base["functions"].items()))}
    flipped_current = {**current, "functions": dict(reversed(current["functions"].items()))}

    assert compare(base, current) == compare(flipped_base, flipped_current)
