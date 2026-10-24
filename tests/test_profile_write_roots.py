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
    path = _profile_with(tmp_path, ["~/out", "D:/Shared Apps/Output"])

    profile = load_profile(path)

    assert profile.write_roots == ("~/out", "D:/Shared Apps/Output")
    assert "write_roots" not in profile.extra


def test_a_profile_without_write_roots_has_none(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"framework_version": "0.3.0"}), encoding="utf-8")

    assert load_profile(path).write_roots == ()


@pytest.mark.parametrize("roots", ["~/out", [1], ["~/out", None], {"a": "b"}], ids=["string", "number", "mixed", "object"])
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
    path = _profile_with(tmp_path, ["~/out", entry])

    with pytest.raises(ProfileError, match="write_roots") as caught:
        load_profile(path)

    assert f'"{entry}"' in str(caught.value)


@pytest.mark.parametrize("entry", ["..", "../..", "./..", "..\\", ".", "./", "out/../.."])
def test_an_entry_made_only_of_dot_segments_is_rejected(tmp_path: Path, entry: str) -> None:
    """`..` is the folder holding the main checkout, and with it every other repository there."""
    with pytest.raises(ProfileError, match="write_roots") as caught:
        load_profile(_profile_with(tmp_path, [entry]))

    assert f'"{entry}"' in str(caught.value)


@pytest.mark.parametrize("entry", ["/c", "/c/", "/d", "/C", "C:/.", "C:/..", "~/.", "~/..", "~/out/..", "$HOME/out/.."])
def test_a_drive_or_dot_form_of_a_root_or_the_home_folder_is_rejected(tmp_path: Path, entry: str) -> None:
    with pytest.raises(ProfileError, match="write_roots") as caught:
        load_profile(_profile_with(tmp_path, [entry]))

    assert f'"{entry}"' in str(caught.value)


@pytest.mark.parametrize("entry", ["%USERPROFILE%\\out", "%HOMEDRIVE%%HOMEPATH%/out", "D:/%BUILD%/out"])
def test_a_percent_variable_is_rejected_with_a_pointer_to_the_home_form(tmp_path: Path, entry: str) -> None:
    """The guard expands no `%...%` variable, so such an entry would open nothing; `~` is the home spelling."""
    with pytest.raises(ProfileError, match="write_roots") as caught:
        load_profile(_profile_with(tmp_path, [entry]))

    assert f'"{entry}"' in str(caught.value) and '"~/out"' in str(caught.value)


@pytest.mark.parametrize("entry", [
    "~/out", "$HOME/out", "C:/out", "C:\\out", "../out", "out", "/opt/build", "//server/share/out",
    "\\\\server\\share\\out", "~user", "D:/Shared Apps/Output", "~\\out", "$HOME\\out", "$env:USERPROFILE\\out",
    "${env:USERPROFILE}\\out", "/c/out", "./out", "C:/out/./x",
])
def test_a_named_folder_is_accepted(tmp_path: Path, entry: str) -> None:
    assert load_profile(_profile_with(tmp_path, [entry])).write_roots == (entry,)


def test_a_profile_without_write_roots_is_written_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0"))

    assert "write_roots" not in json.loads(path.read_text(encoding="utf-8"))


def test_write_roots_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"

    write_profile(path, Profile(framework_version="0.3.0", write_roots=("~/out", "../out")))

    assert load_profile(path).write_roots == ("~/out", "../out")
