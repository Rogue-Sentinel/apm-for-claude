"""path_words in PowerShell mode: a `\\` before a blank ends a folder path instead of escaping the blank."""
from __future__ import annotations

import pytest

from apm.guard_words import path_words

TEXT = r"Copy-Item -Destination C:\out\ -Path a"


def test_a_backslash_before_a_blank_is_a_separator_for_powershell() -> None:
    assert path_words(TEXT, powershell=True) == ["Copy-Item", "-Destination", "C:/out/", "-Path", "a"]


def test_the_bash_reading_of_a_backslash_before_a_blank_is_unchanged() -> None:
    assert path_words(TEXT) == ["Copy-Item", "-Destination", "C:/out -Path", "a"]


@pytest.mark.parametrize("text", [
    r"Copy-Item a C:\Users\me\b",
    r'echo "C:\a b\c"',
    r"Add-Content $HOME\.claude\x a",
    'echo "a',
])
def test_every_other_reading_is_the_same_in_powershell(text: str) -> None:
    assert path_words(text, powershell=True) == path_words(text)


def test_a_trailing_backslash_at_the_end_of_the_text_is_a_separator_for_powershell() -> None:
    assert path_words("Copy-Item a C:\\out\\", powershell=True) == ["Copy-Item", "a", "C:/out/"]
