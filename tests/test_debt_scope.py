from apm.debt import compare
from apm.standard_config import DEFAULT_EXCLUDES, MetricsConfig
from debt_helpers import file_metric as fm, snap


def _scoped(include=(), exclude=DEFAULT_EXCLUDES, builtin=True) -> dict:
    config = MetricsConfig(include=tuple(include), exclude=tuple(exclude), builtin=builtin)
    return snap(fm("a.py"), scope=config)


def _narrowed(base: dict, current: dict) -> bool:
    return any(r.startswith("measurement scope narrowed") for r in compare(base, current).regressions)


def test_snapshot_records_the_scope() -> None:
    snapshot = _scoped(include=["src/**"], exclude=["**/gen/**"])

    assert snapshot["scope"] == {"include": ["src/**"], "exclude": ["**/gen/**"], "builtin": True}


def test_snapshot_without_a_scope_records_the_default_one() -> None:
    assert snap(fm("a.py"))["scope"] == {"include": [], "exclude": list(DEFAULT_EXCLUDES), "builtin": True}


def test_a_newly_excluded_glob_narrows_the_scope() -> None:
    base = _scoped()
    current = _scoped(exclude=(*DEFAULT_EXCLUDES, "legacy/**"))

    assert _narrowed(base, current)
    assert "measurement scope narrowed: now excludes legacy/**" in compare(base, current).regressions


def test_going_from_all_files_to_an_include_list_narrows_the_scope() -> None:
    assert _narrowed(_scoped(), _scoped(include=["src/**"]))


def test_dropping_an_include_glob_narrows_the_scope() -> None:
    assert _narrowed(_scoped(include=["src/**", "lib/**"]), _scoped(include=["src/**"]))


def test_widening_the_scope_is_fine() -> None:
    base = _scoped(include=["src/**"], exclude=[*DEFAULT_EXCLUDES, "legacy/**"])

    assert not _narrowed(base, _scoped(include=["src/**", "lib/**"], exclude=[*DEFAULT_EXCLUDES, "legacy/**"]))
    assert not _narrowed(base, _scoped(include=["src/**"]))
    assert not _narrowed(base, _scoped())


def test_a_snapshot_without_a_scope_key_counts_as_the_default_scope() -> None:
    base = {k: v for k, v in _scoped().items() if k != "scope"}

    assert not _narrowed(base, _scoped())
    assert _narrowed(_scoped(include=["src/**"]), base) is False


def test_turning_the_built_in_metrics_off_narrows_the_scope() -> None:
    result = compare(_scoped(), _scoped(builtin=False))

    assert "measurement scope narrowed: built-in metrics turned off" in result.regressions


def test_turning_the_built_in_metrics_on_is_fine() -> None:
    assert not _narrowed(_scoped(builtin=False), _scoped())
    assert not _narrowed({**_scoped(), "scope": {"include": [], "exclude": list(DEFAULT_EXCLUDES)}}, _scoped())
