"""Issue 20: the profile's `write_roots` key, the folders outside the project that shell commands may write."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apm.profile import Profile, ProfileError, load_profile, write_profile


def _profile_with(tmp_path: Path, roots: object) -> Path:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"framework_version": "0.3.0", "write_roots": roots}), encoding="utf-8")
    return path


def test_write_roots_load_from_the_profile(tmp_path: Path) -> None:
    path = _profile_with(tmp_path, ["~/vab", "D:/X-Plane 12/Output"])

    profile = load_profile(path)

    assert profile.write_roots == ("~/vab", "D:/X-Plane 12/Output")
    assert "write_roots" not in profile.extra


def test_a_profile_without_write_roots_has_none(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"framework_version": "0.3.0"}), encoding="utf-8")

    assert load_profile(path).write_roots == ()


@pytest.mark.parametrize("roots", ["~/vab", [1], ["~/vab", None], {"a": "b"}], ids=["string", "number", "mixed", "object"])
def test_write_roots_must_be_strings(tmp_path: Path, roots: object) -> None:
    path = _profile_with(tmp_path, roots)

    with pytest.raises(ProfileError, match="write_roots must be a list of strings"):
        load_profile(path)


def test_a_profile_without_write_roots_is_written_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0"))

    assert "write_roots" not in json.loads(path.read_text(encoding="utf-8"))


def test_write_roots_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0", write_roots=("~/vab", "../out")))

    assert load_profile(path).write_roots == ("~/vab", "../out")
