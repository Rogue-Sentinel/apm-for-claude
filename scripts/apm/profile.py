"""Load and write the project profile at .apm/profile.json."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ALWAYS_PROTECTED: tuple[str, ...] = (".git/**", ".apm/state/**")
DEFAULT_MODELS: dict[str, str] = {
    "auditor": "haiku",
    "planner": "opus",
    "implementer": "sonnet",
    "debugger": "opus",
    "reviewer": "opus",
}
MAX_WORKERS_CAP = 3
_KNOWN_KEYS = frozenset({"framework_version", "protected_paths", "max_workers", "models"})


class ProfileError(Exception):
    """The project profile is missing, malformed, or out of range."""


@dataclass(frozen=True)
class Profile:
    framework_version: str
    protected_paths: tuple[str, ...] = ()
    max_workers: int = MAX_WORKERS_CAP
    models: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_MODELS))
    extra: Mapping[str, Any] = field(default_factory=dict)

    def protected_globs(self) -> tuple[str, ...]:
        return ALWAYS_PROTECTED + self.protected_paths


def load_profile(path: Path) -> Profile:
    data = _read_object(path)
    version = data.get("framework_version")
    if not isinstance(version, str) or not version:
        raise ProfileError(f"{path}: framework_version is required")
    return Profile(
        framework_version=version,
        protected_paths=_string_list(data.get("protected_paths", []), "protected_paths"),
        max_workers=_max_workers(data.get("max_workers", MAX_WORKERS_CAP)),
        models={**DEFAULT_MODELS, **_models(data.get("models", {}))},
        extra={key: value for key, value in data.items() if key not in _KNOWN_KEYS},
    )


def write_profile(path: Path, profile: Profile) -> None:
    data = {
        **dict(profile.extra),
        "framework_version": profile.framework_version,
        "protected_paths": list(profile.protected_paths),
        "max_workers": profile.max_workers,
        "models": dict(profile.models),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileError(f"cannot read profile {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileError(f"profile {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"profile {path} must be a JSON object")
    return data


def _max_workers(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileError("max_workers must be an integer")
    if value < 1:
        raise ProfileError(f"max_workers must be at least 1, got {value}")
    if value > MAX_WORKERS_CAP:
        raise ProfileError(f"max_workers may be at most {MAX_WORKERS_CAP}, got {value}")
    return value


def _models(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise ProfileError("models must map role names to model names")
    return dict(value)


def _string_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProfileError(f"{name} must be a list of strings")
    return tuple(value)
