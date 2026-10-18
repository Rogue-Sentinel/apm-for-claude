"""Class scanners in the debt ratchet: a language the baseline never measured is not new debt.

Works on snapshot dicts only. A snapshot lists the languages whose classes it scanned (`class_scanners`)
and the language of each file holding a wide class (`class_languages`). A baseline written before those
fields existed scanned Python only.
"""
from __future__ import annotations

from collections.abc import Mapping

LEGACY_CLASS_SCANNERS = ("Python",)


def class_path(key: str) -> str:
    """The file path of a class key such as `src/db.h::Database`."""
    return key.split("::", 1)[0]


def _scanners(snapshot: Mapping) -> set[str]:
    return set(snapshot.get("class_scanners", LEGACY_CLASS_SCANNERS))


def _unmeasured_language(key: str, languages: Mapping[str, str], scanned: set[str]) -> str:
    """The language of the class's file when the baseline did not scan it; empty when it did or is unknown."""
    language = languages.get(class_path(key), "")
    return language if language not in scanned else ""


def project_classes(base: Mapping, current: dict) -> tuple[dict, list[str], list[str]]:
    """`current` without the wide classes the base never measured, the regressions, and the notes."""
    scanned, languages, classes = _scanners(base), current.get("class_languages", {}), current.get("classes", {})
    missing = [f"class scanner missing: {name}" for name in sorted(scanned - _scanners(current))]
    newly = {key: _unmeasured_language(key, languages, scanned) for key in classes if key not in base.get("classes", {})}
    newly = {key: language for key, language in newly.items() if language}
    notes = [f"newly measured: {key} ({classes[key]} public methods; the baseline did not measure {language} classes)"
             for key, language in sorted(newly.items())]
    if not newly:
        return current, missing, notes
    kept = {key: n for key, n in classes.items() if key not in newly}
    return {**current, "classes": kept, "totals": {**current["totals"], "wide_classes": len(kept)}}, missing, notes
