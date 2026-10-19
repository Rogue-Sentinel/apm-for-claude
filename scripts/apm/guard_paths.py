"""Decide whether a write to a path is blocked."""
from __future__ import annotations

import os
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Literal

from .paths import Project, worktree_relative


# `*` and `?` stay inside a segment, `**` crosses `/`, and a trailing `/**` also
# matches the directory itself. Matching ignores case: Windows paths do, and a
# false block is cheaper than a missed one.
_TOKEN = re.compile(r"/\*\*\Z|\*\*/|\*\*|\*|\?|.", re.DOTALL)
_TRANSLATE = {"/**": "(?:/.*)?", "**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}


@lru_cache(maxsize=256)
def _compile(glob: str) -> re.Pattern[str]:
    parts = [_TRANSLATE.get(t) or re.escape(t) for t in _TOKEN.findall(glob)]
    return re.compile("".join(parts), re.IGNORECASE | re.DOTALL)


def glob_matches(glob: str, relative: str) -> bool:
    """True when the slash-separated `relative` path matches `glob`."""
    return _compile(glob).fullmatch(relative) is not None


def matches_any(globs: Sequence[str], relative: str) -> bool:
    return any(glob_matches(glob, relative) for glob in globs)


def _real(path: Path | str) -> str:
    return os.path.normcase(os.path.realpath(str(path)))


def same_path(left: Path | str, right: Path | str) -> bool:
    return _real(left) == _real(right)


def is_under(path: Path | str, root: Path | str) -> bool:
    base = _real(root)
    return _real(path) == base or _real(path).startswith(base.rstrip(os.sep) + os.sep)


def memory_folder(main_root: Path, config_dir: Path) -> Path:
    """Where Claude Code keeps the memory of the project at `main_root`: its path with every
    character outside [A-Za-z0-9] turned into `-`, under the config dir's `projects` folder."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(main_root))
    return config_dir / "projects" / slug / "memory"


def is_unlinked(path: Path | str) -> bool:
    """True when no part of `path` is a symlink or junction (a missing part is not a link)."""
    return _real(path) == os.path.normcase(os.path.normpath(str(path)))


def _in_scope(target: Path, project: Project, temp_roots: Sequence[Path]) -> bool:
    roots = [project.main_root, project.worktree_root, *temp_roots]
    return any(is_under(target, root) for root in roots)


def _protected(relative: str, globs: Sequence[str], allowed_globs: Sequence[str]) -> str | None:
    if matches_any(globs, relative) and not matches_any(allowed_globs, relative):
        return f"{relative} is a protected path"
    return None


def write_denial(
    target: Path,
    project: Project,
    globs: Sequence[str],
    allowed_globs: Sequence[str],
    temp_roots: Sequence[Path],
) -> tuple[Literal["state", "outside", "protected"], str] | None:
    """Return which check blocks writing `target` and why, or None when it may proceed."""
    if is_under(target, project.state_dir):
        return "state", f"{target} is inside the APM state directory"
    if not _in_scope(target, project, temp_roots):
        return "outside", f"{target} is outside the project"
    found = worktree_relative(Path(os.path.realpath(str(target))))
    reason = _protected(found[1], globs, allowed_globs) if found else None
    return ("protected", reason) if reason else None


def check_write(
    target: Path,
    project: Project,
    globs: Sequence[str],
    allowed_globs: Sequence[str],
    temp_roots: Sequence[Path],
) -> str | None:
    """Return why writing `target` is blocked, or None when it may proceed."""
    denial = write_denial(target, project, globs, allowed_globs, temp_roots)
    return denial[1] if denial else None
