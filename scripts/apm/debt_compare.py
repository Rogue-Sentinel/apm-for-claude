"""Compare two debt snapshots, one section at a time. Each section returns Findings."""
from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Mapping
from typing import NamedTuple

Items = Mapping[str, int]
Entry = tuple[str, int]


class Findings(NamedTuple):
    regressions: list[str]
    improvements: list[str]
    moves: list[str]


# (snapshot section, name of a new item, unit of its number)
KINDS = (
    ("functions", "over-limit function", "lines"),
    ("files", "over-limit file", "lines"),
    ("classes", "wide class", "public methods"),
)


def _bare_name(key: str) -> str:
    return re.sub(r"#\d+$", "", key.split("::", 1)[-1])


def _group_of(section: str) -> Callable[[str], str]:
    """The same-file group of a key: all the items that may renumber among themselves."""
    if section == "files":
        return lambda key: key
    return lambda key: f"{key.split('::', 1)[0]}::{_bare_name(key)}"


def _bare_of(section: str) -> Callable[[str], str]:
    return posixpath.basename if section == "files" else _bare_name


def _by_group(items: Items, group_of: Callable[[str], str]) -> dict[str, list[Entry]]:
    groups: dict[str, list[Entry]] = {}
    for key, number in items.items():
        groups.setdefault(group_of(key), []).append((key, number))
    return {group: sorted(entries, key=lambda e: -e[1]) for group, entries in groups.items()}


def _pair(base: Items, current: Items, group_of: Callable[[str], str]):
    """Pair the largest with the largest inside each group, so renumbering never matters."""
    base_groups, current_groups = _by_group(base, group_of), _by_group(current, group_of)
    paired: list[tuple[str, int, int]] = []
    new: list[Entry] = []
    gone: list[Entry] = []
    for group in sorted(base_groups.keys() | current_groups.keys()):
        old, now = base_groups.get(group, []), current_groups.get(group, [])
        paired += [(now[i][0], old[i][1], now[i][1]) for i in range(min(len(old), len(now)))]
        gone += old[len(now):]
        new += now[len(old):]
    return paired, new, gone


def _match_moves(new: list[Entry], gone: list[Entry], bare_of: Callable[[str], str]):
    """Match each new item to a departed one of the same bare name and no smaller a number."""
    pool, moves, unmatched = list(gone), [], []
    for key, number in sorted(new, key=lambda e: (-e[1], e[0])):
        fits = [g for g in pool if bare_of(g[0]) == bare_of(key) and g[1] >= number]
        if not fits:
            unmatched.append((key, number))
            continue
        old = min(fits, key=lambda g: (g[1], g[0]))
        pool.remove(old)
        moves.append((old[0], key, number))
    return moves, unmatched, pool


def _changes(paired: list[tuple[str, int, int]]) -> Findings:
    grew = [f"grew: {key} {old} → {now}" for key, old, now in paired if now > old]
    shrank = [f"shrank: {key} {old} → {now}" for key, old, now in paired if now < old]
    return Findings(grew, shrank, [])


def compare_items(base: Mapping, current: Mapping, kind: tuple[str, str, str]) -> Findings:
    section, label, unit = kind
    paired, new, gone = _pair(base.get(section, {}), current.get(section, {}), _group_of(section))
    moves, new, gone = _match_moves(new, gone, _bare_of(section))
    grew, shrank, _ = _changes(paired)
    return Findings(
        grew + [f"new {label}: {key} ({n} {unit})" for key, n in new],
        shrank + [f"fixed: {key} ({n} {unit})" for key, n in gone],
        [f"moved: {old} → {key} ({n} {unit})" for old, key, n in moves],
    )


def _numbers(base: Items, current: Items, rose: str, fell: str, prefix: str = "") -> Findings:
    """A number that rose is a regression; one that fell is an improvement. Names in both only."""
    both = [name for name in base if name in current]
    regressions = [f"{rose}: {prefix}{n} {base[n]} → {current[n]}" for n in both if current[n] > base[n]]
    improvements = [f"{fell}: {prefix}{n} {base[n]} → {current[n]}" for n in both if current[n] < base[n]]
    return Findings(regressions, improvements, [])


def compare_limits(base: Mapping, current: Mapping) -> Findings:
    return _numbers(base.get("limits", {}), current.get("limits", {}), "limit loosened", "limit tightened")


def compare_totals(base: Mapping, current: Mapping) -> Findings:
    now = current.get("totals", {})
    old = {name: 0 for name in now} | dict(base.get("totals", {}))
    return _numbers(old, now, "total rose", "total fell")


def compare_unmeasured(base: Mapping, current: Mapping) -> Findings:
    old, now = set(base.get("unmeasured", [])), set(current.get("unmeasured", []))
    return Findings([f"now unmeasured: {path}" for path in sorted(now - old)],
                    [f"measures again: {path}" for path in sorted(old - now)], [])


def _one_source(name: str, old: Items, now: Mapping | None) -> Findings:
    if now is None:
        return Findings([f"source disappeared: {name}"], [], [])
    lost = [f"source metric disappeared: {name}.{metric}" for metric in old if metric not in now]
    found = _numbers(old, now, "source metric rose", "source metric fell", f"{name}.")
    return Findings(lost + found.regressions, found.improvements, [])


def compare_sources(base: Mapping, current: Mapping) -> Findings:
    now = current.get("sources", {})
    return merge([_one_source(name, old, now.get(name)) for name, old in base.get("sources", {}).items()])


def merge(parts: list[Findings]) -> Findings:
    return Findings(*([line for part in parts for line in part[i]] for i in range(3)))
