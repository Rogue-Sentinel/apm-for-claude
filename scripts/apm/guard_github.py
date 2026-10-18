"""Which `gh` calls a worker may not run. Workers never write to GitHub; the manager files and closes issues.

A worker may run only the `gh` verbs known to read (and `gh api` without a method or a field). Known limits,
none of which a check on the command text can close:
- runtime indirection: `$GH issue create`, `eval "$cmd"`, `gh $(echo issue) create` (a substitution in the
  group or verb position is denied, but one that builds the name `gh` itself is not seen);
- a PowerShell backtick escape inside the word `gh` or its verb;
- other tools that reach GitHub: `curl` to api.github.com, `git push`, an HTTP library;
- a script the worker writes and then runs, whose text this check never sees.
"""
from __future__ import annotations

import re

from .guard_words import shell_words, spellings

_ANY = frozenset({"*"})
# The verbs a worker may run, per group, read from `gh <group> --help` (gh 2.78.0). Everything else is
# a write: a verb not listed, a group not listed, and every alias (`new`, `ext`, `cs`, or one the user
# defined with `gh alias set`). A name missing here is denied, so a new gh verb fails closed.
_READS: dict[str, frozenset[str]] = {
    "issue": frozenset("list ls status view".split()),
    "pr": frozenset("list ls status checks diff view".split()),  # not `checkout`: it moves the worktree
    "release": frozenset("list view download".split()),
    "repo": frozenset("list view clone gitignore license".split()),
    "label": frozenset({"list"}),
    "workflow": frozenset("list view".split()),
    "run": frozenset("list view watch download".split()),
    "cache": frozenset({"list"}),
    "secret": frozenset({"list"}),
    "variable": frozenset("list get".split()),
    "gist": frozenset("list view clone".split()),
    "ssh-key": frozenset({"list"}),
    "gpg-key": frozenset({"list"}),
    "project": frozenset("list view field-list item-list".split()),
    "alias": frozenset({"list"}),
    "auth": frozenset({"status"}),
    "config": frozenset("get list".split()),
    "extension": frozenset("list search".split()),
    "codespace": frozenset("list view".split()),
    "org": frozenset({"list"}),
    "ruleset": frozenset("list view check".split()),
    "attestation": frozenset("verify trusted-root download".split()),
    "search": _ANY,
    "status": _ANY,
    "browse": _ANY,
    "help": _ANY,
    "version": _ANY,
    "completion": _ANY,
}
# `-R/--repo` and `--hostname` take a value, which must not be taken for the group or the verb.
_VALUED = frozenset({"-R", "--repo", "--hostname"})
_FIELD_FLAGS = frozenset({"--field", "--raw-field", "--input"})
# Short flags of `gh api` that take a value; the rest of a cluster such as `-Hx` is that value.
_API_VALUED = "HqtpX"
# `gh` or `gh.exe` in any case, alone or at the end of a path, never the tail of another word.
# The text after it is a zero-width capture, so a second `gh` in the same segment is found too
# (`exec -a gh gh issue create`).
_GH = re.compile(
    r"(?<![\w.-])(?:\S*[/\\])?gh(?:\.exe)?(?=[\s()<>{}`;|&$]|$)(?=(?P<rest>.*))", re.IGNORECASE)
_REASON = (
    "workers do not write to GitHub; report to the manager instead "
    "(to search for the text, use the Grep tool: it does not go through the shell)"
)


def _group_and_verb(words: list[str]) -> tuple[str, str]:
    """The first two words that are neither options nor an option's value."""
    plain: list[str] = []
    skip = False
    for word in words:
        if skip or word.startswith("-"):
            skip = word in _VALUED
        else:
            plain.append(word.lower())
    group, verb, *_ = [*plain, "", ""]
    return group, verb


def _method_writes(method: str) -> bool:
    return bool(method) and method.upper() != "GET"


def _short_flag_writes(token: str, following: str) -> bool:
    """A `-fF` or `-X` in a cluster of short flags: fields imply a POST, `-X` names the method."""
    letters = token[1:]
    for index, letter in enumerate(letters):
        if letter in "fF":
            return True
        if letter == "X":
            return _method_writes(letters[index + 1:].lstrip("=") or following)
        if letter in _API_VALUED:
            return False
    return False


def _flag_writes(token: str, following: str) -> bool:
    if token.startswith("--"):
        name, _, value = token.partition("=")
        return name in _FIELD_FLAGS or (name == "--method" and _method_writes(value or following))
    return len(token) > 1 and token.startswith("-") and _short_flag_writes(token, following)


def _api_writes(words: list[str]) -> bool:
    """`gh api` is a read unless it names a method other than GET or sends a field or a body."""
    followers = [*words[1:], ""]
    return any(_flag_writes(token, following) for token, following in zip(words, followers))


def _shows_token(words: list[str]) -> bool:
    """`gh auth status --show-token` or `-t`, alone or in a cluster before `-h`, prints the token."""
    return any(word.partition("=")[0] == "--show-token"
               or (word[:1] == "-" and word[1:2] != "-" and "t" in word[1:].partition("h")[0])
               for word in words)


def _writes(words: list[str]) -> bool:
    group, verb = _group_and_verb(words)
    if group == "api":
        return _api_writes(words)
    if (group, verb) == ("auth", "status") and _shows_token(words):
        return True
    reads = _READS.get(group)
    return bool(group) and (reads is None or not ("*" in reads or verb in reads))


def gh_write_reason(segment: str) -> str | None:
    """Why a worker may not run `segment`: it runs `gh` with anything but a verb known to read."""
    for text in spellings(segment):
        if any(_writes(shell_words(found.group("rest"))) for found in _GH.finditer(text)):
            return f"{_REASON}: {segment}"
    return None
