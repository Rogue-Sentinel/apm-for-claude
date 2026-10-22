"""`approve --path` and `allow --path` refuse a glob that can never match a write."""
import json
from pathlib import Path

import pytest

import apm_cli
from apm.paths import find_project
from apm.state_store import init_state

USAGE_ERROR = 2
REFUSAL = (
    "apm: --path must be relative to the checkout root, as the denial names it "
    "(got {path}); a write outside the project cannot be approved"
)
FORMS = {
    "approve": lambda path: ["approve", "--path", path, "--reason", "r"],
    "allow": lambda path: ["allow", "1", "--path", path, "--reason", "r"],
}
NEVER_MATCH = [
    "/abs/x.md", "C:/Users/x/MEMORY.md", "C:\\Users\\x\\MEMORY.md", "//server/share/x",
    "~/x.md", "../other/x.md", "docs/../../x.md",
]


@pytest.fixture
def repo(git_repo: Path, monkeypatch) -> Path:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text('{"framework_version": "0.1.0"}', encoding="utf-8")
    init_state(find_project(git_repo))
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["issue", "1", "--title", "T"]) == 0
    return git_repo


def _ledger(repo: Path) -> dict:
    return json.loads((repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", NEVER_MATCH)
@pytest.mark.parametrize("form", FORMS)
def test_a_path_that_can_never_match_is_refused(repo: Path, capsys, form: str, path: str) -> None:
    before = _ledger(repo)

    code = apm_cli.main(FORMS[form](path))

    assert (code, capsys.readouterr().err.strip(), _ledger(repo)) == (USAGE_ERROR, REFUSAL.format(path=path), before)


@pytest.mark.parametrize("path", ["data/fleet.db", "docs/**", ".git/config"])
@pytest.mark.parametrize("form", FORMS)
def test_a_checkout_relative_path_is_recorded(repo: Path, form: str, path: str) -> None:
    code = apm_cli.main(FORMS[form](path))

    ledger = _ledger(repo)
    entries = ledger["approvals"] if form == "approve" else ledger["issues"]["1"]["allowlist"]
    assert (code, [e["path"] for e in entries]) == (0, [path])
