"""Handlers for the commands that measure a project against the standard."""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path

from apm.cli_debt import run_debt
from apm.cli_errors import UsageError
from apm.coverage import INVENTORY_PATH, PLUGIN_ROOT, find_gaps, load_inventory, render_table, scan_source
from apm.guard_paths import is_under
from apm.layer_map import layer_overlaps
from apm.metrics import Report, measure_tree, render_text, report_json
from apm.metrics_ref import RefError, measure_at_ref
from apm.paths import Project
from apm.profile import load_profile
from apm.standard_config import Standard, load_standard


def _standard(project: Project) -> Standard:
    profile = load_profile(project.profile_path) if project.is_initialized else None
    return load_standard(profile)


def _relative(project: Project, argument: str) -> str:
    target = Path.cwd() / argument
    if not is_under(target, project.worktree_root):
        raise UsageError(f"{argument} is outside the repository")
    if not target.exists():
        raise UsageError(f"{argument} does not exist")
    return Path(os.path.relpath(os.path.realpath(target), project.worktree_root)).as_posix()


def _measure(project: Project, standard: Standard, args: argparse.Namespace) -> Report:
    paths = [_relative(project, argument) for argument in args.paths]
    if not args.ref:
        return measure_tree(project.worktree_root, standard.metrics, paths)
    try:
        return measure_at_ref(project.worktree_root, args.ref, standard.metrics, paths)
    except RefError as error:
        raise UsageError(str(error)) from error


def _overlap_lines(overlaps: list[tuple[str, str, str]]) -> str:
    rows = [f"  {path}: {first}, {second}" for path, first, second in overlaps]
    return "\n".join([f"files in two layers: {len(overlaps)}", *rows])


def metrics(project: Project, args: argparse.Namespace) -> int:
    standard = _standard(project)
    report = _measure(project, standard, args)
    overlaps = layer_overlaps([f.path for f in report.files], standard.layers)
    data = report_json(report, standard.limits)
    if standard.layers:
        data["layer_overlaps"] = [list(overlap) for overlap in overlaps]
    text = render_text(report, standard.limits) + (f"\n{_overlap_lines(overlaps)}" if standard.layers else "")
    print(json.dumps(data, indent=2) if args.json else text)
    return 0


def debt(project: Project, args: argparse.Namespace) -> int:
    return run_debt(project, _standard(project), args)


def _scan(inventory: dict, spec: str) -> list[str]:
    source_id, _, folder = spec.partition("=")
    if not folder:
        raise UsageError(f"--source needs ID=DIR, got {spec!r}")
    return scan_source(inventory, source_id, Path(folder))


def coverage(project: Project | None, args: argparse.Namespace) -> int:
    inventory = load_inventory(INVENTORY_PATH)
    if args.table:
        print(render_table(inventory), end="")
    problems = find_gaps(inventory, PLUGIN_ROOT)
    for spec in args.source:
        problems += _scan(inventory, spec)
    if not args.table:
        print(*problems, f"Gaps: {len(problems)}", sep="\n")
    return 1 if problems else 0


HANDLERS: dict[str, Callable[[Project, argparse.Namespace], int | None]] = {
    "metrics": metrics, "debt": debt, "coverage": coverage,
}
