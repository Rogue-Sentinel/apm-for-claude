"""The guard's decision: allow or deny a tool call."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .guard_cli import is_cli_call
from .guard_commands import all_read_only, check_command
from .guard_paths import check_write, is_under, memory_folder, same_path
from .guard_workers import worker_command_violation, worker_file_violation
from .paths import PLUGIN_ROOT, Project, cli_command, to_native_path
from .profile import Profile

PREFIX = "APM guard: "
_FILE_KEYS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
_COMMAND_TOOLS = ("Bash", "PowerShell")
_CLI = cli_command(PLUGIN_ROOT)
_ASK_USER = (
    ". Ask the user in chat; if they approve this exact action, record it with "
    f'{_CLI} approve --command "<the exact full command>" --reason "<why>" '
    "(or --path <glob> for a file write), then retry."
    " Run the approve call with the Bash tool, on its own, with the command in single quotes "
    "if it holds a double quote."
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


def _write_roots(
    project: Project, temp_roots: Sequence[Path], config_dir: Path | None, worker: bool
) -> list[Path]:
    """The temp roots, plus this project's memory folder for the main session."""
    if worker or config_dir is None:
        return list(temp_roots)
    return [*temp_roots, memory_folder(project.main_root, config_dir)]


def _roots_for(
    target: Path, project: Project, temp_roots: Sequence[Path], config_dir: Path | None, worker: bool
) -> list[Path]:
    """The write roots for `target`; the memory folder opens only for paths strictly under it."""
    roots = _write_roots(project, temp_roots, config_dir, worker)
    return [*temp_roots, *(root for root in roots[len(temp_roots):] if not same_path(target, root))]


def _file_violation(
    event: Mapping[str, Any],
    project: Project,
    profile: Profile,
    allowed_globs: Sequence[str],
    temp_roots: Sequence[Path],
    windows: bool,
    config_dir: Path | None,
) -> str | None:
    raw = (event.get("tool_input") or {}).get(_FILE_KEYS.get(str(event.get("tool_name")), ""))
    if not isinstance(raw, str):
        return None
    target = to_native_path(raw, Path(event.get("cwd") or project.worktree_root), windows)
    roots = _roots_for(target, project, temp_roots, config_dir, bool(event.get("agent_id")))
    return worker_file_violation(target, event) or check_write(
        target, project, profile.protected_globs(), allowed_globs, roots)


def _state_dir_write(command: str, cwd: Path, project: Project) -> str | None:
    if not is_under(cwd, project.state_dir) or all_read_only(command):
        return None
    return "command runs inside the APM state directory"


def _cwd(event: Mapping[str, Any], project: Project, windows: bool) -> Path:
    return to_native_path(str(event.get("cwd") or "."), project.worktree_root, windows)


def _command_violation(
    command: str, event: Mapping[str, Any], project: Project, profile: Profile,
    prefixes: Sequence[str], windows: bool,
) -> str | None:
    cwd = _cwd(event, project, windows)
    reason = (
        worker_command_violation(command, event, cwd, project.worktree_root)
        or _state_dir_write(command, cwd, project)
        or check_command(command, profile.protected_globs(), prefixes, cwd=cwd, root=project.worktree_root)
    )
    return f"{reason}: {command.strip()}" if reason else None


def _violation(
    event: Mapping[str, Any],
    project: Project,
    profile: Profile,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
    config_dir: Path | None,
) -> str | None:
    globs, prefixes = _split_allowlist(allowlist)
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name") in _COMMAND_TOOLS and isinstance(command, str):
        return _command_violation(command, event, project, profile, prefixes, windows)
    return _file_violation(event, project, profile, globs, temp_roots, windows, config_dir)


def _approved(entry: Any, command: str, cwd: Path) -> bool:
    """True when `entry` approves exactly this whole command, run from this directory."""
    if not isinstance(entry, Mapping) or not isinstance(entry.get("command"), str):
        return False
    if not isinstance(entry.get("cwd"), str) or entry["command"].strip() != command.strip():
        return False
    return same_path(entry["cwd"], cwd)


def _exempt_command(
    event: Mapping[str, Any], project: Project, approvals: Sequence[Any], windows: bool
) -> bool:
    """True for a plain call of this plugin's CLI from Bash (its arguments, such as the command
    being approved, are data), or for an approved command outside the state directory."""
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name") not in _COMMAND_TOOLS or not isinstance(command, str):
        return False
    cwd = _cwd(event, project, windows)
    if event.get("tool_name") == "Bash" and is_cli_call(command.strip(), cwd, windows):
        return True
    if _state_dir_write(command, cwd, project):
        return False
    return any(_approved(entry, command, cwd) for entry in approvals)


def decide(
    event: Mapping[str, Any],
    project: Project | None,
    profile: Profile | None,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
    approvals: Sequence[Any] = (),
    config_dir: Path | None = None,
) -> Decision:
    """Return none or deny for a tool call. Live one-off `approvals` count only in the main session,
    and so does the memory folder under `config_dir`."""
    if project is None or profile is None:
        return Decision("none")
    worker = bool(event.get("agent_id"))
    if not worker and _exempt_command(event, project, approvals, windows):
        return Decision("none")
    globs = [] if worker else _split_allowlist(approvals)[0]
    rules = [*allowlist, *({"path": glob} for glob in globs)]
    reason = _violation(event, project, profile, rules, temp_roots, windows, config_dir)
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
