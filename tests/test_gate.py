import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from apm.debt import accept
from apm.debt_store import DEBT_FILE, current_snapshot, write_baseline
from apm.gate import GateError, gate, render_gate
from apm.standard_config import load_standard
from apm.workflow_config import Checker, Commands, Workflow
from conftest import run_git

STANDARD = load_standard(None)
CRITERIA = "## Structural acceptance criteria\n- The note `docs/promised.md` exists.\n- Limits hold.\n"
WORKFLOW = Workflow(commands=Commands(build="BUILD", test="TEST", checkers=(Checker("lint", "LINT"),)), gate_timeout=7)


class FakeRun:
    """Stands in for subprocess.run: records each call, answers from `results` (default: success)."""

    def __init__(self, results: dict | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.results = results or {}

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        outcome = self.results.get(command, (0, ""))
        if isinstance(outcome, BaseException):
            raise outcome
        return subprocess.CompletedProcess(command, outcome[0], outcome[1], None)


def _head(repo: Path) -> str:
    done = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, message: str = "work") -> None:
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", message)


@pytest.fixture
def repo(git_repo: Path) -> Path:
    """A clean feature branch with a plan, the document it promises, and a recorded debt baseline."""
    (git_repo / ".gitignore").write_text(".apm/tmp/\n", encoding="utf-8")
    (git_repo / "docs").mkdir()
    (git_repo / "docs" / "plan.md").write_text(CRITERIA, encoding="utf-8")
    (git_repo / "docs" / "promised.md").write_text("promised\n", encoding="utf-8")
    write_baseline(git_repo / DEBT_FILE, accept(current_snapshot(git_repo, STANDARD), None, "", datetime.now(timezone.utc)))
    run_git(git_repo, "checkout", "-b", "feature")
    _commit(git_repo, "plan and baseline")
    return git_repo


def reviewed(repo: Path, **changes) -> dict:
    review = {"head": _head(repo), "open": 0, "criteria_met": True, "evidence": "all green", "at": "now"}
    return {"plan": "docs/plan.md", "review": {**review, **changes}}


def failed(result) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    for check in result.checks:
        if not check.passed:
            found.setdefault(check.criterion, []).append(check.name)
    return found


def run_gate(repo: Path, issue: dict, run=None, standard=STANDARD, workflow=WORKFLOW):
    return gate(repo, issue, workflow, standard, "main", run=run or FakeRun())


def test_all_pass(repo: Path) -> None:
    (repo / ".apm" / "tmp").mkdir(parents=True)
    (repo / ".apm" / "tmp" / "old.log").write_text("leftover", encoding="utf-8")
    run = FakeRun({"TEST": (0, "42 passed\n")})

    result = run_gate(repo, reviewed(repo), run)

    assert result.passed
    assert [check.criterion for check in result.checks] == [1, 1, 1, 1, 1, 1, 2, 3, 4]
    assert [call[0] for call in run.calls] == ["BUILD", "TEST", "LINT"]
    assert run.calls[0][1]["shell"] is True and run.calls[0][1]["timeout"] == 7
    assert (repo / ".apm" / "tmp" / "gate" / "test.log").read_text(encoding="utf-8") == "42 passed\n"


def test_dirty_tree_fails_and_skips_commands(repo: Path) -> None:
    (repo / "stray.txt").write_text("x", encoding="utf-8")
    run = FakeRun()

    result = run_gate(repo, reviewed(repo), run)

    assert failed(result)[1] == ["clean tree", "build", "test", "lint"]
    assert run.calls == []
    assert [c.detail for c in result.checks if c.name == "test"] == ["not run: the tree is not clean: stray.txt"]


def test_base_not_merged_fails(repo: Path) -> None:
    run_git(repo, "checkout", "main")
    (repo / "later.txt").write_text("later", encoding="utf-8")
    _commit(repo, "main moves on")
    run_git(repo, "checkout", "feature")
    run = FakeRun()

    result = run_gate(repo, reviewed(repo), run)

    assert failed(result)[1] == ["base merged", "build", "test", "lint"]
    assert run.calls == []
    assert [c.detail for c in result.checks if c.name == "base merged"] == ["main is not merged into HEAD"]


def test_failing_test_command_shows_tail_and_writes_log(repo: Path) -> None:
    output = "".join(f"line {n}\n" for n in range(1, 26))
    run = FakeRun({"TEST": (1, output)})

    result = run_gate(repo, reviewed(repo), run)

    detail = next(c.detail for c in result.checks if c.name == "test")
    assert detail.splitlines() == [f"line {n}" for n in range(6, 26)]
    assert (repo / ".apm" / "tmp" / "gate" / "test.log").read_text(encoding="utf-8") == output
    assert failed(result) == {1: ["test"]}


def test_command_timeout(repo: Path) -> None:
    run = FakeRun({"LINT": subprocess.TimeoutExpired("LINT", 7)})

    result = run_gate(repo, reviewed(repo), run)

    assert [c.detail for c in result.checks if c.name == "lint"] == ["timed out after 7s"]
    assert failed(result) == {1: ["lint"]}


def test_layer_overlap_fails_criterion_1(repo: Path) -> None:
    layers = ({"name": "core", "paths": ["docs/plan.md"]}, {"name": "edge", "paths": ["docs/**"]})

    result = run_gate(repo, reviewed(repo), standard=replace(STANDARD, layers=layers))

    assert failed(result) == {1: ["layers"]}
    assert "docs/plan.md: core, edge" in next(c.detail for c in result.checks if c.name == "layers")


def test_debt_regression_fails_criterion_2(repo: Path) -> None:
    body = "def big():\n" + "".join(f"    x{i} = {i}\n" for i in range(20))
    (repo / "big.py").write_text(body, encoding="utf-8")
    _commit(repo, "debt")

    result = run_gate(repo, reviewed(repo))

    assert failed(result) == {2: ["debt"]}
    assert "worse than the baseline" in next(c.detail for c in result.checks if c.name == "debt")


def test_stale_review_fails_criterion_3(repo: Path) -> None:
    issue = reviewed(repo)
    (repo / "after.txt").write_text("after the review", encoding="utf-8")
    _commit(repo, "after review")

    result = run_gate(repo, issue)

    assert failed(result) == {3: ["review"]}
    assert "is not HEAD" in next(c.detail for c in result.checks if c.name == "review")


def test_open_findings_fail_criterion_3(repo: Path) -> None:
    result = run_gate(repo, reviewed(repo, open=2))

    assert failed(result) == {3: ["review"]}
    assert "2 open findings" in next(c.detail for c in result.checks if c.name == "review")


def test_no_review_recorded_fails_criteria_3_and_4(repo: Path) -> None:
    result = run_gate(repo, {"plan": "docs/plan.md"})

    assert failed(result) == {3: ["review"], 4: ["plan"]}


def test_missing_promised_doc_fails_criterion_4(repo: Path) -> None:
    (repo / "docs" / "promised.md").unlink()
    _commit(repo, "lose the document")

    result = run_gate(repo, reviewed(repo))

    assert failed(result) == {4: ["plan"]}
    assert next(c.detail for c in result.checks if c.name == "plan") == "2 criteria; missing: docs/promised.md"


def test_criteria_not_met_fails_criterion_4(repo: Path) -> None:
    result = run_gate(repo, reviewed(repo, criteria_met=False))

    assert failed(result) == {4: ["plan"]}
    assert "criteria not recorded as met" in next(c.detail for c in result.checks if c.name == "plan")


def test_plan_file_missing_fails_criterion_4(repo: Path) -> None:
    issue = {**reviewed(repo), "plan": "docs/nope.md"}

    result = run_gate(repo, issue)

    assert failed(result) == {4: ["plan"]}
    assert "docs/nope.md" in next(c.detail for c in result.checks if c.name == "plan")


def test_no_test_command_is_gate_error(repo: Path) -> None:
    workflow = Workflow(commands=Commands(build="BUILD"))

    with pytest.raises(GateError, match="no test command"):
        run_gate(repo, reviewed(repo), workflow=workflow)


def test_no_plan_is_gate_error(repo: Path) -> None:
    with pytest.raises(GateError, match="no plan"):
        run_gate(repo, {"review": reviewed(repo)["review"]})


def test_render_lists_each_check_and_the_verdict(repo: Path) -> None:
    passing = render_gate(run_gate(repo, reviewed(repo))).splitlines()
    failing = render_gate(run_gate(repo, reviewed(repo, open=1), FakeRun({"TEST": (1, "boom\n")}))).splitlines()

    assert passing[0] == "PASS  1  clean tree" and passing[-1] == "merge gate: passed"
    assert "FAIL  1  test  boom" in failing
    assert failing[-1] == "merge gate: 2 failed; stop and ask"
