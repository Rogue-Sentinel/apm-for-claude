import json
import subprocess
from pathlib import Path

import pytest

import apm_cli
from apm import cli_github
from apm.paths import find_project
from apm.state_store import init_state

URL = "https://github.com/acme/widgets/issues/12"


class FakeGh:
    def __init__(self, stdout: str = URL, returncode: int = 0, stderr: str = "") -> None:
        self.calls: list[dict] = []
        self.result = (stdout, returncode, stderr)

    def __call__(self, argv, **kwargs):
        self.calls.append({"argv": list(argv), **kwargs})
        stdout, code, stderr = self.result
        return subprocess.CompletedProcess(argv, code, stdout, stderr)


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    init_state(find_project(git_repo))
    monkeypatch.chdir(git_repo)
    return git_repo


@pytest.fixture
def gh(monkeypatch) -> FakeGh:
    fake = FakeGh()
    monkeypatch.setattr(cli_github, "RUN", fake)
    return fake


def _ledger(repo: Path) -> dict:
    return json.loads((repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8"))


def _body(repo: Path, text: str = "Do the thing.") -> str:
    path = repo / "body.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_cli_file_records_ledger_and_parent_line(repo: Path, gh: FakeGh, capsys) -> None:
    apm_cli.main(["issue", "5", "--title", "Epic", "--status", "split"])

    code = apm_cli.main([
        "github", "file", "--title", "Part one", "--body-file", _body(repo), "--label", "bug",
        "--kind", "bug", "--lane", "core", "--parent", "5",
    ])

    issue = _ledger(repo)["issues"]["12"]
    assert code == 0
    assert capsys.readouterr().out.strip().endswith(f"filed #12: {URL}")
    assert gh.calls[0]["input"] == "Do the thing.\n\nPart of #5"
    assert "--label" in gh.calls[0]["argv"]
    assert (issue["status"], issue["title"], issue["kind"], issue["lane"]) == ("queued", "Part one", "bug", "core")
    assert (issue["url"], issue["parent"]) == (URL, 5)


def test_cli_file_without_parent_leaves_body_alone(repo: Path, gh: FakeGh) -> None:
    apm_cli.main(["github", "file", "--title", "Solo", "--body-file", _body(repo)])

    assert gh.calls[0]["input"] == "Do the thing."
    assert "parent" not in _ledger(repo)["issues"]["12"]


def test_cli_file_gh_failure_exits_2_with_hint(repo: Path, gh: FakeGh, capsys) -> None:
    gh.result = ("", 1, "HTTP 401: bad credentials")

    code = apm_cli.main(["github", "file", "--title", "T", "--body-file", _body(repo)])

    err = capsys.readouterr().err
    assert code == 2
    assert "HTTP 401: bad credentials" in err
    assert "file it by hand, then record it with apm issue N" in err
    assert _ledger(repo)["issues"] == {}


def test_cli_close_refuses_before_integrating(repo: Path, gh: FakeGh, capsys) -> None:
    apm_cli.main(["issue", "9", "--title", "T", "--status", "building"])

    code = apm_cli.main(["github", "close", "9", "--pr", "https://x/pull/3"])

    assert code == 1
    assert "integrating" in capsys.readouterr().err
    assert gh.calls == []
    assert _ledger(repo)["issues"]["9"]["status"] == "building"


def test_cli_close_logs_and_prompts_parent(repo: Path, gh: FakeGh, capsys) -> None:
    apm_cli.main(["issue", "1", "--title", "Epic", "--status", "split"])
    apm_cli.main(["issue", "2", "--title", "A", "--status", "merged", "--parent", "1"])
    apm_cli.main(["issue", "3", "--title", "B", "--status", "integrating", "--parent", "1"])

    code = apm_cli.main(["github", "close", "3", "--pr", "https://x/pull/3"])

    ledger = _ledger(repo)
    assert code == 0
    assert gh.calls[0]["argv"] == ["gh", "issue", "close", "3", "--comment", "Shipped in https://x/pull/3."]
    assert (ledger["issues"]["3"]["status"], ledger["issues"]["3"]["pr"]) == ("merged", "https://x/pull/3")
    assert ledger["log"][-1]["event"] == "shipped in https://x/pull/3"
    assert "all sub-issues of #1 are merged; close #1 too" in capsys.readouterr().out


def test_cli_close_says_what_it_closed(repo: Path, gh: FakeGh, capsys) -> None:
    apm_cli.main(["issue", "3", "--title", "B", "--status", "integrating"])
    capsys.readouterr()

    apm_cli.main(["github", "close", "3", "--pr", "https://x/pull/3"])

    assert capsys.readouterr().out.splitlines() == ["closed #3: shipped in https://x/pull/3"]


def test_cli_close_stays_quiet_while_siblings_are_open(repo: Path, gh: FakeGh, capsys) -> None:
    apm_cli.main(["issue", "1", "--title", "Epic", "--status", "split"])
    apm_cli.main(["issue", "2", "--title", "A", "--status", "building", "--parent", "1"])
    apm_cli.main(["issue", "3", "--title", "B", "--status", "merged", "--parent", "1"])

    apm_cli.main(["github", "close", "3", "--pr", "https://x/pull/3"])

    assert "close #1 too" not in capsys.readouterr().out
