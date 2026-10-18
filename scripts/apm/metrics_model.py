"""The measurements the metrics tool reports, one frozen record per thing measured."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionMetric:
    name: str
    line: int
    lines: int


@dataclass(frozen=True)
class ClassMetric:
    name: str
    line: int
    public_methods: int


@dataclass(frozen=True)
class FileMetric:
    path: str
    language: str
    lines: int
    functions: tuple[FunctionMetric, ...] = ()
    classes: tuple[ClassMetric, ...] = ()
    functions_measured: bool = False
    note: str = ""
