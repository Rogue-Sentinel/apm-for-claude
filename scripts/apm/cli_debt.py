"""The `apm debt` commands: record a baseline that only tightens, and check the code against it."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from apm.cli_errors import DebtError
from apm.debt import Comparison, accept, compare
from apm.debt_store import DEBT_FILE, baseline_at, current_snapshot, load_baseline, write_baseline
from apm.paths import Project
from apm.standard_config import Standard

HINT = "Run `apm debt baseline` to record these improvements"
TRACK_HINT = "Run `apm debt baseline` to start tracking the newly measured classes and files"


def _section(title: str, lines: tuple[str, ...]) -> list[str]:
    return [title, *(f"  {line}" for line in lines)] if lines else []


def render_comparison(result: Comparison) -> str:
    """Regressions first, then neutral notes (moves, newly measured), then improvements, then hints."""
    count = len(result.regressions)
    head = f"debt: {count} worse than the baseline" if count else "debt: nothing worse than the baseline"
    lines = [head, *(f"  {line}" for line in result.regressions),
             *_section("moved, not new debt:", result.moves),
             *_section("newly measured, not new debt:", result.newly_measured),
             *_section("better:", result.improvements)]
    if result.newly_measured and not result.worse:
        lines.append(TRACK_HINT)
    if result.improvements and not result.worse:
        lines.append(HINT)
    return "\n".join(lines)


def baseline(project: Project, standard: Standard, args: argparse.Namespace) -> int:
    root = project.worktree_root
    previous, current = load_baseline(root / DEBT_FILE), current_snapshot(root, standard)
    reason = (args.accept or "").strip()
    result = compare(previous, current) if previous is not None else None
    if result is not None and result.worse and not reason:
        print(render_comparison(result))
        print("The baseline was not changed. Pay the debt down, or record why with `--accept REASON`.")
        return 1
    write_baseline(root / DEBT_FILE, accept(current, previous, reason, datetime.now(timezone.utc)))
    print(f"wrote {DEBT_FILE}" + (f", accepting: {reason}" if reason else ""))
    return 0


def _new_acceptance(earlier: dict, current: dict) -> bool:
    seen = earlier.get("accepted", [])
    return any(entry not in seen for entry in current.get("accepted", []))


def _loosened(root, current: dict, ref: str) -> str:
    """Why the working-tree baseline is looser than the one at `ref` with no acceptance; else empty."""
    earlier = baseline_at(root, ref)
    if earlier is None or _new_acceptance(earlier, current):
        return ""
    result = compare(earlier, current)
    if not result.worse:
        return ""
    lines = "\n".join(f"  {line}" for line in result.regressions)
    return (f"the baseline is looser than the baseline at {ref}, with no new acceptance:\n{lines}\n"
            "A baseline may be loosened only through `apm debt baseline --accept REASON`.")


def check_result(root: Path, standard: Standard, base: str) -> tuple[bool, str]:
    """(passed, text): whether the code is no worse than the baseline, and the report to show."""
    recorded = load_baseline(root / DEBT_FILE)
    if recorded is None:
        raise DebtError(f"no baseline at {DEBT_FILE}; run `apm debt baseline` to record one")
    result = compare(recorded, current_snapshot(root, standard))
    loosened = _loosened(root, recorded, base)
    text = "\n".join([render_comparison(result), *([loosened] if loosened else [])])
    return not (result.worse or loosened), text


def check(project: Project, standard: Standard, args: argparse.Namespace) -> int:
    passed, text = check_result(project.worktree_root, standard, args.base)
    print(text)
    return 0 if passed else 1


ACTIONS = {"baseline": baseline, "check": check}


def run_debt(project: Project, standard: Standard, args: argparse.Namespace) -> int:
    return ACTIONS[args.action](project, standard, args)
