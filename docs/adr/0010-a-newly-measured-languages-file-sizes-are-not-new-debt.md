# ADR-0010: A newly measured language's file sizes are not new debt

## Status

Accepted, 2026-10-24. Builds on ADR-0003.

## Context

Issue 10. Once QML files are measured for size, a baseline recorded before that, which never measured QML,
meets a 250-line `.qml` file. The ratchet would report "new over-limit file" and "total rose: long_files" and
fail every upgraded project on code nobody touched.

## Decision

**A long file in a language the baseline did not measure is a neutral note, not new debt. It stays outside
the ratchet until `debt baseline` records it.**

- The snapshot gains `measured_languages` (every language the tool measures, sorted) and `file_languages`
  (the language of each over-limit file). Both are optional on load, and a hand edit that breaks their shape
  is rejected.
- A baseline with no `measured_languages` measured the 22 languages listed in `LEGACY_LANGUAGES`.
- An over-limit file that the baseline does not list, in a language the baseline did not measure, is dropped
  from the comparison. `totals.long_files` and `totals.excess_file_lines` are recomputed from what is kept.
  The file is reported as `newly measured: <path> (<N> lines; the baseline did not measure <language> files)`.
- A file with no recorded language is judged as measured.
- A language the baseline measured and the current snapshot lacks is a regression:
  `language no longer measured: <name>`.
- After `debt baseline`, the file is listed, and growth fails like any other over-limit file.

## Consequences

- Newly measured files are outside the ratchet until `debt baseline` runs. The hint says so.
- The rule covers every future size-only language without further change.
- The snapshot stays at version 1, and a baseline written by apm 0.3.2 loads and compares unchanged.

## Alternatives considered

- **Bump the snapshot version.** Rejected, as in ADR-0003.
- **`--accept`.** Rejected, because it records a false reason: nothing got worse.
- **Key files by language.** Rejected, because it renames every recorded file.
