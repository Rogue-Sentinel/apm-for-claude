"""Functions in brace languages, found without a compiler.

The stripped text (comments and literal contents removed) is walked with a scope stack. A `{`
opens a scope classified from its head, the text since the last `;`, `{` or `}` in the enclosing
scope (see `metrics_heads`). A function scope swallows everything inside it, so a lambda or a
nested block counts in its parent and is not reported alone. Every other scope (class, struct,
namespace, impl, object literal, a control block at file level) is declarative, so the functions
inside it are found. A callback passed to a call at file level is read as a function of its own.

Known limits. This is a scanner, not a compiler, and these cases are read wrongly:
- a C++ constructor whose initializer list uses braces (`: x_{1} {`) is read as a function that
  ends at the first `}`; a project that needs exactness declares its own checker;
- code blocks that are not introduced by a parenthesized group are never functions: Java and C#
  static initializers and property accessors, Kotlin `init {` and `get() = {`, Swift computed
  properties, and Scala or Kotlin parameterless members;
- a comma-separated head in an object literal or enum takes the name of its first call;
- `<` and `>` used as comparison operators inside a head can be taken for generic arguments;
- a JavaScript template literal with a nested template ends at the first closing backtick;
- the limits of `strip_code` in `metrics_lang` apply first (regex literals, raw strings, and so on).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from apm.metrics_heads import function_name, keeps_head
from apm.metrics_lang import Language, count_logic, strip_code
from apm.metrics_model import FileMetric, FunctionMetric

_STRUCTURAL = re.compile(r"[{}();]")


@dataclass
class _Scope:
    kind: str = "decl"
    name: str = ""
    line: int = 1
    open_at: int = 0
    head_start: int = 0
    paren: int = 0
    depth: int = 0


def measure_braces(path: str, text: str, language: Language) -> FileMetric:
    stripped = strip_code(text, language)
    lines = count_logic(stripped)
    functions, balanced = _Scanner(stripped).run()
    if not balanced:
        return FileMetric(path, language.name, lines, note="unbalanced braces")
    return FileMetric(path, language.name, lines, functions=functions, functions_measured=True)


class _Scanner:
    def __init__(self, code: str) -> None:
        self.code = code
        self.stack = [_Scope()]
        self.found: list[FunctionMetric] = []
        self.stray = False

    def run(self) -> tuple[tuple[FunctionMetric, ...], bool]:
        for match in _STRUCTURAL.finditer(self.code):
            top = self.stack[-1]
            step = self._in_function if top.kind == "func" else self._in_decl
            step(top, match.group(), match.start())
        found = tuple(sorted(self.found, key=lambda f: f.line))
        return found, not self.stray and len(self.stack) == 1

    def _in_function(self, top: _Scope, char: str, at: int) -> None:
        if char == "{":
            top.depth += 1
        elif char == "}" and top.depth:
            top.depth -= 1
        elif char == "}":
            body = self.code[top.open_at + 1:at]
            self.found.append(FunctionMetric(top.name, top.line, count_logic(body)))
            self._pop(at)

    def _pop(self, at: int) -> None:
        closed = self.stack.pop()
        top = self.stack[-1]
        if closed.kind == "func" or not top.paren:
            top.head_start = at + 1

    def _in_decl(self, top: _Scope, char: str, at: int) -> None:
        if char in "()":
            top.paren = max(0, top.paren + (1 if char == "(" else -1))
        elif char == ";":
            self._end_statement(top, at)
        elif char == "{":
            self._open(top, at)
        elif len(self.stack) > 1:
            self._pop(at)
        else:
            self.stray = True
            top.head_start = at + 1

    def _end_statement(self, top: _Scope, at: int) -> None:
        if not top.paren and not keeps_head(self.code[top.head_start:at]):
            top.head_start = at + 1

    def _open(self, top: _Scope, at: int) -> None:
        head = self.code[top.head_start:at]
        name = function_name(head, in_call=top.paren > 0)
        kind = "decl" if name is None else "func"
        self.stack.append(_Scope(kind, name or "", self._line(top.head_start, head, name), at, at + 1))

    def _line(self, start: int, head: str, name: str | None) -> int:
        """The line of the name in the head, or of the brace when the head does not show it."""
        found = re.search(rf"\b{re.escape(name.split('::')[-1])}\b", head) if name else None
        index = start + (found.start() if found else len(head))
        return self.code.count("\n", 0, index) + 1
