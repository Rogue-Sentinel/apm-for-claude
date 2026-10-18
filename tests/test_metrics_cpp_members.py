import pytest

from apm.metrics import measure_text


def _classes(text: str) -> list[tuple[str, int, int]]:
    return [(c.name, c.line, c.public_methods) for c in measure_text("a.hpp", text).classes]


def _count(member: str) -> int:
    [(_, _, count)] = _classes(f"struct A {{\n{member}\n}};\n")
    return count


@pytest.mark.parametrize("member", [
    "std::function<void(int)> on_operator_change;",
    "std::string operator_name = default_name();",
    "int operator_id = f();",
])
def test_a_data_member_whose_name_contains_operator_is_not_a_method(member: str) -> None:
    assert _count(member) == 0


@pytest.mark.parametrize("member", ["void (*handlers[4])(int);", "char (&ref)[10];"])
def test_an_array_of_function_pointers_or_a_reference_to_an_array_is_not_a_method(member: str) -> None:
    assert _count(member) == 0


def test_a_struct_with_an_attribute_before_its_name_is_still_a_class() -> None:
    methods = "".join(f"void m{n}();\n" for n in range(7))

    assert _classes(f"struct __attribute__((packed)) P {{\n{methods}}};\n") == [("P", 1, 7)]


def test_a_conversion_operator_to_a_template_type_is_counted() -> None:
    assert _count("operator std::vector<int>() const;") == 1
