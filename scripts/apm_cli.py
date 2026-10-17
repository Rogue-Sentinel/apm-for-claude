"""The apm command line: records project state in the ledger and prints the briefing."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apm.cli_handlers import HANDLERS  # noqa: E402
from apm.cli_parser import build_parser  # noqa: E402
from apm.ledger import LedgerError  # noqa: E402
from apm.paths import Project, find_project  # noqa: E402
from apm.profile import ProfileError, load_profile  # noqa: E402


class UsageError(Exception):
    """The command cannot run here; the message is one line for the user."""


def _project(command: str) -> Project:
    project = find_project(Path.cwd())
    if project is None or not project.is_initialized:
        raise UsageError("not an initialized APM project (no .apm/profile.json)")
    load_profile(project.profile_path)
    if command != "brief" and not (project.state_dir / ".git").exists():
        raise UsageError(f"state is not set up at {project.state_dir}; run 'apm setup'")
    return project


def _run(argv: list[str] | None) -> None:
    args = build_parser().parse_args(argv)
    handler = HANDLERS.get(args.subcommand)
    if handler is None:
        raise UsageError(f"'{args.subcommand}' is not available yet")
    handler(_project(args.subcommand), args)


def main(argv: list[str] | None = None) -> int:
    try:
        _run(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 2)
    except (UsageError, LedgerError, ProfileError, subprocess.CalledProcessError, OSError) as exc:
        print(f"apm: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
