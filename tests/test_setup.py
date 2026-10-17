import copy
import json
from pathlib import Path

import pytest

import apm_cli
from apm import VERSION
from apm.paths import find_project
from apm.profile import load_profile
from apm.setup import MANAGER_AGENT, SUPERPOWERS_ID, SetupError, merge_settings, setup_project


def _settings(repo: Path) -> dict:
    return json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))


def test_merge_settings_preserves_unrelated_keys() -> None:
    existing = {"permissions": {"allow": ["Bash(ls)"]}, "env": {"FOO": "1"}}
    merged = merge_settings(existing, 3)
    assert merged["permissions"] == {"allow": ["Bash(ls)"]}
    assert merged["env"]["FOO"] == "1"
    assert merged["agent"] == MANAGER_AGENT
    assert merged["env"]["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "3"
    assert merged["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert merged["enabledPlugins"][SUPERPOWERS_ID] is False


def test_merge_settings_does_not_mutate_input() -> None:
    existing = {"env": {"FOO": "1"}, "enabledPlugins": {"other@x": True}}
    before = copy.deepcopy(existing)
    merged = merge_settings(existing, 2)
    assert existing == before
    assert merged["enabledPlugins"]["other@x"] is True


def test_setup_project_fresh_repo(git_repo: Path) -> None:
    project = find_project(git_repo)
    changed = setup_project(project)
    assert sorted(changed) == sorted([".claude/settings.json", ".apm/profile.json", ".gitignore"])
    profile = load_profile(project.profile_path)
    assert profile.framework_version == VERSION
    assert profile.protected_paths == ()
    assert (project.state_dir / ".git").exists()
    assert _settings(git_repo)["agent"] == MANAGER_AGENT


def test_setup_project_is_idempotent(git_repo: Path) -> None:
    project = find_project(git_repo)
    setup_project(project)
    assert setup_project(project) == []
    lines = (git_repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines.count(".apm/state/") == 1


def test_setup_keeps_existing_profile(git_repo: Path) -> None:
    (git_repo / ".apm").mkdir()
    path = git_repo / ".apm" / "profile.json"
    text = '{"framework_version": "0.0.9", "protected_paths": ["data/*.db"]}'
    path.write_text(text, encoding="utf-8")
    changed = setup_project(find_project(git_repo))
    assert ".apm/profile.json" not in changed
    assert path.read_text(encoding="utf-8") == text


def test_setup_gitignore_without_trailing_newline(git_repo: Path) -> None:
    (git_repo / ".gitignore").write_text("node_modules", encoding="utf-8", newline="\n")
    setup_project(find_project(git_repo))
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert text == "node_modules\n.apm/state/\n"


@pytest.mark.parametrize("content", ["{not json", "[1, 2]"])
def test_setup_refuses_unreadable_settings(git_repo: Path, content: str) -> None:
    (git_repo / ".claude").mkdir()
    path = git_repo / ".claude" / "settings.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SetupError):
        setup_project(find_project(git_repo))
    assert path.read_text(encoding="utf-8") == content


def test_cli_setup_prints_changed_paths(git_repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["setup"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert sorted(out) == sorted([".claude/settings.json", ".apm/profile.json", ".gitignore"])


def test_cli_setup_reports_bad_settings_in_one_line(git_repo: Path, monkeypatch, capsys) -> None:
    (git_repo / ".claude").mkdir()
    (git_repo / ".claude" / "settings.json").write_text("{oops", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["setup"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("apm: ") and len(err.strip().splitlines()) == 1


def test_cli_setup_outside_a_repo_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert apm_cli.main(["setup"]) == 2
    assert "git" in capsys.readouterr().err


def test_other_commands_still_need_an_initialized_project(git_repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(git_repo)
    assert apm_cli.main(["brief"]) == 2
    assert "not an initialized APM project" in capsys.readouterr().err


def test_bad_settings_leave_no_other_files_behind(git_repo: Path) -> None:
    (git_repo / ".claude").mkdir()
    (git_repo / ".claude" / "settings.json").write_text("{oops", encoding="utf-8")
    with pytest.raises(SetupError):
        setup_project(find_project(git_repo))
    assert not (git_repo / ".apm" / "profile.json").exists()
    assert not (git_repo / ".gitignore").exists()
