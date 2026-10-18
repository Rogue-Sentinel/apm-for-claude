"""Which `gh` calls write to GitHub. Workers never run them; the manager files and closes issues."""
from __future__ import annotations

import re

_ANY = frozenset({"*"})
# Every verb that changes something on GitHub, or runs code or changes the login. A verb missing
# here is a hole, so the list errs on the side of denying: reads (`list`, `view`, `diff`, `status`) stay out.
_WRITES: dict[str, frozenset[str]] = {
    "issue": frozenset("create close reopen edit comment delete transfer lock unlock pin unpin develop".split()),
    "pr": frozenset("create merge close reopen edit comment review ready lock unlock update-branch".split()),
    "release": frozenset("create delete delete-asset edit upload".split()),
    "repo": frozenset("create delete edit rename archive unarchive fork sync deploy-key autolink".split()),
    "label": frozenset("create edit delete clone".split()),
    "workflow": frozenset("run enable disable".split()),
    "run": frozenset("rerun cancel delete".split()),
    "cache": frozenset({"delete"}),
    "secret": frozenset("set delete remove".split()),
    "variable": frozenset("set delete remove".split()),
    "gist": frozenset("create edit delete rename".split()),
    "ssh-key": frozenset("add delete".split()),
    "gpg-key": frozenset("add delete".split()),
    "project": frozenset(
        "create edit delete close copy link unlink mark-template item-add item-create item-edit "
        "item-delete item-archive field-create field-delete".split()),
    "alias": frozenset("set delete import".split()),
    "auth": frozenset("login logout refresh setup-git switch".split()),
    "config": frozenset({"set"}),
    "extension": _ANY,
    "codespace": _ANY,
}
# `-R/--repo` and `--hostname` take a value, which must not be taken for the group or the verb.
_VALUED = frozenset({"-R", "--repo", "--hostname"})
_FIELD_FLAGS = frozenset({"--field", "--raw-field", "--input"})
# Short flags of `gh api` that take a value; the rest of a cluster such as `-Hx` is that value.
_API_VALUED = "HqtpX"
# `gh` or `gh.exe` in any case, alone or at the end of a path, never the tail of another word.
_GH = re.compile(r"(?<![\w.-])(?:\S*[/\\])?gh(?:\.exe)?(?=\s|$)(?P<rest>.*)", re.IGNORECASE)
_REASON = "workers do not write to GitHub; report to the manager instead"


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


def _writes(words: list[str]) -> bool:
    group, verb = _group_and_verb(words)
    if group == "api":
        return _api_writes(words)
    verbs = _WRITES.get(group, frozenset())
    return verb in verbs or "*" in verbs


def _spellings(segment: str) -> tuple[str, str]:
    """The segment without quotes, with `\\` read as a path separator and then as an escape."""
    bare = segment.replace('"', "").replace("'", "")
    return bare.replace("\\", "/"), bare.replace("\\", "")


def gh_write_reason(segment: str) -> str | None:
    """Why a worker may not run `segment`: it runs `gh` with a verb that writes to GitHub."""
    for text in _spellings(segment):
        if any(_writes(found.group("rest").split()) for found in _GH.finditer(text)):
            return f"{_REASON}: {segment}"
    return None
