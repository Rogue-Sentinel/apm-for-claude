"""path_words reads the words of a shell command as paths: quotes gone, `\\` a separator or an escape."""
from __future__ import annotations

import pytest

from apm.guard_words import path_words

CASES = [
    (r"cd /c/My\ Repo/sub", ["cd", "/c/My Repo/sub"]),
    (r"Copy-Item a C:\Users\me\b", ["Copy-Item", "a", "C:/Users/me/b"]),
    (r'echo "C:\a b\c"', ["echo", "C:/a b/c"]),
    (r"Add-Content $HOME\.claude\x a", ["Add-Content", "$HOME/.claude/x", "a"]),
    ('echo "a', ["echo", "a"]),
    (r"Copy-Item a C:\Users\Ömer\b", ["Copy-Item", "a", "C:/Users/Ömer/b"]),
    (r"python x.py > C:\Users\Ömer\proj\out.log", ["python", "x.py", ">", "C:/Users/Ömer/proj/out.log"]),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_shell_words_read_as_paths(text, expected):
    assert path_words(text) == expected


def test_a_trailing_backslash_in_a_quoted_path_leaves_no_quote():
    assert path_words(r'Copy-Item README.md "C:\Users\me\out\"') == ["Copy-Item", "README.md", "C:/Users/me/out/"]


def test_an_unterminated_quote_leaves_every_word_without_quotes():
    words = path_words(r'Set-Content -Path "C:\Users\me\out\a.md" -Value "C:\temp\"')
    assert words == ["Set-Content", "-Path", "C:/Users/me/out/a.md", "-Value", "C:/temp/"]
