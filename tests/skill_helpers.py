"""Shared helpers for the skill tests: frontmatter, headings, links and spelling.

Markdown is read the way a CommonMark renderer reads it, as far as the tests need: a fence opens
with three or more backticks or tildes and closes only with a line of the same character, at least
as long, with nothing after it. (Any indentation is accepted, so fences nested in list items count.)
"""
import re
from collections.abc import Sequence
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
OPENING_HEADING = "## When this applies"
CORE_RULE_HEADING = "## The core rule"
CLOSING_HEADING = "## Common mistakes"
_HEADING = re.compile(r"#{1,6} \S")
_FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)")
_TARGET = r"(<[^>\n]*>|[^\s)>][^\s)]*)"
_INLINE_LINK = re.compile(r"\[[^\]]*\]\(\s*" + _TARGET + r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_REFERENCE_LINK = re.compile(r"\s{0,3}\[(?!\^)[^\]]+\]:\s*" + _TARGET)
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_ISE = ("e", "ed", "es", "ing", "er", "ers", "ation", "ations")
BRITISH_STEMS = {
    "colour": ("", "s", "ed", "ing", "ful", "less"),
    "behaviour": ("", "s", "al", "ally"),
    "favour": ("", "s", "ed", "ing", "able", "ite", "ites"),
    "centr": ("e", "es", "ed", "ing"),
    "analys": ("e", "ed", "ing", "er", "ers"),
    "organis": _ISE,
    "recognis": _ISE + ("able",),
    "prioritis": _ISE,
    "initialis": _ISE,
    "normalis": _ISE,
    "catalogu": ("e", "es", "ed", "ing"),
    "judgement": ("", "s", "al"),
}


def _stem_pattern(stem: str, suffixes: Sequence[str]) -> str:
    ordered = sorted(suffixes, key=len, reverse=True)
    return stem + "(?:" + "|".join(re.escape(suffix) for suffix in ordered) + ")"


_BRITISH = re.compile(
    r"\b(" + "|".join(_stem_pattern(s, x) for s, x in BRITISH_STEMS.items()) + r")\b",
    re.IGNORECASE,
)


def british_spellings(text: str) -> list[str]:
    """Every British spelling in `text`, inflected forms included ("analyses" is American too)."""
    return _BRITISH.findall(text)


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


def _opening_fence(line: str) -> str | None:
    """The fence a line opens (its run of backticks or tildes), or None."""
    match = _FENCE.fullmatch(line)
    if not match or (match.group(1)[0] == "`" and "`" in match.group(2)):
        return None
    return match.group(1)


def _closes(line: str, fence: str) -> bool:
    match = _FENCE.fullmatch(line)
    if not match or match.group(2).strip():
        return False
    run = match.group(1)
    return run[0] == fence[0] and len(run) >= len(fence)


def _prose_flags(lines: Sequence[str]) -> list[bool]:
    """For each line, whether it lies outside every code fence (a fence line itself does not)."""
    flags, fence = [], None
    for line in lines:
        if fence:
            flags.append(False)
            fence = None if _closes(line, fence) else fence
        else:
            fence = _opening_fence(line)
            flags.append(fence is None)
    return flags


def prose_lines(text: str) -> list[str]:
    """The lines of a Markdown text outside fenced code blocks, fence lines dropped."""
    lines = text.splitlines()
    return [line for line, prose in zip(lines, _prose_flags(lines)) if prose]


def sections(body: str) -> list[str]:
    """Every heading line of a Markdown text, outside code fences."""
    return [line.rstrip() for line in prose_lines(body) if _HEADING.match(line)]


def _heading_level(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def section(body: str, heading: str) -> str:
    """The lines under `heading`, fences included, up to the next heading of its level or above."""
    lines = body.splitlines()
    kept, inside = [], False
    for line, prose in zip(lines, _prose_flags(lines)):
        is_heading = prose and bool(_HEADING.match(line))
        if inside and is_heading and _heading_level(line) <= _heading_level(heading):
            break
        if inside:
            kept.append(line)
        inside = inside or (is_heading and line.rstrip() == heading)
    assert inside, f"no heading {heading!r}"
    return "\n".join(kept)


def assert_sections(name: str, required: Sequence[str]) -> None:
    _, body = parse_skill(name)
    found = sections(body)
    missing = [heading for heading in required if heading not in found]
    assert not missing, f"{name} is missing {missing}"


def _line_targets(line: str) -> list[str]:
    line = _CODE_SPAN.sub("", line)
    definition = _REFERENCE_LINK.match(line)
    targets = [definition.group(1)] if definition else []
    return targets + _INLINE_LINK.findall(line)


def local_links(text: str) -> list[str]:
    """Relative link targets (inline, angle-bracket and reference-style), without #anchors."""
    targets = []
    for line in prose_lines(text):
        for target in _line_targets(line):
            target = target.removeprefix("<").removesuffix(">")
            if target.startswith("#") or _SCHEME.match(target):
                continue
            targets.append(target.split("#", 1)[0])
    return targets


def term_pattern(term: str) -> re.Pattern[str]:
    """A pattern for `term` that does not match inside a longer word."""
    before = r"(?<!\w)" if re.match(r"\w", term[0]) else ""
    after = r"(?!\w)" if re.match(r"\w", term[-1]) else ""
    return re.compile(before + re.escape(term) + after)


def names_term(text: str, term: str) -> bool:
    """Whether `text` names `term`, ignoring case and not matching inside a longer word."""
    return bool(re.search(term_pattern(term).pattern, text, re.IGNORECASE))
