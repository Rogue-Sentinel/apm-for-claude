"""Apply an approved audit: check that it is ready, then set the project up from it.

Init never edits methodology files and never removes anything (no worktree, branch or file).
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from apm import ledger as lg
from apm import ledger_workflow as wf
from apm.cli_errors import UsageError
from apm.coverage import CoverageError, find_gaps, load_inventory
from apm.debt import accept
from apm.debt_store import DEBT_FILE, current_snapshot, load_baseline, write_baseline
from apm.paths import Project, find_project
from apm.profile import ProfileError, load_profile, write_profile
from apm.setup import PROFILE_PATH, setup_project
from apm.standard_config import Standard, load_standard
from apm.state_store import commit_state
from apm.workflow_config import load_workflow

AUDIT_DIR = ".apm/audit"
DECISIONS = ("finish", "adopt", "leave")
PLAN_KINDS = ("plan", "spec")
IMPORTED = "imported {path}: not approved; needs the user's approval before building"
LOGGED = "initialized from audit"


class Refusal(Exception):
    """An input of init is missing or unreadable; the message is one refusal line."""


def _path(root: Path, name: str) -> Path:
    path = root / AUDIT_DIR / name
    if not path.is_file():
        raise Refusal(f"missing {AUDIT_DIR}/{name}")
    return path


def _load(root: Path, name: str) -> dict:
    try:
        data = json.loads(_path(root, name).read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise Refusal(f"cannot read {AUDIT_DIR}/{name}: {err}") from err
    if not isinstance(data, dict):
        raise Refusal(f"{AUDIT_DIR}/{name} must be a JSON object")
    return data


def _coverage_lines(root: Path, plugin_root: Path, audit: dict) -> list[str]:
    if audit.get("mode") == "fresh" and not (root / AUDIT_DIR / "coverage.json").exists():
        return []
    path = _path(root, "coverage.json")
    try:
        inventory = load_inventory(path)
    except (CoverageError, KeyError, ValueError, OSError) as err:
        raise Refusal(f"cannot read {AUDIT_DIR}/coverage.json: {err}") from err
    return [f"coverage gap: {gap}" for gap in find_gaps(inventory, plugin_root)]


def _is_ancestor(ref: str, base: str, root: Path, run) -> bool:
    argv = ["git", "merge-base", "--is-ancestor", ref, base]
    return run(argv, cwd=root, capture_output=True, text=True, encoding="utf-8").returncode == 0


def _exists(ref: str, root: Path, run) -> bool:
    argv = ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]
    return run(argv, cwd=root, capture_output=True, text=True, encoding="utf-8").returncode == 0


def _merged(item: dict, base: str, root: Path, run) -> bool:
    """Whether every copy of the item's branch that exists, local and on origin, is in `base`.

    Items with no branch (issues, documents) always are. With no copy left, the plain name is asked,
    which git cannot prove merged.
    """
    if item["kind"] == "branch":
        name = item["id"].removeprefix("branch:")
    elif item["kind"] == "worktree" and item["title"] != "detached":
        name = item["title"]
    else:
        return True
    refs = [ref for ref in (name, f"origin/{name}") if _exists(ref, root, run)] or [name]
    return all(_is_ancestor(ref, base, root, run) for ref in refs)


def _decision_line(item: dict, decision: object, audit: dict, root: Path, run) -> list[str]:
    ident = item["id"]
    if decision is None:
        return [f"no decision for {ident}"]
    if decision not in DECISIONS:
        return [f"unknown decision for {ident}: {decision!r}"]
    if decision == "finish" and not _merged(item, audit["base"], root, run):
        return [f"finish first: {ident} is not merged into {audit['base']} yet"]
    return []


def _decision_lines(root: Path, audit: dict, run) -> list[str]:
    decisions = _load(root, "decisions.json")
    return [line for item in audit["in_flight"] for line in _decision_line(item, decisions.get(item["id"]), audit, root, run)]


def _profile_lines(root: Path) -> list[str]:
    path = _path(root, "profile.json")
    try:
        draft = load_profile(path)
        load_standard(draft)
        load_workflow(draft)
    except ProfileError as err:
        return [f"draft profile rejected: {err}"]
    return []


def _safely(check, *args) -> list[str]:
    try:
        return check(*args)
    except Refusal as err:
        return [str(err)]
    except (KeyError, TypeError, AttributeError) as err:
        return [f"{AUDIT_DIR} has the wrong shape: {err!r}"]


def refusals(root: Path, plugin_root: Path, run=subprocess.run) -> list[str]:
    """Why init cannot run yet, one line each; empty when the approved audit is ready to apply."""
    try:
        audit = _load(root, "audit.json")
    except Refusal as err:
        return [str(err)]
    return [
        *_safely(_coverage_lines, root, plugin_root, audit),
        *_safely(_decision_lines, root, audit, run),
        *_safely(_profile_lines, root),
    ]


def _install(project: Project, draft) -> list[str]:
    target = project.worktree_root / PROFILE_PATH
    before = target.read_text(encoding="utf-8") if target.exists() else None
    write_profile(target, draft)
    wrote = [PROFILE_PATH] if target.read_text(encoding="utf-8") != before else []
    return [f"wrote {name}" for name in [*wrote, *setup_project(project)]]


def _import_issue(ledger: dict, item: dict) -> list[str]:
    number = int(item["id"].removeprefix("issue:"))
    if str(number) in ledger["issues"]:
        return []
    lg.upsert_issue(ledger, number, status="queued", imported=True, title=item["title"])
    return [f"imported issue #{number}"]


def _note_text(item: dict, decision: str) -> str:
    if decision == "adopt" and item["kind"] in PLAN_KINDS:
        return IMPORTED.format(path=item["id"].removeprefix(f"{item['kind']}:"))
    return f"{decision} {item['id']}"


def _decide(ledger: dict, issue: int, item: dict, decision: str, now: datetime) -> list[str]:
    adopted = _import_issue(ledger, item) if decision == "adopt" and item["kind"] == "issue" else []
    text = _note_text(item, decision)
    return adopted + ([f"noted: {text}"] if wf.add_note(ledger, issue, "decision", text, now) else [])


def _adopt_debt(ledger: dict, audit: dict) -> list[str]:
    merged = sorted({*ledger.get("debt_issues", []), *audit["debt_issues"]})
    if merged == ledger.get("debt_issues", []):
        return []
    ledger["debt_issues"] = merged
    return ["adopted debt issues " + ", ".join(f"#{number}" for number in merged)]


def _record(project: Project, issue: int, now: datetime, audit: dict, decisions: dict) -> list[str]:
    ledger = lg.load_ledger(project.ledger_path)
    before = json.dumps(ledger, sort_keys=True)
    lg.upsert_issue(ledger, issue)
    actions = [a for item in audit["in_flight"] for a in _decide(ledger, issue, item, decisions[item["id"]], now)]
    actions += _adopt_debt(ledger, audit)
    if json.dumps(ledger, sort_keys=True) != before:
        lg.append_log(ledger, issue, LOGGED, now)
        lg.save_ledger(project.ledger_path, ledger)
        commit_state(project, LOGGED)
    return actions


def _baseline(root: Path, standard: Standard, now: datetime) -> list[str]:
    path = root / DEBT_FILE
    if load_baseline(path) is not None:
        return []
    write_baseline(path, accept(current_snapshot(root, standard), None, "baseline from the approved audit", now))
    return [f"wrote {DEBT_FILE}"]


def apply(root: Path, issue: int, now: datetime, run=subprocess.run) -> list[str]:
    """Set the project up from the audit in AUDIT_DIR and return what changed (empty on a repeat run).

    Call `refusals` first. `run` is accepted so callers pass one seam to both; apply itself needs no git.
    """
    project = find_project(root)
    if project is None:
        raise UsageError("not inside a git repository")
    draft = load_profile(_path(root, "profile.json"))
    actions = _install(project, draft)
    actions += _record(project, issue, now, _load(root, "audit.json"), _load(root, "decisions.json"))
    return actions + _baseline(project.worktree_root, load_standard(draft), now)
