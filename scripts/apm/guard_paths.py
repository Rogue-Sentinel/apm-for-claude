"""Decide whether a write to a path is blocked."""
from __future__ import annotations

import os
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

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


def is_under(path: Path | str, root: Path | str) -> bool:
    base = _real(root)
    return _real(path) == base or _real(path).startswith(base.rstrip(os.sep) + os.sep)


def _in_scope(target: Path, project: Project, temp_roots: Sequence[Path]) -> bool:
    roots = [project.main_root, project.worktree_root, *temp_roots]
    return any(is_under(target, root) for root in roots)


def _protected(relative: str, globs: Sequence[str], allowed_globs: Sequence[str]) -> str | None:
    if matches_any(globs, relative) and not matches_any(allowed_globs, relative):
        return f"{relative} is a protected path"
    return None


def check_write(
    target: Path,
    project: Project,
    globs: Sequence[str],
    allowed_globs: Sequence[str],
    temp_roots: Sequence[Path],
) -> str | None:
    """Return why writing `target` is blocked, or None when it may proceed."""
    if is_under(target, project.state_dir):
        return f"{target} is inside the APM state directory"
    if not _in_scope(target, project, temp_roots):
        return f"{target} is outside the project"
    found = worktree_relative(Path(os.path.realpath(str(target))))
    return _protected(found[1], globs, allowed_globs) if found else None
