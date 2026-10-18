import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from conftest import run_git

from apm.init_apply import AUDIT_DIR, apply, refusals

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
PLAN_NOTE = "imported docs/plans/x.md: not approved; needs the user's approval before building"


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "rules.md").write_text("rule", encoding="utf-8")
    return root


def inventory(cover: str = "rules.md") -> dict:
    source = {"id": "s", "title": "S", "origin": "o"}
    return {"sources": [source], "items": [{"id": "r1", "what": "w", "source": "s", "covered_by": [{"file": cover}]}]}


def item(ident: str, kind: str, title: str = "T") -> dict:
    return {"id": ident, "kind": kind, "title": title, "detail": "d"}


def put(root: Path, name: str, data: dict) -> None:
    path = root / AUDIT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def stage(root: Path, in_flight=(), decisions=None, mode="existing", debt=(), profile=None, cover="rules.md") -> None:
    audit = {"mode": mode, "base": "main", "notes": [], "in_flight": list(in_flight), "debt_issues": list(debt), "totals": {}}
    put(root, "audit.json", audit)
    put(root, "decisions.json", decisions or {})
    put(root, "profile.json", profile or {"framework_version": "0.1.0", "workflow": {"review": "per-task"}})
    if mode != "fresh":
        put(root, "coverage.json", inventory(cover))


def ledger(root: Path) -> dict:
    return json.loads((root / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8"))


def commit_branch(repo: Path, name: str) -> None:
    run_git(repo, "checkout", "-b", name)
    (repo / f"{name}.txt").write_text(name, encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", name)
    run_git(repo, "checkout", "main")


def test_refuses_on_coverage_gap(git_repo: Path, plugin: Path) -> None:
    stage(git_repo, cover="gone.md")

    found = refusals(git_repo, plugin)

    assert found == ["coverage gap: r1: cover file missing: gone.md"]


def test_refuses_missing_decision_and_bad_value(git_repo: Path, plugin: Path) -> None:
    stage(git_repo, [item("issue:7", "issue"), item("issue:8", "issue")], {"issue:8": "maybe"})

    found = refusals(git_repo, plugin)

    assert found == ["no decision for issue:7", "unknown decision for issue:8: 'maybe'"]


def test_refuses_unmerged_finish_first_branch(git_repo: Path, plugin: Path) -> None:
    commit_branch(git_repo, "feat")
    stage(git_repo, [item("branch:feat", "branch", "feat")], {"branch:feat": "finish"})

    found = refusals(git_repo, plugin)

    assert found == ["finish first: branch:feat is not merged into main yet"]


def test_finish_branch_merged_into_base_passes(git_repo: Path, plugin: Path) -> None:
    commit_branch(git_repo, "feat")
    run_git(git_repo, "merge", "feat")
    stage(git_repo, [item("branch:feat", "branch", "feat")], {"branch:feat": "finish"})

    assert refusals(git_repo, plugin) == []


def test_fresh_needs_no_coverage(git_repo: Path, plugin: Path) -> None:
    stage(git_repo, mode="fresh")

    assert refusals(git_repo, plugin) == []


def test_existing_mode_needs_coverage_and_every_file(git_repo: Path, plugin: Path) -> None:
    stage(git_repo, mode="fresh")
    put(git_repo, "audit.json", {"mode": "existing", "base": "main", "in_flight": []})
    (git_repo / AUDIT_DIR / "profile.json").unlink()

    found = refusals(git_repo, plugin)

    assert found == [f"missing {AUDIT_DIR}/coverage.json", f"missing {AUDIT_DIR}/profile.json"]


def test_refuses_without_the_audit(git_repo: Path, plugin: Path) -> None:
    assert refusals(git_repo, plugin) == [f"missing {AUDIT_DIR}/audit.json"]


def test_refuses_invalid_draft_profile(git_repo: Path, plugin: Path) -> None:
    stage(git_repo, profile={"framework_version": "0.1.0", "workflow": {"review": "sometimes"}})

    found = refusals(git_repo, plugin)

    assert len(found) == 1 and found[0].startswith("draft profile rejected:") and "review" in found[0]


def test_apply_writes_profile_imports_and_baseline(git_repo: Path) -> None:
    stage(git_repo, [item("issue:7", "issue", "Feature")], {"issue:7": "adopt"}, debt=[9, 4])

    actions = apply(git_repo, 1, NOW)

    state = ledger(git_repo)
    profile = json.loads((git_repo / ".apm" / "profile.json").read_text(encoding="utf-8"))
    assert profile["workflow"] == {"review": "per-task"}
    assert (git_repo / ".apm" / "state" / "profile.json").read_text(encoding="utf-8") == (
        git_repo / ".apm" / "profile.json"
    ).read_text(encoding="utf-8")
    assert state["issues"]["7"]["status"] == "queued" and state["issues"]["7"]["imported"] is True
    assert state["debt_issues"] == [4, 9]
    assert (git_repo / ".apm" / "debt.json").is_file()
    assert [entry["event"] for entry in state["log"]] == ["initialized from audit"]
    assert ".apm/profile.json" in " ".join(actions) and "imported issue #7" in actions


def test_imported_plans_are_not_approved(git_repo: Path) -> None:
    stage(git_repo, [item("plan:docs/plans/x.md", "plan", "x")], {"plan:docs/plans/x.md": "adopt"})

    apply(git_repo, 1, NOW)

    state = ledger(git_repo)
    assert [note["text"] for note in state["issues"]["1"]["decisions"]] == [PLAN_NOTE]
    assert all(entry["status"] != "building" for entry in state["issues"].values())


def test_other_decisions_are_notes(git_repo: Path) -> None:
    stage(git_repo, [item("branch:old", "branch", "old")], {"branch:old": "leave"})

    apply(git_repo, 1, NOW)

    assert [note["text"] for note in ledger(git_repo)["issues"]["1"]["decisions"]] == ["leave branch:old"]


def test_apply_twice_adds_nothing(git_repo: Path) -> None:
    stage(git_repo, [item("issue:7", "issue"), item("plan:p.md", "plan")], {"issue:7": "adopt", "plan:p.md": "adopt"}, debt=[4])
    apply(git_repo, 1, NOW)
    first = (git_repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8")
    commits = run_git_out(git_repo / ".apm" / "state", "rev-list", "--count", "HEAD")

    actions = apply(git_repo, 1, NOW)

    assert actions == []
    assert (git_repo / ".apm" / "state" / "ledger.json").read_text(encoding="utf-8") == first
    assert run_git_out(git_repo / ".apm" / "state", "rev-list", "--count", "HEAD") == commits


def test_adopting_an_issue_again_keeps_its_progress(git_repo: Path) -> None:
    stage(git_repo, [item("issue:7", "issue")], {"issue:7": "adopt"})
    apply(git_repo, 1, NOW)
    state = ledger(git_repo)
    state["issues"]["7"]["status"] = "building"
    (git_repo / ".apm" / "state" / "ledger.json").write_text(json.dumps(state), encoding="utf-8")

    apply(git_repo, 1, NOW)

    assert ledger(git_repo)["issues"]["7"]["status"] == "building"


def test_existing_baseline_kept(git_repo: Path) -> None:
    stage(git_repo)
    baseline = git_repo / ".apm" / "debt.json"
    baseline.write_text('{"version": 1, "marker": "mine"}', encoding="utf-8")

    apply(git_repo, 1, NOW)

    assert baseline.read_text(encoding="utf-8") == '{"version": 1, "marker": "mine"}'


def run_git_out(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
