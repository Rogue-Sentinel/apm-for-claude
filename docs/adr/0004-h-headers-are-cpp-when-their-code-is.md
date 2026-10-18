# ADR-0004: A `.h` header is C++ when its code holds a C++-only construct

## Status

Accepted, 2026-10-18.

## Context

Issue 9 found that `.h` mapped to C, so every C++ header was skipped by the class scan. Public methods were
never counted for the classes that live in headers. C and C++ function scanning is identical, so the language
a file is given decides only two things: whether the class scan runs, and the label the report shows.

A `.h` file is ambiguous. It can be a C header or a C++ one, and the extension does not say which.

## Decision

**A file ending in `.h` (any case) is read as C++ when its code holds a C++-only construct. Otherwise it stays C.**

The check runs on the file's code after comments, string contents and preprocessor lines are removed, so the
words `class` or `namespace` in a comment or a string do not count, and neither does an `#ifdef __cplusplus` /
`extern "C" {` wrapper. The C++ markers are:

- a line starting with `template` and then `<`;
- `namespace`, an optional name (with `::`), and `{`;
- `using namespace`;
- `class Name`, then anything except `;`, `{`, `(` or `=`, and then `{`;
- a line that is only `public`, `protected` or `private` followed by a single `:`.

Only `.h` files are checked. `language_for(path)` is unchanged, so file selection stays path-only and `.h` still
selects as a brace-language file. `language_of(path, text)` is the content-aware lookup that `measure_text` uses.

## Consequences

- **No configuration.** A project does not list its C++ headers anywhere.
- **A C header misread as C++ costs only its label.** A C struct has no methods, and function pointers are not
  counted, so no false wide class appears.
- **A C++ header with no marker is read as C and its classes are missed.** One that holds only a `struct` with
  methods is the example. The "not measured" line does not catch it, because C has no class scanner and is not
  listed as class-unmeasured.
- A header with a marker is measured the same way as a `.hpp` file.

## Alternatives considered

- **A profile setting that lists the C++ headers.** Rejected: it needs configuration in every project, and it
  goes stale as files are added.
- **Read every `.h` as C++ when the repository holds other C++ files.** Rejected: a mixed repository with C
  headers would label them wrongly, and the answer would change when an unrelated file is added.
- **Always read `.h` as C++.** Rejected: it would label every C project's headers as C++ and run a class scan
  on code that has no classes.
