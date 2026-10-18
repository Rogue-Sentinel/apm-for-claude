import json
from pathlib import Path

import pytest

import apm_cli

WIDE_HEADER = "class Database {\npublic:\n" + "".join(f"    void m{i}();\n" for i in range(7)) + "};\n"


@pytest.fixture
def headers(git_repo: Path, monkeypatch) -> Path:
    (git_repo / "database.h").write_text(WIDE_HEADER, encoding="utf-8")
    (git_repo / "database.hpp").write_text(WIDE_HEADER, encoding="utf-8")
    monkeypatch.chdir(git_repo)
    return git_repo


def _file_entry(capsys, name: str) -> dict:
    data = json.loads(capsys.readouterr().out)
    return next(f for f in data["files"] if f["path"] == name)


@pytest.mark.parametrize("name", ["database.h", "database.hpp"])
def test_metrics_counts_the_public_methods_of_a_cpp_class(headers: Path, capsys, name: str) -> None:
    assert apm_cli.main(["metrics", "--json"]) == 0

    entry = _file_entry(capsys, name)
    assert entry["classes"] == [{"name": "Database", "line": 1, "public_methods": 7}]


def test_a_h_header_holding_cpp_is_measured_as_cpp(headers: Path, capsys) -> None:
    assert apm_cli.main(["metrics", "--json"]) == 0

    assert _file_entry(capsys, "database.h")["language"] == "C++"


def test_metrics_text_flags_both_headers(headers: Path, capsys) -> None:
    assert apm_cli.main(["metrics"]) == 0

    out = capsys.readouterr().out
    assert "Review flags -- classes with 7+ public methods: 2" in out
    assert "database.h:1 Database -- 7 public methods" in out
    assert "database.hpp:1 Database -- 7 public methods" in out
