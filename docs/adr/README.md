# Architecture decision records

| Number | Decision | Status |
|--------|----------|--------|
| [0001](0001-lean-pacing-by-default.md) | Lean pacing is the default | Accepted, 2026-10-18 |
| [0002](0002-guard-threat-model.md) | The guard is a guardrail against a cooperative worker's mistakes, not a sandbox | Accepted, 2026-10-18 |
| [0003](0003-newly-measured-classes-are-not-new-debt.md) | A newly measured language is not new debt | Accepted, 2026-10-18 |
| [0004](0004-h-headers-are-cpp-when-their-code-is.md) | A `.h` header is C++ when its code holds a C++-only construct | Accepted, 2026-10-18 |
| [0005](0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md) | The guard reads an apm CLI call and a cat heredoc as data only where bash reads them literally | Accepted, 2026-10-18 |
| [0006](0006-the-main-session-writes-its-memory-folder.md) | The main session may write Claude Code's memory folder for its project, and a file-tool write outside the project cannot be approved | Accepted, 2026-10-18 |
