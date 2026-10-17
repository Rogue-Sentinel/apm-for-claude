import json
import subprocess
import sys
from pathlib import Path

import apm
import hook_pretooluse
import hook_session_start
from conftest import run_git

ROOT = Path(__file__).resolve().parent.parent


def _init(repo: Path, version: str = apm.VERSION, **extra) -> None:
    (repo / ".apm").mkdir(exist_ok=True)
    profile = {"framework_version": version, **extra}
    (repo / ".apm" / "profile.json").write_text(json.dumps(profile), encoding="utf-8")


def _event(repo: Path, command: str = "rm -rf x", **extra) -> str:
    event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(repo), **extra}
    return json.dumps(event)


def _decision(out: str) -> dict:
    return json.loads(out)["hookSpecificOutput"]


def test_pretooluse_silent_outside_apm_project(git_repo: Path) -> None:
    assert hook_pretooluse.run(_event(git_repo), {}) == (0, "")


def test_pretooluse_silent_in_repo_without_profile_even_for_worker(git_repo: Path) -> None:
    assert hook_pretooluse.run(_event(git_repo, agent_id="w1"), {}) == (0, "")


def test_pretooluse_denies_worker_rm_rf(git_repo: Path) -> None:
    _init(git_repo)
    code, out = hook_pretooluse.run(_event(git_repo, agent_id="w1"), {})
    assert code == 0
    assert _decision(out)["permissionDecision"] == "deny"


def test_pretooluse_asks_in_main_session(git_repo: Path) -> None:
    _init(git_repo)
    _, out = hook_pretooluse.run(_event(git_repo), {})
    assert _decision(out)["permissionDecision"] == "ask"


def test_pretooluse_fails_closed_on_internal_error(git_repo: Path, monkeypatch) -> None:
    _init(git_repo)

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(hook_pretooluse, "decide", boom)
    _, out = hook_pretooluse.run(_event(git_repo), {})
    assert _decision(out)["permissionDecision"] == "deny"
    assert "APM guard error" in _decision(out)["permissionDecisionReason"]
    assert "kaboom" in _decision(out)["permissionDecisionReason"]


def test_pretooluse_bad_profile_fails_closed(git_repo: Path) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text("{nope", encoding="utf-8")
    _, out = hook_pretooluse.run(_event(git_repo), {})
    assert _decision(out)["permissionDecision"] == "deny"
    assert "APM guard error" in _decision(out)["permissionDecisionReason"]


def test_pretooluse_bad_stdin_outside_project_is_silent(git_repo: Path) -> None:
    assert hook_pretooluse.run("not json", {"CLAUDE_PROJECT_DIR": str(git_repo)}) == (0, "")


def test_pretooluse_bad_stdin_in_initialized_project_denies(git_repo: Path) -> None:
    _init(git_repo)
    _, out = hook_pretooluse.run("not json", {"CLAUDE_PROJECT_DIR": str(git_repo)})
    assert _decision(out)["permissionDecision"] == "deny"


def test_pretooluse_bad_stdin_falls_back_to_cwd(git_repo: Path, monkeypatch) -> None:
    _init(git_repo)
    monkeypatch.chdir(git_repo)
    _, out = hook_pretooluse.run("not json", {})
    assert _decision(out)["permissionDecision"] == "deny"


def test_pretooluse_corrupt_ledger_is_empty_allowlist(git_repo: Path) -> None:
    _init(git_repo, protected_paths=["dist/**"])
    state = git_repo / ".apm" / "state"
    state.mkdir(parents=True)
    (state / "ledger.json").write_text("garbage{", encoding="utf-8")
    _, out = hook_pretooluse.run(_event(git_repo, "touch dist/app.js"), {})
    assert _decision(out)["permissionDecision"] == "ask"


def test_pretooluse_uses_ledger_allowlist(git_repo: Path) -> None:
    _init(git_repo, protected_paths=["dist/**"])
    state = git_repo / ".apm" / "state"
    state.mkdir(parents=True)
    issue = {"status": "building", "allowlist": [{"command": "touch dist/app.js"}]}
    (state / "ledger.json").write_text(json.dumps({"issues": {"1": issue}, "log": []}), encoding="utf-8")
    assert hook_pretooluse.run(_event(git_repo, "touch dist/app.js"), {}) == (0, "")


def test_session_start_silent_outside_project(git_repo: Path) -> None:
    assert hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {}) == (0, "")


def test_session_start_bad_stdin_is_silent() -> None:
    assert hook_session_start.run("not json", {}) == (0, "")


def test_session_start_includes_briefing(git_repo: Path, monkeypatch) -> None:
    _init(git_repo)
    monkeypatch.setattr(hook_session_start, "render_briefing", lambda ledger, error: "BRIEF-XYZ")
    code, out = hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {})
    context = _decision(out)["additionalContext"]
    assert code == 0 and "BRIEF-XYZ" in context
    assert _decision(out)["hookEventName"] == "SessionStart"
    assert "mismatch" not in context.lower()


def test_session_start_reports_version_mismatch(git_repo: Path) -> None:
    _init(git_repo, version="0.0.9")
    _, out = hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {})
    context = _decision(out)["additionalContext"]
    assert "0.0.9" in context and apm.VERSION in context


def test_session_start_reports_profile_error(git_repo: Path) -> None:
    (git_repo / ".apm").mkdir()
    (git_repo / ".apm" / "profile.json").write_text("{nope", encoding="utf-8")
    code, out = hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {})
    assert code == 0 and "profile" in _decision(out)["additionalContext"].lower()


def test_session_start_passes_ledger_error_to_briefing(git_repo: Path, monkeypatch) -> None:
    _init(git_repo)
    state = git_repo / ".apm" / "state"
    state.mkdir(parents=True)
    (state / "ledger.json").write_text("garbage{", encoding="utf-8")
    seen = {}
    monkeypatch.setattr(
        hook_session_start, "render_briefing", lambda ledger, error: seen.update(l=ledger, e=error) or ""
    )
    hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {})
    assert seen["l"] is None and seen["e"]


def test_hooks_json_points_at_existing_scripts() -> None:
    config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    pre = config["hooks"]["PreToolUse"][0]
    assert pre["matcher"] == "Bash|PowerShell|Write|Edit|NotebookEdit"
    commands = [h["command"] for group in config["hooks"].values() for e in group for h in e["hooks"]]
    assert 'python "${CLAUDE_PLUGIN_ROOT}/scripts/hook_pretooluse.py"' in commands
    assert 'python "${CLAUDE_PLUGIN_ROOT}/scripts/hook_session_start.py"' in commands
    assert "matcher" not in config["hooks"]["SessionStart"][0]
    for command in commands:
        relative = command.split("${CLAUDE_PLUGIN_ROOT}/")[1].rstrip('"')
        assert (ROOT / relative).is_file()


def test_hook_script_end_to_end(git_repo: Path) -> None:
    _init(git_repo)
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hook_pretooluse.py")],
        input=_event(git_repo, agent_id="w1"),
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert _decision(done.stdout)["permissionDecision"] == "deny"


def test_session_start_survives_briefing_crash(git_repo: Path, monkeypatch) -> None:
    _init(git_repo)

    def boom(ledger, error):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(hook_session_start, "render_briefing", boom)
    code, out = hook_session_start.run(json.dumps({"cwd": str(git_repo)}), {})
    assert code == 0 and "Briefing unavailable: kaboom" in _decision(out)["additionalContext"]


def test_pretooluse_script_reads_stdin_as_utf8(tmp_path: Path) -> None:
    repo = tmp_path / "répö-日本"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    _init(repo)
    payload = _event(repo, agent_id="w1")
    raw = json.dumps(json.loads(payload), ensure_ascii=False).encode("utf-8")
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hook_pretooluse.py")],
        input=raw, capture_output=True, check=True,
    )
    assert _decision(done.stdout.decode("utf-8"))["permissionDecision"] == "deny"


def test_session_start_script_reads_stdin_as_utf8(tmp_path: Path) -> None:
    repo = tmp_path / "répö-日本"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    _init(repo, version="0.0.9")
    raw = json.dumps({"cwd": str(repo)}, ensure_ascii=False).encode("utf-8")
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hook_session_start.py")],
        input=raw, capture_output=True, check=True,
    )
    assert "0.0.9" in _decision(done.stdout.decode("utf-8"))["additionalContext"]
