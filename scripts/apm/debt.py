"""The debt ratchet's pure core: snapshot a report, compare two snapshots, accept a change.

Snapshots are plain dicts so the baseline file stays diff-friendly. Only items over a limit are
listed, which is why a function that shrinks under the limit simply leaves the snapshot.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from apm.debt_compare import (
    KINDS, compare_items, compare_limits, compare_sources, compare_totals, compare_unmeasured, merge,
)
from apm.metrics import Report
from apm.standard_config import Limits

VERSION = 1


def _numbered(path: str, named: Iterable[tuple[str, int]], limit: int, at_least: bool = False) -> dict:
    """Number every name in a file in source order (`f`, `f#2`, ...), then keep the ones over."""
    seen: dict[str, int] = {}
    kept = {}
    for name, number in named:
        seen[name] = seen.get(name, 0) + 1
        label = name if seen[name] == 1 else f"{name}#{seen[name]}"
        if number >= limit if at_least else number > limit:
            kept[f"{path}::{label}"] = number
    return kept


def _by_line(items):
    return sorted(items, key=lambda item: item.line)


def _functions(report: Report, limits: Limits) -> dict[str, int]:
    kept: dict[str, int] = {}
    for metric in report.files:
        named = [(fn.name, fn.lines) for fn in _by_line(metric.functions)]
        kept |= _numbered(metric.path, named, limits.function)
    return kept


def _classes(report: Report, limits: Limits) -> dict[str, int]:
    kept: dict[str, int] = {}
    for metric in report.files:
        named = [(c.name, c.public_methods) for c in _by_line(metric.classes)]
        kept |= _numbered(metric.path, named, limits.public_methods, at_least=True)
    return kept


def _totals(functions: Mapping, files: Mapping, classes: Mapping, unmeasured: list, limits: Limits) -> dict:
    return {
        "long_functions": len(functions), "long_files": len(files), "wide_classes": len(classes),
        "excess_function_lines": sum(n - limits.function for n in functions.values()),
        "excess_file_lines": sum(n - limits.file for n in files.values()),
        "unmeasured_files": len(unmeasured),
    }


def snapshot(report: Report, limits: Limits, sources: Mapping[str, Mapping[str, int]] | None = None) -> dict:
    functions, classes = _functions(report, limits), _classes(report, limits)
    files = {f.path: f.lines for f in report.over_files(limits)}
    unmeasured = sorted(f.path for f in report.unmeasured())
    return {
        "version": VERSION,
        "limits": {"function": limits.function, "file": limits.file, "public_methods": limits.public_methods},
        "totals": _totals(functions, files, classes, unmeasured, limits),
        "unmeasured": unmeasured,
        "functions": functions, "files": files, "classes": classes,
        "sources": {name: dict(numbers) for name, numbers in (sources or {}).items()},
        "accepted": [],
    }


@dataclass(frozen=True)
class Comparison:
    regressions: tuple[str, ...]
    improvements: tuple[str, ...]
    moves: tuple[str, ...] = ()  # neutral notes: an over-limit item that only changed place

    @property
    def worse(self) -> bool:
        return bool(self.regressions)


def compare(base: dict, current: dict) -> Comparison:
    """Everything in `current` that is worse than `base`, and everything that got better."""
    parts = [compare_limits(base, current), compare_totals(base, current),
             compare_unmeasured(base, current), compare_sources(base, current),
             *(compare_items(base, current, kind) for kind in KINDS)]
    return Comparison(*(tuple(lines) for lines in merge(parts)))


def accept(new: dict, previous: dict | None, reason: str, now: datetime) -> dict:
    """`new` with the accepted history carried forward, plus this acceptance when a reason is given."""
    history = list((previous or {}).get("accepted", []))
    if reason:
        history.append({"reason": reason, "at": now.astimezone(timezone.utc).isoformat()})
    return {**new, "accepted": history}
