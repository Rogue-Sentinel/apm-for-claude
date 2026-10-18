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


def add_workflow_parsers(sub) -> None:
    _note(sub)
    _review(sub)
