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
"""
from __future__ import annotations

import re

_PIECE = re.compile(
    r"""
    "(?:\\.|[^"\\])*"      # a double-quoted string
    |'[^']*'               # a single-quoted string
    |\\.                   # an escaped character
    |(?P<op>&?[<>][<>&]*)  # a run of redirect characters
    """,
    re.DOTALL | re.VERBOSE,
)


def _spaced(match: re.Match[str]) -> str:
    return f" {match['op']} " if match["op"] else match[0]


def space_redirects(segment: str) -> str:
    """Return `segment` with a blank before and after each unquoted, unescaped redirect run."""
    return _PIECE.sub(_spaced, segment)
