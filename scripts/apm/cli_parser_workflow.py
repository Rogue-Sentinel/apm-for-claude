"""The argparse definitions for the workflow subcommands; later tasks add theirs to `add_workflow_parsers`."""
from __future__ import annotations


def _note(sub) -> None:
    parser = sub.add_parser("note", help="record a decision or a concern on an issue")
    parser.add_argument("number", type=int)
    kind = parser.add_mutually_exclusive_group(required=True)
    kind.add_argument("--decision", metavar="TEXT")
    kind.add_argument("--concern", metavar="TEXT")


def _review(sub) -> None:
    parser = sub.add_parser("review", help="record the final review of an issue")
    parser.add_argument("number", type=int)
    parser.add_argument("--open", type=int, required=True, metavar="COUNT", help="findings still open")
    parser.add_argument("--criteria-met", action="store_true", help="the acceptance criteria are met")
    parser.add_argument("--evidence", required=True)


def _github(sub) -> None:
    from apm.cli_parser import KINDS  # lazy: cli_parser imports this module

    parser = sub.add_parser("github", help="file and close GitHub issues, mirrored into the ledger")
    actions = parser.add_subparsers(dest="action", required=True)
    file = actions.add_parser("file", help="file an issue and record it as queued")
    file.add_argument("--title", required=True)
    file.add_argument("--body-file", required=True, metavar="PATH")
    file.add_argument("--label", action="append", default=[], metavar="L")
    file.add_argument("--kind", choices=KINDS)
    file.add_argument("--lane", metavar="NAME")
    file.add_argument("--parent", type=int, metavar="P", help="make this a sub-issue of issue P")
    close = actions.add_parser("close", help="close a shipped issue and record it as merged")
    close.add_argument("number", type=int)
    close.add_argument("--pr", required=True, metavar="URL")


def add_workflow_parsers(sub) -> None:
    _note(sub)
    _review(sub)
    _github(sub)
