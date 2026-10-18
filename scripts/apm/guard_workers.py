"""What a worker may not do: change APM state, which only the manager records, or write `.apm/`."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .guard_commands import protected_reason, split_segments
from .guard_data import mask_data
from .guard_paths import matches_any
from .paths import worktree_relative
from .profile import WORKER_PROTECTED

# A worker never records state; the manager does. Matches `apm issue ...` at the start of a
# segment, also by path, and `python ".../scripts/apm_cli.py" issue ...` anywhere in it, in any
# case, with an optional `--` before the subcommand. `debt baseline` rewrites the ratchet's
# baseline, so it counts; `debt check` only reads.
_DASHES = r"""(?:--\s+)?["']?"""
_BASELINE = r"""debt["']?\s+""" + _DASHES + r"""baseline"""
_MUTATIONS = _DASHES + r"(?:issue|task|allow|question|resolve|setup|approve|" + _BASELINE + r")(?![\w-])"
_APM_MUTATION = re.compile(
    r"""(?:^|(?i:\s-\w*c|\s-command|\s/c)\s+)["']?(?:[^\s"']*[/\\])?apm["']?\s+""" + _MUTATIONS
    + r"""|(?<![\w.-])(?i:apm_cli\.py)\\*["']?\s+""" + _MUTATIONS
)


def _state_change(command: str) -> str | None:
    for segment in split_segments(command):
        if _APM_MUTATION.search(segment):
            return f"workers do not change APM state; report to the manager instead: {segment}"
    return None


def _apm_write(command: str, cwd: Path, root: Path) -> str | None:
    for segment in split_segments(mask_data(command)):
        reason = protected_reason(segment, WORKER_PROTECTED, cwd, root)
        if reason:
            return f"workers do not write .apm/ or the Claude settings; {reason}"
    return None


def worker_command_violation(command: str, event: Mapping[str, Any], cwd: Path, root: Path) -> str | None:
    """Why a worker may not run `command`: it changes APM state or writes `.apm/`. No allowlist lifts this."""
    if not event.get("agent_id"):
        return None
    return _state_change(command) or _apm_write(command, cwd, root)


def worker_file_violation(target: Path, event: Mapping[str, Any]) -> str | None:
    """Why a worker may not write `target`: it is under `.apm/` of its checkout."""
    found = worktree_relative(Path(os.path.realpath(str(target)))) if event.get("agent_id") else None
    if found and matches_any(WORKER_PROTECTED, found[1]):
        return f"workers do not write .apm/ or the Claude settings; {found[1]} is a protected path"
    return None
