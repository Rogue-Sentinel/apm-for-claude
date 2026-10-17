"""SessionStart hook: brief the session on the APM ledger, name the CLI, and flag version drift."""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apm  # noqa: E402
from apm.briefing import render_briefing  # noqa: E402
from apm.ledger import LedgerError  # noqa: E402
from apm.paths import Project, cli_command, find_project  # noqa: E402
from apm.profile import ProfileError, load_profile  # noqa: E402
from apm.state_store import load_state  # noqa: E402

# The Bash tool's PATH may lack the plugin's bin/, and another tool may own the name `apm`.
CLI_LINE = "APM CLI: " + cli_command(Path(__file__).resolve().parent.parent)


def _cwd(stdin: str) -> Path | None:
    try:
        event = json.loads(stdin)
    except ValueError:
        return None
    cwd = event.get("cwd") if isinstance(event, dict) else None
    return Path(cwd) if isinstance(cwd, str) and cwd else None


def _render(project: Project) -> str:
    try:
        return render_briefing(load_state(project), None)
    except LedgerError as exc:
        return render_briefing(None, str(exc))


def _briefing(project: Project) -> str:
    try:
        return _render(project)
    except Exception as exc:  # a broken briefing must never crash session start
        return f"Briefing unavailable: {exc}"


def _version_line(version: str) -> str:
    if version == apm.VERSION:
        return ""
    return f"APM version mismatch: project framework {version}, plugin {apm.VERSION}."


def _context(project: Project) -> str:
    try:
        profile = load_profile(project.profile_path)
    except ProfileError as exc:
        return f"APM profile error: {exc}"
    return "\n".join(part for part in (_briefing(project), _version_line(profile.framework_version)) if part)


def run(stdin: str, environ: Mapping[str, str]) -> tuple[int, str]:
    cwd = _cwd(stdin)
    project = find_project(cwd) if cwd else None
    if project is None or not project.is_initialized:
        return 0, ""
    context = f"{_context(project)}\n{CLI_LINE}"
    specific = {"hookEventName": "SessionStart", "additionalContext": context}
    return 0, json.dumps({"hookSpecificOutput": specific})


if __name__ == "__main__":
    code, out = run(sys.stdin.buffer.read().decode("utf-8", "replace"), os.environ)
    sys.stdout.write(out)
    sys.exit(code)
