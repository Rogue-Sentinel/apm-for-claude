"""Handlers for the commands that measure a project against the standard."""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path

from apm.cli_errors import UsageError
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


HANDLERS: dict[str, Callable[[Project, argparse.Namespace], int | None]] = {"metrics": metrics}
