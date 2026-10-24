"""Read a shell command the way the outside-write check needs: its segments, the words each writes, and `cd`.

`command_segments` cuts a command at `&&`, `||`, `;`, `|`, a newline and a lone `&`, only where these stand outside
quotes and escapes, so a `|` inside `sed 's|a|b|'` or a `;` inside a string cuts nothing. `command_readings`
gives that bash reading and, when the text holds `\\"`, a second, PowerShell reading, because the two disagree on
`"C:\\x\\"`: the whole text is cut again, not one segment, and the caller judges each reading. `write_targets` names
the words a segment writes (its redirects, then what the program writes), as written: the caller resolves them.
`cd_target` names where a `cd` goes. Comments are stripped before cutting, in both readings: a `#` that starts a
word (at the start, or after a blank, `;`, `&`, `|` or `(`) runs to the end of its line, and PowerShell's
`<# ... #>` is a comment too; a `#` inside a word (`http://x#frag`, `${#a}`, `$#`) or in quotes is not. The program
is found past `NAME=value`, a PowerShell `$x =`, the wrappers `sudo`, `env`, `command`, `nohup`, `time` and the
clause words `if then else elif do while until !`.

Known limits (inputs built to evade, or writes this check does not name): writes a program makes itself (`python -c`
and scripts, `node -e`, `perl -i`, `cmake -B`, `curl -o`, `wget -O`, `tar -C`, `unzip -d`, `dd of=`, `install`, `ln`,
`rsync`, `robocopy`, `xcopy`, `git clone <dir>`, `git worktree add <dir>`, `git format-patch -o`, .NET calls such as
`[IO.File]::WriteAllText`); PowerShell script blocks and cmdlets this module does not read (`ForEach-Object { ... }`,
`Rename-Item`, `Clear-Content`, `Expand-Archive -DestinationPath`, `Invoke-WebRequest -OutFile`); wrappers beyond the
list above (`xargs`, `find -exec`, `timeout`) and the values of wrapper options (`sudo -u bob`, `env -u VAR`); a
command string another shell runs (`bash -c '...'`), `$(...)` and `eval`; `git --git-dir`, `git --work-tree` and
`git config --global`; `popd`, `cd -` and a subshell's `cd` (which this reading keeps past the `)`, failing closed);
PowerShell parameter abbreviations (`-Dest`), arrays (`-Path a,b`), `Join-Path` expressions and `''` quoting; a `\\;`
before a PowerShell command (read as bash's escaped `;`, so no cut); a stray quote outside a comment, read as a plain
character (the text is still cut, but a second stray quote can pair with it and hide the cuts between them); a
positional PowerShell value read as a target (failing closed), except the value of an option this module knows takes
one (`-ErrorAction Stop`, `-Filter *.dll`: see `_POWERSHELL_VALUE_OPTIONS`; for a PowerShell command only, since in
bash `-pv` is `-p -v`), which is skipped, so an option it does not know (`-Dest`, an abbreviation) can still hide the
destination; `mv` and `Move-Item`, which count only the destination, so removing a source in another checkout is not
seen; a `#` right after an escaped blank (`a\\ #b`), read as a comment; PowerShell backtick escapes, which are not
read (only a backtick at the end of a line joins lines); a redirect target, which `split_redirects` reads the bash
way for both tools, so in PowerShell's `> C:\\o\\ y` the `\\` before the blank is an escape and the target is
`C:/o y`, not `C:/o/` (a program's words, by contrast, take the `powershell` reading).
"""
from __future__ import annotations

import re
from collections.abc import Callable

from .guard_commands import join_continuations
from .guard_redirects import split_redirects
from .guard_words import path_words

# Pieces that hide an operator: a quoted string, a quote never closed (`open`), an escaped character, and the
# redirect operators that hold a `&` or `|` (`2>&1`, `&>f`, `>|f`). What is left of `cut` is an operator.
_PIECES = (
    r"""(?P<comment><#.*?#>|(?<![^\s;&|(])\#[^\n]*)|(?P<string>{double}|'[^']*')|(?P<open>["'])"""
    r"""|\\.|[<>]&|&>|>\||(?P<cut>&&|\|\||;|\n|&|\|)"""
)
_BASH = re.compile(_PIECES.format(double=r'"(?:\\.|[^"\\])*"'), re.DOTALL)
_POWERSHELL = re.compile(_PIECES.format(double=r'"[^"]*"'), re.DOTALL)
# An odd run of backticks before a newline, as `guard_commands.join_continuations` reads it; the last backtick stays.
_BACKTICK_CONTINUATION = re.compile(r"(?<!`)((?:``)*)`\r?\n")
_LINE_END_BACKSLASH = re.compile(r"\\(?=\r?\n)")

_ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
_VARIABLE = re.compile(r"\$[\w:]+=?")
_WRAPPERS = frozenset({"sudo", "env", "command", "nohup", "time"})
# Words that start a command's clause; the program follows them, and their own options (there are none) are not
# skipped.
_RESERVED = frozenset({"if", "then", "else", "elif", "do", "while", "until", "!"})
_EVERY_WORD = frozenset(
    "tee touch mkdir rm rmdir unlink set-content add-content ac out-file tee-object new-item ni md "
    "remove-item ri del erase rd".split()
)
_DESTINATION = frozenset("cp mv copy-item cpi copy move-item mi move".split())
_VALUE_OPTIONS = frozenset("-value -encoding -itemtype -type -inputobject -width -stream -delimiter -name".split())
# PowerShell options whose next word is their value, not a path, dropped only for a PowerShell command: in bash
# `-pv` is `-p -v` and `-iv` is `-i -v`, so there they hide nothing. The common parameters, then the cmdlets' own.
_POWERSHELL_VALUE_OPTIONS = frozenset(
    "-erroraction -ea -warningaction -wa -informationaction -infa -errorvariable -ev -warningvariable -wv "
    "-informationvariable -iv -outvariable -ov -outbuffer -ob -pipelinevariable -pv "
    "-filter -include -exclude -credential -tosession -fromsession".split()
)
_DESTINATION_OPTION = re.compile(r"(?:-t|--target-directory|(?i:-destination))(?:[=:](?P<value>.*))?", re.DOTALL)
_CD = frozenset("cd chdir pushd set-location sl push-location".split())
_SED_IN_PLACE = re.compile(r"-i.*|-[A-Za-z]*i[A-Za-z]*|--in-place(=.*)?")
_SED_SCRIPT_VALUE = re.compile(r"-[A-Za-z]*[ef]|--expression|--file")
_SED_SCRIPT_GIVEN = re.compile(r"--(?:expression|file)=")
_GIT_READS = frozenset(
    "status log diff show blame rev-parse ls-files ls-tree cat-file describe grep shortlog reflog rev-list "
    "merge-base for-each-ref show-ref name-rev help version".split()
)
_GIT_LISTS = frozenset("branch remote tag config worktree".split())
_GIT_LISTING = frozenset({"list", "show"})


def _pieces(joined: str, pattern: re.Pattern[str]) -> list[str]:
    joined = pattern.sub(lambda found: " " if found["comment"] else found[0], joined)
    spans = [found.span() for found in pattern.finditer(joined) if found["cut"]]
    starts = [0] + [end for _, end in spans]
    stops = [start for start, _ in spans] + [len(joined)]
    return [piece for piece in (joined[a:b].strip() for a, b in zip(starts, stops)) if piece]


def command_segments(text: str) -> list[str]:
    """The bash reading: `text` with continued lines joined, cut at the operators outside quotes and escapes.

    Pieces are stripped and empty pieces dropped. A quote that never closes is read as a plain character and the
    cutting goes on, so a stray apostrophe in a comment stops nothing."""
    return _pieces(join_continuations(text), _BASH)


def _joined(text: str, powershell: bool) -> str:
    """`text` with its continued lines joined. PowerShell has no `\\` escape and no `\\` continuation: there a `\\`
    at the end of a line is a path's last separator (`Copy-Item a C:\\out\\`), so it is read as `/` and the newline
    after it still cuts; only an odd run of backticks joins lines."""
    if not powershell:
        return join_continuations(text)
    return _LINE_END_BACKSLASH.sub("/", _BACKTICK_CONTINUATION.sub(r"\1` ", text))


def command_readings(text: str, powershell: bool = False) -> list[list[str]]:
    """Each reading of `text` as a list of segments: the bash reading, then, when the text holds `\\"`, the
    PowerShell reading.

    PowerShell does not escape a quote with `\\`, so `"C:\\x\\"` is a closed string there and the `;` after it cuts.
    The whole text is cut again with `\\` plain inside double quotes, and each `\\"` is rewritten to `/"` in the
    segments so that `write_targets` reads the path (`C:/x/`). The caller judges each reading and acts on any.
    With `powershell` (a PowerShell command), only backtick continuations join lines: see `_joined`."""
    joined = _joined(text, powershell)
    readings = [_pieces(joined, _BASH)]
    if '\\"' in joined:
        readings.append([piece.replace('\\"', '/"') for piece in _pieces(joined, _POWERSHELL)])
    return readings


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


def _after_variable(words: list[str]) -> list[str]:
    """The words after a leading PowerShell assignment (`$f = `, `$f=`, `$f =`), or the words as they are."""
    head = _VARIABLE.match(words[0])
    if head and head.group().endswith("="):
        rest = [words[0][head.end():]] + words[1:]
    elif head and len(words) > 1 and words[1].startswith("="):
        rest = [words[1][1:]] + words[2:]
    else:
        return words
    return [word for word in rest[:1] if word] + rest[1:]


def _peel(words: list[str], wrapped: bool) -> tuple[list[str], bool] | None:
    """One leading word that is not the program, dropped; None when the first word is the program."""
    first = words[0].lower()
    if first in _WRAPPERS:
        return _unwrapped(words[1:]), True
    if first in _RESERVED or _ASSIGNMENT.match(first) or (wrapped and first.startswith("-")):
        return _unwrapped(words[1:]), wrapped
    dropped = _after_variable(words)
    return (_unwrapped(dropped), wrapped) if dropped is not words else None


def _program(words: list[str]) -> tuple[str, list[str]]:
    """The program's name (basename, lowercase, no `.exe`) and its arguments, past assignments, reserved words
    (`do`, `then`, `!`) and wrappers."""
    words, wrapped = _unwrapped(words), False
    while words and (peeled := _peel(words, wrapped)) is not None:
        words, wrapped = peeled
    if not words:
        return "", []
    return words[0].rsplit("/", 1)[-1].lower().removesuffix(".exe"), words[1:]


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


def _without_option_values(args: list[str]) -> list[str]:
    """The arguments without each PowerShell option that takes a value (`-ErrorAction`, `-Filter`, in any case) and
    that value."""
    kept, skip = [], False
    for word in args:
        if skip:
            skip = False
        elif word.lower() in _POWERSHELL_VALUE_OPTIONS:
            skip = True
        else:
            kept.append(word)
    return kept


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
    first = next(iter(_non_options(after)), None)
    if (sub in _GIT_LISTS and first is None) or (sub in _GIT_LISTS | {"stash"} and first in _GIT_LISTING):
        return []
    return directories or ["."]


_FAMILIES: dict[str, Callable[[list[str]], list[str]]] = {
    **dict.fromkeys(_EVERY_WORD, _every_word),
    **dict.fromkeys(_DESTINATION, _destination),
    "sed": _sed_files,
    "git": _git,
}


def write_targets(segment: str, powershell: bool = False) -> list[str]:
    """The words one segment writes, as written: its redirect targets, then its program's targets.

    Redirect targets are returned as they stand, devices included (`is_device` decides); the program is read with
    `path_words`, so quotes are gone and `\\` is a separator or an escape."""
    rest, redirects = split_redirects(segment)
    name, args = _program(path_words(rest, powershell))
    if powershell and _FAMILIES.get(name) in (_every_word, _destination):
        args = _without_option_values(args)
    return redirects + _FAMILIES.get(name, lambda _: [])(args)


def cd_target(segment: str, powershell: bool = False) -> str | None:
    """Where a `cd` (`chdir`, `pushd`, `Set-Location` and their aliases) goes: its first non-option word, `~` when
    it has none, None for `cd -` and for any other program."""
    rest, _ = split_redirects(segment)
    name, args = _program(path_words(rest, powershell))
    if name not in _CD or args[:1] == ["-"]:
        return None
    return next(iter(_non_options(args)), "~")
