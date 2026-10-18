"""Mask the text of message arguments: it is data, not a command, so the guard must not read it as one."""
from __future__ import annotations

import re

_OPTION = r"(?<![\w-])(?:-a?m|--(?:message|title|body|reason|evidence|text|answer))(?:=|\s+)"
_QUOTED = r""""(?:\\.|[^"\\])*"|'[^']*'"""
# A quoted string that follows no data option, or an escaped character, is consumed whole, so a
# data option written inside a string of code (`bash -c '... -m "x; rm -rf y"'`) is never read.
_ARGUMENT = re.compile(r"(?P<option>" + _OPTION + r")(?P<value>" + _QUOTED + r")|\\.|" + _QUOTED, re.DOTALL)
_HEREDOC = re.compile(
    r"""(?P<head>^[^\n]*\bgit\b[^\n]*\bcommit\b[^\n]*\s-F\s+-(?=\s)[^\n]*?<<-?\s*(?P<quote>['"]?)(?P<tag>\w+)(?P=quote)[^\n]*\n)"""
    r"(?P<body>.*?)(?P<end>^[ \t]*(?P=tag)[ \t]*$)",
    re.DOTALL | re.MULTILINE,
)


def _expands(text: str) -> bool:
    return "$(" in text or "`" in text


def _mask_argument(found: re.Match[str]) -> str:
    value = found.group("value")
    if value is None or (value[0] == '"' and _expands(value)):
        return found.group(0)
    return found.group("option") + value[0] * 2


def _mask_heredoc(found: re.Match[str]) -> str:
    if not found.group("quote") and _expands(found.group("body")):
        return found.group(0)
    return found.group("head") + found.group("end")


def mask_data(command: str) -> str:
    """Empty the value of each message argument and the heredoc body of `git commit -F -`.

    A value that the shell would expand (`$(...)` or backticks outside single quotes) is code and stays.
    """
    return _ARGUMENT.sub(_mask_argument, _HEREDOC.sub(_mask_heredoc, command))
