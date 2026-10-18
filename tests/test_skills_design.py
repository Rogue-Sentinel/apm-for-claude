"""The design and architecture skills carry every heading the coverage inventory anchors to."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, parse_skill

REQUIRED = {
    "solid": (
        "## Single responsibility", "## Open-closed", "## Liskov substitution",
        "## Interface segregation", "## Dependency inversion",
    ),
    "object-design": (
        "## Encapsulation", "## Composition over inheritance", "## Seven or more public methods",
    ),
    "functional-core": (
        "## Pure functions", "## Higher-order functions", "## Absence and failure are values",
        "## Time and randomness are parameters",
    ),
    "clean-architecture": (
        "## The dependency rule", "## Ports and adapters", "## Domain isolation",
        "## Testing at the edges", "## The layer map",
    ),
}
REFERENCES = {
    "solid": (
        "srp-indicators.md", "ocp-strategies.md", "lsp-violations.md", "isp-patterns.md",
        "dip-patterns.md",
    ),
    "object-design": ("encapsulation-checklist.md", "composition-patterns.md"),
    "functional-core": ("purity-rules.md", "hof-patterns.md", "result-and-option.md"),
    "clean-architecture": ("port-adapter-anatomy.md", "anti-corruption-layer.md"),
}


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_skill_has_its_required_headings(name):
    assert_sections(name, REQUIRED[name])


@pytest.mark.parametrize("name", sorted(REFERENCES))
def test_skill_has_its_named_references(name):
    for file_name in REFERENCES[name]:
        assert (SKILLS_DIR / name / "references" / file_name).is_file(), f"{name}: {file_name}"


def test_public_method_limit_comes_from_the_profile():
    _, body = parse_skill("object-design")
    assert "`standard.limits.public_methods`" in body
    assert "default 7" in body


def test_layer_map_comes_from_the_profile():
    _, body = parse_skill("clean-architecture")
    assert "`standard.layers`" in body


def test_layer_map_names_both_reserved_import_names():
    _, body = parse_skill("clean-architecture")
    assert '"outside"' in body
    assert '"*"' in body


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_credits_name_the_skill(name):
    credits = (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
    assert f"| `{name}` |" in credits, f"CREDITS.md has no row for {name}"
