"""What a worker may not do: change APM state, which only the manager records."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .guard_commands import split_segments

# A worker never records state; the manager does. Matches `apm issue ...` at the start of a
# segment, also by path, and `python ".../scripts/apm_cli.py" issue ...` anywhere in it, in any
# case, with an optional `--` before the subcommand.
_MUTATIONS = r"""(?:--\s+)?["']?(?:issue|task|allow|question|resolve|setup|approve)(?![\w-])"""
_APM_MUTATION = re.compile(
    r"""^["']?(?:[^\s"']*[/\\])?apm["']?\s+""" + _MUTATIONS
    + r"""|(?<![\w.-])(?i:apm_cli\.py)["']?\s+""" + _MUTATIONS
)


def worker_state_change(command: str, event: Mapping[str, Any]) -> str | None:
    if not event.get("agent_id"):
        return None
    for segment in split_segments(command):
        if _APM_MUTATION.search(segment):
            return f"workers do not change APM state; report to the manager instead: {segment}"
    return None
