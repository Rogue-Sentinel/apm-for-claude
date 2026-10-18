"""Functions in brace languages, found without a compiler.

The stripped text (comments and literal contents removed) is walked with a scope stack. A `{`
opens a scope classified from its head, the last statement before it in the enclosing scope (see
`metrics_heads`). A `;` ends a statement, and so does a newline outside parentheses unless the
statement plainly continues on the next line. A function scope swallows everything inside it, so a
lambda or a nested block counts in its parent and is not reported alone. Every other scope (class,
struct, namespace, impl, object literal, a control block at file level) is declarative, so the
functions inside it are found.

A callback passed as a call argument, at file level or inside another such callback, is a function
named after its callee (`describe`, `it`, `app.get`). Its lines leave out the callbacks nested in
it as call arguments, and each of those is reported on its own. Duplicate callback names are
numbered in source order: `it`, `it#2`. Overloads of named functions are not numbered.

Known limits. This is a scanner, not a compiler, and these cases are read wrongly:
- a C++ constructor whose initializer list uses braces (`: x_{1} {`) is read as a function that
  ends at the first `}`; a project that needs exactness declares its own checker;
- `#ifdef` arms that each open a signature (`#ifdef X`, `void f() {`, `#else`, `void f(int) {`)
  leave an extra `{`, so the file is reported as "unbalanced braces";
- code blocks that are not introduced by a parenthesized group are never functions: Java and C#
  static initializers and property accessors, Kotlin `init {`, `get() = {` and `fun f() = run {`,
  Swift computed properties, and Scala or Kotlin parameterless members;
- a Rust `match` arm (`_ => {`) at declarative scope is read as an anonymous function, a Go
  `map[string]func() {...}` literal is read as one anonymous function, and a C function that returns
  a function pointer (`int (*get(void))(int) {`) takes the wrong name;
- a comma-separated head in an object literal or enum takes the name of its first call;
- `<` and `>` used as comparison operators inside a head can be taken for generic arguments;
- a JavaScript template literal with a nested template ends at the first closing backtick;
- the limits of `strip_code` in `metrics_lang` apply first (regex literals, raw strings, and so on).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Literal, NamedTuple

from apm.metrics_heads import continues, function_name, keeps_head
from apm.metrics_lang import Language, count_logic, strip_code
from apm.metrics_model import FileMetric, FunctionMetric

_STRUCTURAL = re.compile(r"[{}();\n]")
_CALLEE = re.compile(r"([\w$.:]+)\s*$")
_Found = tuple[int, FunctionMetric, bool]
_Kind = Literal["decl", "func", "callback"]


class _Call(NamedTuple):
    callee: str
    open_at: int


@dataclass
class _Scope:
    kind: _Kind = "decl"
    name: str = ""
    line: int = 1
    open_at: int = 0
    head_start: int = 0
    depth: int = 0
    calls: list[_Call] = field(default_factory=list)
    holes: list[tuple[int, int]] = field(default_factory=list)


def measure_braces(path: str, text: str, language: Language) -> FileMetric:
    stripped = strip_code(text, language)
    lines = count_logic(stripped)
    functions, balanced = _Scanner(stripped).run()
    if not balanced:
        return FileMetric(path, language.name, lines, note="unbalanced braces")
    return FileMetric(path, language.name, lines, functions=functions, functions_measured=True)


def _number_callbacks(found: list[_Found]) -> tuple[FunctionMetric, ...]:
    seen: dict[str, int] = {}
    metrics = []
    for _, metric, is_callback in sorted(found, key=lambda item: item[0]):
        seen[metric.name] = seen.get(metric.name, 0) + is_callback
        if is_callback and seen[metric.name] > 1:
            metric = replace(metric, name=f"{metric.name}#{seen[metric.name]}")
        metrics.append(metric)
    return tuple(metrics)


class _Scanner:
    def __init__(self, code: str) -> None:
        self.code = code
        self.stack = [_Scope()]
        self.found: list[_Found] = []
        self.stray = False

    def run(self) -> tuple[tuple[FunctionMetric, ...], bool]:
        for match in _STRUCTURAL.finditer(self.code):
            self._step(self.stack[-1], match.group(), match.start())
        return _number_callbacks(self.found), not self.stray and len(self.stack) == 1

    def _step(self, top: _Scope, char: str, at: int) -> None:
        if char == "{":
            self._open(top, at)
        elif char == "}":
            self._close(top, at)
        elif top.kind != "func":
            self._plain(top, char, at)

    def _plain(self, top: _Scope, char: str, at: int) -> None:
        if char in "()":
            self._paren(top, char, at)
        elif top.kind == "decl" and char == ";":
            self._end_statement(top, at)
        elif top.kind == "decl" and char == "\n":
            self._end_line(top, at)

    def _paren(self, top: _Scope, char: str, at: int) -> None:
        if char == "(":
            before = self.code[max(top.head_start, at - 200):at]
            found = _CALLEE.search(before)
            top.calls.append(_Call(found.group(1).lstrip(".:") if found else "", at))
        elif top.calls:
            top.calls.pop()

    def _end_statement(self, top: _Scope, at: int) -> None:
        if not top.calls and not keeps_head(self.code[top.head_start:at]):
            top.head_start = at + 1

    def _end_line(self, top: _Scope, at: int) -> None:
        """A newline ends a statement unless the statement plainly continues."""
        head = self.code[top.head_start:at]
        if not top.calls and head.strip() and not continues(head, self.code[at + 1:]):
            top.head_start = at + 1

    def _open(self, top: _Scope, at: int) -> None:
        name = self._function_head(top, at)
        if name is not None:
            self.stack.append(self._function_scope(top, at, name))
        elif top.kind == "decl":
            self.stack.append(_Scope(open_at=at, head_start=at + 1))
        else:
            top.depth += 1

    def _function_head(self, top: _Scope, at: int) -> str | None:
        if top.kind == "func" or (top.kind == "callback" and not top.calls):
            return None
        start = max(top.head_start, top.calls[-1].open_at + 1) if top.calls else top.head_start
        return function_name(self.code[start:at], in_call=bool(top.calls))

    def _function_scope(self, top: _Scope, at: int, name: str) -> _Scope:
        if top.calls:
            callee, paren = top.calls[-1]
            return _Scope("callback", callee or "<anonymous>", self._line_at(paren), at, at + 1)
        head = self.code[top.head_start:at]
        return _Scope("func", name, self._line_of_name(top.head_start, head, name), at, at + 1)

    def _close(self, top: _Scope, at: int) -> None:
        if top.kind == "decl":
            self._close_decl(at)
        elif top.depth:
            top.depth -= 1
        else:
            body = self._body(top, at)
            metric = FunctionMetric(top.name, top.line, count_logic(body))
            self.found.append((top.open_at, metric, top.kind == "callback"))
            self._pop(at)

    def _close_decl(self, at: int) -> None:
        if len(self.stack) > 1:
            self._pop(at)
        else:
            self.stray = True
            self.stack[0].head_start = at + 1

    def _pop(self, at: int) -> None:
        closed = self.stack.pop()
        top = self.stack[-1]
        if closed.kind != "decl" or not top.calls:
            top.head_start = at + 1
        if closed.kind == "callback":
            top.holes.append((closed.open_at + 1, at))

    def _body(self, scope: _Scope, at: int) -> str:
        """The text between the braces, without the bodies of callbacks nested in it."""
        pieces, cursor = [], scope.open_at + 1
        for start, end in scope.holes:
            pieces.append(self.code[cursor:start])
            cursor = end
        return "".join(pieces) + self.code[cursor:at]

    def _line_at(self, index: int) -> int:
        return self.code.count("\n", 0, index) + 1

    def _line_of_name(self, start: int, head: str, name: str) -> int:
        """The line of the name in the head, or of the brace when the head does not show it."""
        word = name.split("::")[-1]
        word = "operator" if word.startswith("operator") else word
        found = re.search(rf"(?<![\w$]){re.escape(word)}(?![\w$])", head)
        return self._line_at(start + (found.start() if found else len(head)))
