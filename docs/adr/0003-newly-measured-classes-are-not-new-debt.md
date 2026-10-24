# ADR-0003: A newly measured language is not new debt

## Status

Accepted, 2026-10-18.

## Context

Issue 9 made the class scan read C++ classes. A baseline recorded before that fix holds no C++ classes, so it
lists 0 wide classes. After the fix, an unchanged C++ project's tree measures 30 of them. Both `compare_items` and
`compare_totals` would report those as regressions ("new wide class", "total rose: wide_classes") on code
nobody touched. The ratchet would fail every project on its first check after the upgrade, for no change of
its own.

## Decision

**A wide class in a language the baseline did not scan is a neutral note, not a regression.**

- A snapshot records `class_scanners`, the sorted list of languages whose classes it scanned, and
  `class_languages`, a map from path to language for every file that holds a wide class.
- A baseline without `class_scanners` scanned Python only.
- When `debt check` compares, the wide classes whose file's language the baseline did not scan are set aside.
  They are listed under "newly measured, not new debt:", and the wide-class total is lowered to match. A wide
  class whose file has no recorded language is kept, so it is judged as measured.
- A scanner the baseline had and the current snapshot lacks is a regression, `class scanner missing: C++`.
  It is the same rule as a narrowed measurement scope: measuring less than the baseline did hides debt.
  The branch-baseline-versus-main check catches a hand edit that removes a scanner.

## Consequences

- Until someone runs `debt baseline`, the newly measured classes are outside the ratchet and can grow unseen.
  The report says so, with a hint to record them.
- The rule covers every future class scanner with no further change.
- The snapshot gains two fields but keeps `version: 1`. An old baseline loads and compares unchanged.
- A Python wide class added next to the newly measured ones still fails.

## Alternatives considered

- **Bump the snapshot version and refuse old baselines.** Rejected: it forces every project to re-baseline by
  hand before it can check anything.
- **Accept the regressions with `--accept`.** Rejected: it asks the user to approve debt that is not new, and
  it records a false reason in the history.
- **Key classes by language.** Rejected: it renames every existing key, so every recorded class would read as
  fixed and new at once.
