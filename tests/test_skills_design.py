"""The design and architecture skills carry every heading the coverage inventory anchors to."""
import pytest

from skill_helpers import SKILLS_DIR, assert_sections, names_term, parse_skill, section as _section

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
        "dip-patterns.md", "examples-by-language.md",
    ),
    "object-design": (
        "encapsulation-checklist.md", "composition-patterns.md", "examples-by-language.md",
    ),
    "functional-core": (
        "purity-rules.md", "hof-patterns.md", "result-and-option.md", "examples-by-language.md",
    ),
    "clean-architecture": (
        "port-adapter-anatomy.md", "anti-corruption-layer.md", "examples-by-language.md",
    ),
}
TRIGGERS = {
    "solid": (
        "SRP", "OCP", "LSP", "ISP", "DIP", "single responsibility", "open-closed",
        "Liskov substitution", "interface segregation", "dependency inversion",
        "separation of concerns", "multiple reasons to change", "fat interfaces",
        "depending on abstractions", "decoupling", "inheritance hierarchies",
    ),
    "object-design": (
        "encapsulation", "information hiding", "exposing internal state", "public fields",
        "getter/setter abuse", "invariants", "composition over inheritance",
        "fragile base class", "combining behaviors",
    ),
    "clean-architecture": (
        "ports and adapters", "hexagonal architecture", "clean architecture boundaries",
        "separating infrastructure from the domain", "domain isolation",
        "anti-corruption layer", "keeping the domain pure", "infrastructure leakage",
    ),
    "functional-core": (
        "pure functions", "immutability", "referential transparency", "higher-order functions",
        "HOFs", "map, filter and reduce", "callbacks", "functional error handling",
        "Result, Either or Option", "Maybe monad", "replacing try-catch with types",
        "errors without exceptions",
    ),
}
EXAMPLE_NAMES = {
    "solid": (
        "`instanceof`", "`NotImplementedException`", "`pg`", "`mysql`", "`axios`", "`fs`",
        "PostgreSQL", "MongoDB",
    ),
    "object-design": (
        "`toString()`", "`ArrayList.get(index)`", "class extends Base", "React class components",
    ),
    "clean-architecture": (
        "`express`", "`pg`", "`axios`", "Express", "Fastify", "Commander", "yargs", "RabbitMQ",
        "Kafka", "PostgreSQL", "Stripe SDK", "Nodemailer", "Kotlin", "C#",
    ),
    "functional-core": (
        "`{ ...obj, field: value }`", "`[...items, newItem]`", "`[...items].sort()`", "`sort()`",
        "`splice()`", "`const`", "`Date.now()`", "`Math.random()`", "`process.env`",
    ),
}
DISTINCTIVE = {
    "solid": ("instanceof", "NotImplementedException", "MongoDB"),
    "object-design": ("toString", "ArrayList"),
    "clean-architecture": ("Fastify", "Nodemailer", "RabbitMQ", "Stripe SDK"),
    "functional-core": ("Date.now", "Math.random", "process.env"),
}
POINTERS = (
    ("solid", "SKILL.md", "## Liskov substitution"),
    ("solid", "SKILL.md", "## Dependency inversion"),
    ("object-design", "SKILL.md", "## Common mistakes"),
    ("object-design", "references/composition-patterns.md", "## 3. Delegation"),
    ("object-design", "references/composition-patterns.md", "## 4. Mixins and traits"),
    ("object-design", "references/composition-patterns.md",
     "## When inheritance is still appropriate"),
    ("clean-architecture", "SKILL.md", "## Ports and adapters"),
    ("clean-architecture", "references/port-adapter-anatomy.md", "## Adapters"),
    ("clean-architecture", "references/anti-corruption-layer.md", "## Mapping strategies"),
    ("functional-core", "SKILL.md", "## Pure functions"),
    ("functional-core", "references/purity-rules.md", "## The two rules"),
    ("functional-core", "references/purity-rules.md", "## Immutable updates"),
)
CLASS_SIZE_SIGNAL = ("about 200 lines", "judged by the reviewer, not measured")


def _text(name: str, *path: str) -> str:
    return (SKILLS_DIR / name).joinpath(*path).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """A section's text on one line, so a phrase wrapped across lines is still found."""
    return " ".join(_section(text, heading).split())


def _trigger_cases():
    return [(name, term) for name, terms in sorted(TRIGGERS.items()) for term in terms]


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


@pytest.mark.parametrize(("name", "term"), _trigger_cases())
def test_description_names_the_original_triggers(name, term):
    assert names_term(parse_skill(name)[0]["description"], term), f"{name}: {term}"


@pytest.mark.parametrize("name", sorted(EXAMPLE_NAMES))
def test_examples_by_language_keep_the_original_names(name):
    text = _text(name, "references", "examples-by-language.md")
    assert [term for term in EXAMPLE_NAMES[name] if term not in text] == []


@pytest.mark.parametrize("name", sorted(DISTINCTIVE))
def test_original_names_stay_in_the_by_language_files(name):
    files = [p for p in (SKILLS_DIR / name).rglob("*.md") if not p.name.endswith("-by-language.md")]
    leaks = [(p.name, term) for p in files for term in DISTINCTIVE[name]
             if names_term(p.read_text(encoding="utf-8"), term)]
    assert leaks == []


@pytest.mark.parametrize(("name", "path", "heading"), POINTERS)
def test_generic_wording_points_at_its_examples(name, path, heading):
    assert "examples-by-language.md" in section(_text(name, *path.split("/")), heading)


def test_hot_path_pitfall_names_performance_critical_paths():
    body = " ".join(parse_skill("functional-core")[1].split())
    assert "performance-critical hot path" in body
    assert "measured hot path immutable" not in body


def test_srp_indicators_carry_the_class_size_signal():
    structure = section(_text("solid", "references", "srp-indicators.md"), "### In the structure")
    for phrase in CLASS_SIZE_SIGNAL:
        assert phrase in structure


def test_credits_say_where_the_original_names_are_kept():
    assert "examples-by-language.md" in (SKILLS_DIR / "CREDITS.md").read_text(encoding="utf-8")
