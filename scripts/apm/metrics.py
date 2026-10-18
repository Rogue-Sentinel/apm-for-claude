"""Measure a project: choose its files, measure each one, and report against the limits."""
from __future__ import annotations

import posixpath
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from apm.guard_paths import matches_any
from apm.metrics_braces import measure_braces
from apm.metrics_lang import language_for, measure_plain
from apm.metrics_model import ClassMetric, FileMetric, FunctionMetric
from apm.metrics_python import measure_python
from apm.standard_config import Limits, MetricsConfig

PLAIN_NOTE = "functions are not measured for this language"


def measure_text(path: str, text: str) -> FileMetric | None:
    """Measure one file's text by its language family; None when the language is unknown."""
    language = language_for(path)
    if language is None:
        return None
    if language.family == "python":
        return measure_python(path, text)
    if language.family == "brace":
        return measure_braces(path, text, language)
    return replace(measure_plain(path, text, language), note=PLAIN_NOTE)


def tracked_files(root: Path) -> list[str]:
    """Tracked and untracked-but-not-ignored files, as sorted POSIX paths."""
    done = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, check=True,
    )
    names = done.stdout.decode("utf-8", errors="replace").split("\0")
    return sorted({name for name in names if name})


def select_files(paths: Sequence[str], config: MetricsConfig) -> list[str]:
    """The paths in a known language that the config includes and does not exclude."""
    return [
        path for path in paths
        if language_for(path) is not None
        and (not config.include or matches_any(config.include, path))
        and not matches_any(config.exclude, path)
    ]


@dataclass(frozen=True)
class Report:
    files: tuple[FileMetric, ...]

    def over_functions(self, limits: Limits) -> list[tuple[str, FunctionMetric]]:
        found = [(f.path, fn) for f in self.files for fn in f.functions if fn.lines > limits.function]
        return sorted(found, key=lambda item: -item[1].lines)

    def over_files(self, limits: Limits) -> list[FileMetric]:
        return sorted((f for f in self.files if f.lines > limits.file), key=lambda f: -f.lines)

    def wide_classes(self, limits: Limits) -> list[tuple[str, ClassMetric]]:
        found = [(f.path, c) for f in self.files for c in f.classes if c.public_methods >= limits.public_methods]
        return sorted(found, key=lambda item: -item[1].public_methods)

    def unmeasured(self) -> list[FileMetric]:
        return sorted((f for f in self.files if not f.functions_measured), key=lambda f: -f.lines)


def _under(name: str, prefixes: Sequence[str]) -> bool:
    return any(p == "." or name == p or name.startswith(p + "/") for p in prefixes)


def _read(path: Path) -> str | None:
    try:
        text = path.read_bytes().decode("utf-8-sig", errors="replace")
    except OSError:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def measure_tree(root: Path, config: MetricsConfig, paths: Sequence[str] | None = None) -> Report:
    """Measure the selected files of the git tree at `root`, optionally only under `paths`."""
    names = select_files(tracked_files(root), config)
    prefixes = [posixpath.normpath(p) for p in paths or ()]
    if prefixes:
        names = [name for name in names if _under(name, prefixes)]
    texts = ((name, _read(root / name)) for name in names)
    measured = (measure_text(name, text) for name, text in texts if text is not None)
    return Report(tuple(metric for metric in measured if metric is not None))


def _section(title: str, rows: list[str]) -> list[str]:
    return [title, *(f"  {row}" for row in rows)]


def _function_section(report: Report, limits: Limits) -> list[str]:
    over = report.over_functions(limits)
    total = sum(len(f.functions) for f in report.files)
    return _section(f"Functions over {limits.function} lines of logic: {len(over)} of {total}",
                    [f"{p}:{fn.line} {fn.name} -- {fn.lines} lines" for p, fn in over])


def _file_section(report: Report, limits: Limits) -> list[str]:
    over = report.over_files(limits)
    return _section(f"Files over {limits.file} lines of logic: {len(over)} of {len(report.files)}",
                    [f"{f.path} -- {f.lines} lines" for f in over])


def _class_section(report: Report, limits: Limits) -> list[str]:
    wide = report.wide_classes(limits)
    return _section(f"Review flags -- classes with {limits.public_methods}+ public methods: {len(wide)}",
                    [f"{p}:{c.line} {c.name} -- {c.public_methods} public methods" for p, c in wide])


def _unmeasured_section(report: Report) -> list[str]:
    bad = report.unmeasured()
    return _section(f"Files whose functions could not be measured: {len(bad)}",
                    [f"{f.path} -- {f.note or PLAIN_NOTE}" for f in bad])


def render_text(report: Report, limits: Limits) -> str:
    """Counts of what is over the limits, each item on a line, then the review flags."""
    sections = (
        _function_section(report, limits), _file_section(report, limits),
        _class_section(report, limits), _unmeasured_section(report),
    )
    return "\n".join(line for section in sections for line in section)


def _file_json(metric: FileMetric) -> dict:
    return {
        "path": metric.path, "language": metric.language, "lines": metric.lines,
        "functions_measured": metric.functions_measured, "note": metric.note,
        "functions": [asdict(fn) for fn in metric.functions],
        "classes": [asdict(c) for c in metric.classes],
    }


def report_json(report: Report, limits: Limits) -> dict:
    """Every measured number, as plain JSON-ready data."""
    return {"limits": asdict(limits), "files": [_file_json(f) for f in report.files]}
