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


TOO_BROAD = [
    "", "  ", "/", "//", "C:", "C:/", "C:\\", "c:\\\\", "\\\\server\\share", "//server/share", "//server/share/",
    "~", "~/", "~\\", "$HOME", "$HOME/", "${HOME}", "${HOME}/", "$USERPROFILE", "${USERPROFILE}", "%USERPROFILE%",
    "%USERPROFILE%\\", "$env:USERPROFILE", "$home",
]


@pytest.mark.parametrize("entry", TOO_BROAD)
def test_an_entry_that_opens_a_root_or_the_home_folder_is_rejected(tmp_path: Path, entry: str) -> None:
    path = _profile_with(tmp_path, ["~/vab", entry])

    with pytest.raises(ProfileError, match="write_roots") as caught:
        load_profile(path)

    assert f'"{entry}"' in str(caught.value)


@pytest.mark.parametrize("entry", [
    "~/vab", "$HOME/vab", "C:/vab", "C:\\vab", "../vab", "vab", "/opt/build", "//server/share/vab",
    "\\\\server\\share\\vab", "%USERPROFILE%\\vab", "~user", "D:/X-Plane 12/Output",
])
def test_a_named_folder_is_accepted(tmp_path: Path, entry: str) -> None:
    assert load_profile(_profile_with(tmp_path, [entry])).write_roots == (entry,)


def test_a_profile_without_write_roots_is_written_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0"))

    assert "write_roots" not in json.loads(path.read_text(encoding="utf-8"))


def test_write_roots_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0", write_roots=("~/vab", "../out")))

    assert load_profile(path).write_roots == ("~/vab", "../out")
