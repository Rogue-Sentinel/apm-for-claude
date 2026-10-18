"""memory_folder: the folder Claude Code keeps a project's memory in, from literal known slugs."""
from pathlib import Path

from apm.guard_paths import memory_folder


def _slug(root: Path) -> str:
    return memory_folder(root, Path("/cfg")).parent.name


def test_a_windows_root_gives_the_folder_claude_code_uses() -> None:
    root = Path(r"C:\Users\darby\source\repos\Agentic Project Management")
    assert _slug(root) == "C--Users-darby-source-repos-Agentic-Project-Management"


def test_a_hyphenated_root_keeps_its_hyphens() -> None:
    root = Path(r"C:\Users\darby\source\repos\VirtualAirline-Plugin-for-XP12")
    assert _slug(root) == "C--Users-darby-source-repos-VirtualAirline-Plugin-for-XP12"


def test_a_posix_root_with_dots_and_underscores() -> None:
    assert _slug(Path("/home/pat/src/my.repo_v2")) == "-home-pat-src-my-repo-v2"


def test_a_non_ascii_letter_is_replaced_like_any_other_character() -> None:
    assert _slug(Path("/home/pat/caf\u00e9")) == "-home-pat-caf-"


def test_the_folder_is_named_memory_under_the_config_dirs_projects() -> None:
    folder = memory_folder(Path("/home/pat/src/app"), Path("/cfg"))
    assert (folder.name, folder.parent.parent) == ("memory", Path("/cfg/projects"))
