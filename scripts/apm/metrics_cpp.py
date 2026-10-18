"""Classes in C++ source, with their public methods counted.

The stripped text is walked with a scope stack over the characters `{ } ; :`, in the manner of
`metrics_braces`. File, namespace and class scopes collect a head, the statement before the next
structural character. Every other `{` opens an opaque scope whose contents are skipped, so classes
inside function bodies and members of nested blocks are not reported. A `{` in a class that
follows a function head is an inline method body: the method is counted there. Any other opaque
scope inside a class (`int y{0};`, `y_{2}` in an initializer list, `enum E {...}`) adds `{}` to the
class's head, which keeps the statement one piece. A nested class is named `Outer::Inner`, and
namespaces do not qualify names. What counts as a public method is in `metrics_cpp_heads`.

Known limits. This is a scanner, not a compiler, and these cases are read wrongly:
- a class defined in a macro argument, or whose head is built by a macro, is read by its text;
- `#ifdef` arms that each open a class or a function leave an extra `{`, and the file is then
  reported as "unbalanced braces" by the function scanner, so no classes are reported either;
- the limits of `metrics_cpp_heads` and of `strip_code` in `metrics_lang` apply first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

from apm.metrics_cpp_heads import (
    access_label, class_head, is_function_head, is_public_method, scope_kind,
)
from apm.metrics_lang import Language, strip_code
from apm.metrics_model import ClassMetric, FileMetric

_EVENT = re.compile(r"[{};]|(?<!:):(?!:)")
_BASE_COLON = re.compile(r"(?<!:):(?!:)")


@dataclass
class _Scope:
    kind: Literal["namespace", "class", "skip"]
    name: str = ""
    access: str = "public"
    count: int = 0
    head: str = ""
    depth: int = 0
    slot: int = -1
    inline: bool = False


def cpp_classes(code: str) -> tuple[ClassMetric, ...]:
    """Every class, struct and union defined at file, namespace or class scope, in source order."""
    return _Walker(code).run()


def with_cpp_classes(metric: FileMetric, text: str, language: Language) -> FileMetric:
    """`metric` with its C++ classes, when it is a C++ file whose braces balanced."""
    if language.name != "C++" or not metric.functions_measured:
        return metric
    return replace(metric, classes=cpp_classes(strip_code(text, language)))


class _Walker:
    def __init__(self, code: str) -> None:
        self.code = code
        self.stack = [_Scope("namespace")]
        self.found: list[ClassMetric] = []
        self.pos = 0

    def run(self) -> tuple[ClassMetric, ...]:
        for match in _EVENT.finditer(self.code):
            self._step(match.group(), match.start())
        return tuple(self.found)

    def _step(self, char: str, at: int) -> None:
        top = self.stack[-1]
        if top.kind != "skip":
            top.head += self.code[self.pos:at]
        self.pos = at + 1
        if top.kind == "skip":
            self._skip(top, char)
        elif char == "{":
            self._open(top, at)
        elif char == "}":
            self._close(top)
        else:
            self._statement(top, char)

    def _statement(self, top: _Scope, char: str) -> None:
        if char == ";":
            self._count(top)
            top.head = ""
            return
        label = access_label(top.head) if top.kind == "class" else None
        if label:
            top.access, top.head = label, ""
        else:
            top.head += ":"

    def _count(self, top: _Scope) -> None:
        if top.kind == "class" and top.access == "public" and is_public_method(top.head, top.name):
            top.count += 1

    def _skip(self, top: _Scope, char: str) -> None:
        if char == "{":
            top.depth += 1
        elif char == "}" and top.depth:
            top.depth -= 1
        elif char == "}":
            self.stack.pop()
            parent = self.stack[-1]
            parent.head = parent.head + "{}" if parent.kind == "class" and not top.inline else ""

    def _open(self, top: _Scope, at: int) -> None:
        kind = scope_kind(top.head)
        if kind == "class":
            self._open_class(top, at)
        elif kind == "namespace":
            self.stack.append(_Scope("namespace"))
            top.head = ""
        else:
            inline = top.kind == "class" and is_function_head(top.head)
            if inline:
                self._count(top)
            self.stack.append(_Scope("skip", inline=inline))

    def _open_class(self, top: _Scope, at: int) -> None:
        bare, access = class_head(top.head)
        name = f"{top.name}::{bare}" if top.kind == "class" else bare
        self.found.append(ClassMetric(name, self._name_line(top.head, bare, at), 0))
        self.stack.append(_Scope("class", name, access, slot=len(self.found) - 1))
        top.head = ""

    def _close(self, top: _Scope) -> None:
        if len(self.stack) == 1:
            top.head = ""
            return
        self.stack.pop()
        if top.kind == "class":
            self.found[top.slot] = replace(self.found[top.slot], public_methods=top.count)
        self.stack[-1].head = ""

    def _name_line(self, head: str, name: str, at: int) -> int:
        """The line of the class name in its head, or of the brace when the head does not show it."""
        base = _BASE_COLON.search(head)
        region = head[:base.start()] if base else head
        hits = list(re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", region))
        end = hits[-1].end() if hits else len(head)
        return self.code.count("\n", 0, at) + 1 - head[end:].count("\n")
