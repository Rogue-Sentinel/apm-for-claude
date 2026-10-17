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

from apm.metrics_lang import PYTHON, is_logic_line, measure_plain
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
# Stands in for a token that spans lines, so every line it covers still counts as code.
_MULTILINE = "s"
_Span = tuple[tuple[int, int], tuple[int, int]]


def measure_python(path: str, text: str) -> FileMetric:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as error:  # ValueError: null bytes on older Pythons, defensive
        return _unparsed(path, text, error)
    logic = _logic_lines(text, _docstring_spans(tree, text))
    collector = _Collector(logic)
    collector.visit(tree)
    return FileMetric(
        path, _LANGUAGE, len(logic), tuple(collector.functions), tuple(collector.classes),
        functions_measured=True,
    )


def _unparsed(path: str, text: str, error: Exception) -> FileMetric:
    note = f"syntax error: {getattr(error, 'msg', error)}"
    try:
        lines = len(_logic_lines(text))
    except (tokenize.TokenError, SyntaxError):
        lines = measure_plain(path, text, PYTHON).lines
    return FileMetric(path, _LANGUAGE, lines, note=note)


def _logic_lines(text: str, skip: list[_Span] | None = None) -> set[int]:
    rows: dict[int, list[str]] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type in _SKIPPED or _inside(token, skip or []):
            continue
        multiline = token.start[0] != token.end[0]
        for row in range(token.start[0], token.end[0] + 1):
            rows.setdefault(row, []).append(_MULTILINE if multiline else token.string)
    return {row for row, parts in rows.items() if is_logic_line("".join(parts))}


def _inside(token: tokenize.TokenInfo, spans: list[_Span]) -> bool:
    return any(start <= token.start and token.end <= end for start, end in spans)


def _docstring(node: ast.AST) -> ast.stmt | None:
    body = getattr(node, "body", None)
    if not body or not isinstance(body[0], ast.Expr):
        return None
    value = body[0].value
    return body[0] if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _docstring_spans(tree: ast.AST, text: str) -> list[_Span]:
    """Where each docstring sits, in the character columns that tokenize reports."""
    lines = text.split("\n")

    def column(row: int, offset: int) -> tuple[int, int]:
        return row, len(lines[row - 1].encode()[:offset].decode())  # ast offsets are UTF-8 bytes

    docs = [_docstring(n) for n in ast.walk(tree) if isinstance(n, _DOC_OWNERS)]
    return [
        (column(d.lineno, d.col_offset), column(d.end_lineno, d.end_col_offset))
        for d in docs
        if d is not None
    ]


def _body_start(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    first = node.body[0]
    decorators = getattr(first, "decorator_list", [])
    return min([first.lineno, *(d.lineno for d in decorators)])


class _Collector(ast.NodeVisitor):
    def __init__(self, logic: set[int]) -> None:
        self.logic = logic
        self.scope: list[str] = []
        self.functions: list[FunctionMetric] = []
        self.classes: list[ClassMetric] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        body_lines = range(_body_start(node), node.end_lineno + 1)
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
