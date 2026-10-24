"""Read a shell segment as words, the way the worker checks need to: quotes gone, punctuation as a break."""
from __future__ import annotations

import re
import shlex

# A `\` before one of these is a path separator, as PowerShell and Windows paths use it; any other `\` is bash's escape.
_SEPARATOR = re.compile(r"\\(?=[\w.~-])")
# PowerShell has no backslash escape, so there a `\` before a blank or at the end of the text also ends a folder.
_POWERSHELL_SEPARATOR = re.compile(r"\\(?=[\w.~-]|\s|\Z)")
# Whitespace and the characters that end a word in a shell: groups, redirects, substitutions, separators,
# and the comma that separates the pieces of a brace expansion (`{gh,issue,create}`).
_BREAK = re.compile(r"[\s()<>{}`;|&$,]+")
# A redirection and its target (`2>&1`, `>/dev/null`, `<body.md`) are not arguments.
_REDIRECT = re.compile(r"\d*[<>]+&?[^\s()<>{}`;|&$]*")
# The first brace expansion of a word: the text before it, its pieces, and the rest of the word.
_BRACE = re.compile(r"(?P<head>[^\s{}]*)\{(?P<pieces>[^\s{}]*,[^\s{}]*)\}(?P<tail>\S*)")
# Each round expands the first group of every word; past these caps the text cannot be read.
_BRACE_ROUNDS = 16
_BRACE_LENGTH = 10_000


def _expand_first(found: re.Match[str]) -> str:
    head, tail = found.group("head"), found.group("tail")
    return " ".join(head + piece + tail for piece in found.group("pieces").split(","))


def expand_braces(text: str) -> str | None:
    """Expand brace expansions as the shell would, so `apm no{t,}e 1` reads `apm note noe 1`.

    None when the expansion is too large to read, so a caller can fail closed."""
    for _ in range(_BRACE_ROUNDS):
        text, count = _BRACE.subn(_expand_first, text)
        if not count:
            return text
        if len(text) > _BRACE_LENGTH:
            return None
    return None if _BRACE.search(text) else text


def _bare(segment: str) -> str:
    return segment.replace('"', "").replace("'", "")


def unreadable_braces(segment: str) -> bool:
    """True when the segment's brace expansions are too large to read."""
    return expand_braces(_bare(segment)) is None


def spellings(segment: str) -> tuple[str, str]:
    """The segment without quotes and braces expanded, with `\\` read as a path separator and then as an escape."""
    bare = _bare(segment)
    bare = expand_braces(bare) or bare
    return bare.replace("\\", "/"), bare.replace("\\", "")


def shell_words(text: str) -> list[str]:
    """Split on whitespace and shell punctuation, so `(gh pr ready)>x` has the words gh, pr and ready.

    Redirections are dropped."""
    return [word for word in _BREAK.split(_REDIRECT.sub(" ", text)) if word]


def path_words(text: str, powershell: bool = False) -> list[str]:
    """The shell words of `text` read as paths: quotes removed, a `\\` before a letter, digit, `_`, `.`, `~` or `-`
    a path separator (`C:\\Users\\me`), every other `\\` bash's escape (`My\\ Repo` is one word). With `powershell`,
    a `\\` before a blank or at the end of the text is a separator too (`C:\\vab\\ -Path a` names `C:/vab/`).

    On an unterminated quote every `\\` is a separator, the text is split on blanks and the quote characters are
    removed from each word, so a trailing `\\"` (`"C:\\Users\\me\\vab\\"`) still names its folder. Known limit: a word built
    from a variable or a substitution is returned as written; the caller decides what that means."""
    read = (_POWERSHELL_SEPARATOR if powershell else _SEPARATOR).sub("/", text)
    try:
        return shlex.split(read)
    except ValueError:
        return [word.replace('"', "").replace("'", "") for word in read.replace("\\", "/").split()]
