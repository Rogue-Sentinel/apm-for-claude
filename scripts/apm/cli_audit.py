"""`apm audit`: a read-only look at a repository, as a report or as the JSON that `apm init` applies."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from apm.audit_report import audit_json, render_audit
from apm.audit_scan import audit as scan
from apm.cli_errors import UsageError
from apm.coverage import CoverageError, load_inventory
from apm.metrics_ref import RefError
from apm.paths import Project
from apm.profile import load_profile
from apm.standard_config import Standard, load_standard

RUN = subprocess.run  # the one place git and `gh` are run from; tests replace it


def _standard(project: Project) -> Standard:
    return load_standard(load_profile(project.profile_path) if project.is_initialized else None)


def _inventory(path: str | None) -> dict | None:
    if path is None:
        return None
    try:
        return load_inventory(Path(path))
    except (CoverageError, KeyError, ValueError) as err:
        raise UsageError(f"cannot read the coverage inventory {path}: {err}") from err


def audit(project: Project, args: argparse.Namespace) -> int:
    standard = _standard(project)
    inventory = _inventory(args.coverage)
    try:
        found, report = scan(project.worktree_root, args.base, run=RUN, config=standard.metrics)
    except RefError as err:
        raise UsageError(str(err)) from err
    if args.json:
        print(json.dumps(audit_json(found, report, standard.limits), indent=2))
    else:
        print(render_audit(found, report, standard.limits, inventory), end="")
    return 0
