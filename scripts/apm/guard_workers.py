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
from .guard_words import shell_words, spellings
from .paths import worktree_relative
from .profile import WORKER_PROTECTED

# A worker never records state; the manager does. A segment changes state when a word naming the apm
# program (`apm`, by path, `.exe`/`.cmd`/`.bat`, in any case, or `apm_cli.py`) is followed anywhere later
# in the segment by a state subcommand. There is no list of wrappers to fall behind (`eval`, `timeout 30s`,
# `uv run`, `parallel` all run it), and an expansion that is empty at run time (`apm $X note 1`) cannot
# hide the subcommand. `debt` counts unless the word after it starts with `check`, which only reads:
# `debt baseline` rewrites the ratchet's baseline, and an action added later is denied until classified.
# The cost is that text naming such a call (`echo apm note`, `grep apm issue docs`) is denied too; a
# message argument is masked first, so a commit message that only names one is allowed. Known limits:
# the subcommand built at run time (`apm $CMD 1`), and the program named at run time (`$APM note 1`).
_STATE_SUBCOMMANDS = frozenset("issue task allow question resolve setup approve note review github init gate".split())
# The subcommands a worker may run; every other one is denied above. A test walks the parser.
WORKER_READ_ONLY = ("brief", "metrics", "coverage", "audit", "debt check")
_APM_PROGRAMS = frozenset({"apm", "apm_cli.py"})
_STATE_REASON = (
    "workers do not change APM state; report to the manager instead "
    "(to search for the text, use the Grep tool: it does not go through the shell)"
)


def _program(word: str) -> str:
    return re.sub(r"\.(?:exe|cmd|bat)$", "", word.rsplit("/", 1)[-1].lower())


def _changes_state(after: list[str]) -> bool:
    """True when any word after the program is a state subcommand, or `debt` not followed by `check`."""
    followers = [*after[1:], ""]
    return any(word in _STATE_SUBCOMMANDS or (word == "debt" and not following.startswith("check"))
               for word, following in zip(after, followers))


def _runs_apm_state_change(words: list[str]) -> bool:
    return any(_program(word) in _APM_PROGRAMS and _changes_state(words[index + 1:])
               for index, word in enumerate(words))


def _state_change(command: str) -> str | None:
    for segment in split_segments(mask_data(command)):
        if any(_runs_apm_state_change(shell_words(text)) for text in spellings(segment)):
            return f"{_STATE_REASON}: {segment}"
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
