"""Mask the text of message arguments: it is data, not a command, so the guard must not read it as one."""
from __future__ import annotations

import re

_OPTION = r"(?<![\w-])(?:-a?m|--(?:message|title|body|reason|evidence|text|answer))(?:=|\s+)"
_QUOTED = r""""(?:\\.|[^"\\])*"|'[^']*'"""
# A quoted string that follows no data option, or an escaped character, is consumed whole, so a
# data option written inside a string of code (`bash -c '... -m "x; rm -rf y"'`) is never read.
_ARGUMENT = re.compile(r"(?P<option>" + _OPTION + r")(?P<value>" + _QUOTED + r")|\\.|" + _QUOTED, re.DOTALL)
# A run of quoted strings, escapes and characters that end no command, or any one other character: the
# pieces cover the whole command, and a piece starts after each unquoted `;`, `&`, `|` or newline.
_SEGMENT = re.compile(r"(?:" + _QUOTED + r"""|\\.|[^"'\\;&|\r\n])+|.""", re.DOTALL)
# A short `-m`/`-am` is a message only when the program is git: `python -m apm_cli` names code to run.
_GIT = re.compile(r"""\s*["']?(?:\S*[/\\])?git(?:\.exe)?["']?\s""", re.IGNORECASE)
_HEREDOC = re.compile(
    r"""(?P<head>^[^\n]*\bgit\b[^\n]*\bcommit\b[^\n]*\s-F\s+-(?=\s)[^\n]*?<<-?\s*(?P<quote>['"]?)(?P<tag>\w+)(?P=quote)[^\n]*\n)"""
    r"(?P<body>.*?)(?P<end>^[ \t]*(?P=tag)[ \t]*$)",
    re.DOTALL | re.MULTILINE,
)
# A shell given a command string (`bash -c`, `pwsh -Command`, `cmd /c`): it takes `-m` and the like as its
# own options and still runs the string, so nothing in such a command is masked. A shell, by path, with
# `.exe`, in any case, followed later by an option holding a `c` (`-c`, `-lc`, `-Command`), or `cmd` by `/c`,
# `/k` or `/r` (`//c` from Git Bash). It is looked for in the whole command, quotes removed, so it fails closed.
_SHELL_STRING = re.compile(
    r"(?<![\w.-])(?:\S*[/\\])?(?:(?:bash|sh|zsh|dash|ksh|mksh|pwsh|powershell)(?:\.exe)?\s(?:.*?\s)?-[\w-]*c"
    r"|cmd(?:\.exe)?\s(?:.*?\s)?//?[ckr]\b)",
    re.IGNORECASE | re.DOTALL,
)


def _expands(text: str) -> bool:
    return "$(" in text or "`" in text


def _mask_argument(found: re.Match[str], is_git: bool) -> str:
    value = found.group("value")
    if value is None or (value[0] == '"' and _expands(value)):
        return found.group(0)
    if not (is_git or found.group("option").startswith("--")):
        return found.group(0)
    return found.group("option") + value[0] * 2


def _mask_segment(segment: str) -> str:
    is_git = bool(_GIT.match(segment))
    return _ARGUMENT.sub(lambda found: _mask_argument(found, is_git), segment)


def _mask_heredoc(found: re.Match[str]) -> str:
    if not found.group("quote") and _expands(found.group("body")):
        return found.group(0)
    return found.group("head") + found.group("end")


def mask_data(command: str) -> str:
    """Empty the value of each message argument and the heredoc body of `git commit -F -`.

    A long option (`--message`, `--title` and the like) is a message in any command; a short `-m`/`-am` only
    in a command whose program is git. A value that the shell would expand (`$(...)` or backticks outside
    single quotes) is code and stays, and so does every value in a command that runs a shell's command string.
    """
    if _SHELL_STRING.search(command.replace('"', "").replace("'", "")):
        return command
    pieces = _SEGMENT.finditer(_HEREDOC.sub(_mask_heredoc, command))
    return "".join(_mask_segment(piece.group(0)) for piece in pieces)
