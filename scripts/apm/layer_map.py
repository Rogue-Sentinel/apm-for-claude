"""Find files that the layer map assigns to more than one layer."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

from apm.guard_paths import matches_any


def layer_overlaps(paths: Sequence[str], layers: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str]]:
    """(path, first layer, second layer) for each path that two layers' globs both match, sorted by path."""
    found = []
    for path in sorted(paths):
        owners = [layer["name"] for layer in layers if matches_any(layer["paths"], path)]
        found.extend((path, first, second) for first, second in combinations(owners, 2))
    return found
