"""Shared helpers for the skill tests: frontmatter, headings and links."""
import re
from collections.abc import Sequence
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
OPENING_HEADING = "## When this applies"
CLOSING_HEADING = "## Common mistakes"
_HEADING = re.compile(r"#{1,6} \S")
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")


def skill_names() -> list[str]:
    """Every directory under skills/ that holds a SKILL.md, sorted."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md"))


def skill_files() -> list[Path]:
    """Every file under skills/, sorted."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(path for path in SKILLS_DIR.rglob("*") if path.is_file())


def _split_frontmatter(text: str, label: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", f"{label}: no frontmatter"
    end = lines.index("---", 1)
    return lines[1:end], lines[end + 1:]


def frontmatter_lines(name: str) -> list[str]:
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    return _split_frontmatter(text, name)[0]


def parse_skill(name: str) -> tuple[dict[str, str], str]:
    """The frontmatter fields and the body of skills/<name>/SKILL.md."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    head, body = _split_frontmatter(text, name)
    fields = {}
    for line in head:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, "\n".join(body)


def prose_lines(text: str) -> list[str]:
    """The lines of a Markdown text that are outside fenced code blocks."""
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return kept


def sections(body: str) -> list[str]:
    """Every heading line of a Markdown text, outside code fences."""
    return [line.rstrip() for line in prose_lines(body) if _HEADING.match(line)]


def assert_sections(name: str, required: Sequence[str]) -> None:
    _, body = parse_skill(name)
    found = sections(body)
    missing = [heading for heading in required if heading not in found]
    assert not missing, f"{name} is missing {missing}"


def local_links(text: str) -> list[str]:
    """Relative link targets in a Markdown text, without their #anchor."""
    targets = []
    for line in prose_lines(text):
        for target in _LINK.findall(line):
            if target.startswith("#") or _SCHEME.match(target):
                continue
            targets.append(target.split("#", 1)[0])
    return targets
