"""The guard's decision: allow, ask, or deny a tool call."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .guard_commands import all_read_only, check_command, split_segments
from .guard_paths import check_write, is_under
from .paths import Project, to_native_path
from .profile import Profile

PREFIX = "APM guard: "
_FILE_KEYS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
_COMMAND_TOOLS = ("Bash", "PowerShell")
# A worker never records state; the manager does. Matches `apm issue ...`, also by path.
_APM_MUTATION = re.compile(
    r"""["']?(?:[^\s"']*/)?apm["']?\s+(?:issue|task|allow|question|resolve|setup)(?![\w-])"""
)


@dataclass(frozen=True)
class Decision:
    kind: Literal["none", "ask", "deny"]
    reason: str = ""


def _split_allowlist(allowlist: Sequence[Any]) -> tuple[list[str], list[str]]:
    """Return (allowed globs, allowed command prefixes); malformed entries are ignored."""
    globs, prefixes = [], []
    for entry in allowlist:
        if not isinstance(entry, Mapping):
            continue
        if isinstance(entry.get("path"), str):
            globs.append(entry["path"])
        if isinstance(entry.get("command"), str):
            prefixes.append(entry["command"])
    return globs, prefixes


def _file_violation(
    event: Mapping[str, Any],
    project: Project,
    profile: Profile,
    allowed_globs: Sequence[str],
    temp_roots: Sequence[Path],
    windows: bool,
) -> str | None:
    raw = (event.get("tool_input") or {}).get(_FILE_KEYS.get(str(event.get("tool_name")), ""))
    if not isinstance(raw, str):
        return None
    target = to_native_path(raw, Path(event.get("cwd") or project.worktree_root), windows)
    return check_write(target, project, profile.protected_globs(), allowed_globs, temp_roots)


def _worker_state_change(command: str, event: Mapping[str, Any]) -> str | None:
    if not event.get("agent_id"):
        return None
    for segment in split_segments(command):
        if _APM_MUTATION.match(segment):
            return f"workers do not change APM state; report to the manager instead: {segment}"
    return None


def _state_dir_write(command: str, cwd: Path, project: Project) -> str | None:
    if not is_under(cwd, project.state_dir) or all_read_only(command):
        return None
    return f"command runs inside the APM state directory: {command}"


def _command_violation(
    command: str, event: Mapping[str, Any], project: Project, profile: Profile,
    prefixes: Sequence[str], windows: bool,
) -> str | None:
    cwd = to_native_path(str(event.get("cwd") or "."), project.worktree_root, windows)
    return (
        _worker_state_change(command, event)
        or _state_dir_write(command, cwd, project)
        or check_command(command, profile.protected_globs(), prefixes, cwd=cwd, root=project.worktree_root)
    )


def _violation(
    event: Mapping[str, Any],
    project: Project,
    profile: Profile,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
) -> str | None:
    globs, prefixes = _split_allowlist(allowlist)
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name") in _COMMAND_TOOLS and isinstance(command, str):
        return _command_violation(command, event, project, profile, prefixes, windows)
    return _file_violation(event, project, profile, globs, temp_roots, windows)


def decide(
    event: Mapping[str, Any],
    project: Project | None,
    profile: Profile | None,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
) -> Decision:
    """Return none, ask (main session) or deny (worker) for a tool call."""
    if project is None or profile is None:
        return Decision("none")
    reason = _violation(event, project, profile, allowlist, temp_roots, windows)
    if reason is None:
        return Decision("none")
    return Decision("deny" if event.get("agent_id") else "ask", PREFIX + reason)


def to_hook_output(decision: Decision) -> dict | None:
    if decision.kind == "none":
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.kind,
            "permissionDecisionReason": decision.reason,
        }
    }
