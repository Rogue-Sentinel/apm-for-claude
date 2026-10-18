"""Numbers from a project's own checker: run its command and read the figures off its output."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from apm.cli_errors import DebtError
from apm.standard_config import DebtSource


def _number(source: DebtSource, metric: str, pattern: str, output: str) -> int:
    found = re.search(pattern, output, re.MULTILINE)
    if found is None:
        raise DebtError(f"{source.name}: no match for {metric}")
    text = found.group(1)
    if not text.isdecimal():
        raise DebtError(f"{source.name}: {metric} is not a whole number: {text!r}")
    return int(text)


def run_source(source: DebtSource, root: Path, run=subprocess.run) -> dict[str, int]:
    """Run the source's command in `root` and read each metric from its stdout.

    The exit code is ignored, because a checker exits non-zero when it finds debt.
    """
    try:
        done = run(source.command, shell=True, cwd=root, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    except OSError as exc:
        raise DebtError(f"{source.name}: cannot run {source.command}: {exc}") from exc
    output = done.stdout or ""
    return {metric: _number(source, metric, pattern, output) for metric, pattern in source.numbers.items()}
