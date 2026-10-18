import json
from pathlib import Path

import pytest

import apm_cli
from apm.coverage import CoverageError, find_gaps, load_inventory, render_table, scan_source

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "standard" / "coverage.json"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "coverage"

VA_SKILLS = (
    "solid-single-responsibility solid-open-closed solid-liskov-substitution solid-interface-segregation "
    "solid-dependency-inversion hexagonal-ports-adapters hexagonal-domain-isolation oop-encapsulation "
    "oop-composition-over-inheritance fp-pure-functions fp-higher-order-functions fp-error-handling "
    "refactor-extract-method refactor-rename refactor-replace-conditional-with-polymorphism "
    "tdd-test-first tdd-red-green-refactor tdd-arrange-act-assert clean-code-boy-scout-rule "
    "clean-code-detect-smells branch-review"
).split()
VA_COMMANDS = ["clean-code-audit", "branch-review"]
SCORECARD = (
    "type-and-contract-safety state-management module-architecture entry-points-and-routing "
    "styling-and-presentation testing error-handling external-integration accessibility "
    "code-duplication developer-experience"
).split()
AUDIT = "tdd refactoring solid oop functional architecture hygiene report-format".split()
VA_RULES = (
    "function-limit file-limit public-method-reason mandatory-tdd no-skipped-tests no-waiting-tests "
    "regression-test-before-fix never-weaken-a-test extract-before-you-add refactor-and-behavior-apart "
    "structural-constraints-are-acceptance-criteria logic-does-not-move-sideways adrs honest-reporting "
    "debt-never-grows skills-are-invoked"
).split()
SUPERPOWERS = (
    "brainstorming diagnosing-superpowers dispatching-parallel-agents executing-plans "
    "finishing-a-development-branch receiving-code-review requesting-code-review subagent-driven-development "
    "systematic-debugging test-driven-development using-git-worktrees using-superpowers "
    "verification-before-completion writing-plans writing-skills"
).split()

EXPECTED = (
    [f"va-skill/{n}" for n in VA_SKILLS] + [f"va-command/{n}" for n in VA_COMMANDS]
    + [f"va-scorecard/{n}" for n in SCORECARD] + [f"va-audit/{n}" for n in AUDIT]
    + [f"va-rule/{n}" for n in VA_RULES] + [f"sp-skill/{n}" for n in SUPERPOWERS]
)


def _write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _item(item_id: str, source: str = "s", covers: list | None = None, source_path: str = "") -> dict:
    return {"id": item_id, "source": source, "what": item_id, "source_path": source_path,
            "covered_by": covers if covers is not None else [{"file": "a.md"}]}


def _inventory(*items: dict, scan: list | None = None, not_methodology: list | None = None) -> dict:
    source = {"id": "s", "title": "S", "origin": "o", "scan": scan or [], "not_methodology": not_methodology or []}
    return {"sources": [source], "items": list(items)}


def test_the_inventory_has_every_expected_item() -> None:
    ids = {item["id"] for item in load_inventory(INVENTORY)["items"]}

    assert [i for i in EXPECTED if i not in ids] == []
    assert (len(VA_SKILLS), len(VA_COMMANDS), len(SCORECARD), len(AUDIT), len(VA_RULES), len(SUPERPOWERS)) == (
        21, 2, 11, 8, 16, 15)


def test_no_gaps() -> None:
    assert find_gaps(load_inventory(INVENTORY), ROOT) == []


def test_rendered_table_is_current() -> None:
    table = render_table(load_inventory(INVENTORY))

    assert (ROOT / "docs" / "coverage.md").read_text(encoding="utf-8") == table
    assert table.rstrip().endswith("**Gaps: 0**")


def test_find_gaps_reports_missing_file_and_anchor(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Title\n\n## Real heading\nsome text here\n", encoding="utf-8")
    inventory = _inventory(
        _item("ok", covers=[{"file": "a.md", "anchor": "## Real heading"}, {"file": "a.md", "anchor": "text here"}]),
        _item("no-file", covers=[{"file": "gone.md"}]),
        _item("no-heading", covers=[{"file": "a.md", "anchor": "## Real"}]),
        _item("no-text", covers=[{"file": "a.md", "anchor": "absent words"}]),
        _item("no-cover", covers=[]),
    )

    gaps = find_gaps(inventory, tmp_path)

    assert [g.split(":")[0] for g in gaps] == ["no-file", "no-heading", "no-text", "no-cover"]


def test_load_rejects_duplicate_ids_and_unknown_source(tmp_path: Path) -> None:
    duplicate = _write(tmp_path / "dup.json", _inventory(_item("x"), _item("x")))
    unknown = _write(tmp_path / "unknown.json", _inventory(_item("y", source="nope")))
    empty = _write(tmp_path / "empty.json", _inventory(_item("z", covers=[])))

    for bad in (duplicate, unknown, empty):
        with pytest.raises(CoverageError):
            load_inventory(bad)


def test_scan_source_finds_uninventoried_and_missing() -> None:
    inventory = _inventory(
        _item("alpha", source_path="skills/alpha/SKILL.md"),
        _item("beta", source_path="skills/beta/SKILL.md"),
        _item("vanished", source_path="skills/vanished/SKILL.md"),
        scan=["skills/*/SKILL.md", "skills/*/references/*"],
        not_methodology=[{"path": "skills/gamma/SKILL.md", "reason": "not part of the method"}],
    )

    assert scan_source(inventory, "s", FIXTURE) == [
        "not inventoried: skills/beta/references/notes.md",
        "missing in source: skills/vanished/SKILL.md",
    ]


def test_cli_coverage_exit_codes(capsys) -> None:
    assert apm_cli.main(["coverage"]) == 0
    assert "Gaps: 0" in capsys.readouterr().out
    assert apm_cli.main(["coverage", "--table"]) == 0
    assert "**Gaps: 0**" in capsys.readouterr().out
    assert apm_cli.main(["coverage", "--source", f"sp-skills={FIXTURE}"]) == 1
    assert "missing in source" in capsys.readouterr().out
