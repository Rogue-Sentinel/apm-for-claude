"""The guard's decision: allow or deny a tool call."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .guard_cli import is_cli_call
from .guard_commands import all_read_only, check_command
from .guard_outside import SHELL_TEMP_ROOTS, Reach, outside_write
from .guard_paths import is_under, roots_for, same_path, write_denial
from .guard_workers import worker_command_violation, worker_file_violation
from .paths import PLUGIN_ROOT, Project, cli_command, to_native_path
from .profile import Profile

PREFIX = "APM guard: "
_FILE_KEYS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}
_COMMAND_TOOLS = ("Bash", "PowerShell")
_CLI = cli_command(PLUGIN_ROOT)
_REMEDIES = {
    "command": (
        ". Ask the user in chat; if they approve this exact action, record it with "
        f'{_CLI} approve --command "<the exact full command>" --reason "<why>", then retry.'
        " Run the approve call with the Bash tool, on its own, with the command in single quotes "
        "if it holds a double quote."
    ),
    "protected": (
        ". Ask the user in chat; if they approve this exact write, record it with "
        f'{_CLI} approve --path "<the path named above, as written>" --reason "<why>", then retry.'
        " Run the approve call with the Bash tool, on its own."
    ),
    "outside": ". No approval lifts this for a file tool. Ask the user in chat to make the change themselves.",
    "state": (
        f". Ask the user in chat. No approval lifts this: APM state changes only through the CLI ({_CLI}), "
        "never by editing its files."
    ),
}


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
    config_dir: Path | None,
) -> tuple[str, str] | None:
    raw = (event.get("tool_input") or {}).get(_FILE_KEYS.get(str(event.get("tool_name")), ""))
    if not isinstance(raw, str):
        return None
    target = to_native_path(raw, Path(event.get("cwd") or project.worktree_root), windows)
    if reason := worker_file_violation(target, event):
        return reason, ""
    roots = roots_for(target, project, temp_roots, config_dir, bool(event.get("agent_id")))
    denial = write_denial(target, project, profile.protected_globs(), allowed_globs, roots)
    return (denial[1], _REMEDIES[denial[0]]) if denial else None


def _state_dir_write(command: str, cwd: Path, project: Project) -> str | None:
    if not is_under(cwd, project.state_dir) or all_read_only(command):
        return None
    return "command runs inside the APM state directory"


def _cwd(event: Mapping[str, Any], project: Project, windows: bool) -> Path:
    return to_native_path(str(event.get("cwd") or "."), project.worktree_root, windows)


def _command_violation(
    command: str, event: Mapping[str, Any], profile: Profile, prefixes: Sequence[str], reach: Reach
) -> tuple[str, str] | None:
    """The worker rules, the state directory and `check_command` first, so their reasons stay; then outside writes."""
    project = reach.project
    cwd = _cwd(event, project, reach.windows)
    if reason := worker_command_violation(command, event, cwd, project.worktree_root):
        return f"{reason}: {command.strip()}", _REMEDIES["command"]
    if reason := _state_dir_write(command, cwd, project):
        return f"{reason}: {command.strip()}", _REMEDIES["state"]
    reason = check_command(command, profile.protected_globs(), prefixes, cwd=cwd, root=project.worktree_root)
    reason = reason or outside_write(command, cwd, prefixes, reach)
    return (f"{reason}: {command.strip()}", _REMEDIES["command"]) if reason else None


def _violation(
    event: Mapping[str, Any],
    project: Project,
    profile: Profile,
    allowlist: Sequence[Any],
    temp_roots: Sequence[Path],
    windows: bool,
    config_dir: Path | None,
    *,
    home: Path | None,
    shell_temp: Sequence[Path],
) -> tuple[str, str] | None:
    """Return (reason, remedy) for a denied call, or None. The remedy offers only an approval that works.
    The shell temp roots (`/tmp`) and the home folder reach only the command check, never the file tools."""
    globs, prefixes = _split_allowlist(allowlist)
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name") in _COMMAND_TOOLS and isinstance(command, str):
        worker = bool(event.get("agent_id"))
        reach = Reach(project, (*temp_roots, *shell_temp), config_dir, home, worker, windows)
        return _command_violation(command, event, profile, prefixes, reach)
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
    home: Path | None = None,
    shell_temp: Sequence[Path] = SHELL_TEMP_ROOTS,
) -> Decision:
    """Return none or deny for a tool call. Live one-off `approvals` count only in the main session,
    and so does the memory folder under `config_dir`. `home` and `shell_temp` serve shell commands only;
    `shell_temp` defaults to the roots the hook passes, so a direct caller gets the hook's verdict."""
    if project is None or profile is None:
        return Decision("none")
    worker = bool(event.get("agent_id"))
    if not worker and _exempt_command(event, project, approvals, windows):
        return Decision("none")
    globs = [] if worker else _split_allowlist(approvals)[0]
    rules = [*allowlist, *({"path": glob} for glob in globs)]
    violation = _violation(event, project, profile, rules, temp_roots, windows, config_dir,
                           home=home, shell_temp=shell_temp)
    if violation is None:
        return Decision("none")
    reason, remedy = violation
    return Decision("deny", PREFIX + reason + ("" if worker else remedy))


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
