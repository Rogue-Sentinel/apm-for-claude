"""Read a shell segment as words, the way the worker checks need to: quotes gone, punctuation as a break."""
from __future__ import annotations

import re

# Whitespace and the characters that end a word in a shell: groups, redirects, substitutions, separators.
_BREAK = re.compile(r"[\s()<>{}`;|&$]+")
# A redirection and its target (`2>&1`, `>/dev/null`, `<body.md`) are not arguments.
_REDIRECT = re.compile(r"\d*[<>]+&?[^\s()<>{}`;|&$]*")


def spellings(segment: str) -> tuple[str, str]:
    """The segment without quotes, with `\\` read as a path separator and then as an escape."""
    bare = segment.replace('"', "").replace("'", "")
    return bare.replace("\\", "/"), bare.replace("\\", "")


def shell_words(text: str) -> list[str]:
    """Split on whitespace and shell punctuation, so `(gh pr ready)>x` has the words gh, pr and ready.

    Redirections are dropped."""
    return [word for word in _BREAK.split(_REDIRECT.sub(" ", text)) if word]
