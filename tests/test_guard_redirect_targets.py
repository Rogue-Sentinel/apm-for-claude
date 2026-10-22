"""split_redirects reads the files a redirect writes; is_device names the targets that are no file."""
from __future__ import annotations

import pytest

from apm.guard_redirects import is_device, split_redirects

WRITES = [
    ("echo x >> a.md", ["a.md"], ["echo", "x"]),
    ("cat>docs/x.md", ["docs/x.md"], ["cat"]),
    ("python x.py 2>err.log", ["err.log"], ["python", "x.py"]),
    ("python x.py &>out.log", ["out.log"], ["python", "x.py"]),
    ("python x.py *> all.log", ["all.log"], ["python", "x.py"]),
    ("echo x >& out.log", ["out.log"], ["echo", "x"]),
    ("cat < in.txt > out.txt", ["out.txt"], ["cat"]),
    ("cat <<'EOF' > body.md", ["body.md"], ["cat"]),
    (r'cmd > "C:\Users\me\a b.md"', ["C:/Users/me/a b.md"], ["cmd"]),
]


@pytest.mark.parametrize(("segment", "targets", "rest"), WRITES)
def test_the_files_a_redirect_writes(segment, targets, rest):
    left, found = split_redirects(segment)
    assert (found, left.split()) == (targets, rest)


def test_a_redirect_inside_a_substitution_ends_at_the_parenthesis():
    assert split_redirects("x=$(git rev-parse HEAD 2>/dev/null)")[1] == ["/dev/null"]


def test_a_redirect_inside_backticks_ends_at_the_backtick():
    assert split_redirects("x=`git rev-parse HEAD 2>/dev/null`")[1] == ["/dev/null"]


def test_an_escaped_blank_stays_inside_the_target_word():
    assert split_redirects(r"echo x > My\ Repo/a.md")[1] == ["My Repo/a.md"]


def test_a_redirect_with_no_blank_before_a_word_digit_keeps_the_word():
    left, found = split_redirects("echo a2>out.log")
    assert (found, left.split()) == (["out.log"], ["echo", "a2"])


@pytest.mark.parametrize(
    "segment",
    [
        "python x.py 2>&1",
        "echo x >&2",
        "x 2>&-",
        "x <&3",
        'echo "a > b"',
        "grep '>' x",
        r"echo a\>b",
        r"sed -i 's|a|b|;s/\n/ > /' notes.md",
    ],
)
def test_a_descriptor_or_a_quoted_sign_is_no_target(segment):
    assert split_redirects(segment)[1] == []


@pytest.mark.parametrize("word", ["/dev/null", "/dev/stderr", "/dev/fd/2", "NUL", "nul", "$null", "$NULL"])
def test_a_device_is_not_a_file(word):
    assert is_device(word) is True


@pytest.mark.parametrize("word", ["/dev/nullx", "null", "nul.txt", "docs/null", "/dev/sda"])
def test_a_file_that_looks_like_a_device_is_a_file(word):
    assert is_device(word) is False
