"""`apm github file` and `apm github close`: file and close GitHub issues, mirrored into the ledger."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from apm import ledger as lg
from apm import ledger_workflow as wf
from apm.cli_workflow import mutate
from apm.github import GitHubError, close_issue, create_issue
from apm.paths import Project

RUN = subprocess.run  # the one place `gh` is run from; tests replace it
CLOSABLE = ("integrating", "merged")


def _body(args: argparse.Namespace) -> str:
    text = Path(args.body_file).read_text(encoding="utf-8")
    return text if args.parent is None else f"{text.rstrip()}\n\nPart of #{args.parent}"


def _fields(args: argparse.Namespace, url: str) -> dict:
    given = {name: getattr(args, name) for name in ("kind", "lane") if getattr(args, name) is not None}
    return {"title": args.title, "status": "queued", "url": url, **given}


def _require_parent(project: Project, parent: int | None) -> None:
    if parent is not None and str(parent) not in lg.load_ledger(project.ledger_path)["issues"]:
        raise lg.LedgerError(f"unknown issue: {parent}")


def file(project: Project, args: argparse.Namespace) -> int:
    _require_parent(project, args.parent)
    try:
        number, url = create_issue(project.worktree_root, args.title, _body(args), args.label, run=RUN)
    except GitHubError as err:
        print(f"apm: {err}\nfile it by hand, then record it with apm issue N", file=sys.stderr)
        return 2

    def apply(ledger: dict) -> str:
        lg.upsert_issue(ledger, number, **_fields(args, url))
        if args.parent is not None:
            wf.set_parent(ledger, number, args.parent)
        return f"filed {number} {url}"

    mutate(project, number, apply)
    print(f"filed #{number}: {url}")
    return 0


def _refusal(project: Project, number: int) -> str | None:
    status = lg.load_ledger(project.ledger_path)["issues"].get(str(number), {}).get("status")
    if status in CLOSABLE:
        return None
    return f"issue {number} is {status or 'unknown'}; close it only once it is integrating or merged"


def _closed_on_github(project: Project, args: argparse.Namespace) -> bool:
    try:
        close_issue(project.worktree_root, args.number, f"Shipped in {args.pr}.", run=RUN)
    except GitHubError as err:
        print(f"apm: {err}\nclose it by hand, then record it with apm issue {args.number} --status merged", file=sys.stderr)
        return False
    return True


def close(project: Project, args: argparse.Namespace) -> int:
    refusal = _refusal(project, args.number)
    if refusal:
        print(f"apm: {refusal}", file=sys.stderr)
        return 1
    if not _closed_on_github(project, args):
        return 2

    def apply(ledger: dict) -> str:
        lg.upsert_issue(ledger, args.number, status="merged", pr=args.pr)
        _prompt_parent(ledger, args.number)
        return f"shipped in {args.pr}"

    mutate(project, args.number, apply)
    return 0


def _prompt_parent(ledger: dict, number: int) -> None:
    parent = ledger["issues"][str(number)].get("parent")
    if parent is None:
        return
    merged, total = wf.parent_progress(ledger, parent)
    if merged == total:
        print(f"all sub-issues of #{parent} are merged; close #{parent} too")


ACTIONS = {"file": file, "close": close}


def github(project: Project, args: argparse.Namespace) -> int:
    return ACTIONS[args.action](project, args)
