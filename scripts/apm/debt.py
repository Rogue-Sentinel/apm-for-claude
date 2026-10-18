"""The debt ratchet's pure core: snapshot a report, compare two snapshots, accept a change.

Snapshots are plain dicts so the baseline file stays diff-friendly. Only items over a limit are
listed, which is why a function that shrinks under the limit simply leaves the snapshot.

Accepted limits. The snapshot lists only items already over a limit, and same-named items are matched
by one greedy pass per bare name across all files (each current item takes the smallest base item that is
no smaller). Within that rule:
  * a cross-file "move" can hide an unlisted same-named function that grew past the limit, because it
    had no number to compare against;
  * the same name swapping sizes across two files passes as two moves;
  * a same-named larger function deleted elsewhere can absorb another's growth.
Each of these needs every current item matched to a distinct base item at least as large, so the total
count and the total excess lines of functions and files cannot rise, and the totals check still fires if
they do. A reworded but equivalent glob reads as a narrowed scope, which is the conservative direction.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from apm.debt_compare import (
    KINDS, Findings, compare_items, compare_limits, compare_sources, compare_scope, compare_totals, compare_unmeasured, merge,
)
from apm.debt_classes import project_classes
from apm.metrics import Report
from apm.metrics_model import CLASS_LANGUAGES
from apm.standard_config import Limits, MetricsConfig

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


def _scope(scope: MetricsConfig | None) -> dict:
    config = scope or MetricsConfig()
    return {"include": list(config.include), "exclude": list(config.exclude), "builtin": config.builtin}


def _class_fields(report: Report, classes: Mapping) -> dict:
    """The languages whose classes were scanned, and the language of each file holding a wide class."""
    paths = {key.split("::", 1)[0] for key in classes}
    return {"class_scanners": sorted(CLASS_LANGUAGES),
            "class_languages": {f.path: f.language for f in report.files if f.path in paths}}


def snapshot(report: Report, limits: Limits, sources: Mapping[str, Mapping[str, int]] | None = None,
             scope: MetricsConfig | None = None) -> dict:
    functions, classes = _functions(report, limits), _classes(report, limits)
    files = {f.path: f.lines for f in report.over_files(limits)}
    unmeasured = sorted(f.path for f in report.unmeasured())
    return {
        "version": VERSION,
        "limits": {"function": limits.function, "file": limits.file, "public_methods": limits.public_methods},
        "totals": _totals(functions, files, classes, unmeasured, limits),
        "scope": _scope(scope),
        "unmeasured": unmeasured,
        "functions": functions, "files": files, "classes": classes, **_class_fields(report, classes),
        "sources": {name: dict(numbers) for name, numbers in (sources or {}).items()},
        "accepted": [],
    }


@dataclass(frozen=True)
class Comparison:
    regressions: tuple[str, ...]
    improvements: tuple[str, ...]
    moves: tuple[str, ...] = ()  # neutral notes: an over-limit item that only changed place
    newly_measured: tuple[str, ...] = ()  # neutral notes: a wide class in a language the base never scanned

    @property
    def worse(self) -> bool:
        return bool(self.regressions)


def _unsupported(base: dict, current: dict) -> tuple[str, ...]:
    bad = [("baseline", base.get("version")), ("current", current.get("version"))]
    return tuple(f"{who} version {version} is not supported" for who, version in bad if version != VERSION)


# (section, limit, total of its count, total of its excess lines or None, whether the limit itself is over)
_LIMITED = (
    ("functions", "function", "long_functions", "excess_function_lines", False),
    ("files", "file", "long_files", "excess_file_lines", False),
    ("classes", "public_methods", "wide_classes", None, True),
)


def _project(current: dict, old_limits: Mapping, spec: tuple) -> dict:
    """`current` seen at the base's looser limit, for one section, when the limit was tightened."""
    section, name, count, excess, inclusive = spec
    old, now = old_limits.get(name), current.get("limits", {}).get(name)
    if not (isinstance(old, int) and isinstance(now, int) and now < old):
        return current
    kept = {key: n for key, n in current.get(section, {}).items() if n > old - inclusive}
    totals = {**current.get("totals", {}), count: len(kept)}
    if excess:
        totals[excess] = sum(n - old for n in kept.values())
    return {**current, section: kept, "totals": totals}


def project_onto(base: dict, current: dict) -> dict:
    """Keep only what is over the base's limits where `current` tightened them.

    Code that was fine under the old limit is not new debt. The limits themselves stay as recorded.
    """
    for spec in _LIMITED:
        current = _project(current, base.get("limits", {}), spec)
    return current


def compare(base: dict, current: dict) -> Comparison:
    """Everything in `current` that is worse than `base`, and everything that got better."""
    if _unsupported(base, current):
        return Comparison(_unsupported(base, current), ())
    current, scanners, newly_measured = project_classes(base, current)
    current = project_onto(base, current)
    parts = [Findings(scanners, [], []), compare_limits(base, current), compare_scope(base, current), compare_totals(base, current),
             compare_unmeasured(base, current), compare_sources(base, current),
             *(compare_items(base, current, kind) for kind in KINDS)]
    return Comparison(*(tuple(lines) for lines in merge(parts)), tuple(newly_measured))


def accept(new: dict, previous: dict | None, reason: str, now: datetime) -> dict:
    """`new` with the accepted history carried forward, plus this acceptance when a reason is given.

    The reason is stripped, and a blank one counts as none. `now` must be timezone-aware; it is
    recorded in UTC.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("accept needs a timezone-aware datetime")
    history = list((previous or {}).get("accepted", []))
    if reason.strip():
        history.append({"reason": reason.strip(), "at": now.astimezone(timezone.utc).isoformat()})
    return {**new, "accepted": history}
