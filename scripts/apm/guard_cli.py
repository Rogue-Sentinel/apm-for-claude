"""Recognize a single, plain call of the apm CLI, whose arguments are data to record."""
from __future__ import annotations

import re
import shlex

SUBCOMMANDS = ("brief", "setup", "issue", "task", "allow", "question", "resolve", "approve")
_INTERPRETER = re.compile(r"(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?", re.IGNORECASE)
# Escapes, expansions and line breaks make bash quoting hard to read, so they rule the exemption out.
_UNSAFE = ("\\", "$", "`", "\n", "\r")
_QUOTED = re.compile(r""""[^"]*"|'[^']*'""")
_OPERATORS = frozenset(";&|<>()#")


def _single_command(command: str) -> bool:
    """True when nothing outside quotes chains, redirects, groups or comments."""
    if any(marker in command for marker in _UNSAFE):
        return False
    bare = _QUOTED.sub(" ", command)
    return not (_OPERATORS & set(bare) or '"' in bare or "'" in bare)


def _name(token: str) -> str:
    return token.rsplit("/", 1)[-1]


def _arguments(tokens: list[str]) -> list[str] | None:
    """The arguments after `apm` or `python .../apm_cli.py`, or None for any other program."""
    if tokens and _name(tokens[0]) == "apm":
        return tokens[1:]
    if len(tokens) > 1 and _INTERPRETER.fullmatch(_name(tokens[0])) and _name(tokens[1]) == "apm_cli.py":
        return tokens[2:]
    return None


def is_cli_call(command: str) -> bool:
    """True when `command` is exactly one apm CLI call with a known subcommand."""
    if not _single_command(command):
        return False
    arguments = _arguments(shlex.split(command))
    return bool(arguments) and arguments[0] in SUBCOMMANDS
