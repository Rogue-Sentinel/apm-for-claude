"""The merge gate: the four criteria, each checked from evidence on disk, never from a claim."""
from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apm.cli_debt import check_result
from apm.cli_errors import DebtError
from apm.gate_plan import HEADING, promised_paths, structural_criteria
from apm.layer_map import layer_overlaps
from apm.metrics import tracked_files
from apm.setup import TMP_IGNORE
from apm.standard_config import Standard
from apm.workflow_config import Workflow

LOG_DIR = ".apm/tmp/gate"
TAIL_LINES = 20


class GateError(Exception):
    """The gate cannot run: no test command is declared, or no plan is recorded for the issue."""


@dataclass(frozen=True)
class Check:
    criterion: int
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class GateResult:
    checks: tuple[Check, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _write_log(root: Path, name: str, output: str) -> None:
    folder = root / LOG_DIR
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.log").write_text(output, encoding="utf-8")


def run_command(name: str, command: str, root: Path, timeout: int, run: Callable = subprocess.run) -> Check:
    """Run one declared command in a shell, log its output, and report its tail when it fails."""
    try:
        done = run(command, shell=True, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        _write_log(root, name, f"timed out after {timeout}s\n")
        return Check(1, name, False, f"timed out after {timeout}s")
    output = done.stdout or ""
    _write_log(root, name, output)
    tail = "\n".join(output.splitlines()[-TAIL_LINES:]) or f"exit code {done.returncode}"
    return Check(1, name, done.returncode == 0, "" if done.returncode == 0 else tail)


def _clean_check(root: Path) -> Check:
    done = _git(root, "status", "--porcelain", "--untracked-files=all")
    lines = [line for line in done.stdout.splitlines() if line.strip() and not line[3:].startswith(TMP_IGNORE)]
    if done.returncode:
        lines = [done.stderr.strip() or "git status failed"]
    return Check(1, "clean tree", not lines, "" if not lines else "the tree is not clean: " + ", ".join(l[3:] for l in lines[:5]))


def _base_check(root: Path, base: str) -> Check:
    merged = not base.startswith("-") and _git(root, "merge-base", "--is-ancestor", base, "HEAD").returncode == 0
    return Check(1, "base merged", merged, "" if merged else f"{base} is not merged into HEAD")


def _layers_check(root: Path, standard: Standard) -> Check:
    overlaps = layer_overlaps(tracked_files(root), standard.layers) if standard.layers else []
    return Check(1, "layers", not overlaps, "; ".join(f"{path}: {first}, {second}" for path, first, second in overlaps))


def _commands(workflow: Workflow) -> list[tuple[str, str]]:
    commands = workflow.commands
    build = [("build", commands.build)] if commands.build else []
    return [*build, ("test", commands.test), *((c.name, c.command) for c in commands.checkers)]


def _criterion_one(root: Path, workflow: Workflow, standard: Standard, base: str, run: Callable) -> list[Check]:
    checks = [_clean_check(root), _base_check(root, base), _layers_check(root, standard)]
    why = next((check.detail for check in checks[:2] if not check.passed), "")
    for name, command in _commands(workflow):
        checks.append(Check(1, name, False, f"not run: {why}") if why else run_command(name, command, root, workflow.gate_timeout, run))
    return checks


def _debt_check(root: Path, standard: Standard, base: str) -> Check:
    try:
        passed, text = check_result(root, standard, base)
    except DebtError as error:
        return Check(2, "debt", False, str(error))
    return Check(2, "debt", passed, "" if passed else text)


def _review_check(root: Path, review: dict[str, Any] | None) -> Check:
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    problems = ["no review recorded"] if not review else []
    if review and review.get("head") != head:
        problems.append(f"the review was of {str(review.get('head'))[:7]}, which is not HEAD ({head[:7]})")
    if review and review.get("open") != 0:
        problems.append(f"{review.get('open')} open findings")
    return Check(3, "review", not problems, "; ".join(problems))


def _plan_check(root: Path, plan: str, review: dict[str, Any] | None) -> Check:
    if not (root / plan).is_file():
        return Check(4, "plan", False, f"plan file not found: {plan}")
    criteria = structural_criteria((root / plan).read_text(encoding="utf-8"))
    if not criteria:
        return Check(4, "plan", False, f"no `{HEADING}` section in {plan}")
    missing = [path for path in promised_paths(criteria) if not (root / path).exists()]
    notes = [f"{len(criteria)} criteria"] + ([f"missing: {', '.join(missing)}"] if missing else [])
    notes += [] if (review or {}).get("criteria_met") else ["criteria not recorded as met"]
    return Check(4, "plan", len(notes) == 1, "; ".join(notes))


def gate(root: Path, issue: dict[str, Any], workflow: Workflow, standard: Standard, base: str,
         run: Callable = subprocess.run) -> GateResult:
    """Check the four criteria for `issue` at `root`; raise GateError when the gate cannot run at all."""
    if not workflow.commands.test:
        raise GateError("no test command declared; set workflow.commands.test in the profile")
    if not issue.get("plan"):
        raise GateError("no plan recorded for the issue; record it with `apm issue N --plan PATH`")
    review = issue.get("review")
    checks = [*_criterion_one(root, workflow, standard, base, run), _debt_check(root, standard, base),
              _review_check(root, review), _plan_check(root, issue["plan"], review)]
    return GateResult(tuple(checks))


def _line(check: Check) -> str:
    first, *rest = check.detail.splitlines() or [""]
    head = f"{'PASS' if check.passed else 'FAIL'}  {check.criterion}  {check.name}  {first}".rstrip()
    return "\n".join([head, *(f"    {line}" for line in rest)])


def render_gate(result: GateResult) -> str:
    """One line per check, then the verdict."""
    failures = sum(1 for check in result.checks if not check.passed)
    verdict = "merge gate: passed" if not failures else f"merge gate: {failures} failed; stop and ask"
    return "\n".join([*(_line(check) for check in result.checks), verdict])
