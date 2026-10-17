"""apm setup: the minimum a project needs to run its main session as the manager."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apm import VERSION
from apm.paths import Project
from apm.profile import Profile, load_profile, write_profile
from apm.state_store import commit_state, init_state

MANAGER_AGENT = "apm:manager"
SUPERPOWERS_ID = "superpowers@claude-plugins-official"
SETTINGS_PATH = ".claude/settings.json"
PROFILE_PATH = ".apm/profile.json"
GITIGNORE_PATH = ".gitignore"
STATE_IGNORE = ".apm/state/"
MIRROR_NAME = "profile.json"


class SetupError(Exception):
    """Setup cannot proceed without risking the user's files; the message is one line."""


def merge_settings(existing: dict, max_workers: int) -> dict:
    merged = {**existing}
    merged["agent"] = MANAGER_AGENT
    merged["env"] = {
        **existing.get("env", {}),
        "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": str(max_workers),
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
    }
    merged["enabledPlugins"] = {**existing.get("enabledPlugins", {}), SUPERPOWERS_ID: False}
    return merged


def _read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _load_settings(path: Path, text: str | None) -> dict[str, Any]:
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SetupError(f"{path} is not valid JSON; fix it and rerun: {exc}") from exc
    if not isinstance(data, dict):
        raise SetupError(f"{path} must be a JSON object; fix it and rerun")
    return data


def _setup_settings(project: Project, max_workers: int) -> bool:
    path = project.worktree_root / SETTINGS_PATH
    old = _read_text(path)
    merged = merge_settings(_load_settings(path, old), max_workers)
    new = json.dumps(merged, indent=2, sort_keys=True) + "\n"
    if new == old:
        return False
    _write_text(path, new)
    return True


def _existing_profile(project: Project) -> Profile | None:
    return load_profile(project.profile_path) if project.is_initialized else None


def _setup_profile(project: Project, profile: Profile) -> bool:
    path = project.worktree_root / PROFILE_PATH
    if path.exists():
        return False
    write_profile(path, profile)
    return True


def _mirror_profile(project: Project) -> None:
    """Commit this checkout's profile on the state branch, so every worktree finds it."""
    text = (project.worktree_root / PROFILE_PATH).read_text(encoding="utf-8")
    mirror = project.state_dir / MIRROR_NAME
    if _read_text(mirror) == text:
        return
    _write_text(mirror, text)
    commit_state(project, "Mirror the APM profile")


def _setup_gitignore(project: Project) -> bool:
    path = project.worktree_root / GITIGNORE_PATH
    old = _read_text(path) or ""
    if STATE_IGNORE in old.splitlines():
        return False
    lead = "" if not old or old.endswith("\n") else "\n"
    _write_text(path, old + lead + STATE_IGNORE + "\n")
    return True


def setup_project(project: Project) -> list[str]:
    existing = _existing_profile(project)
    profile = existing or Profile(framework_version=VERSION)
    changed = [SETTINGS_PATH] if _setup_settings(project, profile.max_workers) else []
    if _setup_profile(project, profile):
        changed.append(PROFILE_PATH)
    if _setup_gitignore(project):
        changed.append(GITIGNORE_PATH)
    init_state(project)
    _mirror_profile(project)
    return changed
