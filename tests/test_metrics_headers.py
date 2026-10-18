import pytest

from apm.metrics import measure_text
from apm.metrics_lang import C, CPP, language_for, language_of

_C_HEADER = """#ifndef POINT_H
#define POINT_H
#ifdef __cplusplus
extern "C" {
#endif
struct point { int x; int y; };
typedef struct node node;
int add(int a, int b);
#ifdef __cplusplus
}
#endif
#endif
"""


def test_a_header_declaring_a_class_is_cpp_and_its_classes_are_counted() -> None:
    methods = "\n".join(f"void m{i}();" for i in range(7))
    text = f"class Database {{\npublic:\n{methods}\n}};\n"

    metric = measure_text("db.h", text)

    assert (metric.language, metric.classes[0].public_methods) == ("C++", 7)


@pytest.mark.parametrize(
    "text",
    [
        "namespace a {}\n",
        "namespace a::b {}\n",
        "template <typename T> T id(T);\n",
        "using namespace std;\n",
        "class Y : public Base {};\n",
        "struct S {\npublic:\nint x;\n};\n",
    ],
)
def test_each_cpp_marker_makes_a_header_cpp(text: str) -> None:
    assert language_of("x.h", text) is CPP


def test_a_c_header_with_guards_and_an_extern_c_wrapper_stays_c() -> None:
    assert language_of("point.h", _C_HEADER) is C


@pytest.mark.parametrize(
    "text",
    [
        "/* class Foo { namespace x { */\n",
        'const char* s = "template <T>";\n',
        "int class;\n",
        "struct s { int private; };\n",
    ],
)
def test_cpp_words_in_comments_strings_and_c_identifiers_leave_a_header_c(text: str) -> None:
    assert language_of("x.h", text) is C


def test_only_h_files_are_sniffed() -> None:
    assert language_of("a.c", "class X {};") is C
    assert language_of("a.hpp", "int f(void);") is CPP


def test_language_for_still_reads_h_as_c() -> None:
    assert language_for("a.h").name == "C"
