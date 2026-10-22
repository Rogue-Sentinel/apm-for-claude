"""path_words reads the words of a shell command as paths: quotes gone, `\\` a separator or an escape."""
from __future__ import annotations

import pytest

from apm.guard_words import path_words

CASES = [
    (r"cd /c/My\ Repo/sub", ["cd", "/c/My Repo/sub"]),
    (r"Copy-Item a C:\Users\me\b", ["Copy-Item", "a", "C:/Users/me/b"]),
    (r'echo "C:\a b\c"', ["echo", "C:/a b/c"]),
    (r"Add-Content $HOME\.claude\x a", ["Add-Content", "$HOME/.claude/x", "a"]),
    ('echo "a', ["echo", '"a']),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_shell_words_read_as_paths(text, expected):
    assert path_words(text) == expected
