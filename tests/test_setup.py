import copy
import json
import subprocess
from pathlib import Path

import pytest

import apm_cli
from apm import VERSION
from apm.paths import find_project
from apm.profile import load_profile
from apm.setup import MANAGER_AGENT, SUPERPOWERS_ID, SetupError, merge_settings, setup_project
from conftest import run_git


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
    assert text == "node_modules\n.apm/state/\n.apm/tmp/\n"


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


def _git_out(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)
    return done.stdout


SETUP_FILES = (".claude/settings.json", ".apm/profile.json", ".gitignore")


def test_setup_from_a_linked_worktree_writes_into_that_worktree(git_repo: Path) -> None:
    run_git(git_repo, "worktree", "add", "../wt", "-b", "wt")
    wt = git_repo.parent / "wt"
    assert sorted(setup_project(find_project(wt))) == sorted(SETUP_FILES)
    for name in SETUP_FILES:
        assert (wt / name).is_file(), name
        assert not (git_repo / name).exists(), name
    assert (git_repo / ".apm" / "state" / ".git").exists()


def test_setup_mirrors_the_profile_on_the_state_branch(git_repo: Path) -> None:
    project = find_project(git_repo)
    setup_project(project)
    mirror = project.state_dir / "profile.json"
    assert mirror.read_text(encoding="utf-8") == (git_repo / ".apm" / "profile.json").read_text(encoding="utf-8")
    assert _git_out(project.state_dir, "ls-files", "profile.json").strip() == "profile.json"
    assert _git_out(project.state_dir, "status", "--porcelain") == ""


def test_mirror_makes_every_worktree_initialized_before_the_profile_merges(git_repo: Path) -> None:
    run_git(git_repo, "worktree", "add", "../wt", "-b", "wt")
    setup_project(find_project(git_repo.parent / "wt"))
    run_git(git_repo, "worktree", "add", "../other", "-b", "other")
    other = find_project(git_repo.parent / "other")
    assert other.is_initialized and other.profile_path == other.state_dir / "profile.json"


def test_setup_twice_adds_no_state_commit(git_repo: Path) -> None:
    project = find_project(git_repo)
    setup_project(project)
    before = _git_out(project.state_dir, "rev-parse", "HEAD")
    setup_project(project)
    assert _git_out(project.state_dir, "rev-parse", "HEAD") == before


def test_setup_mirrors_an_existing_profile_verbatim(git_repo: Path) -> None:
    (git_repo / ".apm").mkdir()
    text = '{"framework_version": "0.0.9", "protected_paths": ["data/*.db"]}'
    (git_repo / ".apm" / "profile.json").write_text(text, encoding="utf-8")
    project = find_project(git_repo)
    setup_project(project)
    assert (project.state_dir / "profile.json").read_text(encoding="utf-8") == text


def test_setup_ignores_tmp_once(git_repo: Path) -> None:
    project = find_project(git_repo)
    setup_project(project)
    setup_project(project)
    lines = (git_repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines.count(".apm/tmp/") == 1 and lines.count(".apm/state/") == 1


def test_setup_adds_the_tmp_ignore_to_a_gitignore_that_only_has_state(git_repo: Path) -> None:
    (git_repo / ".gitignore").write_text(".apm/state/\n", encoding="utf-8", newline="\n")
    changed = setup_project(find_project(git_repo))
    text = (git_repo / ".gitignore").read_text(encoding="utf-8")
    assert ".gitignore" in changed and text == ".apm/state/\n.apm/tmp/\n"
