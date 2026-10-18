import json

from apm.metrics import Report, measure_text, render_text, report_json
from apm.metrics_model import ClassMetric, FileMetric
from apm.standard_config import Limits

LIMITS = Limits(function=15, file=200, public_methods=7)
HEADER = "Review flags -- classes with 7+ public methods: "
UNSCANNED = "Files whose classes were not measured (no class scanner for the language): "


def _metric(path: str, language: str, measured: bool = True, **kw) -> FileMetric:
    return FileMetric(path, language, 5, functions_measured=measured, **kw)


def _lines(*files: FileMetric) -> list[str]:
    return render_text(Report(files), LIMITS).split("\n")


def test_a_java_only_report_says_classes_were_not_measured() -> None:
    lines = _lines(_metric("A.java", "Java"))

    at = lines.index(HEADER + "not measured (no class scanner for Java)")
    assert lines[at + 1:at + 3] == [UNSCANNED + "1", "  Java: 1"]


def test_a_mixed_report_counts_measured_classes_and_names_the_rest() -> None:
    wide = _metric("a.py", "Python", classes=(ClassMetric("Wide", 4, 8),))

    lines = _lines(wide, _metric("A.java", "Java"), _metric("B.java", "Java"), _metric("c.ts", "TypeScript"))

    at = lines.index(HEADER + "1 (classes not measured for Java, TypeScript)")
    assert lines[at + 1:at + 3] == ["  a.py:4 Wide -- 8 public methods", UNSCANNED + "3"]
    assert lines[at + 3:at + 5] == ["  Java: 2", "  TypeScript: 1"]


def test_c_plain_and_broken_python_files_are_not_listed_as_class_unmeasured() -> None:
    lines = _lines(_metric("a.c", "C"), _metric("run.sh", "Shell", measured=False),
                   _metric("b.py", "Python", measured=False))

    assert HEADER + "0" in lines
    assert not any(line.startswith("Files whose classes") for line in lines)


def test_json_marks_whether_each_file_had_its_classes_measured() -> None:
    texts = {"a.py": "def f():\n    return 1\n", "A.java": "class A {}\n", "run.sh": "echo hi\n"}
    files = tuple(measure_text(path, text) for path, text in texts.items())

    data = json.loads(json.dumps(report_json(Report(files), LIMITS)))

    assert {f["path"]: f["classes_measured"] for f in data["files"]} == {
        "a.py": True, "A.java": False, "run.sh": False,
    }
