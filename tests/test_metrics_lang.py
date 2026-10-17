"""Language table, comment and string stripping, and logic-line counting."""
from __future__ import annotations

import pytest

from apm.metrics_lang import (
    count_logic,
    is_logic_line,
    language_for,
    measure_plain,
    strip_code,
)


def _lang(path: str):
    language = language_for(path)
    assert language is not None
    return language


def test_language_for_known_and_unknown():
    assert language_for("src/a.TS").name == "TypeScript"
    assert language_for("src/a.TS").family == "brace"
    assert language_for("x.py").family == "python"
    assert language_for("run.sh").family == "plain"
    assert language_for("README.md") is None
    assert language_for("Makefile") is None


@pytest.mark.parametrize(
    "ext",
    "c h cc cpp cxx hpp hh cs java js jsx mjs cjs ts tsx go rs swift kt kts scala php dart m".split(),
)
def test_every_brace_extension_is_listed(ext):
    assert _lang(f"f.{ext}").family == "brace"


@pytest.mark.parametrize("ext", "sh bash ps1 rb lua sql pl r".split())
def test_every_plain_extension_is_listed(ext):
    assert _lang(f"f.{ext}").family == "plain"


def test_preprocessor_flag_and_backtick_quotes():
    assert _lang("a.cpp").preprocessor and _lang("a.cs").preprocessor
    assert _lang("a.c").preprocessor and _lang("a.m").preprocessor
    assert not _lang("a.java").preprocessor
    assert "`" in _lang("a.js").quotes and "`" in _lang("a.ts").quotes
    assert "`" in _lang("a.go").quotes


def test_strip_removes_line_and_block_comments_keeping_newlines():
    text = "a(); // {\n/* x\n y */ b();\n"
    stripped = strip_code(text, _lang("a.cpp"))
    assert stripped.count("\n") == text.count("\n") == 3
    assert "{" not in stripped
    assert count_logic(stripped) == 2


def test_brace_inside_string_is_not_code():
    assert strip_code('s = "{";', _lang("a.c")) == 's = "";'


def test_escaped_quote_does_not_end_literal():
    assert strip_code('s = "a\\"{";', _lang("a.c")) == 's = "";'


def test_comment_marker_inside_string_is_not_a_comment():
    assert strip_code('u = "http://x"; v();', _lang("a.js")) == 'u = ""; v();'


def test_multiline_template_literal_keeps_newlines():
    text = "x = `a\n{\nb`;\ny();\n"
    stripped = strip_code(text, _lang("a.js"))
    assert stripped.count("\n") == text.count("\n")
    assert "{" not in stripped and "y();" in stripped


def test_lone_apostrophe_is_a_plain_character():
    assert strip_code("fn f(x: &'a str) {", _lang("a.rs")) == "fn f(x: &'a str) {"


def test_triple_quoted_string_is_blanked_for_python():
    text = 'x = """a\n{ # b\n"""\ny = 1\n'
    stripped = strip_code(text, _lang("a.py"))
    assert stripped.count("\n") == text.count("\n")
    assert "{" not in stripped and "y = 1" in stripped


def test_hash_comment_is_stripped_for_python():
    assert strip_code("x = 1  # {\n", _lang("a.py")) == "x = 1  \n"


def test_crlf_line_endings_keep_their_line_count():
    stripped = strip_code("a();\r\n// c\r\nb();\r\n", _lang("a.c"))
    assert stripped.count("\n") == 3
    assert count_logic(stripped) == 2


def test_preprocessor_lines_drop_only_when_flagged():
    include = "#include <x>\nint a;\n"
    assert "include" not in strip_code(include, _lang("a.cpp"))
    assert "include" in strip_code(include, _lang("a.java"))
    assert "include" not in strip_code(include, _lang("a.sh"))


def test_preprocessor_continuation_lines_drop_together():
    text = "#define M(a) \\\n  { a }\nint b;\n"
    stripped = strip_code(text, _lang("a.c"))
    assert stripped.count("\n") == 3
    assert count_logic(stripped) == 1


@pytest.mark.parametrize("line", ["}", "};", "});", "  ],", ")", "", "   "])
def test_lone_brackets_are_not_logic(line):
    assert not is_logic_line(line)


@pytest.mark.parametrize("line", ["} else {", "x", "  return;"])
def test_code_lines_are_logic(line):
    assert is_logic_line(line)


def test_measure_plain_counts_file_only():
    text = "#!/bin/sh\n# a comment\n\necho hi\nif true; then\n  echo '#'\nfi\n"
    metric = measure_plain("run.sh", text, _lang("run.sh"))
    assert metric.path == "run.sh"
    assert metric.language == "Shell"
    assert metric.lines == 4
    assert metric.functions == () and metric.classes == ()
    assert metric.functions_measured is False


def test_multiline_template_literal_counts_every_line_it_spans():
    stripped = strip_code("x = `a\n{\nb`;\n", _lang("a.js"))
    assert "{" not in stripped
    assert count_logic(stripped) == 3


def test_multiline_kotlin_block_counts_every_line_it_spans():
    stripped = strip_code('x = """a\n{\nb"""\n', _lang("a.kt"))
    assert "{" not in stripped
    assert count_logic(stripped) == 3


def test_raw_quotes_are_declared_for_go_kotlin_scala_and_csharp():
    assert "`" in _lang("a.go").raw_quotes
    for name in ("a.kt", "a.scala", "a.cs"):
        assert '"""' in _lang(name).raw_quotes
    assert not _lang("a.js").raw_quotes and not _lang("a.java").raw_quotes
    assert not _lang("a.swift").raw_quotes and not _lang("a.dart").raw_quotes


def test_go_raw_string_ending_in_backslash_keeps_the_next_function():
    text = "s := `C:\\`\nfunc f() {\n}\n"
    stripped = strip_code(text, _lang("a.go"))
    assert "func f() {" in stripped
    assert count_logic(stripped) == 2


def test_kotlin_raw_string_has_no_escapes():
    stripped = strip_code('s = """a\\"""\nfun f() {\n}\n', _lang("a.kt"))
    assert "fun f() {" in stripped


def test_escapes_still_work_in_a_js_template_literal():
    assert strip_code("s = `a\\`{`;", _lang("a.js")) == "s = ``;"


def test_count_logic_splits_on_newline_only():
    assert count_logic("a\u2028b\n\x0c\nc") == 2


def test_lone_carriage_return_becomes_a_newline():
    stripped = strip_code("a();\rb();\r", _lang("a.c"))
    assert stripped == "a();\nb();\n"


def test_apostrophe_in_a_line_comment_does_not_open_a_literal():
    stripped = strip_code("a(); // don't {\nb() {\n", _lang("a.c"))
    assert "b() {" in stripped and "don" not in stripped


def test_block_comment_opener_inside_a_string_is_not_a_comment():
    stripped = strip_code('s = "/*"; f() {\n', _lang("a.c"))
    assert stripped == 's = ""; f() {\n'


def test_escaped_backslash_before_closing_quote_ends_the_literal():
    assert strip_code('s = "a\\\\"; {', _lang("a.c")) == 's = ""; {'


def test_indented_hash_pragma_is_a_preprocessor_line():
    stripped = strip_code("  # pragma once\nint a;\n", _lang("a.c"))
    assert "pragma" not in stripped and count_logic(stripped) == 1


def test_unterminated_literal_falls_back_to_a_plain_quote():
    assert strip_code('x = "abc\ny {', _lang("a.c")) == 'x = "abc\ny {'


def test_unterminated_block_comment_runs_to_the_end_of_the_file():
    stripped = strip_code("a();\n/* open\n{ b", _lang("a.c"))
    assert stripped.count("\n") == 2
    assert "{" not in stripped and count_logic(stripped) == 1
