"""Language table and the definition of a line of logic.

A line of logic is a line that still holds code once comments, string contents and preprocessor
lines are removed, and that is not made only of brackets, semicolons and commas.
"""
from __future__ import annotations

import os
import string
from dataclasses import dataclass
from typing import Literal

from apm.metrics_model import FileMetric

_BRACKETS = "{}()[];,"
_Hit = tuple[str, int] | None


@dataclass(frozen=True)
class Language:
    name: str
    family: Literal["brace", "python", "plain"]
    line_comments: tuple[str, ...]
    block_comments: tuple[tuple[str, str], ...]
    quotes: tuple[str, ...]
    preprocessor: bool = False


_PLAIN_QUOTES = ('"', "'")
_TRIPLE_QUOTES = ('"""', '"', "'")


def _brace(name: str, quotes=_PLAIN_QUOTES, line=("//",), preprocessor=False) -> Language:
    return Language(name, "brace", line, (("/*", "*/"),), quotes, preprocessor)


def _plain(name: str, line=("#",), block=()) -> Language:
    return Language(name, "plain", line, block, _PLAIN_QUOTES)


_PYTHON = Language("Python", "python", ("#",), (), ('"""', "'''", '"', "'"))
_JS_QUOTES = ('"', "'", "`")
_LANGUAGE_EXTENSIONS: tuple[tuple[Language, str], ...] = (
    (_brace("C", preprocessor=True), "c h"),
    (_brace("C++", preprocessor=True), "cc cpp cxx hpp hh"),
    (_brace("C#", _TRIPLE_QUOTES, preprocessor=True), "cs"),
    (_brace("Objective-C", preprocessor=True), "m"),
    (_brace("Java", _TRIPLE_QUOTES), "java"),
    (_brace("JavaScript", _JS_QUOTES), "js jsx mjs cjs"),
    (_brace("TypeScript", _JS_QUOTES), "ts tsx"),
    (_brace("Go", _JS_QUOTES), "go"),
    (_brace("Rust"), "rs"),
    (_brace("Swift", _TRIPLE_QUOTES), "swift"),
    (_brace("Kotlin", _TRIPLE_QUOTES), "kt kts"),
    (_brace("Scala", _TRIPLE_QUOTES), "scala"),
    (_brace("PHP", line=("//", "#")), "php"),
    (_brace("Dart", ('"""', "'''", '"', "'")), "dart"),
    (_PYTHON, "py"),
    (_plain("Shell"), "sh bash"),
    (_plain("PowerShell", block=(("<#", "#>"),)), "ps1"),
    (_plain("Ruby"), "rb"),
    (_plain("Lua", ("--",), (("--[[", "]]"),)), "lua"),
    (_plain("SQL", ("--",), (("/*", "*/"),)), "sql"),
    (_plain("Perl"), "pl"),
    (_plain("R"), "r"),
)
_BY_EXTENSION = {
    f".{ext}": language for language, exts in _LANGUAGE_EXTENSIONS for ext in exts.split()
}


def language_for(path: str) -> Language | None:
    return _BY_EXTENSION.get(os.path.splitext(path)[1].lower())


def is_logic_line(line: str) -> bool:
    return bool(line.strip(_BRACKETS + string.whitespace))


def count_logic(stripped: str) -> int:
    return sum(is_logic_line(line) for line in stripped.splitlines())


def measure_plain(path: str, text: str, language: Language) -> FileMetric:
    return FileMetric(path, language.name, count_logic(strip_code(text, language)))


def strip_code(text: str, language: Language) -> str:
    """Remove comments, literal contents and preprocessor lines; every newline survives."""
    text = text.replace("\r\n", "\n")
    out: list[str] = []
    i = 0
    while i < len(text):
        piece, i = _next_piece(text, i, language)
        out.append(piece)
    return "".join(out)


def _next_piece(text: str, i: int, language: Language) -> tuple[str, int]:
    for step in (_preprocessor, _block_comment, _line_comment, _literal):
        hit = step(text, i, language)
        if hit:
            return hit
    return text[i], i + 1


def _at_line_start(text: str, i: int) -> bool:
    start = text.rfind("\n", 0, i) + 1
    return not text[start:i].strip()


def _preprocessor(text: str, i: int, language: Language) -> _Hit:
    if not (language.preprocessor and text[i] == "#" and _at_line_start(text, i)):
        return None
    end = i
    while end < len(text) and text[end] != "\n":
        end += 2 if text[end] == "\\" else 1
    end = min(end, len(text))
    return "\n" * text.count("\n", i, end), end


def _line_comment(text: str, i: int, language: Language) -> _Hit:
    if not any(text.startswith(marker, i) for marker in language.line_comments):
        return None
    end = text.find("\n", i)
    return "", len(text) if end < 0 else end


def _block_comment(text: str, i: int, language: Language) -> _Hit:
    for opener, closer in language.block_comments:
        if text.startswith(opener, i):
            end = text.find(closer, i + len(opener))
            end = len(text) if end < 0 else end + len(closer)
            return " " + "\n" * text.count("\n", i, end), end
    return None


def _literal(text: str, i: int, language: Language) -> _Hit:
    for quote in language.quotes:
        if text.startswith(quote, i):
            end = _literal_end(text, i, quote)
            if end is None:
                return quote, i + len(quote)
            return quote + quote + "\n" * text.count("\n", i, end), end
    return None


def _literal_end(text: str, i: int, quote: str) -> int | None:
    """Index just past the closing quote, or None when the literal never closes."""
    multiline = len(quote) > 1 or quote == "`"
    j = i + len(quote)
    while j < len(text):
        if text[j] == "\\":
            j += 2
        elif text.startswith(quote, j):
            return j + len(quote)
        elif text[j] == "\n" and not multiline:
            return None
        else:
            j += 1
    return None
