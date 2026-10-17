"""Recognize a single, plain call of this plugin's own apm CLI, whose arguments are data to record."""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from .guard_paths import same_path
from .paths import PLUGIN_ROOT, to_native_path

SUBCOMMANDS = ("brief", "setup", "issue", "task", "allow", "question", "resolve", "approve")
_INTERPRETER = re.compile(r"(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?", re.IGNORECASE)
# Escapes, expansions and line breaks make bash quoting hard to read, so they rule the exemption out.
_UNSAFE = ("\\", "$", "`", "\n", "\r")
_QUOTED = re.compile(r""""[^"]*"|'[^']*'""")
_OPERATORS = frozenset(";&|<>()#")
_PLUGIN_CLI = PLUGIN_ROOT / "scripts" / "apm_cli.py"


def _single_command(command: str) -> bool:
    """True when nothing outside quotes chains, redirects, groups or comments."""
    if any(marker in command for marker in _UNSAFE):
        return False
    bare = _QUOTED.sub(" ", command)
    return not (_OPERATORS & set(bare) or '"' in bare or "'" in bare)


def _name(token: str) -> str:
    return token.rsplit("/", 1)[-1]


def _arguments(tokens: list[str], cwd: Path, windows: bool) -> list[str] | None:
    """The arguments after `python <this plugin>/scripts/apm_cli.py`, or None for any other program."""
    if len(tokens) < 2 or not _INTERPRETER.fullmatch(_name(tokens[0])):
        return None
    script = to_native_path(tokens[1], cwd, windows)
    return tokens[2:] if same_path(script, _PLUGIN_CLI) else None


def is_cli_call(command: str, cwd: Path, windows: bool) -> bool:
    """True when `command`, run in `cwd`, is exactly one call of this plugin's CLI with a known subcommand."""
    if not _single_command(command):
        return False
    arguments = _arguments(shlex.split(command), cwd, windows)
    return bool(arguments) and arguments[0] in SUBCOMMANDS
