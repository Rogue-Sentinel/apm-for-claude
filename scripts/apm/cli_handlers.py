"""One handler per apm subcommand; each mutation saves, logs, and commits the ledger."""
from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apm import ledger as lg
from apm.briefing import render_briefing
from apm.cli_standard import HANDLERS as STANDARD_HANDLERS
from apm.cli_workflow import WORKFLOW_HANDLERS
from apm.cli_workflow import mutate as _mutate
from apm.ledger_workflow import set_parent
from apm.paths import Project, to_native_path
from apm.setup import setup_project
from apm.state_store import load_state

ISSUE_FIELDS = ("title", "kind", "lane", "status", "branch", "plan")
TASK_FIELDS = ("title", "status", "worker", "model", "evidence")


def _given(args: argparse.Namespace, names: tuple[str, ...]) -> dict[str, Any]:
    return {n: getattr(args, n) for n in names if getattr(args, n) is not None}


def brief(project: Project, args: argparse.Namespace) -> int:
    try:
        print(render_briefing(load_state(project), None))
    except lg.LedgerError as exc:
        print(render_briefing(None, str(exc)))
        return 2
    return 0


def issue(project: Project, args: argparse.Namespace) -> None:
    fields = _given(args, ISSUE_FIELDS)

    def apply(ledger: dict) -> str:
        lg.upsert_issue(ledger, args.number, **fields)
        if args.parent is not None:
            set_parent(ledger, args.number, args.parent)
        status = fields.get("status")
        return f"issue {args.number} status {status}" if status else f"issue {args.number} updated"

    _mutate(project, args.number, apply)


def task(project: Project, args: argparse.Namespace) -> None:
    fields = _given(args, TASK_FIELDS)

    def apply(ledger: dict) -> str:
        lg.update_task(ledger, args.number, args.id, **fields)
        what = fields.get("status") or "updated"
        return f"task {args.number}/{args.id} {what}"

    _mutate(project, args.number, apply)


def allow(project: Project, args: argparse.Namespace) -> None:
    def apply(ledger: dict) -> str:
        lg.add_allow(ledger, args.number, path=args.path, command=args.command, reason=args.reason)
        kind, value = ("path", args.path) if args.path else ("command", args.command)
        return f"allow {args.number} {kind} {value}"

    _mutate(project, args.number, apply)


def approve(project: Project, args: argparse.Namespace) -> None:
    def apply(ledger: dict) -> str:
        now = datetime.now(timezone.utc)
        cwd = to_native_path(os.getcwd(), Path.cwd(), os.name == "nt").as_posix()
        lg.add_approval(ledger, path=args.path, command=args.command, reason=args.reason, now=now, cwd=cwd)
        kind, value = ("path", args.path) if args.path else ("command", args.command)
        return f"approve {kind} {value}"

    _mutate(project, None, apply)


def question(project: Project, args: argparse.Namespace) -> None:
    def apply(ledger: dict) -> str:
        index = lg.add_question(ledger, args.number, args.text, args.blocks)
        print(f"question {index}")
        return f"question {args.number} #{index}"

    _mutate(project, args.number, apply)


def resolve(project: Project, args: argparse.Namespace) -> None:
    def apply(ledger: dict) -> str:
        lg.resolve_question(ledger, args.number, args.index, args.answer)
        return f"resolve {args.number} #{args.index}"

    _mutate(project, args.number, apply)


def setup(project: Project, args: argparse.Namespace) -> None:
    for path in setup_project(project):
        print(path)


HANDLERS: dict[str, Callable[[Project, argparse.Namespace], int | None]] = {
    "brief": brief, "issue": issue, "task": task, "allow": allow, "approve": approve,
    "question": question, "resolve": resolve, "setup": setup,
    **STANDARD_HANDLERS, **WORKFLOW_HANDLERS,
}
