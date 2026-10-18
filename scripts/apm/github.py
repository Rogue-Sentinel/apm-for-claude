"""Talking to GitHub through the `gh` CLI. Every call goes through an injected `run`, so tests need no network."""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_DIR = ".github/ISSUE_TEMPLATE"
TEMPLATE_SUFFIXES = (".yml", ".yaml", ".md")


class GitHubError(Exception):
    """`gh` is missing, or GitHub refused the call."""


@dataclass(frozen=True)
class IssueTemplate:
    name: str
    path: str
    labels: tuple[str, ...]


def run_gh(
    args: Sequence[str], root: Path, run: Callable = subprocess.run, stdin: str | None = None
) -> str:
    """Run `gh` in `root`; return its stdout, or raise GitHubError."""
    try:
        done = run(
            ["gh", *args], cwd=root, input=stdin, capture_output=True, text=True, encoding="utf-8",
        )
    except FileNotFoundError as err:
        raise GitHubError("gh is not installed") from err
    if done.returncode != 0:
        raise GitHubError((done.stderr or "").strip())
    return done.stdout


def create_issue(
    root: Path, title: str, body: str, labels: Sequence[str], run: Callable = subprocess.run
) -> tuple[int, str]:
    """File an issue with the body on stdin; return its number and URL."""
    flags = [part for label in labels for part in ("--label", label)]
    printed = run_gh(["issue", "create", "--title", title, "--body-file", "-", *flags], root, run, stdin=body)
    found = re.search(r"https?://\S+/issues/(\d+)", printed)
    if found is None:
        raise GitHubError(f"gh printed no issue URL: {printed.strip()!r}")
    return int(found.group(1)), found.group(0)


def close_issue(root: Path, number: int, comment: str, run: Callable = subprocess.run) -> None:
    run_gh(["issue", "close", str(number), "--comment", comment], root, run)


def list_open_issues(root: Path, run: Callable = subprocess.run) -> list[dict]:
    printed = run_gh(
        ["issue", "list", "--state", "open", "--limit", "500", "--json", "number,title,labels"], root, run,
    )
    return [
        {"number": item["number"], "title": item["title"], "labels": [lab["name"] for lab in item["labels"]]}
        for item in json.loads(printed or "[]")
    ]


def _unquote(text: str) -> str:
    text = text.strip()
    return text[1:-1] if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"" else text


def _inline(value: str) -> list[str]:
    """`[a, b]`, `a, b` or `a` as a list of labels."""
    inner = value.strip().removeprefix("[").removesuffix("]")
    return [_unquote(part) for part in inner.split(",") if part.strip()]


def _block(lines: Sequence[str]) -> list[str]:
    """The `- item` lines that follow a bare `labels:`, up to the first line that is not one."""
    items: list[str] = []
    for line in lines:
        if line.strip().startswith("- "):
            items.append(_unquote(line.strip()[2:]))
        elif line.strip():
            break
    return items


def _read_keys(lines: Sequence[str]) -> tuple[str | None, list[str]]:
    """The top-level `name:` and `labels:` of a template, read line by line (no YAML library)."""
    name: str | None = None
    labels: list[str] = []
    for index, line in enumerate(lines):
        key, colon, value = line.partition(":")
        if line[:1].isspace() or not colon:
            continue
        if key == "name":
            name = _unquote(value)
        elif key == "labels":
            labels = _inline(value) if value.strip() else _block(lines[index + 1:])
    return name, labels


def _front_matter(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), len(lines))
    return lines[1:end]


def _template_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return _front_matter(text) if path.suffix == ".md" else text.splitlines()


def issue_templates(root: Path) -> list[IssueTemplate]:
    """The issue templates under .github/ISSUE_TEMPLATE, by file name; config.yml is not a template."""
    folder = root / TEMPLATE_DIR
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.iterdir()):
        if path.suffix not in TEMPLATE_SUFFIXES or path.stem == "config":
            continue
        name, labels = _read_keys(_template_lines(path))
        found.append(IssueTemplate(name or path.stem, f"{TEMPLATE_DIR}/{path.name}", tuple(labels)))
    return found
