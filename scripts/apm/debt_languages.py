"""File sizes in the debt ratchet: a language the baseline never measured is not new debt.

Works on snapshot dicts only. A snapshot lists the languages it measured (`measured_languages`) and the
language of each over-limit file (`file_languages`). A baseline written before those fields existed
measured the languages in `LEGACY_LANGUAGES`.
"""
from __future__ import annotations

from collections.abc import Mapping

LEGACY_LANGUAGES = (
    "C", "C#", "C++", "Dart", "Go", "Java", "JavaScript", "Kotlin", "Lua", "Objective-C", "PHP", "Perl",
    "PowerShell", "Python", "R", "Ruby", "Rust", "SQL", "Scala", "Shell", "Swift", "TypeScript",
)


def _measured(snapshot: Mapping) -> set[str]:
    return set(snapshot.get("measured_languages", LEGACY_LANGUAGES))


def _newly_measured(base: Mapping, current: Mapping, measured: set[str]) -> dict[str, str]:
    """The over-limit files the base did not list, mapped to their language, when the base did not measure it."""
    languages, recorded = current.get("file_languages", {}), base.get("files", {})
    found = {path: languages.get(path, "") for path in current.get("files", {}) if path not in recorded}
    return {path: language for path, language in found.items() if language and language not in measured}


def _without(current: dict, dropped: Mapping) -> dict:
    kept = {path: n for path, n in current["files"].items() if path not in dropped}
    limit = current["limits"]["file"]
    totals = {**current["totals"], "long_files": len(kept), "excess_file_lines": sum(n - limit for n in kept.values())}
    return {**current, "files": kept, "totals": totals}


def project_languages(base: Mapping, current: dict) -> tuple[dict, list[str], list[str]]:
    """`current` without the long files the base never measured, the regressions, and the notes."""
    measured = _measured(base)
    missing = [f"language no longer measured: {name}" for name in sorted(measured - _measured(current))]
    newly = _newly_measured(base, current, measured)
    notes = [f"newly measured: {path} ({current['files'][path]} lines; the baseline did not measure {language} files)"
             for path, language in sorted(newly.items())]
    return (_without(current, newly) if newly else current), missing, notes
