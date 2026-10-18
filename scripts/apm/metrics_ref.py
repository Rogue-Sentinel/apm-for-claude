"""Measure the files of a git ref (a branch, tag or commit) without touching the working tree."""
from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from apm.metrics import Report, decode_text, measure_text, select_files, under_paths
from apm.standard_config import MetricsConfig

Run = Callable[..., subprocess.CompletedProcess]


class RefError(Exception):
    """The ref does not name a commit in this repository."""


def ref_files(root: Path, ref: str, run: Run = subprocess.run) -> list[str]:
    """The files committed at `ref`, as sorted POSIX paths."""
    done = None if ref.startswith("-") else run(
        ["git", "ls-tree", "-r", "--name-only", ref], cwd=root, capture_output=True,
    )
    if done is None or done.returncode != 0:
        raise RefError(f"unknown ref: {ref}")
    return sorted(done.stdout.decode("utf-8", errors="replace").splitlines())


def _text_at(root: Path, ref: str, path: str, run: Run) -> str | None:
    done = run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True)
    return decode_text(done.stdout) if done.returncode == 0 else None


def measure_at_ref(
    root: Path, ref: str, config: MetricsConfig, paths: Sequence[str] | None = None, run: Run = subprocess.run,
) -> Report:
    """Measure the selected files as committed at `ref`, optionally only under `paths`."""
    names = under_paths(select_files(ref_files(root, ref, run), config), paths)
    texts = ((name, _text_at(root, ref, name, run)) for name in names)
    measured = (measure_text(name, text) for name, text in texts if text is not None)
    return Report(tuple(metric for metric in measured if metric is not None))
