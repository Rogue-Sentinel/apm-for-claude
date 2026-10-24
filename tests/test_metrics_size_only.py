"""QML, Inno Setup and CMake files are measured for size only."""
from __future__ import annotations

import pytest

from apm.metrics import measure_text
from apm.metrics_lang import LANGUAGE_NAMES, language_for

_OLD_LANGUAGE_NAMES = {
    "C", "C#", "C++", "Dart", "Go", "Java", "JavaScript", "Kotlin", "Lua", "Objective-C",
    "PHP", "Perl", "PowerShell", "Python", "R", "Ruby", "Rust", "SQL", "Scala", "Shell",
    "Swift", "TypeScript",
}  # fmt: skip


@pytest.mark.parametrize(
    ("path", "name"),
    [
        ("ui/Main.qml", "QML"),
        ("UI/MAIN.QML", "QML"),
        ("setup/installer.iss", "Inno Setup"),
        ("cmake/deps.cmake", "CMake"),
        ("CMakeLists.txt", "CMake"),
        ("src/CMakeLists.txt", "CMake"),
        ("src/cmakelists.TXT", "CMake"),
    ],
)
def test_qml_inno_setup_and_cmake_are_size_only_languages(path, name):
    language = language_for(path)

    assert (language.name, language.family) == (name, "plain")


@pytest.mark.parametrize("path", ["notes.txt", "CMakeLists.txt.bak"])
def test_other_txt_files_still_have_no_language(path):
    assert language_for(path) is None


def test_qml_comments_do_not_count():
    text = "import QtQuick\n// note\n/* a\n b */\nItem {\n    width: 10\n}\n"

    metric = measure_text("Main.qml", text)

    assert (metric.lines, metric.functions_measured) == (3, False)


def test_inno_setup_section_and_pascal_comments_do_not_count():
    text = (
        "[Setup]\n; comment\nAppName=Sample App\nDefaultDirName={autopf}\\Sample\n[Code]\n"
        "{ pascal comment }\n(* another *)\n// line\nfunction InitializeSetup(): Boolean;\n"
        "begin\n  Result := True;\nend;\n"
    )

    assert measure_text("setup.iss", text).lines == 8


def test_an_inno_setup_string_ending_in_a_backslash_does_not_escape_its_quote():
    text = "x := 'C:\\' + '{';\ny := 2;\nz := '}';\n"

    assert measure_text("setup.iss", text).lines == 3


def test_cmake_line_and_bracket_comments_do_not_count():
    text = (
        "# top\ncmake_minimum_required(VERSION 3.20)\n#[[ a\nblock ]]\nproject(Sample)\n"
        "add_library(core\n  src/a.c\n)\n"
    )

    assert measure_text("CMakeLists.txt", text).lines == 4


def test_a_cmake_string_hides_a_comment_marker():
    assert measure_text("a.cmake", 'message("#[[ not a comment")\nset(Y 2)\n').lines == 2


def test_language_names_are_the_old_table_plus_the_three_new_ones():
    assert set(LANGUAGE_NAMES) == _OLD_LANGUAGE_NAMES | {"QML", "Inno Setup", "CMake"}


def test_language_names_are_sorted_and_listed_once():
    assert list(LANGUAGE_NAMES) == sorted(set(LANGUAGE_NAMES))
