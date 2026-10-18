"""Reading the head of a brace: the text before a `{` that says whether a function opens there.

The head is tidied first (annotations, attributes and generic arguments dropped). It is a function
when it holds a parenthesized group, is not a control block or a class head, and what follows the
last group is a plausible tail (qualifiers, a return type, an arrow). Everything here works on text
already stripped of comments and literals.
"""
from __future__ import annotations

import re

_CONTROL = frozenset(
    "if for while switch catch foreach using lock synchronized with when match do try else guard elif".split()
)
_LEADING = frozenset("if for while switch catch foreach else do try guard match elif loop finally".split())
_GUARDED = frozenset("using lock synchronized with when".split())
_CARRY = frozenset("if for switch while".split())
_NOT_A_NAME = frozenset(
    "pub func function fun fn def async await decltype alignas noexcept sizeof static_assert __declspec".split()
)
_ANNOTATION = re.compile(r"@[\w.]+(?:\s*\((?:[^()]|\([^()]*\))*\))?")
_BRACKETED = re.compile(r"\[[^\[\]]*\]")
_ANGLES = re.compile(r"<[^<>]*>")
_NAME = re.compile(
    r"((?:[A-Za-z_$][\w$]*\s*::\s*)*"
    r"(?:operator\s*\(\s*\)|operator\s*[^\s\w(]+|operator\s+\w+|~?[A-Za-z_$][\w$]*))\s*\("
)
_DECLARATOR = re.compile(r"\b(?:class|struct|union|enum|interface|trait|object|record|impl|new)\s+$")
_ASSIGNED = re.compile(r"([\w$.]+)\s*(?::[^=()]*)?=(?![=>])")
_PROPERTY = re.compile(r"([\w$]+)\s*:\s*(?:async\s+)?(?:function\b|\()")
_ASSIGNMENT = re.compile(r"(?<![=!<>])=(?![=>])")
_LITERAL_MARK = re.compile(r"=>|->|\b(?:function|func|fun)\b")
_TIGHT = re.compile(r"\s*(\W)\s*")


def function_name(head: str, in_call: bool = False) -> str | None:
    """The function a `{` opens after `head`, or None when it opens a declarative block."""
    text = tidy(argument_head(head) if in_call else head)
    call = _first_call(text)
    if _is_control(text, call) or not _function_shape(text):
        return None
    if call and (_DECLARATOR.search(text[: call.start()]) or _assigns_value(text, call)):
        return None
    return _name_of(text, call)


def keeps_head(head: str) -> bool:
    """A `;` inside a paren-less control head (Go `if x := f(); g(x) {`) does not end the head."""
    first = re.match(r"\s*(\w+)\s*(\()?", head)
    return bool(first) and first.group(1) in _CARRY and not first.group(2)


def argument_head(head: str) -> str:
    """The part of `head` after the innermost unclosed `(` or the last top-level `,`."""
    depth = 0
    for i in range(len(head) - 1, -1, -1):
        if head[i] == ")":
            depth += 1
        elif head[i] == "(" and depth:
            depth -= 1
        elif head[i] in "(," and not depth:
            return head[i + 1:]
    return head


def tidy(head: str) -> str:
    head = _repeat(_BRACKETED, _ANNOTATION.sub(" ", head))
    if "operator" not in head:
        protected = head.replace("->", "\x01").replace("=>", "\x02")
        head = _repeat(_ANGLES, protected).replace("\x01", "->").replace("\x02", "=>")
    return head.strip()


def _repeat(pattern: re.Pattern[str], text: str) -> str:
    previous = None
    while previous != text:
        previous, text = text, pattern.sub(" ", text)
    return text


def _groups(text: str) -> list[tuple[int, int]]:
    spans, depth, start = [], 0, 0
    for i, char in enumerate(text):
        if char == "(":
            start = i if not depth else start
            depth += 1
        elif char == ")" and depth:
            depth -= 1
            if not depth:
                spans.append((start, i + 1))
    return spans


def _function_shape(text: str) -> bool:
    spans = _groups(text)
    if not spans:
        return text.endswith("=>")
    tail = text[spans[-1][1]:].replace("->", "").replace("=>", "").rstrip()
    return "=" not in tail.removesuffix("=")


def _first_call(text: str) -> re.Match[str] | None:
    for match in _NAME.finditer(text):
        if match.group(1) not in _NOT_A_NAME:
            return match
    return None


def _is_control(text: str, call: re.Match[str] | None) -> bool:
    first = re.match(r"(\w+)\s*(\()?", text)
    word, paren = (first.group(1), first.group(2)) if first else ("", None)
    if word in _LEADING or (word in _GUARDED and paren):
        return True
    return bool(call) and call.group(1).split("::")[-1] in _CONTROL


def _assigns_value(text: str, call: re.Match[str]) -> bool:
    """`val xs = listOf(1).map {` assigns a call's result; `x = function () {` assigns a function."""
    return bool(_ASSIGNMENT.search(text[: call.start()])) and not _LITERAL_MARK.search(text)


def _name_of(text: str, call: re.Match[str] | None) -> str:
    if call and "=>" not in text:
        return _TIGHT.sub(lambda m: m.group(1), " ".join(call.group(1).split()))
    found = _ASSIGNED.search(text) or _PROPERTY.search(text)
    return found.group(1) if found else "<anonymous>"


_LINE_END = re.compile(r"(?:->|=>|[=+\-*/%&|^?:,(.]|\b(?:where|throws|extends|implements))\s*$")
_LINE_START = re.compile(r"\s*(?:[{.)\]:,=?&|+]|->|=>|\b(?:throws|where|extends|implements)\b)")


def continues(head: str, rest: str) -> bool:
    """Whether the statement in `head` goes on in the text after its newline."""
    return bool(_LINE_END.search(head) or _LINE_START.match(rest))
