"""The argparse definition for the apm CLI."""
from __future__ import annotations

import argparse

KINDS = ("feature", "bug", "debt")


def _issue(sub) -> None:
    parser = sub.add_parser("issue", help="create or update an issue")
    parser.add_argument("number", type=int)
    parser.add_argument("--title")
    parser.add_argument("--kind", choices=KINDS)
    for name in ("lane", "status", "branch", "plan"):
        parser.add_argument(f"--{name}")


def _task(sub) -> None:
    parser = sub.add_parser("task", help="create or update a task")
    parser.add_argument("number", type=int)
    parser.add_argument("id")
    for name in ("title", "status", "worker", "model", "evidence"):
        parser.add_argument(f"--{name}")


def _allow(sub) -> None:
    parser = sub.add_parser("allow", help="allow a path or command for an issue")
    parser.add_argument("number", type=int)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--path", metavar="GLOB")
    target.add_argument("--command", metavar="PREFIX")
    parser.add_argument("--reason", required=True)


def _approve(sub) -> None:
    parser = sub.add_parser("approve", help="record the user's one-off approval, good for 10 minutes")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--command", metavar="CMD", help="the exact command the user approved")
    target.add_argument("--path", metavar="GLOB", help="the path the user approved writing")
    parser.add_argument("--reason", required=True)


def _questions(sub) -> None:
    ask = sub.add_parser("question", help="record a question for the user")
    ask.add_argument("number", type=int)
    ask.add_argument("--text", required=True)
    ask.add_argument("--blocks", nargs="*", default=[], metavar="ID")
    resolve = sub.add_parser("resolve", help="answer a recorded question")
    resolve.add_argument("number", type=int)
    resolve.add_argument("index", type=int)
    resolve.add_argument("--answer", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apm", description="Record and report project state.")
    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("brief", help="print where the project stands")
    sub.add_parser("setup", help="initialize APM in this project")
    _issue(sub)
    _task(sub)
    _allow(sub)
    _approve(sub)
    _questions(sub)
    return parser
