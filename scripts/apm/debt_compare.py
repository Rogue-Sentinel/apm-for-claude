"""Compare two debt snapshots, one section at a time. Each section returns Findings."""
from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Mapping
from typing import NamedTuple

from apm.standard_config import DEFAULT_EXCLUDES

Items = Mapping[str, int]


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


def _bare_of(section: str) -> Callable[[str], str]:
    return posixpath.basename if section == "files" else _bare_name


Entry = tuple[str, int]  # (key, number)


def _file_of(section: str) -> Callable[[str], str]:
    return (lambda key: key) if section == "files" else (lambda key: key.split("::", 1)[0])


def _by_bare(items: Items, bare_of: Callable[[str], str]) -> dict[str, list[Entry]]:
    groups: dict[str, list[Entry]] = {}
    for key, number in items.items():
        groups.setdefault(bare_of(key), []).append((key, number))
    return groups


def _rank(now: Entry, file_of: Callable[[str], str]) -> Callable[[Entry], tuple]:
    """The smallest base item that fits, then one from the same file, then the same key."""
    return lambda old: (old[1], file_of(old[0]) != file_of(now[0]), old[0] != now[0], old[0])


def _greedy(base: list[Entry], current: list[Entry], file_of: Callable[[str], str]):
    """Give each current item (largest first) the smallest unused base item that is no smaller."""
    pool, pairs, left = list(base), [], []
    for now in sorted(current, key=lambda entry: (-entry[1], entry[0])):
        fits = [old for old in pool if old[1] >= now[1]]
        if not fits:
            left.append(now)
            continue
        old = min(fits, key=_rank(now, file_of))
        pool.remove(old)
        pairs.append((old, now))
    return pairs, left, pool


def _grew(left: list[Entry], pool: list[Entry], file_of: Callable[[str], str]):
    """Every leftover base item is smaller than every leftover current item of its name."""
    grew, new = [], []
    for now in left:
        same = [old for old in pool if file_of(old[0]) == file_of(now[0])]
        if not same:
            new.append(now)
            continue
        old = max(same, key=lambda entry: (entry[1], entry[0] == now[0], entry[0]))
        pool.remove(old)
        grew.append((old, now))
    return grew, new, pool


def _match_section(base: Items, current: Items, section: str):
    """One greedy pass per bare name across all files: pairs, grown, new and fixed items."""
    bare_of, file_of = _bare_of(section), _file_of(section)
    old_groups, new_groups = _by_bare(base, bare_of), _by_bare(current, bare_of)
    pairs, grew, new, fixed = [], [], [], []
    for bare in sorted(old_groups.keys() | new_groups.keys()):
        found, left, pool = _greedy(old_groups.get(bare, []), new_groups.get(bare, []), file_of)
        more_grew, more_new, pool = _grew(left, pool, file_of)
        pairs += found
        grew += more_grew
        new += more_new
        fixed += pool
    return pairs, grew, new, fixed


def _name(old: Entry, now: Entry) -> str:
    return now[0] if old[0] == now[0] else f"{now[0]} (was {old[0]})"


def _paired(pairs: list, file_of: Callable[[str], str], unit: str):
    """A pair across files is a move. In one file only a smaller number is reported."""
    shrank, moves = [], []
    for old, now in pairs:
        if file_of(old[0]) != file_of(now[0]):
            moves.append(f"moved: {old[0]} → {now[0]} ({now[1]} {unit})")
        elif now[1] < old[1]:
            shrank.append(f"shrank: {_name(old, now)} {old[1]} → {now[1]}")
    return shrank, moves


def _fixed(gone: list[Entry], unit: str, present: Items) -> list[str]:
    plain = "fixed: {} ({} {})"
    reused = "fixed: {} (was {} {}; the name is now numbered differently)"
    return [(reused if key in present else plain).format(key, n, unit) for key, n in gone]


def compare_items(base: Mapping, current: Mapping, kind: tuple[str, str, str]) -> Findings:
    section, label, unit = kind
    now_items = current.get(section, {})
    pairs, grew, new, fixed = _match_section(base.get(section, {}), now_items, section)
    shrank, moves = _paired(pairs, _file_of(section), unit)
    return Findings(
        [f"grew: {_name(o, n)} {o[1]} → {n[1]}" for o, n in grew]
        + [f"new {label}: {key} ({n} {unit})" for key, n in new],
        shrank + _fixed(fixed, unit, now_items),
        moves,
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
