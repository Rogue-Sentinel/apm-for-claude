import json
from pathlib import Path

import pytest

from apm.profile import (
    ALWAYS_PROTECTED,
    DEFAULT_MODELS,
    MAX_WORKERS_CAP,
    Profile,
    ProfileError,
    load_profile,
    write_profile,
)


def _write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_minimal_profile_applies_defaults(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "profile.json", {"framework_version": "0.1.0"})

    profile = load_profile(path)

    assert profile.max_workers == 3
    assert dict(profile.models) == DEFAULT_MODELS
    assert profile.protected_globs() == ALWAYS_PROTECTED


def test_model_overrides_merge_over_defaults(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "profile.json",
        {"framework_version": "0.1.0", "models": {"implementer": "opus"}},
    )

    profile = load_profile(path)

    assert profile.models["implementer"] == "opus"
    assert profile.models["planner"] == "opus"
    assert profile.models["auditor"] == "haiku"


def test_max_workers_above_cap_is_rejected(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "profile.json", {"framework_version": "0.1.0", "max_workers": 4}
    )

    with pytest.raises(ProfileError, match="at most 3"):
        load_profile(path)


def test_max_workers_below_one_is_rejected(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "profile.json", {"framework_version": "0.1.0", "max_workers": 0}
    )

    with pytest.raises(ProfileError):
        load_profile(path)


def test_missing_version_is_rejected(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "profile.json", {"max_workers": 2})

    with pytest.raises(ProfileError):
        load_profile(path)


def test_invalid_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ProfileError):
        load_profile(path)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ProfileError):
        load_profile(tmp_path / "absent.json")


def test_round_trip_preserves_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    original = Profile(
        framework_version="0.1.0",
        protected_paths=("docs/**",),
        max_workers=2,
        models={**DEFAULT_MODELS, "reviewer": "sonnet"},
        extra={"commands": {"test": "ctest"}},
    )

    write_profile(path, original)
    loaded = load_profile(path)

    assert loaded.extra == {"commands": {"test": "ctest"}}
    assert loaded.framework_version == "0.1.0"
    assert loaded.protected_paths == ("docs/**",)
    assert loaded.max_workers == 2
    assert dict(loaded.models) == dict(original.models)


def test_write_profile_uses_indent_sorted_keys_and_trailing_newline(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.1.0"))

    text = path.read_text(encoding="utf-8")
    assert text.endswith("}\n")
    assert '\n  "framework_version": "0.1.0"' in text
    keys = [line.strip().split('"')[1] for line in text.splitlines() if line.startswith('  "')]
    assert keys == sorted(keys)


def test_cap_constant_matches_brief() -> None:
    assert MAX_WORKERS_CAP == 3
