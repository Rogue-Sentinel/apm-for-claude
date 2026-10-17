"""Decide whether a shell command is destructive or touches a protected path."""
from __future__ import annotations

import glob
import itertools
import re
import shlex
from collections.abc import Iterator, Sequence
from pathlib import Path

from .guard_paths import matches_any

READ_ONLY_PREFIXES = (
    "cat ", "head ", "tail ", "less ", "ls", "dir", "stat ", "file ", "wc ", "grep ", "rg ",
    "git log", "git diff", "git show", "git status", "git blame", "sqlite3 -readonly ",
)
_SPLIT = re.compile(r"&&|\|\||;|\||\r?\n|(?<![<>&])&(?![&>])")
_NO_EXEMPT = ("$(", "`")
_GIT = r"(?<![\w-])git\s+(?:(?:-[cC]|--git-dir|--work-tree)\s+\S+\s+|--?\S+\s+)*"
_END = r"(?=\s|$)"
_PS_DELETE = r"(?<![\w-])(?:Remove-Item|ri|rmdir|rd|del|erase)(?![\w-])"
_CMD_DELETE = r"(?<![\w-])(?:rmdir|rd|del|erase)(?![\w-])"


def _p(pattern: str, label: str) -> tuple[re.Pattern[str], str]:
    return re.compile(pattern, re.IGNORECASE), label


DESTRUCTIVE: tuple[tuple[re.Pattern[str], str], ...] = (
    _p(r"(?<![\w-])rm\s+(?:\S+\s+)*?(?:-[a-z]*r[a-z]*|--recursive)" + _END, "recursive rm"),
    _p(_GIT + r"clean(?![\w-])", "git clean"),
    _p(_GIT + r"reset\b.*\s--hard\b", "git reset --hard"),
    _p(_GIT + r"push\b.*(?:\s-[a-z]*f[a-z]*" + _END + r"|\s--force|\s\+\S)", "forced git push"),
    _p(_GIT + r"branch\b.*\s-[a-z]*(?-i:D)[a-z]*" + _END, "git branch -D"),
    _p(_GIT + r"worktree\s+remove\b", "git worktree remove"),
    _p(_GIT + r"checkout\s+(?:\S+\s+)*\." + _END, "git checkout discarding changes"),
    _p(_GIT + r"restore\s+(?:\S+\s+)*\." + _END, "git restore discarding changes"),
    _p(_GIT + r"stash\s+clear\b", "git stash clear"),
    _p(r"(?<![\w-])find\b.*\s-delete\b", "find -delete"),
    _p(r"(?<![\w-])find\b.*\s-exec(?:dir)?\s+(?:\S*/)?rm\b", "find -exec rm"),
    _p(r"\bdrop\s+(?:table|database|schema)\b", "SQL drop"),
    _p(r"\btruncate\s+table\b", "SQL truncate"),
    _p(_PS_DELETE + r".*\s-r[a-z]*(?=[\s:]|$)", "recursive PowerShell delete"),
    _p(_CMD_DELETE + r".*\s/s\b", "recursive cmd delete"),
)


# Checked on the whole command, because a pipe separates the recursive listing
# from the delete: `Get-ChildItem x -Recurse | Remove-Item`.
_PIPED_DELETE = re.compile(
    r"\s-r(?:ecurse)?(?=[\s:|]|$).*\|\s*" + _PS_DELETE + r"|\s-recurse\b.*" + _PS_DELETE,
    re.IGNORECASE,
)
_GLOB_CHARS = frozenset("*?[")
_GLOB_LIMIT = 10000


def split_segments(command: str) -> list[str]:
    """Split a command line on `&&`, `||`, `;`, `|`, `&` and newlines."""
    parts = (part.strip() for part in _SPLIT.split(command))
    return [part for part in parts if part]


def destructive_reason(segment: str) -> str | None:
    for pattern, label in DESTRUCTIVE:
        if pattern.search(segment):
            return f"destructive command ({label}): {segment}"
    return None


def _tokens(segment: str) -> list[str]:
    text = segment.replace("\\", "/")
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _candidates(token: str) -> Iterator[str]:
    """Yield the path-like pieces of a token and each trailing sub-path of them."""
    for piece in {token, token.lstrip("<>&"), token.split("=", 1)[-1]}:
        piece = piece.lstrip("<>&")
        while piece.startswith("./"):
            piece = piece[2:]
        parts = piece.split("/")
        for i in range(len(parts)):
            yield "/".join(parts[i:])


def _glob_hits(token: str, cwd: Path, root: Path) -> Iterator[str]:
    """Yield the root-relative POSIX path of each file a shell glob would expand to."""
    found = glob.glob(token, root_dir=cwd, recursive=True)
    for match in itertools.islice(found, _GLOB_LIMIT):
        try:
            yield (cwd / match).resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            continue


def _token_hits(token: str, globs: Sequence[str], cwd: Path | None, root: Path | None) -> bool:
    if any(matches_any(globs, c) for c in _candidates(token) if c):
        return True
    if cwd is None or not _GLOB_CHARS & set(token):
        return False
    return any(matches_any(globs, hit) for hit in _glob_hits(token, cwd, root or cwd))


def _is_read_only(segment: str) -> bool:
    lowered = segment.lower()
    return lowered.startswith(READ_ONLY_PREFIXES) and ">" not in segment


def protected_reason(
    segment: str, globs: Sequence[str], cwd: Path | None = None, root: Path | None = None
) -> str | None:
    """Report a non-read-only segment that names a protected path.

    A token also counts when any trailing sub-path of it matches, so
    `/repo/data/x.db` and `../data/x.db` hit the glob `data/*.db`. With `cwd`,
    a token holding `*`, `?` or `[` is expanded as the shell would and each
    match, taken relative to `root`, is tested too.
    """
    if _is_read_only(segment):
        return None
    for token in _tokens(segment):
        if _token_hits(token, globs, cwd, root):
            return f"command touches a protected path ({token}): {segment}"
    return None


def _is_exempt(segment: str, allowed_prefixes: Sequence[str]) -> bool:
    if any(marker in segment for marker in _NO_EXEMPT):
        return False
    for prefix in allowed_prefixes:
        rest = segment[len(prefix):]
        if segment.startswith(prefix) and (not rest or rest[0].isspace() or prefix[-1:].isspace()):
            return True
    return False


def check_command(
    command: str,
    globs: Sequence[str],
    allowed_prefixes: Sequence[str],
    cwd: Path | None = None,
    root: Path | None = None,
) -> str | None:
    """Return the reason for the first violating segment, or None."""
    if _PIPED_DELETE.search(command):
        return f"destructive command (piped recursive delete): {command}"
    segments = (g for g in split_segments(command) if not _is_exempt(g, allowed_prefixes))
    reasons = (destructive_reason(g) or protected_reason(g, globs, cwd, root) for g in segments)
    return next((reason for reason in reasons if reason), None)
