"""Python files measured through tokenize and the ast.

A line is logic when it holds a token other than a comment, a newline or an indent marker, and is not
made only of brackets, semicolons and commas. A string spanning several lines counts on every line it
spans, except a docstring, which is removed. A function's lines run from its first body statement to
its end, so the decorators and the signature are not counted.
"""
from __future__ import annotations

import ast
import io
import tokenize

from apm.metrics_lang import is_logic_line, language_for, measure_plain
from apm.metrics_model import ClassMetric, FileMetric, FunctionMetric

_LANGUAGE = "Python"
_SKIPPED = {
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
}
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_DOC_OWNERS = (ast.Module, ast.ClassDef, *_FUNCTIONS)


def measure_python(path: str, text: str) -> FileMetric:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as error:
        return _unparsed(path, text, error)
    logic = _logic_lines(text) - _docstring_lines(tree)
    collector = _Collector(logic)
    collector.visit(tree)
    return FileMetric(
        path, _LANGUAGE, len(logic), tuple(collector.functions), tuple(collector.classes), True
    )


def _unparsed(path: str, text: str, error: Exception) -> FileMetric:
    note = f"syntax error: {getattr(error, 'msg', error)}"
    try:
        lines = len(_logic_lines(text))
    except (tokenize.TokenError, SyntaxError):
        lines = measure_plain(path, text, language_for("x.py")).lines
    return FileMetric(path, _LANGUAGE, lines, note=note)


def _logic_lines(text: str) -> set[int]:
    rows: dict[int, list[str]] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type in _SKIPPED:
            continue
        spans = token.start[0] != token.end[0]
        for row in range(token.start[0], token.end[0] + 1):
            rows.setdefault(row, []).append("s" if spans else token.string)
    return {row for row, parts in rows.items() if is_logic_line("".join(parts))}


def _docstring(node: ast.AST) -> ast.stmt | None:
    body = getattr(node, "body", None)
    if not body or not isinstance(body[0], ast.Expr):
        return None
    value = body[0].value
    return body[0] if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        doc = _docstring(node) if isinstance(node, _DOC_OWNERS) else None
        if doc is not None:
            lines.update(range(doc.lineno, doc.end_lineno + 1))
    return lines


class _Collector(ast.NodeVisitor):
    def __init__(self, logic: set[int]) -> None:
        self.logic = logic
        self.scope: list[str] = []
        self.functions: list[FunctionMetric] = []
        self.classes: list[ClassMetric] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        body_lines = range(node.body[0].lineno, node.end_lineno + 1)
        count = sum(row in self.logic for row in body_lines)
        self.functions.append(FunctionMetric(self._name(node), node.lineno, count))
        self._enter(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        public = sum(isinstance(s, _FUNCTIONS) and not s.name.startswith("_") for s in node.body)
        self.classes.append(ClassMetric(self._name(node), node.lineno, public))
        self._enter(node)

    def _name(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
        return ".".join([*self.scope, node.name])

    def _enter(self, node: ast.AST) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()
