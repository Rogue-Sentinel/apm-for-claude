from pathlib import Path

import pytest

from apm.metrics_ref import RefError, measure_at_ref, ref_files
from apm.standard_config import MetricsConfig
from conftest import run_git


def _func(lines: int) -> str:
    return "def big():\n" + "".join(f"    x{i} = {i}\n" for i in range(lines))


def _commit(repo: Path, name: str, text: str) -> None:
    (repo / name).write_text(text, encoding="utf-8")
    run_git(repo, "add", name)
    run_git(repo, "commit", "-m", f"add {name}")


def test_measure_at_ref_ignores_working_tree(git_repo: Path) -> None:
    _commit(git_repo, "big.py", _func(20))
    (git_repo / "big.py").write_text(_func(2), encoding="utf-8")

    report = measure_at_ref(git_repo, "HEAD", MetricsConfig())

    assert [fn.lines for fn in report.files[0].functions] == [20]


def test_measure_at_ref_only_measures_the_given_paths(git_repo: Path) -> None:
    _commit(git_repo, "a.py", _func(3))
    (git_repo / "sub").mkdir()
    _commit(git_repo, "sub/b.py", _func(4))

    report = measure_at_ref(git_repo, "HEAD", MetricsConfig(), ["sub"])

    assert [f.path for f in report.files] == ["sub/b.py"]


def test_ref_files_lists_the_files_committed_at_the_ref(git_repo: Path) -> None:
    _commit(git_repo, "a.py", _func(3))
    (git_repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")

    assert ref_files(git_repo, "HEAD") == ["a.py"]


def test_a_non_ascii_file_name_is_measured_at_the_ref(git_repo: Path) -> None:
    _commit(git_repo, "café.py", _func(20))

    report = measure_at_ref(git_repo, "HEAD", MetricsConfig())

    assert [f.path for f in report.files] == ["café.py"]


def test_unknown_ref_raises(git_repo: Path) -> None:
    with pytest.raises(RefError, match="unknown ref: nope"):
        measure_at_ref(git_repo, "nope", MetricsConfig())


def test_unknown_ref_raises_from_ref_files(git_repo: Path) -> None:
    with pytest.raises(RefError, match="unknown ref: nope"):
        ref_files(git_repo, "nope")


def test_bytes_that_are_not_utf8_are_replaced_not_fatal(git_repo: Path) -> None:
    (git_repo / "odd.py").write_bytes(b"x = '\xff'\n")
    run_git(git_repo, "add", "odd.py")
    run_git(git_repo, "commit", "-m", "odd")

    report = measure_at_ref(git_repo, "HEAD", MetricsConfig())

    assert [f.path for f in report.files] == ["odd.py"]
