"""Decide whether a shell command is destructive or touches a protected path."""
from __future__ import annotations

import glob
import itertools
import re
import shlex
from collections.abc import Iterator, Sequence
from pathlib import Path

from .guard_data import mask_data
from .guard_paths import matches_any

READ_ONLY_PREFIXES = (
    "cat ", "head ", "tail ", "less ", "ls", "dir", "stat ", "file ", "wc ", "grep ", "rg ",
    "git log", "git diff", "git show", "git status", "git blame", "sqlite3 -readonly ",
)
_SPLIT = re.compile(r"&&|\|\||;|\||\r?\n|(?<![<>&])&(?![&>])")
# Only an odd run of escapes continues a line: an escaped pair is a literal character, kept as it is.
_BACKSLASH_CONTINUATION = re.compile(r"(?<!\\)((?:\\\\)*)\\\r?\n")
_BACKTICK_CONTINUATION = re.compile(r"(?<!`)((?:``)*)`\r?\n")
_NO_EXEMPT = ("$(", "`", "<(", ">(")
# The options git takes before its subcommand. The alternatives are disjoint (a
# value-taking option never matches the generic one, and a value is either quoted
# or not), so a long run of options cannot backtrack exponentially.
_GIT_OPTION = r"(?:-[cC]|--git-dir|--work-tree|--namespace|--super-prefix|--config-env)"
_GIT_VALUE = r"""(?:"[^"]*"|'[^']*'|(?:\\.|[^\s"'\\])(?:\\.|[^\s\\])*)"""
_GIT = (
    r"""(?<![\w-])git(?:\.exe)?["']?\s+(?:""" + _GIT_OPTION + r"(?:=|\s+)" + _GIT_VALUE + r"\s+"
    r"|(?!" + _GIT_OPTION + r"(?:[=\s]|$))-\S+\s+)*"
)
_END = r"(?=\s|$)"
# xargs deletes only when the command it runs, its first word that is not an option or an option's
# value, is a delete: `xargs grep rm` searches for "rm".
_XARGS = (
    r"(?<![\w-])xargs(?![\w-])(?:\s+(?:-[IEnPdLsa]\s+\S+|--(?:max-args|max-procs|delimiter|arg-file"
    r"|max-chars|max-lines|replace|eof)\s+\S+|-\S*))*\s+"
)
_PS_DELETE = r"(?<![\w-])(?:Remove-Item|ri|rmdir|rd|del|erase)(?![\w-])"
_CMD_DELETE = r"(?<![\w-])(?:rmdir|rd|del|erase)(?![\w-])"


def _p(pattern: str, label: str) -> tuple[re.Pattern[str], str]:
    return re.compile(pattern, re.IGNORECASE), label


DESTRUCTIVE: tuple[tuple[re.Pattern[str], str], ...] = (
    _p(r"(?<![\w-])rm\s+(?:\S+\s+)*?(?:-[a-z]*r[a-z]*|--recursive)" + _END, "recursive rm"),
    _p(_GIT + r"clean(?![\w-])", "git clean"),
    _p(_GIT + r"reset\b.*\s--hard\b", "git reset --hard"),
    _p(_GIT + r"push\b.*(?:\s-[a-z]*f[a-z]*" + _END + r"|\s--force|\s\+\S)", "forced git push"),
    _p(_GIT + r"push\b.*(?:\s-[a-z]*d[a-z]*" + _END + r"|\s--delete|\s--mirror|\s:\S)", "git push deleting refs"),
    _p(_GIT + r"branch\b.*\s-[a-z]*(?-i:D)[a-z]*" + _END, "git branch -D"),
    _p(
        _GIT + r"branch\b(?=.*\s(?:--delete|-[a-z]*d[a-z]*)" + _END + r").*\s(?:--force|-[a-z]*f[a-z]*)" + _END,
        "git branch force delete",
    ),
    _p(_GIT + r"worktree\s+remove\b", "git worktree remove"),
    _p(_GIT + r"checkout\s+(?:\S+\s+)*\." + _END, "git checkout discarding changes"),
    _p(_GIT + r"restore\s+(?:\S+\s+)*\." + _END, "git restore discarding changes"),
    _p(_GIT + r"stash\s+clear\b", "git stash clear"),
    _p(r"(?<![\w-])find\b.*\s-delete\b", "find -delete"),
    _p(r"(?<![\w-])find\b.*\s-exec(?:dir)?\s+(?:\S*/)?rm\b", "find -exec rm"),
    _p(r"\bdrop\s+(?:table|database|schema)\b", "SQL drop"),
    _p(r"\btruncate\s+table\b", "SQL truncate"),
    _p(r"(?<![\w-])dropdb(?![\w-])", "dropdb"),
    _p(_XARGS + r"(?:\S*/)?(?:rm|del|erase|Remove-Item)(?![\w-])", "xargs delete"),
    _p(_PS_DELETE + r".*\s-r[a-z]*(?=[\s:]|$)", "recursive PowerShell delete"),
    _p(_CMD_DELETE + r".*\s//?s\b", "recursive cmd delete"),
)


# Checked on the whole command, because a pipe separates the recursive listing
# from the delete: `Get-ChildItem x -Recurse | Remove-Item`.
_PIPED_DELETE = re.compile(
    r"\s-r(?:ecurse)?(?=[\s:|]|$).*\|\s*" + _PS_DELETE + r"|\s-recurse\b.*" + _PS_DELETE,
    re.IGNORECASE,
)
_GLOB_CHARS = frozenset("*?[")
_GLOB_LIMIT = 2000


def split_segments(command: str) -> list[str]:
    """Split a command line on `&&`, `||`, `;`, `|`, `&` and newlines, after joining continued lines.

    An odd run of backslashes before a newline joins the lines with a space. An odd run of PowerShell
    backticks joins them too but its last backtick stays, so a bash backtick substitution that spans lines
    still blocks an exemption. An even run is literal, so the newline still ends the command.
    """
    joined = _BACKTICK_CONTINUATION.sub(r"\1` ", _BACKSLASH_CONTINUATION.sub(r"\1 ", command))
    parts = (part.strip() for part in _SPLIT.split(joined))
    return [part for part in parts if part]


def _unquoted(segment: str) -> str:
    return segment.replace('"', "").replace("'", "")


def destructive_reason(segment: str) -> str | None:
    """Match the raw segment, then the segment with its quotes removed (`rm "-rf" x`)."""
    unquoted = _unquoted(segment)
    for pattern, label in DESTRUCTIVE:
        if pattern.search(segment) or pattern.search(unquoted):
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


def _glob_matches(token: str, cwd: Path) -> list[str]:
    """Expand a shell glob lazily; one match past the cap marks an over-large result."""
    found = glob.iglob(token, root_dir=cwd, recursive=True)
    return list(itertools.islice(found, _GLOB_LIMIT + 1))


def _relative_hits(matches: list[str], cwd: Path, root: Path) -> Iterator[str]:
    """Yield the root-relative POSIX path of each match."""
    for match in matches:
        try:
            yield (cwd / match).resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            continue


def _token_hits(token: str, globs: Sequence[str], cwd: Path | None, root: Path | None) -> bool:
    if any(matches_any(globs, c) for c in _candidates(token) if c):
        return True
    if cwd is None or not _GLOB_CHARS & set(token):
        return False
    matches = _glob_matches(token, cwd)
    if len(matches) > _GLOB_LIMIT:
        return True  # cannot prove a huge expansion is safe, so fail closed
    return any(matches_any(globs, hit) for hit in _relative_hits(matches, cwd, root or cwd))


def _is_read_only(segment: str) -> bool:
    lowered = segment.lower()
    return lowered.startswith(READ_ONLY_PREFIXES) and ">" not in segment


def all_read_only(command: str) -> bool:
    """True when every segment of `command` only reads."""
    return all(_is_read_only(segment) for segment in split_segments(command))


def protected_reason(
    segment: str, globs: Sequence[str], cwd: Path | None = None, root: Path | None = None
) -> str | None:
    """Report a non-read-only segment that names a protected path.

    A token also counts when any trailing sub-path of it matches, so
    `/repo/data/x.db` and `../data/x.db` hit the glob `data/*.db`. With `cwd`,
    a token holding `*`, `?` or `[` is expanded as the shell would and each
    match, taken relative to `root`, is tested too. The segment is read as written and with its quotes
    removed, so a path inside a shell's command string (`sh -c 'cp x data/x.db'`) is seen.
    """
    if _is_read_only(segment):
        return None
    for token in (*_tokens(segment), *_tokens(_unquoted(segment))):
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
    """Return the reason for the first violating segment, or None. Message arguments are data."""
    command = mask_data(command)
    if _PIPED_DELETE.search(command):
        return f"destructive command (piped recursive delete): {command}"
    segments = (g for g in split_segments(command) if not _is_exempt(g, allowed_prefixes))
    reasons = (destructive_reason(g) or protected_reason(g, globs, cwd, root) for g in segments)
    return next((reason for reason in reasons if reason), None)
