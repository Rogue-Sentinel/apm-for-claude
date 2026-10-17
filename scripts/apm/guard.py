"""The guard's decision: allow or deny a tool call."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .guard_cli import is_cli_call
from .guard_commands import all_read_only, check_command, split_segments
from .guard_paths import check_write, is_under
from .paths import Project, cli_command, to_native_path
from .profile import Profile

PREFIX = "APM guard: "
_FILE_KEYS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
_COMMAND_TOOLS = ("Bash", "PowerShell")
# A worker never records state; the manager does. Matches `apm issue ...`, also by path.
_APM_MUTATION = re.compile(
    r"""["']?(?:[^\s"']*/)?apm["']?\s+(?:issue|task|allow|question|resolve|setup|approve)(?![\w-])"""
)
_CLI = cli_command(Path(__file__).resolve().parents[2])
_ASK_USER = (
    ". Ask the user in chat; if they approve this exact action, record it with "
    f'{_CLI} approve --command "<the exact command>" --reason "<why>" '
    "(or --path <glob> for a file write), then retry."
)


@dataclass(frozen=True)
class Decision:
    kind: Literal["none", "deny"]
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


def _exempt_command(event: Mapping[str, Any], commands: Sequence[str]) -> bool:
    """True when the whole command, stripped, is exactly an approved one, or is a plain apm
    CLI call from Bash (its arguments, such as the command being approved, are data)."""
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name") not in _COMMAND_TOOLS or not isinstance(command, str):
        return False
    if event.get("tool_name") == "Bash" and is_cli_call(command.strip()):
        return True
    return command.strip() in {approved.strip() for approved in commands}


def decide(
    event: Mapping[str, Any],
    project: Project | None,
    profile: Profile | None,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
    approvals: Sequence[Any] = (),
) -> Decision:
    """Return none or deny for a tool call. Live one-off `approvals` count only in the main session."""
    if project is None or profile is None:
        return Decision("none")
    worker = bool(event.get("agent_id"))
    globs, commands = ([], []) if worker else _split_allowlist(approvals)
    if not worker and _exempt_command(event, commands):
        return Decision("none")
    rules = [*allowlist, *({"path": glob} for glob in globs)]
    reason = _violation(event, project, profile, rules, temp_roots, windows)
    if reason is None:
        return Decision("none")
    return Decision("deny", PREFIX + reason + ("" if worker else _ASK_USER))


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
