"""Shared helpers for the brace-scanner tests."""
from __future__ import annotations

from apm.metrics_braces import measure_braces
from apm.metrics_lang import language_for
from apm.metrics_model import FileMetric


def measure(path: str, text: str) -> FileMetric:
    language = language_for(path)
    assert language is not None and language.family == "brace"
    return measure_braces(path, text, language)


def found(path: str, text: str) -> list[tuple[str, int]]:
    metric = measure(path, text)
    assert metric.functions_measured and not metric.classes
    return [(f.name, f.lines) for f in metric.functions]
