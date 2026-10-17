"""Python files measured through tokenize and the ast."""
from __future__ import annotations

from pathlib import Path

from apm.metrics_python import measure_python

_SAMPLE = Path(__file__).parent / "fixtures" / "metrics" / "sample.py"


def _lines_by_name(metric) -> dict[str, int]:
    return {f.name: f.lines for f in metric.functions}


def test_docstring_and_comments_are_not_logic():
    text = 'def f():\n    """One.\n    Two.\n    Three."""\n    # note\n    a = 1\n    return a\n'
    metric = measure_python("a.py", text)
    assert _lines_by_name(metric) == {"f": 2}
    assert metric.lines == 3


def test_multiline_string_value_is_logic():
    text = 'def f():\n    x = """a\n    { b\n    c"""\n    return x\n'
    metric = measure_python("a.py", text)
    assert _lines_by_name(metric) == {"f": 4}
    assert metric.lines == 5


def test_methods_are_qualified_and_nested_counted_in_parent():
    text = (
        "class A:\n"
        "    def m(self):\n"
        "        def inner():\n"
        "            return 1\n"
        "        return inner()\n"
        "def top():\n"
        "    pass\n"
    )
    metric = measure_python("a.py", text)
    assert _lines_by_name(metric) == {"A.m": 3, "A.m.inner": 1, "top": 1}
    assert [(f.name, f.line) for f in metric.functions] == [("A.m", 2), ("A.m.inner", 3), ("top", 6)]


def test_public_method_count_skips_private_and_dunder():
    text = "class A:\n    def __init__(self): pass\n    def _helper(self): pass\n    def a(self): pass\n    def b(self): pass\n"
    metric = measure_python("a.py", text)
    assert [(c.name, c.line, c.public_methods) for c in metric.classes] == [("A", 1, 2)]


def test_async_methods_and_nested_classes_are_counted():
    text = "class A:\n    async def go(self): pass\n    class B:\n        def x(self): pass\n"
    metric = measure_python("a.py", text)
    counts = {c.name: c.public_methods for c in metric.classes}
    assert counts == {"A": 1, "A.B": 1}
    assert set(_lines_by_name(metric)) == {"A.go", "A.B.x"}


def test_decorator_and_signature_lines_are_not_body():
    text = "@deco\ndef f(\n    a,\n    b,\n):\n    return a\n"
    metric = measure_python("a.py", text)
    assert metric.functions[0].line == 2
    assert metric.functions[0].lines == 1


def test_lone_bracket_lines_are_not_logic():
    text = "def f():\n    return [\n        1,\n    ]\n"
    assert _lines_by_name(measure_python("a.py", text)) == {"f": 2}


def test_docstring_only_function_has_no_logic_lines():
    text = 'def f():\n    """Only a docstring."""\n'
    metric = measure_python("a.py", text)
    assert _lines_by_name(metric) == {"f": 0}
    assert metric.lines == 1


def test_crlf_and_lone_cr_line_endings_count_the_same():
    text = "def f():\r\n    a = 1\r\n    return a\r\n"
    assert measure_python("a.py", text) == measure_python("a.py", text.replace("\r\n", "\n"))
    assert measure_python("a.py", text.replace("\r\n", "\r")).lines == 3


def test_metric_describes_a_measured_python_file():
    metric = measure_python("pkg/a.py", "x = 1\n")
    assert (metric.path, metric.language) == ("pkg/a.py", "Python")
    assert metric.functions_measured is True and metric.note == ""


def test_syntax_error_is_reported_not_raised():
    metric = measure_python("a.py", "def f(:\n    pass\nx = 1\n")
    assert metric.functions_measured is False
    assert metric.note.startswith("syntax error:")
    assert metric.functions == () and metric.classes == ()
    assert metric.lines == 3


def test_untokenizable_file_falls_back_to_the_plain_count():
    metric = measure_python("a.py", 'x = 1\ny = """open\n{\n')
    assert metric.functions_measured is False
    assert metric.note.startswith("syntax error:")
    assert metric.lines == 2


def test_empty_file_measures_zero():
    metric = measure_python("a.py", "")
    assert metric.lines == 0 and metric.functions_measured is True


def _hand_count() -> tuple[int, dict[str, int], dict[str, int]]:
    file_lines, functions, classes = 0, {}, {}
    for line in _SAMPLE.read_text(encoding="utf-8").splitlines():
        parts = line.removeprefix("# ").split()
        if line.startswith("# file "):
            file_lines = int(parts[1])
        elif line.startswith("# function "):
            functions[parts[1]] = int(parts[2])
        elif line.startswith("# class "):
            classes[parts[1]] = int(parts[2])
    return file_lines, functions, classes


def test_matches_a_hand_count():
    file_lines, functions, classes = _hand_count()
    metric = measure_python(str(_SAMPLE), _SAMPLE.read_text(encoding="utf-8"))
    assert functions and classes
    assert metric.lines == file_lines
    assert _lines_by_name(metric) == functions
    assert {c.name: c.public_methods for c in metric.classes} == classes
