"""Set apart the redirects bash reads outside quotes, so a redirect target is a word of its own.

`shlex.split` cuts a command at blanks and quotes only, so a redirect written with no blank before it
(`cat>docs/x.md`, `cat <<'EOF'>docs/x.md`, `echo "x">docs/a.md`, `2>docs/a.md`) stays inside one word
and its target is never checked as a path. `space_redirects` puts a blank on each side of every run of
redirect characters that bash reads, so the target becomes a word of its own. A `<` or `>` inside a
quoted string or after a backslash is not a redirect and is left alone.

Known limits, not loosenings: a glued redirect inside a quoted string that another shell runs
(`sh -c 'cat>docs/x.md'`, `"$(cat>docs/x.md)"`) is not set apart; the same text with blanks is seen
through the unquoted reading. PowerShell's quoting and escapes are not read (ADR 0005), so a
PowerShell `\\>` is read as bash's escaped `>`.

`split_redirects` reads the same redirects the other way round: it takes them out of the segment and returns
the words they write, which is the reader that `_is_read_only` (issue #13) can use. Its known limits: a
redirect inside a quoted string that another shell runs (`sh -c 'echo x > /y'`) is not read, a target built
from a variable or a substitution (`> "$DIR/x"`, `> $(f)`) is returned as written or not at all, a
process substitution (`>(cmd)`) names no file, and a redirect target is read the bash way for both tools, so a `\\`
before a blank is an escape there: PowerShell's `> C:\\o\\ y` names `C:/o y`, not the folder `C:/o/`.
"""
from __future__ import annotations

import re

from .guard_words import path_words

_QUOTED = r""""(?:\\.|[^"\\])*"|'[^']*'"""  # a double-quoted string or a single-quoted string
_ESCAPED = r"\\."  # an escaped character
_OPERATOR = r"[&*]?[<>][<>&]*"  # a run of redirect characters, PowerShell's `*>` whole
_PIECE = re.compile(f"{_QUOTED}|{_ESCAPED}|(?P<op>{_OPERATOR})", re.DOTALL)


# A descriptor digit starts a word (`2>x`, not the 2 of `a2>x`); the word after the operator ends at a blank or at
# `<>&|;()` or a backtick, and holds quoted strings and escapes whole. `>|` (override noclobber) is one operator.
_DESCRIPTOR = r"(?:(?<![^\s;|&()`])\d+)?"
_WORD = rf"(?:{_QUOTED}|{_ESCAPED}|[^\s<>&|;()`\\\"']|[\\\"'])*"
_REDIRECT = re.compile(
    rf"{_QUOTED}|{_ESCAPED}|{_DESCRIPTOR}(?P<op>{_OPERATOR}(?:(?<=>)\|)?)[ \t]*(?P<word>{_WORD})", re.DOTALL
)
# The word after `>&` or `<&` names a descriptor (`2>&1`, `2>&-`, `>&2-`) when it is digits, or `-`.
_DESCRIPTOR_WORD = re.compile(r"\d+-?|-")
_DEVICES = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"})
_NULL_WORDS = frozenset({"nul", "nul:", "$null"})


def _writes(operator: str, word: str) -> bool:
    if ">" not in operator or not word:
        return False
    return not (operator.endswith("&") and _DESCRIPTOR_WORD.fullmatch(word))


def split_redirects(segment: str) -> tuple[str, list[str]]:
    """The segment without its redirects, and the files they write.

    Every unquoted, unescaped redirect (its descriptor digits, its operator and its word) becomes a blank. The
    files are the words of the redirects whose operator holds `>`, in order, read with `path_words`; a descriptor
    after `>&` (`1`, `2`, `-`, `2-`) is no file."""
    written: list[str] = []

    def take(found: re.Match[str]) -> str:
        if not found["op"]:
            return found[0]
        if _writes(found["op"], found["word"]):
            written.extend(path_words(found["word"]))
        return " "

    return _REDIRECT.sub(take, segment), written


def is_device(word: str) -> bool:
    """True when a redirect target is a device, not a file: `/dev/null`, `/dev/stdout`, `/dev/stderr`, `/dev/tty`,
    `/dev/fd/<n>`, and, in any case, `nul`, `nul:` and `$null`."""
    return word in _DEVICES or word.lower() in _NULL_WORDS or re.fullmatch(r"/dev/fd/\d+", word) is not None


def _spaced(match: re.Match[str]) -> str:
    return f" {match['op']} " if match["op"] else match[0]


def space_redirects(segment: str) -> str:
    """Return `segment` with a blank before and after each unquoted, unescaped redirect run."""
    return _PIECE.sub(_spaced, segment)
