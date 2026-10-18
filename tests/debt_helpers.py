"""Builders for hand-made reports and snapshots, shared by the debt tests."""
from apm.debt import snapshot
from apm.metrics import Report
from apm.metrics_model import ClassMetric, FileMetric, FunctionMetric
from apm.standard_config import Limits

LIMITS = Limits()


def file_metric(path: str, lines: int = 10, funcs=(), classes=(), measured: bool = True,
                language: str = "Python") -> FileMetric:
    fns = tuple(FunctionMetric(name, 1 + i * 50, n) for i, (name, n) in enumerate(funcs))
    cls = tuple(ClassMetric(name, 1 + i * 50, n) for i, (name, n) in enumerate(classes))
    return FileMetric(path, language, lines, fns, cls, functions_measured=measured,
                      note="" if measured else "syntax error")


def snap(*files: FileMetric, sources=None, limits: Limits = LIMITS, scope=None) -> dict:
    extra = {} if scope is None else {"scope": scope}
    return snapshot(Report(tuple(files)), limits, sources, **extra)
