import pytest

from apm.metrics_not_measured import file_kind, holds_text, named_as_not_code


@pytest.mark.parametrize("path", [
    "README.md", "docs/guide.rst", "notes.txt", "data/items.json", "ci.yml", "pyproject.toml",
    "setup.cfg", "config.ini", "layout.xml", "table.csv", "poetry.lock", "icon.svg",
])
def test_docs_data_and_config_files_are_named_as_not_code(path: str) -> None:
    assert named_as_not_code(path)


@pytest.mark.parametrize("path", ["logo.png", "photo.JPG", "lib.dll", "font.woff2", "archive.zip", "doc.pdf"])
def test_binary_extensions_are_named_as_not_code(path: str) -> None:
    assert named_as_not_code(path)


@pytest.mark.parametrize("path", [
    "LICENSE", "sub/COPYING", "NOTICE", ".gitignore", ".editorconfig", "src/.clang-format",
])
def test_license_files_and_dotfiles_are_named_as_not_code(path: str) -> None:
    assert named_as_not_code(path)


@pytest.mark.parametrize("path", [
    "ui/Panel.qrc", "Makefile", "Dockerfile", "bin/run", "config.h.in", "style.css",
])
def test_unknown_code_files_are_not_named_as_not_code(path: str) -> None:
    assert not named_as_not_code(path)


def test_plain_text_holds_text() -> None:
    assert holds_text(b"x = 1\n")


def test_a_nul_byte_marks_a_binary_file() -> None:
    assert not holds_text(b"\x89PNG\r\n\x1a\n\x00\x00")


def test_a_nul_after_the_first_8000_bytes_still_reads_as_text() -> None:
    assert holds_text(b"a" * 8000 + b"\x00")


def test_utf16_text_with_a_byte_order_mark_holds_text() -> None:
    assert holds_text("x = 1\n".encode("utf-16"))


@pytest.mark.parametrize("data", [b"", b" \n\t\n", None])
def test_an_empty_blank_or_unreadable_file_holds_no_text(data: bytes | None) -> None:
    assert not holds_text(data)


@pytest.mark.parametrize("data", [b"\xff\xfe", b"\xfe\xff", " \n".encode("utf-16")])
def test_a_byte_order_mark_alone_or_blank_utf16_holds_no_text(data: bytes) -> None:
    assert not holds_text(data)


@pytest.mark.parametrize("path, kind", [
    ("ui/Panel.QRC", ".qrc"), ("build/Makefile", "Makefile"), ("config.h.in", ".in"),
])
def test_file_kind_is_the_lowercased_extension_or_the_file_name(path: str, kind: str) -> None:
    assert file_kind(path) == kind
