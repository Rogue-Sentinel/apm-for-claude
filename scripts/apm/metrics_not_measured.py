"""Decide which files with no language count as "not measured" in the metrics report.

A file the metrics cannot read as code is either expected (documentation, data, configuration, a
binary) or a surprise (source in a language the tool does not know). Only the surprise is worth
telling the reader about, so these pure functions separate the two.

Rules:
- `named_as_not_code` is called only for a path that has no language; it does not look the
  language up itself. It is True for a dotfile, for a well-known license or readme name, and for a
  documentation, data, configuration or binary extension.
- `holds_text` reads the bytes of such a file. A file with no non-whitespace byte, or one that
  could not be read, holds no text. Otherwise it holds text when it starts with a UTF-16 byte
  order mark, or has no NUL byte in its first 8000 bytes (git's own binary heuristic).
- `file_kind` names a file for the report: its lowercased extension with the dot, or its file name
  when it has no extension.

Known limits:
- The lists are fixed and name by extension only. A `.txt` file that holds source, or a `.json`
  file with a script inside, counts as not code.
- A binary file whose extension is unknown is told apart from text only by `holds_text`.
- UTF-16 or UTF-32 text without a byte order mark has NUL bytes and reads as binary.
- UTF-32 text starting with a byte order mark reads as text only because its first two bytes
  match the UTF-16 mark.
- Only the extension after the last dot counts: `config.h.in` is `.in`, not `.h.in`.
"""
from __future__ import annotations

NOT_CODE_EXTENSIONS: frozenset[str] = frozenset(
    ".md .markdown .mdx .rst .adoc .asciidoc .txt .rtf .json .jsonc .json5 .yaml .yml .toml .ini .cfg "
    ".conf .properties .xml .csv .tsv .lock .log .svg".split()
)
BINARY_EXTENSIONS: frozenset[str] = frozenset(
    ".png .jpg .jpeg .gif .bmp .ico .icns .webp .tif .tiff .psd .pdf .zip .gz .tgz .bz2 .xz .7z .tar "
    ".rar .jar .war .whl .exe .dll .so .dylib .a .lib .o .obj .pyc .class .wasm .ttf .otf .woff .woff2 "
    ".eot .mp3 .wav .ogg .flac .mp4 .mov .avi .mkv .webm .db .sqlite".split()
)
NOT_CODE_NAMES: frozenset[str] = frozenset(
    "license copying notice authors contributors changelog changes readme owners codeowners".split()
)
_UTF16_MARKS = (b"\xff\xfe", b"\xfe\xff")
_BINARY_SNIFF_BYTES = 8000


def _file_name(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _extension(name: str) -> str:
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def file_kind(path: str) -> str:
    """The lowercased extension with its dot, or the file name when it has no extension."""
    name = _file_name(path)
    return _extension(name) or name


def named_as_not_code(path: str) -> bool:
    """True when a file name, not its content, says it is docs, data, config or a binary.

    Call it only for a path that has no language.
    """
    name = _file_name(path)
    extension = _extension(name)
    return (
        name.startswith(".")
        or name.lower() in NOT_CODE_NAMES
        or extension in NOT_CODE_EXTENSIONS
        or extension in BINARY_EXTENSIONS
    )


def holds_text(data: bytes | None) -> bool:
    """True when `data` reads as text: not empty or blank, and not binary."""
    if data is None or not data.strip():
        return False
    return data.startswith(_UTF16_MARKS) or b"\x00" not in data[:_BINARY_SNIFF_BYTES]
