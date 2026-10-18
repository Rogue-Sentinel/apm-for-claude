"""`apm gate N`: run the merge gate for one issue. It records nothing; the manager records the output."""
from __future__ import annotations

import argparse
import subprocess
import sys

from apm import ledger as lg
from apm.gate import GateError, gate, render_gate
from apm.paths import Project
from apm.profile import load_profile
from apm.standard_config import load_standard
from apm.workflow_config import load_workflow

RUN = subprocess.run  # the one place the build, test and checker commands are run from; tests replace it


def _issue(project: Project, number: int) -> dict:
    issue = lg.load_ledger(project.ledger_path)["issues"].get(str(number))
    if issue is None:
        raise GateError(f"unknown issue: {number}")
    return issue


def run_gate(project: Project, args: argparse.Namespace) -> int:
    profile = load_profile(project.profile_path)
    workflow = load_workflow(profile)
    try:
        result = gate(project.worktree_root, _issue(project, args.number), workflow, load_standard(profile),
                      args.base or workflow.base, run=RUN)
    except GateError as error:
        print(f"apm: {error}", file=sys.stderr)
        return 2
    print(render_gate(result))
    return 0 if result.passed else 1
