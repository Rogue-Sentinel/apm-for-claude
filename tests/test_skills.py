"""Every skill under skills/ has the shape the framework's skills share."""
import re

import pytest

from skill_helpers import (
    CLOSING_HEADING,
    CORE_RULE_HEADING,
    OPENING_HEADING,
    SKILLS_DIR,
    british_spellings,
    frontmatter_lines,
    local_links,
    parse_skill,
    sections,
    skill_files,
    skill_names,
)

SKILLS = skill_names()
BANNED_TERMS = (
    "TypeScript", "React", "tsconfig", "C++", "XPLM", "ImGui", "X-Plane", "VirtualAirline",
    "superpowers:",
)
MIT_NOTICE = (
    "MIT License",
    "Permission is hereby granted, free of charge, to any person obtaining a copy",
    "The above copyright notice and this permission notice shall be included in all",
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND',
)


def _term_pattern(term: str) -> re.Pattern[str]:
    before = r"(?<!\w)" if re.match(r"\w", term[0]) else ""
    after = r"(?!\w)" if re.match(r"\w", term[-1]) else ""
    return re.compile(before + re.escape(term) + after)


def _is_by_language_reference(path) -> bool:
    return path.parent.name == "references" and path.name.endswith("-by-language.md")


def _markdown_files():
    return [path for path in skill_files() if path.suffix == ".md"]


def _h2(body: str) -> list[str]:
    return [heading for heading in sections(body) if heading.startswith("## ")]


def test_skills_directory_holds_skills():
    assert SKILLS, "no skills/<name>/SKILL.md found"
    for child in SKILLS_DIR.iterdir():
        if child.is_dir():
            assert (child / "SKILL.md").is_file(), f"{child.name} has no SKILL.md"


@pytest.mark.parametrize("name", SKILLS)
def test_name_matches_directory(name):
    fields, _ = parse_skill(name)
    assert fields.get("name") == name


@pytest.mark.parametrize("name", SKILLS)
def test_description_is_quoted_and_says_when(name):
    description = parse_skill(name)[0].get("description", "")
    assert description.startswith('"Use when'), f"{name}: {description[:40]}"
    assert description.endswith('"') and len(description) > len('"Use when"')


@pytest.mark.parametrize("name", SKILLS)
def test_frontmatter_unquoted_values_hold_no_colon_space(name):
    for line in frontmatter_lines(name):
        value = line.partition(":")[2].strip()
        if value[:1] in ('"', "'"):
            assert value[-1] == value[0] and len(value) > 1, f"{name}: unterminated {line}"
        else:
            assert ": " not in value, f"{name}: unquoted value holds ': ' in {line}"


@pytest.mark.parametrize("name", SKILLS)
def test_body_opens_with_one_h1(name):
    headings = sections(parse_skill(name)[1])
    assert headings and headings[0].startswith("# "), f"{name}: first heading is not an H1"
    assert sum(1 for heading in headings if heading.startswith("# ")) == 1, f"{name}: several H1s"


@pytest.mark.parametrize("name", SKILLS)
def test_opens_with_when_it_applies_and_the_core_rule_and_closes_with_common_mistakes(name):
    level_two = _h2(parse_skill(name)[1])
    assert level_two[:1] == [OPENING_HEADING], f"{name}: first ## is not {OPENING_HEADING}"
    assert level_two[1:2] == [CORE_RULE_HEADING], f"{name}: second ## is not {CORE_RULE_HEADING}"
    assert level_two[-1] == CLOSING_HEADING, f"{name}: last ## is not {CLOSING_HEADING}"


@pytest.mark.parametrize("name", SKILLS)
def test_every_supporting_file_is_linked_from_its_skill(name):
    skill_dir = SKILLS_DIR / name
    _, body = parse_skill(name)
    linked = {(skill_dir / target).resolve() for target in local_links(body)}
    for path in skill_dir.rglob("*"):
        if path.is_file() and path.name != "SKILL.md":
            assert path.resolve() in linked, f"{name}: {path.relative_to(skill_dir)} is not linked"


def test_no_banned_term_outside_by_language_references():
    patterns = [(term, _term_pattern(term)) for term in BANNED_TERMS]
    found = []
    for path in _markdown_files():
        if _is_by_language_reference(path):
            continue
        text = path.read_text(encoding="utf-8")
        found += [f"{path.relative_to(SKILLS_DIR)}: {term}" for term, rx in patterns if rx.search(text)]
    assert not found, found


def test_every_relative_link_resolves():
    broken = []
    for path in _markdown_files():
        for target in local_links(path.read_text(encoding="utf-8")):
            if target and not (path.parent / target).exists():
                broken.append(f"{path.relative_to(SKILLS_DIR)} -> {target}")
    assert not broken, broken


def test_no_british_spelling_under_skills():
    found = []
    for path in skill_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            where = f"{path.relative_to(SKILLS_DIR)}:{number}"
            found += [f"{where}: {word}" for word in british_spellings(line)]
    assert not found, found


def test_credits_name_the_source_and_carry_the_mit_notice():
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert "helmedeiros/clean-code-skills" in credits
    for line in MIT_NOTICE:
        assert line in credits, f"CREDITS.md lacks: {line}"
