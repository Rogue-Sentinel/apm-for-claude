"""Unit tests for `space_redirects`: it sets apart the redirects bash reads outside quotes."""
from __future__ import annotations

import pytest

from apm.guard_redirects import space_redirects


@pytest.mark.parametrize(
    ("text", "spaced"),
    [
        ("cat>docs/x.md", "cat > docs/x.md"),
        ("x 2>>log", "x 2 >> log"),
        ("x&>log", "x &> log"),
        ("x 2>&1", "x 2 >& 1"),
        ('echo "x">log', 'echo "x" > log'),
        ("cat <<'EOF'>log", "cat  << 'EOF' > log"),
        ("x<in", "x < in"),
    ],
)
def test_an_unquoted_redirect_is_set_apart(text: str, spaced: str) -> None:
    assert space_redirects(text) == spaced


@pytest.mark.parametrize(
    "text",
    ['echo "a>b"', "echo 'a>b'", "git log --format='%h>%s'", r"echo a\>b", r'echo "say \"x>y\""'],
)
def test_a_redirect_sign_inside_quotes_or_escaped_is_left_alone(text: str) -> None:
    assert space_redirects(text) == text


def test_an_unterminated_quote_does_not_hide_a_redirect() -> None:
    assert space_redirects('echo "x>y') == 'echo "x > y'
