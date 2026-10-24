"""Measure a project: choose its files, measure each one, and report against the limits."""
from __future__ import annotations

import posixpath
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from apm.guard_paths import matches_any
from apm.metrics_braces import measure_braces
from apm.metrics_cpp import with_cpp_classes
from apm.metrics_lang import language_for, language_of, measure_plain
from apm.metrics_model import (
    CLASS_LANGUAGES, CLASSLESS_LANGUAGES, ClassMetric, FileMetric, FunctionMetric, classes_measured,
)
from apm.metrics_not_measured import file_kind, holds_text, named_as_not_code
from apm.metrics_python import measure_python
from apm.standard_config import Limits, MetricsConfig

Read = Callable[[str], bytes | None]


def measure_text(path: str, text: str) -> FileMetric | None:
    """Measure one file's text by its language family; None when the language is unknown."""
    language = language_of(path, text)
    if language is None:
        return None
    if language.family == "python":
        return measure_python(path, text)
    if language.family == "brace":
        return with_cpp_classes(measure_braces(path, text, language), text, language)
    return measure_plain(path, text, language)


def tracked_files(root: Path) -> list[str]:
    """Tracked and untracked-but-not-ignored files, as sorted POSIX paths."""
    done = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, check=True,
    )
    names = done.stdout.decode("utf-8", errors="replace").split("\0")
    return sorted({name for name in names if name})


def _in_scope(path: str, config: MetricsConfig) -> bool:
    """Whether the config includes the path and does not exclude it."""
    return (not config.include or matches_any(config.include, path)) and not matches_any(config.exclude, path)


def select_files(paths: Sequence[str], config: MetricsConfig) -> list[str]:
    """The paths in a known language that the config includes and does not exclude.

    Globs match case-insensitively, because they reuse the guard's glob compiler.
    """
    return [path for path in paths if language_for(path) is not None and _in_scope(path, config)]


def _is_plain(metric: FileMetric) -> bool:
    language = language_for(metric.path)
    return language is not None and language.family == "plain"


def _is_brace(metric: FileMetric) -> bool:
    language = language_for(metric.path)
    return language is not None and language.family == "brace"


def not_measured_candidates(paths: Sequence[str], config: MetricsConfig) -> list[str]:
    """The in-scope paths with no language that their names do not already mark as docs, data or binaries."""
    return [p for p in paths if language_for(p) is None and _in_scope(p, config) and not named_as_not_code(p)]


@dataclass(frozen=True)
class Report:
    files: tuple[FileMetric, ...]
    not_measured: tuple[str, ...] = ()

    def over_functions(self, limits: Limits) -> list[tuple[str, FunctionMetric]]:
        found = [(f.path, fn) for f in self.files for fn in f.functions if fn.lines > limits.function]
        return sorted(found, key=lambda item: -item[1].lines)

    def over_files(self, limits: Limits) -> list[FileMetric]:
        return sorted((f for f in self.files if f.lines > limits.file), key=lambda f: -f.lines)

    def wide_classes(self, limits: Limits) -> list[tuple[str, ClassMetric]]:
        found = [(f.path, c) for f in self.files for c in f.classes if c.public_methods >= limits.public_methods]
        return sorted(found, key=lambda item: -item[1].public_methods)

    def unmeasured(self) -> list[FileMetric]:
        """Files that should have had their functions measured and did not."""
        failed = (f for f in self.files if not f.functions_measured and not _is_plain(f))
        return sorted(failed, key=lambda f: -f.lines)

    def plain(self) -> list[FileMetric]:
        """Files in a language with no function scanner: measured for size only."""
        return sorted((f for f in self.files if _is_plain(f)), key=lambda f: -f.lines)

    def classes_unscanned(self) -> dict[str, int]:
        """Brace-language files with no class scanner, counted by language name."""
        skipped = CLASS_LANGUAGES | CLASSLESS_LANGUAGES
        names = [f.language for f in self.files if _is_brace(f) and f.language not in skipped]
        return {name: names.count(name) for name in sorted(set(names))}


def not_measured_kinds(report: Report) -> dict[str, int]:
    """The files not measured, counted by kind: most files first, then by kind.

    A function, not a `Report` method, so `Report` stays under the public-method review flag.
    """
    counts = Counter(file_kind(path) for path in report.not_measured)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def under_paths(names: Sequence[str], paths: Sequence[str] | None) -> list[str]:
    """The names at or under any of `paths`; all of them when `paths` is empty."""
    prefixes = [posixpath.normpath(p) for p in paths or ()]
    if not prefixes:
        return list(names)
    return [name for name in names if any(p == "." or name == p or name.startswith(p + "/") for p in prefixes)]


def decode_text(data: bytes) -> str:
    """File bytes as text: UTF-8 with a BOM dropped, bad bytes replaced, and newlines normalized."""
    text = data.decode("utf-8-sig", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def choose_files(
    files: Sequence[str], config: MetricsConfig, paths: Sequence[str] | None,
) -> tuple[list[str], list[str]]:
    """The files to measure and the not-measured candidates, both in scope and under `paths`."""
    return (under_paths(select_files(files, config), paths),
            under_paths(not_measured_candidates(files, config), paths))


def measure_files(names: Sequence[str], read: Read, candidates: Sequence[str] = ()) -> Report:
    """Measure the readable names; the candidates that hold text are the files not measured."""
    datas = ((name, read(name)) for name in names)
    measured = (measure_text(name, decode_text(data)) for name, data in datas if data is not None)
    unmeasured = tuple(name for name in candidates if holds_text(read(name)))
    return Report(tuple(metric for metric in measured if metric is not None), unmeasured)


def measure_tree(root: Path, config: MetricsConfig, paths: Sequence[str] | None = None) -> Report:
    """Measure the selected files of the git tree at `root`, optionally only under `paths`."""
    names, candidates = choose_files(tracked_files(root), config, paths)
    return measure_files(names, lambda name: _read(root / name), candidates)


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


def _class_header(report: Report, limits: Limits) -> str:
    head = f"Review flags -- classes with {limits.public_methods}+ public methods: "
    langs = ", ".join(report.classes_unscanned())
    if not langs:
        return head + str(len(report.wide_classes(limits)))
    if not any(classes_measured(f) for f in report.files):
        return head + f"not measured (no class scanner for {langs})"
    return head + f"{len(report.wide_classes(limits))} (classes not measured for {langs})"


def _class_section(report: Report, limits: Limits) -> list[str]:
    wide = report.wide_classes(limits)
    return _section(_class_header(report, limits),
                    [f"{p}:{c.line} {c.name} -- {c.public_methods} public methods" for p, c in wide])


def _class_unscanned_section(report: Report) -> list[str]:
    unscanned = report.classes_unscanned()
    if not unscanned:
        return []
    title = f"Files whose classes were not measured (no class scanner for the language): {sum(unscanned.values())}"
    return _section(title, [f"{name}: {count}" for name, count in unscanned.items()])


def _unmeasured_section(report: Report) -> list[str]:
    bad = report.unmeasured()
    return _section(f"Files whose functions could not be measured: {len(bad)}",
                    [f"{f.path} -- {f.note}" for f in bad])


def _plain_section(report: Report) -> list[str]:
    plain = report.plain()
    return _section(f"Files measured for size only (no function scanner for the language): {len(plain)}",
                    [f"{f.path} -- {f.lines} lines" for f in plain])


def _not_measured_section(report: Report) -> list[str]:
    return _section(f"Files not measured: {len(report.not_measured)}",
                    [f"{kind}: {count}" for kind, count in not_measured_kinds(report).items()])


def render_text(report: Report, limits: Limits) -> str:
    """Counts of what is over the limits, each item on a line, then the review flags."""
    sections = (
        _function_section(report, limits), _file_section(report, limits),
        _class_section(report, limits), _class_unscanned_section(report),
        _unmeasured_section(report), _plain_section(report), _not_measured_section(report),
    )
    return "\n".join(line for section in sections for line in section)


def _file_json(metric: FileMetric) -> dict:
    return {
        "path": metric.path, "language": metric.language, "lines": metric.lines,
        "functions_measured": metric.functions_measured, "note": metric.note, "plain": _is_plain(metric),
        "classes_measured": classes_measured(metric),
        "functions": [asdict(fn) for fn in metric.functions],
        "classes": [asdict(c) for c in metric.classes],
    }


def report_json(report: Report, limits: Limits) -> dict:
    """Every measured number, as plain JSON-ready data."""
    return {
        "limits": asdict(limits), "files": [_file_json(f) for f in report.files],
        "files_not_measured": len(report.not_measured), "not_measured": list(report.not_measured),
    }
