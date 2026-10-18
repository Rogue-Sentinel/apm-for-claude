"""Brace scanner: statement boundaries, callbacks named after their callee, and name edge cases."""
from __future__ import annotations

import pytest

from braces_helpers import found as _found
from braces_helpers import measure as _measure


def test_known_limit_cpp_brace_initializer_list_is_misread():
    text = "A::A() : x_{1} {\n  a();\n  b();\n  c();\n}\n"
    assert _found("a.cpp", text) == [("A::A", 1)]  # misread: the true body has 3 lines


def test_braced_default_argument_does_not_split_the_signature():
    text = "T make(int a,\n       S s = {})\n{\n  go();\n  stop();\n}\n"
    assert _found("a.cpp", text) == [("make", 2)]


LEAKING_STATEMENTS = [
    ("a.go", 'import (\n"fmt"\n)\nfunc f() {\n  a()\n}\n', ("f", 1)),
    ("a.go", 'var ErrX = errors.New("x")\nfunc f() {\n  a()\n}\n', ("f", 1)),
    ("a.kt", "val xs = listOf(1)\nfun f() {\n  a()\n}\n", ("f", 1)),
    ("a.kt", "data class P(val x: Int)\nfun f() {\n  a()\n}\n", ("f", 1)),
    ("a.swift", "let x = foo(1)\nfunc f() {\n  a()\n}\n", ("f", 1)),
    ("a.swift", "class A {\n  var count: Int = 0\n  init(x: Int) {\n    a()\n  }\n}\n", ("init", 1)),
    ("a.ts", "class A {\n  x = foo()\n  m() {\n    a()\n  }\n}\n", ("m", 1)),
    ("a.js", "const a = require('a')\nfunction f() {\n  a()\n}\n", ("f", 1)),
    ("a.scala", "val x = foo(1)\ndef f(): Int = {\n  x\n}\n", ("f", 1)),
]


@pytest.mark.parametrize("path,text,expected", LEAKING_STATEMENTS)
def test_a_statement_without_a_semicolon_does_not_leak_into_the_next_head(path, text, expected):
    assert _found(path, text) == [expected]


CONTINUED_HEADS = [
    ("a.c", "int f(int x)\n{\n  return x;\n}\n", [("f", 1)]),
    ("a.c", "int f(int x,\n      int y)\n{\n  return x;\n}\n", [("f", 1)]),
    ("A.java", "void run()\n    throws IOException {\n  a();\n}\n", [("run", 1)]),
    ("a.c", "int\nfoo(int x) {\n  return x;\n}\n", [("foo", 1)]),
    ("a.cpp", "A::A()\n    : x_(1)\n    , y_(2)\n{\n  a();\n}\n", [("A::A", 1)]),
    ("a.rs", "fn f<T>(x: T)\nwhere\n    T: Copy,\n{\n    a();\n}\n", [("f", 1)]),
    ("a.rs", "fn f()\n    -> Self\n{\n    a();\n}\n", [("f", 1)]),
    ("a.kt", "val v = base\n    .map(1)\n\nfun f() {\n  a()\n}\n", [("f", 1)]),
]


@pytest.mark.parametrize("path,text,expected", CONTINUED_HEADS)
def test_a_signature_that_plainly_continues_stays_one_head(path, text, expected):
    assert _found(path, text) == expected


SUITE = """describe("x", () => {
  const a = 1;
  beforeEach(() => {
    setup();
  });
  it("a", () => {
    one();
    two();
  });
  it("b", () => {
    three();
  });
});
"""


def test_file_level_callbacks_are_named_after_their_callee_in_source_order():
    metric = _measure("a.test.js", SUITE)
    assert [(f.name, f.line, f.lines) for f in metric.functions] == [
        ("describe", 1, 4),
        ("beforeEach", 3, 1),
        ("it", 6, 2),
        ("it", 10, 1),
    ]


def test_repeated_callees_keep_their_plain_name_in_source_order():
    text = "it('a', () => {\n  a();\n});\nit('b', function () {\n  b();\n  c();\n});\n"
    assert _found("a.js", text) == [("it", 1), ("it", 2)]


def test_dotted_callee_and_iife():
    assert _found("a.js", "app.get('/', (req, res) => {\n  a();\n  b();\n});\n") == [("app.get", 2)]
    assert _found("a.js", "(function () {\n  a();\n})();\n") == [("<anonymous>", 1)]


def test_callback_inside_a_block_of_a_callback_is_reported_alone():
    text = "run(() => {\n  if (z) {\n    step(() => {\n      a();\n    });\n  }\n  b();\n});\n"
    assert _found("a.js", text) == [("run", 3), ("step", 1)]


def test_callbacks_inside_a_named_function_still_count_in_the_parent():
    text = "function load() {\n  items.map((x) => {\n    a();\n  });\n  b();\n}\n"
    assert _found("a.js", text) == [("load", 3)]


def test_object_literal_argument_in_a_callback_is_not_a_function():
    text = "run(() => {\n  go({ a: 1 });\n  stop();\n});\n"
    assert _found("a.js", text) == [("run", 2)]


def test_rust_visibility_with_a_path_is_not_a_function_name():
    assert _found("a.rs", "pub(crate) fn f() {\n    a();\n}\n") == [("f", 1)]
    assert _found("a.rs", "pub(super) fn g() {\n    a();\n}\n") == [("g", 1)]


def test_conversion_operator_keeps_the_space_in_its_name():
    text = "A::operator bool() const {\n  return ok;\n}\n"
    assert _found("a.cpp", text) == [("A::operator bool", 1)]


def test_signature_line_for_destructors_and_operators_on_their_own_line():
    metric = _measure("a.cpp", "int x;\nA::~A()\n{\n  go();\n}\nbool A::operator==(int o)\n{\n  go();\n}\n")
    assert [(f.name, f.line) for f in metric.functions] == [("A::~A", 2), ("A::operator==", 6)]


def test_a_function_and_callbacks_with_one_name_are_not_renumbered():
    text = "function route() {\n  a();\n}\nroute('/a', () => {\n  b();\n});\nroute('/b', () => {\n  c();\n});\n"
    assert _found("a.js", text) == [("route", 1), ("route", 1), ("route", 1)]


def test_multiline_generic_return_type_stays_one_head():
    text = "class A {\n  async load(): Promise<\n    number\n  > {\n    return 1;\n  }\n}\n"
    assert _found("a.ts", text) == [("load", 1)]
