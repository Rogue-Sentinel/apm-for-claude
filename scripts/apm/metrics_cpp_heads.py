"""Reading C++ declaration heads: the text of a statement before its `{` or `;`.

Everything here works on stripped code (comments and literal contents already removed) and on
plain text, so this file imports nothing from the rest of the tool. It answers four questions
about a head: what kind of scope does it open (`scope_kind`), what is the class called and how
does its body start (`class_head`), is it an access label (`access_label`), and does it declare
a method that counts as public (`is_public_method`).

Known limits. This is a scanner, not a compiler, and these cases are read wrongly:
- a macro that expands to a declaration or an access label (`Q_OBJECT`, `public slots:`) is not
  expanded, so a method hidden in a macro is not counted, and a macro with no `;` before a member
  runs into that member's head;
- a method that returns a function pointer (`void (*get())(int);`) is read as a pointer member;
- `noexcept(...)` with nested parentheses is not stripped as a qualifier;
- a `<` or `>` used as a comparison inside a head can be taken for template arguments.
"""
from __future__ import annotations

import re
from typing import Literal

_ACCESS_LABEL = re.compile(r"\b(public|protected|private)\s*$")
_CLASS_WORDS = frozenset({"class", "struct", "union", "final"})
_TEMPLATE = re.compile(r"template\s*<")
_ATTRIBUTE = re.compile(r"\[\[.*?\]\]")
_DECL_SPEC = re.compile(r"\b(?:alignas|__declspec)\s*\([^()]*\)")
_ANGLES = re.compile(r"<[^<>]*>")
_BASE_COLON = re.compile(r"(?<!:):(?!:)")
_CLASS_HEAD = re.compile(r"(?:class|struct|union)\b")
_NAMESPACE = re.compile(r"\bnamespace\b")
_EXTERN_BLOCK = re.compile(r'extern\s*""')
_TRAILING_RETURN = re.compile(r"\)\s*->[^;]*$")
_QUALIFIER = re.compile(
    r"\s*(?<!\w)(?:const|volatile|noexcept(?:\s*\([^()]*\))?|override|final|mutable)\s*$|\s*&&?\s*$"
)
_CTOR_INIT = re.compile(r"\)\s*(?:noexcept\s*)?:(?!:)")
_NAME = re.compile(
    r"((?:[A-Za-z_]\w*\s*::\s*)*"
    r"(?:operator\s*\(\s*\)|operator\s*[^\s\w(]+|operator\s+\w+|~?[A-Za-z_]\w*))\s*\("
)
_NOT_A_NAME = frozenset({"decltype", "alignas", "noexcept", "sizeof", "static_assert", "__declspec"})
_NOT_A_METHOD = re.compile(r"(?:using|friend|typedef|static_assert|enum)\b")
_DELETED = re.compile(r"=\s*delete\s*$")
_FUNCTION_POINTER = re.compile(r"^[^()]*\(\s*(?:[\w:]+::)?[*&]\s*\w*\s*\)\s*\(")
_Kind = Literal["namespace", "class", "other"]


def _drop_templates(head: str) -> str:
    """Remove leading `template <...>` prefixes, whose angle brackets may nest."""
    head = head.strip()
    if not _TEMPLATE.match(head):
        return head
    depth = 0
    for at in range(head.index("<"), len(head)):
        depth += (head[at] == "<") - (head[at] == ">")
        if depth == 0:
            return _drop_templates(head[at + 1:])
    return head


def _drop_angles(head: str) -> str:
    """Remove template arguments, so `std::function<void()>` holds no parentheses."""
    if "operator" in head:
        return head
    previous = None
    while previous != head:
        previous, head = head, _ANGLES.sub("", head)
    return head


def tidy_head(head: str) -> str:
    """The head without template prefixes, attributes, `alignas`, `__declspec` and angle arguments."""
    plain = _DECL_SPEC.sub("", _ATTRIBUTE.sub("", _drop_templates(head)))
    return _drop_angles(plain).strip()


def scope_kind(head: str) -> _Kind:
    """What a `{` after this head opens: a namespace, a class, struct or union, or anything else."""
    tidy = tidy_head(head)
    if _NAMESPACE.search(tidy) and "(" not in tidy:
        return "namespace"
    if _EXTERN_BLOCK.fullmatch(tidy):
        return "namespace"
    if _CLASS_HEAD.match(tidy) and "(" not in tidy and "=" not in tidy:
        return "class"
    return "other"


def class_head(head: str) -> tuple[str, str]:
    """The class name and the access its body starts in (`class` is private, `struct` public)."""
    tidy = tidy_head(head)
    words = [w for w in _BASE_COLON.split(tidy)[0].split() if w not in _CLASS_WORDS]
    access = "private" if tidy.startswith("class") else "public"
    return (words[-1] if words else "<anonymous>", access)


def access_label(head: str) -> str | None:
    """`public`, `protected` or `private` when the head, before a `:`, ends in that word.

    Text before the word is dropped with it: Qt macros such as `Q_OBJECT` or `Q_PROPERTY(...)`
    end with no `;`, so they run into the label's head. `signals:` and `public slots:` are not
    labels, and their members keep the access before them, as XP12's checker reads them.
    """
    match = _ACCESS_LABEL.search(head)
    return match.group(1) if match else None


def is_function_head(head: str) -> bool:
    """True when a `{` after this head opens an inline body, not an initializer like `y_{2}`."""
    tidy = _TRAILING_RETURN.sub(")", tidy_head(head))
    while (shorter := _QUALIFIER.sub("", tidy)) != tidy:
        tidy = shorter
    if "(" not in tidy:
        return False
    return tidy.endswith(")") or (tidy.endswith("{}") and bool(_CTOR_INIT.search(tidy)))


def _function_name(tidy: str) -> str | None:
    for match in _NAME.finditer(tidy):
        name = re.sub(r"\s+", "", match.group(1))
        if name not in _NOT_A_NAME:
            return name
    return None


def _is_data_member(tidy: str) -> bool:
    """A member such as `int x = f();` or `void (*cb)(int);` holds parentheses and is no method."""
    if _FUNCTION_POINTER.match(tidy):
        return True
    equals, paren = tidy.find("="), tidy.find("(")
    return "operator" not in tidy and 0 <= equals < paren


def is_public_method(head: str, class_name: str) -> bool:
    """True for a member function that counts toward the class's public surface."""
    tidy = tidy_head(head)
    if _NOT_A_METHOD.match(tidy) or _DELETED.search(tidy) or "(" not in tidy:
        return False
    name = _function_name(tidy)
    if name is None or _is_data_member(tidy):
        return False
    bare = class_name.split("::")[-1]
    return name.split("::")[-1] not in {bare, "~" + bare}
