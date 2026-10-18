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
from apm.metrics import measure_tree, render_text, report_json
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


def metrics(project: Project, args: argparse.Namespace) -> int:
    standard = _standard(project)
    paths = [_relative(project, argument) for argument in args.paths]
    report = measure_tree(project.worktree_root, standard.metrics, paths)
    if args.json:
        print(json.dumps(report_json(report, standard.limits), indent=2))
    else:
        print(render_text(report, standard.limits))
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
