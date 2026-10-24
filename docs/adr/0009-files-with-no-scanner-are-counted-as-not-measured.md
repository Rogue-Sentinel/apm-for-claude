# ADR-0009: Files with no scanner are counted as not measured

## Status

Accepted, 2026-10-24. Builds on ADR-0003.

## Context

Issue 10. A project's 82 QML files, 4 CMake files and an Inno Setup script vanished from the metrics report,
which then read `0 of 0`. The tool had no language for them, so it dropped them without a word, and a report
that says nothing was over the limits looked the same as a report that measured nothing.

## Decision

**A tracked, in-scope file with no language is counted as not measured, and the count is printed on every
report.**

- The file is counted unless it is one of these: a doc, data or config file by name, a dotfile, a binary by
  extension, a binary by content (a NUL byte in the first 8000 bytes, unless the file starts with a UTF-16
  byte-order mark), or empty.
- The report ends with `Files not measured: N`, then one row per kind (`.qrc: 2`). It is printed with 0 too.
  The JSON report carries `files_not_measured` and the `not_measured` paths.
- Only files the profile's scope includes are listed. An excluded file, or one outside the `PATH` arguments,
  never appears. `metrics --ref` lists the same files as the working tree does.
- The count stays **out of the debt snapshot**. It is not debt the code can pay down, and a new not-measured
  file could be "fixed" by narrowing the scope, which the ratchet already treats as a regression, or by the
  tool gaining a language.
- QML, Inno Setup and CMake files are now measured for size only. As in ADR-0010, a long file in a language
  the baseline did not measure is a neutral note, not new debt.

## Consequences

- Unknown kinds (`.html`, `.css`, `.qrc`, a script with a shebang line) are listed. The user can add an
  exclude under `standard.metrics`, or file an issue asking for the language.
- Each candidate file is read once more.
- The lists of names and extensions are fixed. A `.txt` file that holds source counts as not code.

## Alternatives considered

- **Count every text file.** Rejected: docs and data would drown the line.
- **List only known code extensions.** Rejected: it repeats the silent drop for any extension not listed.
- **Add the count to the ratchet.** Rejected, for the reason under Decision.
