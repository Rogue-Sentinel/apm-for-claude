"""Read a shell command the way the outside-write check needs: its segments, the words each writes, and `cd`.

`command_segments` cuts a command at `&&`, `||`, `;`, `|`, a newline and a lone `&`, only where these stand outside
quotes and escapes, so a `|` inside `sed 's|a|b|'` or a `;` inside a string cuts nothing. `write_targets` names the
words a segment writes (its redirects, then what the program writes), as written: the caller resolves them.
`cd_target` names where a `cd` goes. A segment whose double quote never closes under bash's escapes is read again
with `\\` as a plain character, as PowerShell reads it, so `Copy-Item a "C:\\x\\"; Remove-Item b` is two segments and
`C:/x/` is a target of the first.

Known limits (inputs built to evade, or writes this check does not name): writes a program makes itself (`python -c`
and scripts, `node -e`, `perl -i`, `cmake -B`, `curl -o`, `wget -O`, `tar -C`, `unzip -d`, `dd of=`, `install`, `ln`,
`rsync`, `robocopy`, `xcopy`, `git clone <dir>`, `git worktree add <dir>`, `git format-patch -o`, .NET calls such as
`[IO.File]::WriteAllText`); wrappers beyond `sudo`, `env`, `command`, `nohup` and `time` (`xargs`, `find -exec`,
`timeout`); a command string another shell runs (`bash -c '...'`), `$(...)` and `eval`; `popd`, `cd -` and a
subshell's `cd` (which this reading keeps past the `)`, failing closed); PowerShell parameter abbreviations
(`-Dest`), arrays (`-Path a,b`), `Join-Path` expressions and `''` quoting; a `\\;` before a PowerShell command
(read as bash's escaped `;`, so no cut); a positional PowerShell value read as a target (failing closed).
"""
from __future__ import annotations

import re
from collections.abc import Callable

from .guard_commands import join_continuations
from .guard_redirects import split_redirects
from .guard_words import path_words

# Pieces that hide an operator: a quoted string, a quote never closed (`open`), an escaped character, and the
# redirect operators that hold a `&` or `|` (`2>&1`, `&>f`, `>|f`). What is left of `cut` is an operator.
_PIECES = r"""(?P<string>{double}|'[^']*')|(?P<open>["'])|\\.|[<>]&|&>|>\||(?P<cut>&&|\|\||;|\n|&|\|)"""
_BASH = re.compile(_PIECES.format(double=r'"(?:\\.|[^"\\])*"'), re.DOTALL)
_POWERSHELL = re.compile(_PIECES.format(double=r'"[^"]*"'), re.DOTALL)

_ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
_WRAPPERS = frozenset({"sudo", "env", "command", "nohup", "time"})
_EVERY_WORD = frozenset(
    "tee touch mkdir rm rmdir unlink set-content add-content ac out-file tee-object new-item ni md "
    "remove-item ri del erase rd".split()
)
_DESTINATION = frozenset("cp mv copy-item cpi copy move-item mi move".split())
_VALUE_OPTIONS = frozenset("-value -encoding -itemtype -type -inputobject -width -stream -delimiter -name".split())
_DESTINATION_OPTION = re.compile(r"(?:-t|--target-directory|(?i:-destination))(?:[=:](?P<value>.*))?", re.DOTALL)
_CD = frozenset("cd chdir pushd set-location sl push-location".split())
_SED_IN_PLACE = re.compile(r"-i.*|-[A-Za-z]*i[A-Za-z]*|--in-place(=.*)?")
_SED_SCRIPT_VALUE = re.compile(r"-[A-Za-z]*[ef]|--expression|--file")
_SED_SCRIPT_GIVEN = re.compile(r"--(?:expression|file)=")
_GIT_READS = frozenset(
    "status log diff show blame rev-parse ls-files ls-tree cat-file describe grep shortlog reflog rev-list "
    "merge-base for-each-ref show-ref name-rev help version".split()
)
_GIT_LISTS = frozenset("branch remote tag config worktree stash".split())


def _cuts(text: str, pattern: re.Pattern[str]) -> tuple[list[tuple[int, int]], bool]:
    spans: list[tuple[int, int]] = []
    for found in pattern.finditer(text):
        if found["open"]:
            return spans, True
        if found["cut"]:
            spans.append(found.span())
    return spans, False


def command_segments(text: str) -> list[str]:
    """`text` with continued lines joined, cut at the operators that stand outside quotes and escapes.

    Pieces are stripped and empty pieces dropped. A quote left open ends the cutting under bash's reading; the
    text is then cut again with `\\` plain inside double quotes, which closes `"C:\\x\\"`."""
    joined = join_continuations(text)
    spans, unclosed = _cuts(joined, _BASH)
    if unclosed:
        spans, _ = _cuts(joined, _POWERSHELL)
    starts = [0] + [end for _, end in spans]
    stops = [start for start, _ in spans] + [len(joined)]
    return [piece for piece in (joined[a:b].strip() for a, b in zip(starts, stops)) if piece]


def _unwrapped(words: list[str]) -> list[str]:
    """The words without the `(` or `{` that opens a group and the `)` that closes one."""
    words = list(words)
    while words and not words[0].lstrip("({"):
        words.pop(0)
    while words and not words[-1].rstrip(")"):
        words.pop()
    if words:
        words[0], words[-1] = words[0].lstrip("({"), words[-1].rstrip(")")
    return words


def _program(words: list[str]) -> tuple[str, list[str]]:
    """The program's name (basename, lowercase, no `.exe`) and its arguments, past assignments and wrappers."""
    words = _unwrapped(words)
    wrapped = False
    while words and (_ASSIGNMENT.match(words[0]) or words[0].lower() in _WRAPPERS or (wrapped and words[0][:1] == "-")):
        wrapped = wrapped or words[0].lower() in _WRAPPERS
        words = words[1:]
    if not words:
        return "", []
    name = words[0].rsplit("/", 1)[-1].lower()
    return name.removesuffix(".exe"), words[1:]


def _non_options(args: list[str]) -> list[str]:
    return [word for word in args if not word.startswith("-")]


def _every_word(args: list[str]) -> list[str]:
    found, skip = [], False
    for word in args:
        if skip:
            skip = False
        elif word.lower() in _VALUE_OPTIONS:
            skip = True
        elif not word.startswith("-"):
            found.append(word)
    return found


def _destination_option(args: list[str]) -> str | None:
    for index, word in enumerate(args):
        option = _DESTINATION_OPTION.fullmatch(word)
        if option and option["value"] is not None:
            return option["value"]
        if option:
            return args[index + 1] if index + 1 < len(args) else None
    return None


def _destination(args: list[str]) -> list[str]:
    option = _destination_option(args)
    if option is not None:
        return [option]
    words = _non_options(args)
    return words[-1:] if len(words) >= 2 else []


def _sed_files(args: list[str]) -> list[str]:
    if not any(_SED_IN_PLACE.fullmatch(word) for word in args):
        return []
    words, given, skip = [], False, False
    for word in args:
        if skip:
            skip = False
        elif _SED_SCRIPT_VALUE.fullmatch(word):
            given, skip = True, True
        elif _SED_SCRIPT_GIVEN.match(word):
            given = True
        elif not word.startswith("-"):
            words.append(word)
    return words if given else words[1:]


def _git_options(args: list[str]) -> tuple[list[str], str | None, list[str]]:
    """The -C values, the subcommand, and the words after it."""
    directories, index = [], 0
    while index < len(args) and args[index].startswith("-"):
        if args[index] == "-C" and index + 1 < len(args):
            directories.append(args[index + 1])
        index += 2 if args[index] in ("-C", "-c") else 1
    rest = args[index:]
    return directories, (rest[0] if rest else None), rest[1:]


def _git(args: list[str]) -> list[str]:
    directories, sub, after = _git_options(args)
    if sub is None or sub in _GIT_READS:
        return []
    if sub in _GIT_LISTS and (not _non_options(after) or _non_options(after)[0] in ("list", "show")):
        return []
    return directories or ["."]


_FAMILIES: dict[str, Callable[[list[str]], list[str]]] = {
    **dict.fromkeys(_EVERY_WORD, _every_word),
    **dict.fromkeys(_DESTINATION, _destination),
    "sed": _sed_files,
    "git": _git,
}


def write_targets(segment: str) -> list[str]:
    """The words one segment writes, as written: its redirect targets, then its program's targets.

    Redirect targets are returned as they stand, devices included (`is_device` decides); the program is read with
    `path_words`, so quotes are gone and `\\` is a separator or an escape."""
    rest, redirects = split_redirects(segment)
    name, args = _program(path_words(rest))
    return redirects + _FAMILIES.get(name, lambda _: [])(args)


def cd_target(segment: str) -> str | None:
    """Where a `cd` (`chdir`, `pushd`, `Set-Location` and their aliases) goes: its first non-option word, `~` when
    it has none, None for `cd -` and for any other program."""
    rest, _ = split_redirects(segment)
    name, args = _program(path_words(rest))
    if name not in _CD or args[:1] == ["-"]:
        return None
    return next(iter(_non_options(args)), "~")
