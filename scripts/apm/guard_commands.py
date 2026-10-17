"""Decide whether a shell command is destructive or touches a protected path."""
from __future__ import annotations

import re
import shlex
from collections.abc import Iterator, Sequence

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
    _p(_GIT + r"checkout\s+(?:--\s+)?\." + _END, "git checkout discarding changes"),
    _p(_GIT + r"restore\s+(?:-\S+\s+)*\." + _END, "git restore discarding changes"),
    _p(r"\bdrop\s+(?:table|database|schema)\b", "SQL drop"),
    _p(r"\btruncate\s+table\b", "SQL truncate"),
    _p(_PS_DELETE + r".*\s-r[a-z]*(?=[\s:]|$)", "recursive PowerShell delete"),
    _p(_CMD_DELETE + r".*\s/s\b", "recursive cmd delete"),
)


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


def _is_read_only(segment: str) -> bool:
    lowered = segment.lower()
    return lowered.startswith(READ_ONLY_PREFIXES) and ">" not in segment


def protected_reason(segment: str, globs: Sequence[str]) -> str | None:
    """Report a non-read-only segment that names a protected path.

    A token also counts when any trailing sub-path of it matches, so
    `/repo/data/x.db` and `../data/x.db` hit the glob `data/*.db`.
    """
    if _is_read_only(segment):
        return None
    for token in _tokens(segment):
        if any(matches_any(globs, c) for c in _candidates(token) if c):
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
    command: str, globs: Sequence[str], allowed_prefixes: Sequence[str]
) -> str | None:
    """Return the reason for the first violating segment, or None."""
    for segment in split_segments(command):
        if _is_exempt(segment, allowed_prefixes):
            continue
        reason = destructive_reason(segment) or protected_reason(segment, globs)
        if reason:
            return reason
    return None
