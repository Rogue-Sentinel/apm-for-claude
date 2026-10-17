"""The plugin agent definitions carry the right frontmatter and body."""
from pathlib import Path

import pytest

from apm.profile import DEFAULT_MODELS

AGENTS = Path(__file__).resolve().parent.parent / "agents"
WORKERS = tuple(DEFAULT_MODELS)
MANAGER_HEADINGS = (
    "## Your role",
    "## Talking to the user",
    "## Dispatching workers",
    "## Verifying work",
    "## Recording state",
    "## Safety",
)
REPORT_ITEMS = ("status", "files changed", "commands run", "concerns", "found elsewhere")
ALL_AGENTS = ("manager", *WORKERS)


def parse(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", f"{path.name}: no frontmatter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, "\n".join(lines[end + 1:])


def field_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@pytest.mark.parametrize("name", ALL_AGENTS)
def test_name_matches_stem_and_description_present(name):
    fields, _ = parse(AGENTS / f"{name}.md")
    assert fields["name"] == name
    assert fields.get("description", "").strip()


def test_manager_model_inherit_and_may_dispatch():
    fields, _ = parse(AGENTS / "manager.md")
    assert fields["model"] == "inherit"
    if "tools" in fields:
        assert "Agent" in field_list(fields["tools"])


@pytest.mark.parametrize("name", WORKERS)
def test_worker_model_and_cannot_dispatch(name):
    fields, _ = parse(AGENTS / f"{name}.md")
    assert fields["model"] == DEFAULT_MODELS[name]
    assert "Agent" in field_list(fields["disallowedTools"])


def test_manager_body_has_required_headings():
    _, body = parse(AGENTS / "manager.md")
    for heading in MANAGER_HEADINGS:
        assert heading in body, f"manager missing {heading}"


@pytest.mark.parametrize("name", WORKERS)
def test_worker_report_format_lists_every_item(name):
    _, body = parse(AGENTS / f"{name}.md")
    marker = "## Report format"
    assert marker in body, f"{name} missing {marker}"
    section = body[body.index(marker):]
    for item in REPORT_ITEMS:
        assert item in section, f"{name} report format missing '{item}'"
