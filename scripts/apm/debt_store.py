"""The baseline file `.apm/debt.json`: read it, check its shape, write it, find it at a git ref."""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apm.cli_errors import DebtError
from apm.debt import snapshot as take_snapshot
from apm.debt_sources import run_source
from apm.metrics import Report, measure_tree
from apm.standard_config import Standard

DEBT_FILE = ".apm/debt.json"
__all__ = ["DEBT_FILE", "DebtError", "baseline_at", "current_snapshot", "load_baseline", "validate", "write_baseline"]


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _int_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and _int(n) for k, n in value.items())


def _strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _str_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())


def _per_source(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and _int_map(m) for k, m in value.items())


def _accepted(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(e, dict) and isinstance(e.get("reason"), str) and isinstance(e.get("at"), str) for e in value
    )


def _scope(value: object) -> bool:
    return (isinstance(value, dict) and all(_strings(value[k]) for k in ("include", "exclude") if k in value)
            and isinstance(value.get("builtin", True), bool))


_SHAPES: dict[str, Callable[[object], bool]] = {
    "limits": _int_map, "totals": _int_map, "functions": _int_map, "files": _int_map, "classes": _int_map,
    "unmeasured": _strings, "sources": _per_source, "accepted": _accepted, "scope": _scope,
    "class_scanners": _strings, "class_languages": _str_map,
}


def validate(data: Any, label: str) -> dict:
    """`data` when it has the shape of a snapshot; DebtError naming `label` when a hand edit broke it."""
    if not isinstance(data, dict):
        raise DebtError(f"{label} must be a JSON object")
    if not _int(data.get("version")):
        raise DebtError(f"{label}: version must be a whole number")
    for name, fits in _SHAPES.items():
        if name in data and not fits(data[name]):
            raise DebtError(f"{label}: {name} has the wrong shape")
    return data


def _parse(text: str, label: str) -> dict:
    try:
        return validate(json.loads(text), label)
    except json.JSONDecodeError as exc:
        raise DebtError(f"{label} is not valid JSON: {exc}") from exc


def load_baseline(path: Path) -> dict | None:
    """The baseline at `path`; None when there is no file; DebtError when it is corrupt."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DebtError(f"cannot read {path}: {exc}") from exc
    return _parse(text, str(path))


def write_baseline(path: Path, snapshot: dict) -> None:
    """Indent 2 with sorted keys and a trailing newline, so the file diffs line by line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def baseline_at(root: Path, ref: str) -> dict | None:
    """The baseline committed at `ref`; None when that ref has none; DebtError for an unknown ref."""
    if ref.startswith("-") or _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode:
        raise DebtError(f"unknown ref {ref}")
    shown = _git(root, "show", f"{ref}:{DEBT_FILE}")
    if shown.returncode:
        return None
    return _parse(shown.stdout.decode("utf-8", errors="replace"), f"{ref}:{DEBT_FILE}")


def current_snapshot(root: Path, standard: Standard) -> dict:
    """The built-in metrics (when switched on) plus every declared source, under the project's scope."""
    report = measure_tree(root, standard.metrics) if standard.metrics.builtin else Report(())
    sources = {source.name: run_source(source, root) for source in standard.sources}
    return take_snapshot(report, standard.limits, sources, standard.metrics)
