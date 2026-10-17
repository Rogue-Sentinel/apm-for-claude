"""PreToolUse hook: ask or deny tool calls that break the project's guard rules."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apm.guard import Decision, decide, to_hook_output  # noqa: E402
from apm.ledger import LedgerError, active_allowlist, load_ledger  # noqa: E402
from apm.paths import Project, find_project  # noqa: E402
from apm.profile import load_profile  # noqa: E402


def _deny(exc: BaseException | str) -> tuple[int, str]:
    output = to_hook_output(Decision("deny", f"APM guard error: {exc}"))
    return 0, json.dumps(output)


def _parse(stdin: str) -> dict | None:
    try:
        event = json.loads(stdin)
    except ValueError:
        return None
    return event if isinstance(event, dict) else None


def _start_dir(event: dict | None, environ: Mapping[str, str]) -> Path:
    if event and isinstance(event.get("cwd"), str) and event["cwd"]:
        return Path(event["cwd"])
    return Path(environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _allowlist(project: Project) -> list[dict]:
    try:
        return active_allowlist(load_ledger(project.ledger_path))
    except LedgerError:
        return []


def _guard(event: dict, project: Project) -> tuple[int, str]:
    profile = load_profile(project.profile_path)
    temp_roots = [Path(tempfile.gettempdir())]
    decision = decide(event, project, profile, _allowlist(project), temp_roots, os.name == "nt")
    output = to_hook_output(decision)
    return 0, json.dumps(output) if output else ""


def run(stdin: str, environ: Mapping[str, str]) -> tuple[int, str]:
    event = _parse(stdin)
    project = find_project(_start_dir(event, environ))
    if project is None or not project.is_initialized:
        return 0, ""
    if event is None:
        return _deny("hook input is not a JSON object")
    try:
        return _guard(event, project)
    except Exception as exc:  # fail closed: any error in an initialized project denies
        return _deny(exc)


if __name__ == "__main__":
    code, out = run(sys.stdin.buffer.read().decode("utf-8", "replace"), os.environ)
    sys.stdout.write(out)
    sys.exit(code)
