"""Handlers for the workflow subcommands, and the one mutation helper every handler shares."""
from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone

from apm import ledger as lg
from apm import ledger_workflow as wf
from apm.paths import Project
from apm.state_store import commit_state


def mutate(project: Project, number: int | None, apply: Callable[[dict], str]) -> None:
    """Load the ledger, let `apply` change it and return the log event, then save, log and commit."""
    ledger = lg.load_ledger(project.ledger_path)
    event = apply(ledger)
    lg.append_log(ledger, number, event, datetime.now(timezone.utc))
    lg.save_ledger(project.ledger_path, ledger)
    commit_state(project, event)


def note(project: Project, args: argparse.Namespace) -> None:
    kind, text = ("decision", args.decision) if args.decision is not None else ("concern", args.concern)

    def apply(ledger: dict) -> str:
        added = wf.add_note(ledger, args.number, kind, text, datetime.now(timezone.utc))
        return f"{kind} {args.number} {text}" if added else f"{kind} {args.number} already recorded"

    mutate(project, args.number, apply)


def _head(project: Project) -> str:
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=project.worktree_root,
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return done.stdout.strip()


def review(project: Project, args: argparse.Namespace) -> None:
    head = _head(project)

    def apply(ledger: dict) -> str:
        wf.record_review(
            ledger, args.number, head=head, open_findings=args.open,
            criteria_met=args.criteria_met, evidence=args.evidence, now=datetime.now(timezone.utc),
        )
        return f"review {args.number} {args.open} open at {head[:7]}"

    mutate(project, args.number, apply)


WORKFLOW_HANDLERS: dict[str, Callable[[Project, argparse.Namespace], int | None]] = {
    "note": note, "review": review,
}
