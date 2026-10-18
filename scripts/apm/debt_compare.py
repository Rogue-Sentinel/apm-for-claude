"""Compare two debt snapshots, one section at a time. Each section returns Findings."""
from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Mapping
from typing import NamedTuple

from apm.standard_config import DEFAULT_EXCLUDES

Items = Mapping[str, int]
Item = tuple[str, str, int]  # (same-file group, key, number)


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


def _items(items: Items, group_of: Callable[[str], str]) -> list[Item]:
    return sorted(((group_of(key), key, number) for key, number in items.items()),
                  key=lambda item: (item[0], -item[2], item[1]))


def _match(base: list[Item], current: list[Item], fits: Callable[[Item, Item], bool]):
    """Match each current item (largest first) to the smallest base item that fits; use each once."""
    pool, matched, left = list(base), [], []
    for now in sorted(current, key=lambda item: (-item[2], item[1])):
        options = [old for old in pool if fits(old, now)]
        if not options:
            left.append(now)
            continue
        old = min(options, key=lambda item: (item[2], item[1]))
        pool.remove(old)
        matched.append((old, now))
    return matched, pool, left


def _pair_rest(base: list[Item], current: list[Item]):
    """Inside each group, pair the largest with the largest; what has no partner is new or gone."""
    paired, new, gone = [], [], []
    for group in sorted({item[0] for item in base + current}):
        old = sorted((i for i in base if i[0] == group), key=lambda i: (-i[2], i[1]))
        now = sorted((i for i in current if i[0] == group), key=lambda i: (-i[2], i[1]))
        paired += list(zip(old, now))
        gone += old[len(now):]
        new += now[len(old):]
    return paired, new, gone


def _same_place(old: Item, now: Item) -> bool:
    return old[0] == now[0] and old[2] == now[2]


def _same_bare(bare_of: Callable[[str], str], numbers: Callable[[int, int], bool]):
    """A fit test: the same bare name, and old and new numbers that `numbers` accepts."""
    return lambda old, now: bare_of(old[1]) == bare_of(now[1]) and numbers(old[2], now[2])


def _changes(paired: list[tuple[Item, Item]]) -> Findings:
    def name(old: Item, now: Item) -> str:
        return now[1] if old[1] == now[1] else f"{now[1]} (was {old[1]})"
    grew = [f"grew: {name(o, n)} {o[2]} → {n[2]}" for o, n in paired if n[2] > o[2]]
    shrank = [f"shrank: {name(o, n)} {o[2]} → {n[2]}" for o, n in paired if n[2] < o[2]]
    return Findings(grew, shrank, [])


def _fixed(gone: list[Item], unit: str, present: Items) -> list[str]:
    plain = "fixed: {} ({} {})"
    reused = "fixed: {} (was {} {}; the name is now numbered differently)"
    return [(reused if key in present else plain).format(key, n, unit) for _, key, n in gone]


def compare_items(base: Mapping, current: Mapping, kind: tuple[str, str, str]) -> Findings:
    section, label, unit = kind
    group_of, bare_of = _group_of(section), _bare_of(section)
    now_items = current.get(section, {})
    old, now = _items(base.get(section, {}), group_of), _items(now_items, group_of)
    _, old, now = _match(old, now, _same_place)  # unchanged, whatever the numbering
    exact, old, now = _match(old, now, _same_bare(bare_of, lambda o, n: o == n))
    paired, new, gone = _pair_rest(old, now)
    later, gone, new = _match(gone, new, _same_bare(bare_of, lambda o, n: o >= n))
    grew, shrank, _ = _changes(paired)
    return Findings(
        grew + [f"new {label}: {key} ({n} {unit})" for _, key, n in new],
        shrank + _fixed(gone, unit, now_items),
        [f"moved: {o[1]} → {n[1]} ({n[2]} {unit})" for o, n in exact + later],
    )


def _numbers(base: Items, current: Items, rose: str, fell: str, prefix: str = "") -> Findings:
    """A number that rose is a regression; one that fell is an improvement. Names in both only."""
    both = [name for name in base if name in current]
    regressions = [f"{rose}: {prefix}{n} {base[n]} → {current[n]}" for n in both if current[n] > base[n]]
    improvements = [f"{fell}: {prefix}{n} {base[n]} → {current[n]}" for n in both if current[n] < base[n]]
    return Findings(regressions, improvements, [])


def compare_limits(base: Mapping, current: Mapping) -> Findings:
    old, now = base.get("limits", {}), current.get("limits", {})
    missing = [f"limit missing: {name}" for name in sorted(old.keys() ^ now.keys())]
    found = _numbers(old, now, "limit loosened", "limit tightened")
    return Findings(missing + found.regressions, found.improvements, [])


def _scope_of(snapshot: Mapping) -> tuple[set[str], set[str]]:
    scope = snapshot.get("scope") or {"include": [], "exclude": list(DEFAULT_EXCLUDES)}
    return set(scope.get("include", [])), set(scope.get("exclude", []))


def compare_scope(base: Mapping, current: Mapping) -> Findings:
    """Measuring less than the base did hides debt. An empty include list means every file."""
    (old_in, old_out), (now_in, now_out) = _scope_of(base), _scope_of(current)
    lines = [f"now excludes {glob}" for glob in sorted(now_out - old_out)]
    if now_in and not old_in:
        lines.append("include list is no longer empty (it used to mean every file)")
    elif now_in:
        lines += [f"no longer includes {glob}" for glob in sorted(old_in - now_in)]
    return Findings([f"measurement scope narrowed: {line}" for line in lines], [], [])


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
