import random

from apm.debt import compare
from apm.debt_compare import KINDS, compare_items
from debt_helpers import file_metric as fm, snap

FILES = ("a.py", "b.py", "c.py")
NAMES = ("run", "it", "load")


def test_shrinking_in_place_next_to_a_same_named_function_is_not_growth() -> None:
    base = snap(fm("a.py", 90, [("run", 29), ("run", 18)]), fm("b.py", 50, [("run", 30)]))
    current = snap(fm("a.py", 90, [("run", 24), ("run", 10)]), fm("b.py", 50, [("run", 29)]))

    result = compare(base, current)

    assert not result.worse, result.regressions
    assert not any(line.startswith("grew") for line in result.regressions)


def test_a_name_swapping_sizes_across_two_files_passes_as_two_moves() -> None:
    base = snap(fm("a.py", 50, [("f", 20)]), fm("b.py", 50, [("f", 30)]))
    current = snap(fm("a.py", 50, [("f", 30)]), fm("b.py", 50, [("f", 20)]))

    result = compare(base, current)

    assert not result.worse and len(result.moves) == 2


def test_a_larger_same_named_function_deleted_elsewhere_can_absorb_growth() -> None:
    base = snap(fm("a.py", 50, [("f", 30)]), fm("b.py", 50, [("f", 20)]))
    current = snap(fm("a.py", 10), fm("b.py", 50, [("f", 25)]))

    result = compare(base, current)

    assert not result.worse
    assert "total fell: excess_function_lines 20 → 10" in result.improvements


def _items(rng: random.Random) -> list[tuple[str, str, int]]:
    return [(rng.choice(FILES), rng.choice(NAMES), rng.randint(10, 40)) for _ in range(rng.randint(1, 9))]


def _evolve(rng: random.Random, items: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Moves, shrinks and deletions: every survivor has a distinct original at least as large."""
    kept = [(rng.choice(FILES) if rng.random() < 0.4 else f,
             name, rng.randint(1, n) if rng.random() < 0.5 else n)
            for f, name, n in items if rng.random() < 0.9]
    rng.shuffle(kept)
    return kept


def _report(items: list[tuple[str, str, int]]) -> dict:
    files = [fm(path, 100, [(name, n) for p, name, n in items if p == path]) for path in FILES]
    return snap(*files)


def test_random_moves_reorders_and_shrinks_are_never_regressions() -> None:
    rng = random.Random(20261017)
    for trial in range(400):
        items = _items(rng)
        base, current = _report(items), _report(_evolve(rng, items))

        result = compare(base, current)
        found = [line for kind in KINDS for line in compare_items(base, current, kind).regressions]

        assert not result.worse and not found, (trial, items, result.regressions)


def test_growing_a_uniquely_named_function_is_always_caught() -> None:
    rng = random.Random(7)
    for trial in range(400):
        start = rng.randint(16, 40)
        items = _items(rng) + [(rng.choice(FILES), "unique", start)]
        others = [item for item in _evolve(rng, items) if item[1] != "unique"]
        grown = others + [(rng.choice(FILES), "unique", start + rng.randint(1, 10))]
        base, current = _report(items), _report(grown)

        found = compare_items(base, current, KINDS[0]).regressions

        assert any("unique" in line for line in found), (trial, items, grown)
