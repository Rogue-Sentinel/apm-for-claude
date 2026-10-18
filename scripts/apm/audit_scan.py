"""Read-only scan of a repository for `apm audit`: its mode, its in-flight work and its open debt issues.

Worktrees and branches are reported, never removed. Anything the scan cannot read becomes a note.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from apm.github import GitHubError, list_open_issues
from apm.metrics import Report
from apm.metrics_lang import language_for
from apm.metrics_ref import RefError, measure_at_ref, ref_files
from apm.standard_config import MetricsConfig
from apm.state_store import STATE_BRANCH

Run = Callable[..., subprocess.CompletedProcess]
BASES = ("origin/main", "main", "origin/master", "master")
DEBT_LABELS = ("debt", "tech-debt")
_DOC = re.compile(r"(?:^|/)(plans|specs)/[^/]+\.md$")
_DOC_KINDS: dict[str, Literal["plan", "spec"]] = {"plans": "plan", "specs": "spec"}
_REF_PREFIXES = (("refs/heads/", "local"), ("refs/remotes/origin/", "origin"))
FETCH_TIMEOUT = 60


@dataclass(frozen=True)
class InFlight:
    id: str
    kind: Literal["branch", "worktree", "plan", "spec", "issue"]
    title: str
    detail: str


@dataclass(frozen=True)
class Audit:
    mode: Literal["existing", "fresh"]
    base: str
    notes: tuple[str, ...]
    in_flight: tuple[InFlight, ...]
    debt_issues: tuple[int, ...]


def _git(root: Path, run: Run, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=cwd or root, capture_output=True, text=True, encoding="utf-8")


def _exists(root: Path, ref: str, run: Run) -> bool:
    return _git(root, run, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0


def _fetch(root: Path, run: Run) -> subprocess.CompletedProcess:
    """Fetch without ever prompting for credentials, and give up after a minute."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return run(["git", "fetch", "origin"], cwd=root, capture_output=True, text=True, encoding="utf-8",
               env=env, timeout=FETCH_TIMEOUT)


def _fetch_note(root: Path, run: Run) -> list[str]:
    try:
        done = _fetch(root, run)
    except subprocess.TimeoutExpired:
        return [f"could not fetch origin: timed out after {FETCH_TIMEOUT} seconds"]
    if done.returncode == 0:
        return []
    reason = (done.stderr or "").strip().splitlines()
    return [f"could not fetch origin: {reason[0] if reason else 'git fetch failed'}"]


def resolve_base(root: Path, base: str | None, run: Run) -> tuple[str, list[str]]:
    """The ref to compare against, and notes about what was not possible."""
    if not _exists(root, "HEAD", run):
        return "", ["no commits yet"]
    notes = _fetch_note(root, run)
    if base is not None:
        if not _exists(root, base, run):
            raise RefError(f"unknown ref: {base}")
        return base, notes
    found = next((ref for ref in BASES if _exists(root, ref, run)), None)
    if found is None:
        return "HEAD", [*notes, "no main or master branch found; compared against HEAD"]
    return found, notes


def detect_mode(files: Sequence[str]) -> Literal["existing", "fresh"]:
    return "existing" if any(language_for(name) for name in files) else "fresh"


def _branch_refs(root: Path, run: Run) -> dict[str, dict[str, str]]:
    listed = _git(root, run, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes/origin")
    found: dict[str, dict[str, str]] = {}
    for ref in listed.stdout.splitlines():
        for prefix, where in _REF_PREFIXES:
            name = ref.removeprefix(prefix)
            if ref.startswith(prefix) and name != "HEAD":
                found.setdefault(name, {})[where] = ref
    return found


def _ahead(root: Path, base: str, ref: str, run: Run) -> int:
    done = _git(root, run, "rev-list", "--count", f"{base}..{ref}")
    return int(done.stdout) if done.returncode == 0 and done.stdout.strip().isdigit() else 0


def _branch_detail(ahead: int, where: dict[str, str]) -> str:
    if "local" in where and "origin" in where:
        return f"{ahead} ahead, also on origin"
    return f"{ahead} ahead" if "local" in where else f"{ahead} ahead, only on origin"


def scan_branches(root: Path, base: str, run: Run) -> list[InFlight]:
    """Local and origin branches with commits that `base` lacks; a local and a remote copy are one item."""
    items = []
    for name, where in sorted(_branch_refs(root, run).items()):
        ahead = max(_ahead(root, base, ref, run) for ref in where.values())
        if ahead and name not in (base.removeprefix("origin/"), STATE_BRANCH):
            items.append(InFlight(f"branch:{name}", "branch", name, _branch_detail(ahead, where)))
    return items


def _worktree_blocks(root: Path, run: Run) -> list[dict[str, str]]:
    text = _git(root, run, "worktree", "list", "--porcelain").stdout
    blocks = [block.splitlines() for block in text.strip().split("\n\n") if block.strip()]
    return [dict(line.partition(" ")[::2] for line in block) for block in blocks]


def _same_folder(first: str, second: Path) -> bool:
    return Path(first).resolve() == second.resolve()


def _worktree_detail(root: Path, path: str, run: Run) -> str:
    if not Path(path).is_dir():
        return "folder missing"
    changes = _git(root, run, "status", "--porcelain", cwd=Path(path)).stdout.strip()
    return "uncommitted changes" if changes else "clean"


def _is_work(block: dict[str, str], root: Path, skipped: tuple[str, ...]) -> bool:
    path = block.get("worktree", "")
    branch = block.get("branch", "").removeprefix("refs/heads/")
    return bool(path) and "bare" not in block and not _same_folder(path, root) and branch not in skipped


def scan_worktrees(root: Path, run: Run, base: str = "") -> list[InFlight]:
    """Every worktree but the current one, the base branch's and APM's state, with its state. Nothing is removed."""
    skipped = (STATE_BRANCH, base.removeprefix("origin/")) if base else (STATE_BRANCH,)
    items = []
    for block in (block for block in _worktree_blocks(root, run) if _is_work(block, root, skipped)):
        path, title = block["worktree"], block.get("branch", "detached").removeprefix("refs/heads/")
        items.append(InFlight(f"worktree:{path}", "worktree", title, _worktree_detail(root, path, run)))
    return items


def scan_docs(files: Sequence[str]) -> list[InFlight]:
    """The tracked plan and spec documents."""
    found = sorted((_DOC_KINDS[match.group(1)], name) for name in files if (match := _DOC.search(name)))
    return [InFlight(f"{kind}:{name}", kind, Path(name).stem, f"tracked {kind}") for kind, name in found]


def _is_debt(issue: dict) -> bool:
    labels = {label.lower() for label in issue["labels"]}
    return issue["title"].lower().startswith("[debt]") or bool(labels & set(DEBT_LABELS))


def scan_issues(root: Path, run: Run) -> tuple[list[InFlight], list[int], list[str]]:
    """Open issues as in-flight work, the debt issues apart, and a note when GitHub cannot be read."""
    try:
        issues = list_open_issues(root, run)
    except (GitHubError, ValueError, KeyError, TypeError) as err:
        return [], [], [f"open issues not read: {str(err) or 'gh failed'}"]
    debt = [issue["number"] for issue in issues if _is_debt(issue)]
    open_work = [
        InFlight(f"issue:{i['number']}", "issue", i["title"], ", ".join(i["labels"]) or "no labels")
        for i in issues if not _is_debt(i)
    ]
    return open_work, debt, []


def _in_flight(root: Path, base: str, files: Sequence[str], run: Run) -> list[InFlight]:
    branches = scan_branches(root, base, run) if base else []
    return [*branches, *scan_worktrees(root, run, base), *scan_docs(files)]


def audit(
    root: Path, base: str | None = None, run: Run = subprocess.run, config: MetricsConfig = MetricsConfig(),
) -> tuple[Audit, Report]:
    """Scan `root`; the report is measured at the base, so the working tree's edits do not count."""
    resolved, notes = resolve_base(root, base, run)
    files = ref_files(root, resolved, run) if resolved else []
    issues, debt, issue_notes = scan_issues(root, run)
    found = Audit(
        detect_mode(files), resolved, tuple([*notes, *issue_notes]),
        tuple([*_in_flight(root, resolved, files, run), *issues]), tuple(debt),
    )
    report = measure_at_ref(root, resolved, config, run=run) if resolved else Report(())
    return found, report
