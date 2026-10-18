"""What a worker may not do: change APM state, which only the manager records, or write `.apm/`."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .guard_commands import protected_reason, split_segments
from .guard_data import mask_data
from .guard_github import gh_write_reason
from .guard_paths import matches_any
from .guard_words import command_words, spellings
from .paths import worktree_relative
from .profile import WORKER_PROTECTED

# A worker never records state; the manager does. A segment changes state when `apm <subcommand>` is
# run as a command (at the start, or behind a wrapper such as `env`, `sudo`, `xargs`, `-c`, `$(` or
# `(`), or `apm_cli.py <subcommand>` appears anywhere, in any case, with an optional `--` before the
# subcommand. `debt` counts unless it is `debt check`, which only reads: `debt baseline` rewrites the
# ratchet's baseline, and an action added later is denied until it is classified.
_STATE_SUBCOMMANDS = frozenset("issue task allow question resolve setup approve note review github init gate".split())
# The subcommands a worker may run; every other one is denied above. A test walks the parser.
WORKER_READ_ONLY = ("brief", "metrics", "coverage", "audit", "debt check")
_WRAPPERS = frozenset(
    "env sudo doas command exec xargs time nohup nice ionice setsid stdbuf timeout builtin then do else elif "
    "if while until ! bash sh zsh dash ksh cmd powershell pwsh".split())
_OPTION = re.compile(r"-|//?[a-z]$", re.IGNORECASE)
_RUN_STRING = re.compile(r"-\w*c|-command|//?c", re.IGNORECASE)


def _program(word: str) -> str:
    return re.sub(r"\.(?:exe|cmd|bat)$", "", word.rsplit("/", 1)[-1].lower())


def _before_a_command(words: list[str]) -> bool:
    """True when `words` only lead into a command: wrappers, options and their values, assignments."""
    last = max((i for i, word in enumerate(words) if _RUN_STRING.fullmatch(word)), default=-1)
    words = words[last + 1:]  # `bash -c "..."`: the string that follows starts a command
    after_option = False
    for word in words:
        option = bool(_OPTION.match(word))
        if not (after_option or option or "=" in word or word.isdigit() or _program(word) in _WRAPPERS):
            return False
        after_option = option
    return True


def _changes_state(after: list[str]) -> bool:
    """True when the words after `apm` name a subcommand that records state."""
    plain = [word for word in after if word != "--"]
    if plain[:1] == ["debt"]:
        return not plain[1:2] or not plain[1].startswith("check")
    return bool(plain) and plain[0] in _STATE_SUBCOMMANDS


def _runs_apm_state_change(words: list[str]) -> bool:
    for index, word in enumerate(words):
        name = _program(word)
        if name == "apm_cli.py" or (name == "apm" and _before_a_command(words[:index])):
            if _changes_state(words[index + 1:]):
                return True
    return False


def _state_change(command: str) -> str | None:
    for segment in split_segments(command):
        if any(_runs_apm_state_change(words) for text in spellings(segment) for words in command_words(text)):
            return f"workers do not change APM state; report to the manager instead: {segment}"
    return None


def _github_write(command: str) -> str | None:
    for segment in split_segments(mask_data(command)):
        reason = gh_write_reason(segment)
        if reason:
            return reason
    return None


def _apm_write(command: str, cwd: Path, root: Path) -> str | None:
    for segment in split_segments(mask_data(command)):
        reason = protected_reason(segment, WORKER_PROTECTED, cwd, root)
        if reason:
            return f"workers do not write .apm/ or the Claude settings; {reason}"
    return None


def worker_command_violation(command: str, event: Mapping[str, Any], cwd: Path, root: Path) -> str | None:
    """Why a worker may not run `command`: it changes APM state, writes `.apm/` or writes to GitHub.

    No allowlist lifts this.
    """
    if not event.get("agent_id"):
        return None
    return _state_change(command) or _github_write(command) or _apm_write(command, cwd, root)


def worker_file_violation(target: Path, event: Mapping[str, Any]) -> str | None:
    """Why a worker may not write `target`: it is under `.apm/` of its checkout."""
    found = worktree_relative(Path(os.path.realpath(str(target)))) if event.get("agent_id") else None
    if found and matches_any(WORKER_PROTECTED, found[1]):
        return f"workers do not write .apm/ or the Claude settings; {found[1]} is a protected path"
    return None
