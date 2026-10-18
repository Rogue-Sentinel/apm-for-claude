"""Read a plan's structural acceptance criteria and the documents they promise."""
from __future__ import annotations

import re
from collections.abc import Sequence

HEADING = "## Structural acceptance criteria"
_BACKTICKED = re.compile(r"`([^`]+)`")


def _section(plan_text: str) -> list[str]:
    lines = plan_text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(HEADING)), None)
    if start is None:
        return []
    rest = lines[start + 1:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return rest[:end]


def structural_criteria(plan_text: str) -> list[str]:
    """The bullet items under the first `## Structural acceptance criteria` heading, up to the next `## `.

    A line that continues a bullet (indented, not itself a bullet) is joined to it with a space.
    """
    items: list[str] = []
    for line in _section(plan_text):
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif items and line.strip():
            items[-1] += " " + line.strip()
    return items


def _is_promise(token: str) -> bool:
    return token.endswith(".md") and not any(mark in token for mark in " *<")


def promised_paths(criteria: Sequence[str]) -> list[str]:
    """The backticked tokens ending in `.md` with no space, `*` or `<`, once each, in order."""
    found = [token for text in criteria for token in _BACKTICKED.findall(text) if _is_promise(token)]
    return list(dict.fromkeys(found))
