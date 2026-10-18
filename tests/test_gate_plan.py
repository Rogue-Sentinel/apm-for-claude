from pathlib import Path

from apm.gate_plan import promised_paths, structural_criteria

FIXTURE = Path(__file__).parent / "fixtures" / "gate" / "plan2_criteria.md"


def test_criteria_and_promised_paths() -> None:
    criteria = structural_criteria(FIXTURE.read_text(encoding="utf-8"))

    assert len(criteria) == 5
    assert criteria[0].startswith("Every runtime file is at most 200 lines")
    assert criteria[0].endswith("(`test_framework_meets_its_own_limits`).")
    assert criteria[4].endswith("and the PR says so.")
    assert promised_paths(criteria) == ["SKILL.md", "docs/coverage.md"]


def test_no_criteria_section_gives_no_criteria() -> None:
    assert structural_criteria("# Plan\n\n## Tasks\n- do it\n") == []


def test_only_the_first_matching_section_counts() -> None:
    text = "## Structural acceptance criteria\n- one\n## Other\n- two\n## Structural acceptance criteria (again)\n- three\n"

    assert structural_criteria(text) == ["one"]


def test_promised_paths_skip_spaces_wildcards_and_placeholders() -> None:
    criteria = ["`a b.md` `skills/*/SKILL.md` `docs/<name>.md` `docs/ok.md` `code.py` plain.md `docs/ok.md`"]

    assert promised_paths(criteria) == ["docs/ok.md"]
