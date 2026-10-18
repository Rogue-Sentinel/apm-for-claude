"""Handlers for the workflow subcommands, and the one mutation helper every handler shares."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from apm import ledger as lg
from apm.paths import Project
from apm.state_store import commit_state


def mutate(project: Project, number: int | None, apply: Callable[[dict], str]) -> None:
    """Load the ledger, let `apply` change it and return the log event, then save, log and commit."""
    ledger = lg.load_ledger(project.ledger_path)
    event = apply(ledger)
    lg.append_log(ledger, number, event, datetime.now(timezone.utc))
    lg.save_ledger(project.ledger_path, ledger)
    commit_state(project, event)
